"""
Configuration management for CommitForge.

Supports TOML-style configuration files with project-level and user-level
config locations. CLI flags override config file settings. Environment
variables provide an additional override layer.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ─── Constants ────────────────────────────────────────────────────────────────

PROJECT_CONFIG_FILE = ".commitforge.toml"
USER_CONFIG_DIR = ".config/commitforge"
USER_CONFIG_FILE = "config.toml"

DEFAULT_CONFIG = {
    "backend": "rules",
    "language": "en",
    "default_type": "",
    "default_scope": "",
    "emoji": False,
    "max_body_length": 72,
    "max_subject_length": 72,
    "history_count": 50,
    "dry_run": False,
    "verbose": False,
    "openai": {
        "api_key": "",
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": 512,
    },
    "anthropic": {
        "api_key": "",
        "model": "claude-sonnet-4-20250514",
        "base_url": "https://api.anthropic.com",
        "temperature": 0.7,
        "max_tokens": 512,
    },
    "deepseek": {
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "temperature": 0.7,
        "max_tokens": 512,
    },
    "ollama": {
        "model": "llama3",
        "base_url": "http://localhost:11434",
        "temperature": 0.7,
        "max_tokens": 512,
    },
    "gemini": {
        "api_key": "",
        "model": "gemini-2.0-flash",
        "temperature": 0.7,
        "max_tokens": 512,
    },
    "scope_rules": {
        "src/": "core",
        "lib/": "lib",
        "tests/": "test",
        "test/": "test",
        "docs/": "docs",
        "examples/": "examples",
        "scripts/": "scripts",
        "tools/": "tools",
        "config/": "config",
        "assets/": "assets",
        "pkg/": "pkg",
        "cmd/": "cmd",
        "api/": "api",
        "web/": "web",
        "ui/": "ui",
        "app/": "app",
        "middleware/": "middleware",
        "routes/": "routes",
        "models/": "models",
        "views/": "views",
        "controllers/": "controllers",
        "services/": "services",
        "handlers/": "handlers",
        "utils/": "utils",
        "helpers/": "helpers",
        "internal/": "internal",
        "cmd/": "cmd",
    },
    "custom_templates": {},
    "system_prompt": "",
    "retry_count": 3,
    "retry_delay": 1.0,
}

# Environment variable mapping
ENV_MAP = {
    "COMMITFORGE_BACKEND": "backend",
    "COMMITFORGE_LANGUAGE": "language",
    "COMMITFORGE_DEFAULT_TYPE": "default_type",
    "COMMITFORGE_DEFAULT_SCOPE": "default_scope",
    "COMMITFORGE_API_KEY": "openai.api_key",
    "COMMITFORGE_OPENAI_API_KEY": "openai.api_key",
    "COMMITFORGE_OPENAI_MODEL": "openai.model",
    "COMMITFORGE_OPENAI_BASE_URL": "openai.base_url",
    "COMMITFORGE_ANTHROPIC_API_KEY": "anthropic.api_key",
    "COMMITFORGE_ANTHROPIC_MODEL": "anthropic.model",
    "COMMITFORGE_DEEPSEEK_API_KEY": "deepseek.api_key",
    "COMMITFORGE_DEEPSEEK_MODEL": "deepseek.model",
    "COMMITFORGE_OLLAMA_MODEL": "ollama.model",
    "COMMITFORGE_OLLAMA_BASE_URL": "ollama.base_url",
    "COMMITFORGE_GEMINI_API_KEY": "gemini.api_key",
    "COMMITFORGE_GEMINI_MODEL": "gemini.model",
    "COMMITFORGE_EMOJI": "emoji",
    "COMMITFORGE_VERBOSE": "verbose",
    "COMMITFORGE_DRY_RUN": "dry_run",
}


# ─── TOML Parser (minimal, stdlib-only) ──────────────────────────────────────

def _parse_toml(text: str) -> Dict[str, Any]:
    """Parse a minimal TOML file into a dictionary.

    Supports basic TOML features: strings, integers, floats, booleans,
    arrays, and nested tables (sections).

    Args:
        text: TOML file content as string.

    Returns:
        Parsed dictionary.
    """
    result: Dict[str, Any] = {}
    current_section: List[str] = []
    current_table: Dict[str, Any] = result

    for line in text.split("\n"):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue

        # Section header [section] or [section.subsection]
        section_match = re.match(r"^\[([^\]]+)\]$", stripped)
        if section_match:
            section_path = section_match.group(1).strip().split(".")
            current_section = section_path
            current_table = result
            for part in section_path:
                if part not in current_table:
                    current_table[part] = {}
                current_table = current_table[part]
            continue

        # Key-value pair
        kv_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$', stripped)
        if kv_match:
            key = kv_match.group(1)
            value_str = kv_match.group(2).strip()
            current_table[key] = _parse_toml_value(value_str)

    return result


def _parse_toml_value(value_str: str) -> Any:
    """Parse a single TOML value.

    Args:
        value_str: The value string to parse.

    Returns:
        Parsed Python value.
    """
    value_str = value_str.strip()

    # Boolean
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False

    # Integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Float
    try:
        return float(value_str)
    except ValueError:
        pass

    # String (double-quoted)
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t")

    # String (single-quoted, literal)
    if value_str.startswith("'") and value_str.endswith("'"):
        return value_str[1:-1]

    # Array
    if value_str.startswith("[") and value_str.endswith("]"):
        inner = value_str[1:-1].strip()
        if not inner:
            return []
        items: List[Any] = []
        current = ""
        in_string = False
        string_char = ""
        for ch in inner:
            if ch in ('"', "'") and not in_string:
                in_string = True
                string_char = ch
                current += ch
            elif ch == string_char and in_string:
                in_string = False
                current += ch
            elif ch == "," and not in_string:
                items.append(_parse_toml_value(current.strip()))
                current = ""
            else:
                current += ch
        if current.strip():
            items.append(_parse_toml_value(current.strip()))
        return items

    # Fallback: return as string
    return value_str


def _serialize_toml(data: Dict[str, Any], indent: int = 0) -> str:
    """Serialize a dictionary to TOML format.

    Args:
        data: The dictionary to serialize.
        indent: Current indentation level.

    Returns:
        TOML-formatted string.
    """
    lines: List[str] = []
    prefix = ""

    for key, value in data.items():
        if isinstance(value, dict):
            # Write as a section
            lines.append(f"\n[{key}]")
            lines.append(_serialize_toml(value, indent=2))
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key} = {'true' if value else 'false'}")
        elif isinstance(value, str):
            # Escape special characters
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
            lines.append(f'{prefix}{key} = "{escaped}"')
        elif isinstance(value, (int, float)):
            lines.append(f"{prefix}{key} = {value}")
        elif isinstance(value, list):
            items = []
            for item in value:
                if isinstance(item, str):
                    items.append(f'"{item}"')
                elif isinstance(item, bool):
                    items.append("true" if item else "false")
                else:
                    items.append(str(item))
            lines.append(f"{prefix}{key} = [{', '.join(items)}]")

    return "\n".join(lines)


# ─── Deep merge utility ───────────────────────────────────────────────────────

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries. Override values take precedence.

    Args:
        base: Base dictionary.
        override: Override dictionary.

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _set_nested(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set a value in a nested dictionary using dot notation.

    Args:
        data: The dictionary to modify.
        path: Dot-separated path (e.g., 'openai.api_key').
        value: The value to set.
    """
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _get_nested(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get a value from a nested dictionary using dot notation.

    Args:
        data: The dictionary to read.
        path: Dot-separated path (e.g., 'openai.api_key').
        default: Default value if path not found.

    Returns:
        The value at the path, or default.
    """
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


# ─── Config Class ─────────────────────────────────────────────────────────────

class Config:
    """Configuration manager for CommitForge.

    Loads configuration from multiple sources with the following priority
    (highest to lowest):
    1. CLI flags (passed explicitly)
    2. Environment variables
    3. Project-level config (.commitforge.toml)
    4. User-level config (~/.config/commitforge/config.toml)
    5. Built-in defaults
    """

    def __init__(self, cli_overrides: Optional[Dict[str, Any]] = None):
        """Initialize configuration.

        Args:
            cli_overrides: Dictionary of CLI flag overrides.
        """
        self._data: Dict[str, Any] = {}
        self._cli_overrides = cli_overrides or {}
        self._project_root: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load configuration from all sources in priority order."""
        # Start with defaults
        import copy
        self._data = copy.deepcopy(DEFAULT_CONFIG)

        # Load user-level config
        user_config = self._load_user_config()
        if user_config:
            self._data = _deep_merge(self._data, user_config)

        # Detect project root and load project-level config
        self._project_root = self._find_project_root()
        if self._project_root:
            project_config = self._load_project_config(self._project_root)
            if project_config:
                self._data = _deep_merge(self._data, project_config)

        # Apply environment variable overrides
        self._apply_env_overrides()

        # Apply CLI overrides
        if self._cli_overrides:
            self._data = _deep_merge(self._data, self._cli_overrides)

    def _find_project_root(self) -> Optional[str]:
        """Find the project root by searching for .git directory.

        Returns:
            Path to project root, or None if not found.
        """
        current = os.getcwd()
        while current != os.path.dirname(current):
            if os.path.isdir(os.path.join(current, ".git")):
                return current
            current = os.path.dirname(current)
        return None

    def _load_user_config(self) -> Optional[Dict[str, Any]]:
        """Load user-level configuration file.

        Returns:
            Parsed config dictionary, or None if file doesn't exist.
        """
        home = os.path.expanduser("~")
        config_path = os.path.join(home, USER_CONFIG_DIR, USER_CONFIG_FILE)

        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return _parse_toml(content)
            except (IOError, OSError) as e:
                import sys
                print(f"Warning: Failed to read user config: {e}", file=sys.stderr)
        return None

    def _load_project_config(self, project_root: str) -> Optional[Dict[str, Any]]:
        """Load project-level configuration file.

        Args:
            project_root: Path to the project root directory.

        Returns:
            Parsed config dictionary, or None if file doesn't exist.
        """
        config_path = os.path.join(project_root, PROJECT_CONFIG_FILE)

        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return _parse_toml(content)
            except (IOError, OSError) as e:
                import sys
                print(f"Warning: Failed to read project config: {e}", file=sys.stderr)
        return None

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        for env_var, config_path in ENV_MAP.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Handle boolean conversion
                if value.lower() in ("true", "1", "yes"):
                    value = True
                elif value.lower() in ("false", "0", "no"):
                    value = False
                _set_nested(self._data, config_path, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.

        Args:
            key: Dot-separated configuration key.
            default: Default value if key not found.

        Returns:
            The configuration value.
        """
        return _get_nested(self._data, key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation.

        Args:
            key: Dot-separated configuration key.
            value: Value to set.
        """
        _set_nested(self._data, key, value)

    @property
    def data(self) -> Dict[str, Any]:
        """Return the full configuration dictionary."""
        return self._data

    @property
    def project_root(self) -> Optional[str]:
        """Return the detected project root path."""
        return self._project_root

    @property
    def backend(self) -> str:
        """Return the configured AI backend name."""
        return str(self.get("backend", "rules"))

    @property
    def language(self) -> str:
        """Return the configured output language."""
        return str(self.get("language", "en"))

    @property
    def use_emoji(self) -> bool:
        """Return whether emoji should be used in commit messages."""
        return bool(self.get("emoji", False))

    @property
    def is_verbose(self) -> bool:
        """Return whether verbose output is enabled."""
        return bool(self.get("verbose", False))

    @property
    def is_dry_run(self) -> bool:
        """Return whether dry-run mode is enabled."""
        return bool(self.get("dry_run", False))

    def get_backend_config(self, backend_name: str) -> Dict[str, Any]:
        """Get configuration for a specific AI backend.

        Args:
            backend_name: Name of the backend (e.g., 'openai', 'anthropic').

        Returns:
            Backend-specific configuration dictionary.
        """
        config = self.get(backend_name, {})
        if not isinstance(config, dict):
            return {}
        return config

    def save_project_config(self, path: Optional[str] = None) -> str:
        """Save current configuration to a project-level config file.

        Args:
            path: Optional custom path. Defaults to project root.

        Returns:
            Path where the config was saved.
        """
        if path is None:
            if self._project_root:
                path = os.path.join(self._project_root, PROJECT_CONFIG_FILE)
            else:
                path = os.path.join(os.getcwd(), PROJECT_CONFIG_FILE)

        toml_content = _serialize_toml(self._data)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# CommitForge Configuration\n")
            f.write(toml_content)
            f.write("\n")

        return path

    def save_user_config(self) -> str:
        """Save current configuration to user-level config file.

        Returns:
            Path where the config was saved.
        """
        home = os.path.expanduser("~")
        config_dir = os.path.join(home, USER_CONFIG_DIR)
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, USER_CONFIG_FILE)

        toml_content = _serialize_toml(self._data)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# CommitForge User Configuration\n")
            f.write(toml_content)
            f.write("\n")

        return config_path

    def show(self) -> str:
        """Generate a human-readable display of current configuration.

        Returns:
            Formatted configuration string.
        """
        from .utils import Table, dim, bold, cyan

        lines: List[str] = []
        lines.append(bold(cyan("CommitForge Configuration")))
        lines.append(dim("─" * 40))
        lines.append("")

        # General settings
        lines.append(bold("General:"))
        lines.append(f"  Backend:     {self.backend}")
        lines.append(f"  Language:    {self.language}")
        lines.append(f"  Emoji:       {'enabled' if self.use_emoji else 'disabled'}")
        lines.append(f"  Dry run:     {'yes' if self.is_dry_run else 'no'}")
        lines.append(f"  Verbose:     {'yes' if self.is_verbose else 'no'}")
        lines.append(f"  History:     last {self.get('history_count', 50)} commits")
        lines.append("")

        # Backend configs
        for backend_name in ["openai", "anthropic", "deepseek", "ollama", "gemini"]:
            backend_config = self.get_backend_config(backend_name)
            if not backend_config:
                continue
            lines.append(bold(f"  {backend_name}:"))
            for k, v in backend_config.items():
                if "key" in k.lower() and v:
                    display_val = v[:6] + "..." + v[-4:] if len(str(v)) > 12 else "***"
                else:
                    display_val = str(v)
                lines.append(f"    {k}: {display_val}")
        lines.append("")

        # Config file locations
        lines.append(bold("Config files:"))
        if self._project_root:
            project_config = os.path.join(self._project_root, PROJECT_CONFIG_FILE)
            exists = os.path.isfile(project_config)
            lines.append(f"  Project: {project_config} {'(exists)' if exists else '(not found)'}")
        else:
            lines.append("  Project: (not in a git repository)")

        home = os.path.expanduser("~")
        user_config = os.path.join(home, USER_CONFIG_DIR, USER_CONFIG_FILE)
        exists = os.path.isfile(user_config)
        lines.append(f"  User:    {user_config} {'(exists)' if exists else '(not found)'}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as a plain dictionary.

        Returns:
            Copy of the configuration data.
        """
        import copy
        return copy.deepcopy(self._data)


def create_default_config(path: Optional[str] = None) -> str:
    """Create a default configuration file.

    Args:
        path: Optional path for the config file. Defaults to .commitforge.toml
              in the current directory.

    Returns:
        Path where the config file was created.
    """
    if path is None:
        path = os.path.join(os.getcwd(), PROJECT_CONFIG_FILE)

    config_content = """# CommitForge Configuration
# This file controls the behavior of CommitForge in this project.

[backend]
# AI backend: "rules" (offline), "openai", "anthropic", "deepseek", "ollama", "gemini"
backend = "rules"

# Output language: "en" for English, "zh" for Chinese
language = "en"

# Enable emoji in commit messages
emoji = false

# Maximum subject line length
max_subject_length = 72

# Maximum body line length
max_body_length = 72

# Number of recent commits to analyze for history
history_count = 50

# Retry settings for AI backends
retry_count = 3
retry_delay = 1.0

[openai]
api_key = ""
model = "gpt-4o-mini"
base_url = "https://api.openai.com/v1"
temperature = 0.7
max_tokens = 512

[anthropic]
api_key = ""
model = "claude-sonnet-4-20250514"
base_url = "https://api.anthropic.com"
temperature = 0.7
max_tokens = 512

[deepseek]
api_key = ""
model = "deepseek-chat"
base_url = "https://api.deepseek.com/v1"
temperature = 0.7
max_tokens = 512

[ollama]
model = "llama3"
base_url = "http://localhost:11434"
temperature = 0.7
max_tokens = 512

[gemini]
api_key = ""
model = "gemini-2.0-flash"
temperature = 0.7
max_tokens = 512

[scope_rules]
src/ = "core"
lib/ = "lib"
tests/ = "test"
test/ = "test"
docs/ = "docs"
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(config_content)

    return path
