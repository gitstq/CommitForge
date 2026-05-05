"""
Conventional Commits parser and validator for CommitForge.

Implements the Conventional Commits v1.0.0 specification:
https://www.conventionalcommits.org/en/v1.0.0/

Provides parsing, validation, and fix suggestions for commit messages.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ─── Constants ────────────────────────────────────────────────────────────────

# Standard conventional commit types
STANDARD_TYPES = [
    "feat", "fix", "docs", "style", "refactor",
    "perf", "test", "build", "ci", "chore", "revert",
]

# Type descriptions (English)
TYPE_DESCRIPTIONS_EN = {
    "feat": "A new feature",
    "fix": "A bug fix",
    "docs": "Documentation only changes",
    "style": "Changes that do not affect the meaning of the code",
    "refactor": "A code change that neither fixes a bug nor adds a feature",
    "perf": "A code change that improves performance",
    "test": "Adding missing tests or correcting existing tests",
    "build": "Changes that affect the build system or external dependencies",
    "ci": "Changes to CI configuration files and scripts",
    "chore": "Other changes that don't modify src or test files",
    "revert": "Reverts a previous commit",
}

# Type descriptions (Chinese)
TYPE_DESCRIPTIONS_ZH = {
    "feat": "新功能",
    "fix": "修复 Bug",
    "docs": "文档变更",
    "style": "代码格式调整（不影响代码含义）",
    "refactor": "代码重构（既不是修复 Bug 也不是添加功能）",
    "perf": "性能优化",
    "test": "添加或修正测试",
    "build": "构建系统或外部依赖变更",
    "ci": "CI 配置文件和脚本变更",
    "chore": "其他不修改源码或测试的变更",
    "revert": "回退之前的提交",
}

# Emoji mapping for commit types
TYPE_EMOJIS = {
    "feat": "✨",
    "fix": "🐛",
    "docs": "📝",
    "style": "💄",
    "refactor": "♻️",
    "perf": "⚡",
    "test": "✅",
    "build": "📦",
    "ci": "👷",
    "chore": "🔧",
    "revert": "⏪",
}

# Regex patterns for parsing conventional commits
# Pattern: type(scope)?: description
# Optional ! after type for breaking changes
COMMIT_PATTERN = re.compile(
    r"^(?P<type>[a-z]+)"
    r"(?:\((?P<scope>[a-zA-Z0-9\-_.]+)\))?"
    r"(?P<breaking_marker>!)?"
    r"\s*:\s*(?P<description>.+)$"
)

# Pattern for BREAKING CHANGE in body/footers
BREAKING_CHANGE_PATTERN = re.compile(
    r"^BREAKING[ -]CHANGE:\s*(.+)$",
    re.MULTILINE
)

# Pattern for footers (key-value)
FOOTER_PATTERN = re.compile(
    r"^(?P<key>[a-zA-Z-]+)(?:\s*:\s*(?P<value>.+)|\s+#(?P<value_ref>.+))$"
)

# Maximum recommended lengths
MAX_SUBJECT_LENGTH = 72
MAX_BODY_LINE_LENGTH = 72


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class ConventionalCommit:
    """Parsed representation of a conventional commit message.

    Attributes:
        type: The commit type (e.g., 'feat', 'fix').
        scope: Optional scope (e.g., 'api', 'core').
        description: The short description.
        body: Optional body text.
        footers: List of footer key-value pairs.
        breaking_change: Whether this is a breaking change.
        breaking_description: Description of the breaking change.
        raw: The original raw commit message.
    """
    type: str
    description: str
    scope: Optional[str] = None
    body: Optional[str] = None
    footers: List[Tuple[str, str]] = field(default_factory=list)
    breaking_change: bool = False
    breaking_description: Optional[str] = None
    raw: str = ""

    @property
    def subject(self) -> str:
        """Return the formatted subject line (type(scope): description)."""
        if self.scope:
            marker = "!" if self.breaking_change else ""
            return f"{self.type}{marker}({self.scope}): {self.description}"
        else:
            marker = "!" if self.breaking_change else ""
            return f"{self.type}{marker}: {self.description}"

    def format(self, include_body: bool = True, include_footers: bool = True,
               emoji: bool = False) -> str:
        """Format the commit message as a string.

        Args:
            include_body: Whether to include the body.
            include_footers: Whether to include footers.
            emoji: Whether to prepend type emoji.

        Returns:
            Formatted commit message string.
        """
        lines: List[str] = []

        # Subject line
        type_prefix = self.type
        if emoji and self.type in TYPE_EMOJIS:
            type_prefix = f"{TYPE_EMOJIS[self.type]} {self.type}"

        if self.scope:
            marker = "!" if self.breaking_change else ""
            lines.append(f"{type_prefix}{marker}({self.scope}): {self.description}")
        else:
            marker = "!" if self.breaking_change else ""
            lines.append(f"{type_prefix}{marker}: {self.description}")

        # Body
        if include_body and self.body:
            lines.append("")
            lines.append(self.body.strip())

        # Footers
        if include_footers and self.footers:
            if self.body:
                lines.append("")
            for key, value in self.footers:
                lines.append(f"{key}: {value}")

        return "\n".join(lines)


@dataclass
class ValidationResult:
    """Result of validating a commit message.

    Attributes:
        is_valid: Whether the message is valid.
        errors: List of error messages.
        warnings: List of warning messages.
        suggestions: List of fix suggestions.
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_suggestion(self, message: str) -> None:
        """Add a fix suggestion."""
        self.suggestions.append(message)


# ─── Parser ───────────────────────────────────────────────────────────────────

def parse_commit(message: str) -> Optional[ConventionalCommit]:
    """Parse a commit message into a ConventionalCommit object.

    Args:
        message: The raw commit message string.

    Returns:
        Parsed ConventionalCommit, or None if the format is invalid.
    """
    if not message or not message.strip():
        return None

    # Normalize line endings
    message = message.replace("\r\n", "\n").strip()

    # Split into subject, body, and footers
    lines = message.split("\n")

    if not lines:
        return None

    subject = lines[0]

    # Parse the subject line
    match = COMMIT_PATTERN.match(subject)
    if not match:
        return None

    commit_type = match.group("type")
    breaking_marker = match.group("breaking_marker") == "!"
    scope = match.group("scope")
    description = match.group("description").strip()

    # Parse body and footers
    body_lines: List[str] = []
    footers: List[Tuple[str, str]] = []
    breaking_description: Optional[str] = None
    in_body = False
    past_blank_line = False

    for line in lines[1:]:
        if not in_body and line.strip() == "":
            past_blank_line = True
            continue

        if past_blank_line and not in_body:
            in_body = True

        if in_body:
            # Check for BREAKING CHANGE
            bc_match = BREAKING_CHANGE_PATTERN.match(line)
            if bc_match:
                breaking_description = bc_match.group(1).strip()
                footers.append(("BREAKING CHANGE", breaking_description))
                continue

            # Check for footer pattern
            footer_match = FOOTER_PATTERN.match(line)
            if footer_match:
                key = footer_match.group("key")
                value = footer_match.group("value") or footer_match.group("value_ref") or ""
                footers.append((key, value.strip()))
                continue

            # Regular body line
            body_lines.append(line)

    body = "\n".join(body_lines).strip() if body_lines else None

    # Determine if breaking change
    is_breaking = breaking_marker or breaking_description is not None

    return ConventionalCommit(
        type=commit_type,
        scope=scope,
        description=description,
        body=body,
        footers=footers,
        breaking_change=is_breaking,
        breaking_description=breaking_description,
        raw=message,
    )


# ─── Validator ────────────────────────────────────────────────────────────────

def validate_commit(message: str, lang: str = "en") -> ValidationResult:
    """Validate a commit message against the Conventional Commits spec.

    Args:
        message: The raw commit message string.
        lang: Language for messages ('en' or 'zh').

    Returns:
        ValidationResult with errors, warnings, and suggestions.
    """
    result = ValidationResult()

    if not message or not message.strip():
        if lang == "zh":
            result.add_error("提交消息为空")
        else:
            result.add_error("Commit message is empty")
        return result

    message = message.replace("\r\n", "\n").strip()
    lines = message.split("\n")

    # Check subject line format
    subject = lines[0]
    match = COMMIT_PATTERN.match(subject)

    if not match:
        if lang == "zh":
            result.add_error(f"提交消息格式不正确: '{subject}'")
            result.add_suggestion("正确格式: type(scope): description")
            result.add_suggestion("示例: feat(api): add user authentication endpoint")
        else:
            result.add_error(f"Invalid commit format: '{subject}'")
            result.add_suggestion("Expected format: type(scope): description")
            result.add_suggestion("Example: feat(api): add user authentication endpoint")
        return result

    commit_type = match.group("type")
    scope = match.group("scope")
    description = match.group("description").strip()

    # Validate type
    if commit_type not in STANDARD_TYPES:
        if lang == "zh":
            result.add_warning(f"非标准类型 '{commit_type}'")
            result.add_suggestion(f"标准类型: {', '.join(STANDARD_TYPES)}")
        else:
            result.add_warning(f"Non-standard type '{commit_type}'")
            result.add_suggestion(f"Standard types: {', '.join(STANDARD_TYPES)}")

    # Validate scope format
    if scope is not None:
        if not re.match(r"^[a-z0-9][a-z0-9\-_.]*$", scope):
            if lang == "zh":
                result.add_error(f"scope 格式不正确: '{scope}'")
                result.add_suggestion("scope 应使用小写字母、数字和连字符")
            else:
                result.add_error(f"Invalid scope format: '{scope}'")
                result.add_suggestion("Scope should use lowercase letters, numbers, and hyphens")

    # Validate description
    if not description:
        if lang == "zh":
            result.add_error("提交描述不能为空")
        else:
            result.add_error("Commit description cannot be empty")

    if description and description[0].isupper():
        if lang == "zh":
            result.add_warning("描述首字母不应大写")
            result.add_suggestion(f"建议: '{description[0].lower()}{description[1:]}'")
        else:
            result.add_warning("Description should not start with uppercase")
            result.add_suggestion(f"Suggestion: '{description[0].lower()}{description[1:]}'")

    if description and description.endswith("."):
        if lang == "zh":
            result.add_warning("描述不应以句号结尾")
            result.add_suggestion(f"建议: '{description[:-1]}'")
        else:
            result.add_warning("Description should not end with a period")
            result.add_suggestion(f"Suggestion: '{description[:-1]}'")

    # Validate subject length
    if len(subject) > MAX_SUBJECT_LENGTH:
        if lang == "zh":
            result.add_warning(f"主题行过长 ({len(subject)} 字符，建议不超过 {MAX_SUBJECT_LENGTH})")
        else:
            result.add_warning(f"Subject line too long ({len(subject)} chars, max {MAX_SUBJECT_LENGTH} recommended)")

    # Validate body line lengths
    body_started = False
    for line in lines[1:]:
        if not body_started and line.strip() == "":
            body_started = True
            continue
        if body_started and len(line) > MAX_BODY_LINE_LENGTH:
            if lang == "zh":
                result.add_warning(f"正文行过长 ({len(line)} 字符): '{line[:50]}...'")
            else:
                result.add_warning(f"Body line too long ({len(line)} chars): '{line[:50]}...'")
            break  # Only report first long line

    # Check for breaking change marker consistency
    has_breaking_marker = match.group("breaking_marker") == "!"
    has_breaking_footer = bool(BREAKING_CHANGE_PATTERN.search(message))

    if has_breaking_marker and not has_breaking_footer:
        if lang == "zh":
            result.add_warning("使用了 breaking change 标记 (!) 但正文中没有 BREAKING CHANGE 说明")
            result.add_suggestion("建议在正文中添加 BREAKING CHANGE: <描述>")
        else:
            result.add_warning("Breaking change marker (!) used but no BREAKING CHANGE in body")
            result.add_suggestion("Add BREAKING CHANGE: <description> in the body")

    return result


def fix_commit_message(message: str, lang: str = "en") -> str:
    """Attempt to fix common issues in a commit message.

    Args:
        message: The raw commit message string.
        lang: Language for messages.

    Returns:
        Fixed commit message string.
    """
    if not message or not message.strip():
        return message

    message = message.replace("\r\n", "\n").strip()
    lines = message.split("\n")

    subject = lines[0]
    match = COMMIT_PATTERN.match(subject)

    if not match:
        # Try to fix common mistakes
        fixed = _try_fix_subject(subject, lang)
        if fixed:
            lines[0] = fixed
        return "\n".join(lines)

    commit_type = match.group("type")
    scope = match.group("scope")
    description = match.group("description").strip()

    # Fix description: lowercase first letter
    if description and description[0].isupper():
        description = description[0].lower() + description[1:]

    # Fix description: remove trailing period
    if description and description.endswith("."):
        description = description[:-1]

    # Rebuild subject
    if scope:
        lines[0] = f"{commit_type}({scope}): {description}"
    else:
        lines[0] = f"{commit_type}: {description}"

    return "\n".join(lines)


def _try_fix_subject(subject: str, lang: str) -> Optional[str]:
    """Try to fix a malformed subject line.

    Args:
        subject: The malformed subject line.
        lang: Language for messages.

    Returns:
        Fixed subject line, or None if cannot be fixed.
    """
    # Try: "type: description" (missing space after colon)
    fix1 = re.match(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert):(\S.*)$", subject)
    if fix1:
        return f"{fix1.group(1)}: {fix1.group(2)}"

    # Try: "Type: description" (uppercase type)
    fix2 = re.match(r"^(Feat|Fix|Docs|Style|Refactor|Perf|Test|Build|CI|Chore|Revert):\s*(.+)$", subject)
    if fix2:
        return f"{fix2.group(1).lower()}: {fix2.group(2)}"

    # Try: "type(scope):description" (missing space after colon)
    fix3 = re.match(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)\(([^)]+)\):(\S.*)$", subject)
    if fix3:
        return f"{fix3.group(1)}({fix3.group(2)}): {fix3.group(3)}"

    # Try: "[type] description" (bracket notation)
    fix4 = re.match(r"^\[(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)\]\s*(.+)$", subject)
    if fix4:
        return f"{fix4.group(1)}: {fix4.group(2)}"

    return None


def get_type_description(commit_type: str, lang: str = "en") -> str:
    """Get the description for a commit type.

    Args:
        commit_type: The commit type string.
        lang: Language ('en' or 'zh').

    Returns:
        Description string.
    """
    if lang == "zh":
        return TYPE_DESCRIPTIONS_ZH.get(commit_type, commit_type)
    return TYPE_DESCRIPTIONS_EN.get(commit_type, commit_type)


def get_type_emoji(commit_type: str) -> str:
    """Get the emoji for a commit type.

    Args:
        commit_type: The commit type string.

    Returns:
        Emoji string, or empty string if not found.
    """
    return TYPE_EMOJIS.get(commit_type, "")


def is_conventional(message: str) -> bool:
    """Quick check if a message follows conventional commit format.

    Args:
        message: The commit message string.

    Returns:
        True if the message matches the conventional commit pattern.
    """
    if not message:
        return False
    message = message.strip().split("\n")[0]  # Only check subject line
    return bool(COMMIT_PATTERN.match(message))
