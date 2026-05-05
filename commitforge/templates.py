"""
Commit message templates for CommitForge.

Provides built-in templates for different commit types, multi-language
support, and customizable template variables.
"""

import re
from typing import Dict, List, Optional


# ─── Constants ────────────────────────────────────────────────────────────────

# Available template variables
TEMPLATE_VARIABLES = [
    "{type}", "{scope}", "{description}", "{body}",
    "{footer}", "{breaking}", "{emoji}", "{ticket}",
]

# Standard commit type templates (English)
TYPE_TEMPLATES_EN = {
    "feat": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "feat(auth): add OAuth2 login support",
    },
    "fix": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "fix(api): handle null response from user endpoint",
    },
    "docs": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "docs(readme): update installation instructions",
    },
    "style": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "style(lint): fix indentation in config module",
    },
    "refactor": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "refactor(core): extract validation logic into separate module",
    },
    "perf": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "perf(db): add query result caching for user lookups",
    },
    "test": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "test(auth): add unit tests for token refresh flow",
    },
    "build": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "build(deps): upgrade webpack to v5",
    },
    "ci": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "ci(github): add automated release workflow",
    },
    "chore": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "chore(deps): update development dependencies",
    },
    "revert": {
        "subject": "{emoji}{type}: {description}",
        "body": "This reverts commit {ticket}",
        "example": "revert: feat(auth): add OAuth2 login support",
    },
}

# Standard commit type templates (Chinese)
TYPE_TEMPLATES_ZH = {
    "feat": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "feat(auth): 添加 OAuth2 登录支持",
    },
    "fix": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "fix(api): 修复用户接口空响应问题",
    },
    "docs": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "docs(readme): 更新安装说明",
    },
    "style": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "style(lint): 修复配置模块缩进问题",
    },
    "refactor": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "refactor(core): 将验证逻辑提取到独立模块",
    },
    "perf": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "perf(db): 添加用户查询结果缓存",
    },
    "test": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "test(auth): 添加令牌刷新流程的单元测试",
    },
    "build": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "build(deps): 升级 webpack 到 v5",
    },
    "ci": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "ci(github): 添加自动化发布工作流",
    },
    "chore": {
        "subject": "{emoji}{type}({scope}): {description}",
        "body": "{body}",
        "example": "chore(deps): 更新开发依赖",
    },
    "revert": {
        "subject": "{emoji}{type}: {description}",
        "body": "此提交回退了 {ticket}",
        "example": "revert: feat(auth): 添加 OAuth2 登录支持",
    },
}

# Full message templates
FULL_TEMPLATE = """{subject}

{body}
{footers}"""

# Body-only template
BODY_TEMPLATE = """{body}

{footers}"""

# Scope templates for different project types
PROJECT_SCOPE_TEMPLATES = {
    "monorepo": {
        "packages": "{package}",
        "apps": "{app}",
        "libs": "{lib}",
    },
    "web": {
        "frontend": "frontend",
        "backend": "backend",
        "api": "api",
        "database": "db",
        "deployment": "deploy",
    },
    "mobile": {
        "ios": "ios",
        "android": "android",
        "shared": "shared",
    },
}


# ─── Template Engine ──────────────────────────────────────────────────────────

class TemplateEngine:
    """Commit message template engine.

    Handles template rendering with variable substitution, multi-language
    support, and custom template management.
    """

    def __init__(self, lang: str = "en", emoji: bool = False):
        """Initialize the template engine.

        Args:
            lang: Output language ('en' or 'zh').
            emoji: Whether to include emoji in templates.
        """
        self._lang = lang
        self._emoji = emoji
        self._custom_templates: Dict[str, Dict[str, str]] = {}

    @property
    def lang(self) -> str:
        """Return the current language setting."""
        return self._lang

    @lang.setter
    def lang(self, value: str) -> None:
        """Set the language."""
        self._lang = value

    @property
    def emoji(self) -> bool:
        """Return whether emoji is enabled."""
        return self._emoji

    @emoji.setter
    def emoji(self, value: bool) -> None:
        """Set emoji enabled/disabled."""
        self._emoji = value

    def get_type_template(self, commit_type: str) -> Dict[str, str]:
        """Get the template for a specific commit type.

        Args:
            commit_type: The commit type (e.g., 'feat', 'fix').

        Returns:
            Template dictionary with 'subject', 'body', and 'example' keys.
        """
        # Check custom templates first
        if commit_type in self._custom_templates:
            return self._custom_templates[commit_type]

        # Fall back to built-in templates
        if self._lang == "zh":
            return TYPE_TEMPLATES_ZH.get(commit_type, TYPE_TEMPLATES_ZH["chore"])
        return TYPE_TEMPLATES_EN.get(commit_type, TYPE_TEMPLATES_EN["chore"])

    def render_subject(self, commit_type: str, scope: Optional[str],
                       description: str, breaking: bool = False) -> str:
        """Render a commit subject line from a template.

        Args:
            commit_type: The commit type.
            scope: Optional scope string.
            description: The description text.
            breaking: Whether this is a breaking change.

        Returns:
            Rendered subject line string.
        """
        template = self.get_type_template(commit_type)
        subject_template = template["subject"]

        # Get emoji
        emoji_str = ""
        if self._emoji:
            from .conventional import TYPE_EMOJIS
            emoji_str = TYPE_EMOJIS.get(commit_type, "") + " "

        # Build scope part
        scope_part = ""
        if scope:
            scope_part = f"({scope})"

        # Handle breaking marker
        breaking_marker = "!" if breaking else ""

        # Substitute variables
        result = subject_template
        result = result.replace("{emoji}", emoji_str)
        result = result.replace("{type}", commit_type)
        result = result.replace("{scope}", scope)
        result = result.replace("{description}", description)

        # Insert breaking marker after type if needed
        if breaking and scope:
            result = result.replace(
                f"{commit_type}({scope})",
                f"{commit_type}!({scope})"
            )
        elif breaking:
            result = result.replace(
                f"{commit_type}:",
                f"{commit_type}!:"
            )

        return result

    def render_full_message(self, commit_type: str, scope: Optional[str],
                            description: str, body: Optional[str] = None,
                            footers: Optional[List[tuple]] = None,
                            breaking: bool = False,
                            breaking_description: Optional[str] = None) -> str:
        """Render a complete commit message from templates.

        Args:
            commit_type: The commit type.
            scope: Optional scope string.
            description: The description text.
            body: Optional body text.
            footers: Optional list of (key, value) footer tuples.
            breaking: Whether this is a breaking change.
            breaking_description: Optional breaking change description.

        Returns:
            Complete rendered commit message string.
        """
        # Render subject
        subject = self.render_subject(commit_type, scope, description, breaking)

        parts: List[str] = [subject]

        # Add body
        if body and body.strip():
            parts.append("")
            parts.append(body.strip())

        # Add footers
        footer_lines: List[str] = []
        if breaking and breaking_description:
            footer_lines.append(f"BREAKING CHANGE: {breaking_description}")

        if footers:
            for key, value in footers:
                if key.upper() != "BREAKING CHANGE":
                    footer_lines.append(f"{key}: {value}")

        if footer_lines:
            if body and body.strip():
                parts.append("")
            parts.extend(footer_lines)

        return "\n".join(parts)

    def register_custom_template(self, commit_type: str,
                                  subject: str, body: str = "",
                                  example: str = "") -> None:
        """Register a custom template for a commit type.

        Args:
            commit_type: The commit type to register for.
            subject: Subject line template.
            body: Optional body template.
            example: Optional example message.
        """
        self._custom_templates[commit_type] = {
            "subject": subject,
            "body": body,
            "example": example,
        }

    def register_custom_templates(self, templates: Dict[str, Dict[str, str]]) -> None:
        """Register multiple custom templates.

        Args:
            templates: Dictionary mapping commit types to template dicts.
        """
        self._custom_templates.update(templates)

    def list_templates(self) -> Dict[str, Dict[str, str]]:
        """List all available templates (built-in + custom).

        Returns:
            Dictionary of all templates.
        """
        if self._lang == "zh":
            all_templates = dict(TYPE_TEMPLATES_ZH)
        else:
            all_templates = dict(TYPE_TEMPLATES_EN)

        all_templates.update(self._custom_templates)
        return all_templates

    def get_examples(self) -> List[str]:
        """Get example commit messages for all types.

        Returns:
            List of example commit message strings.
        """
        templates = self.list_templates()
        examples: List[str] = []
        for commit_type, template in sorted(templates.items()):
            example = template.get("example", "")
            if example:
                if self._emoji:
                    from .conventional import TYPE_EMOJIS
                    emoji = TYPE_EMOJIS.get(commit_type, "")
                    if emoji:
                        example = f"{emoji} {example}"
                examples.append(example)
        return examples

    @staticmethod
    def substitute(template: str, variables: Dict[str, str]) -> str:
        """Substitute variables in a template string.

        Args:
            template: The template string with {variable} placeholders.
            variables: Dictionary of variable name to value mappings.

        Returns:
            Template string with variables substituted.
        """
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    @staticmethod
    def extract_variables(template: str) -> List[str]:
        """Extract variable names from a template string.

        Args:
            template: The template string.

        Returns:
            List of variable names found in the template.
        """
        return re.findall(r"\{(\w+)\}", template)

    def format_template_help(self) -> str:
        """Generate help text for template variables.

        Returns:
            Formatted help string listing available variables.
        """
        from .utils import bold, cyan, dim

        lines: List[str] = []
        lines.append(bold("Available template variables:"))
        lines.append("")

        variable_descriptions = {
            "type": "Commit type (feat, fix, docs, etc.)",
            "scope": "Scope/module affected",
            "description": "Short description of the change",
            "body": "Detailed body text",
            "footer": "Footer lines (e.g., breaking changes)",
            "breaking": "Breaking change marker/description",
            "emoji": "Type-specific emoji (if enabled)",
            "ticket": "Ticket/issue reference",
        }

        for var in TEMPLATE_VARIABLES:
            desc = variable_descriptions.get(var[1:-1], "")
            lines.append(f"  {cyan(var):<15} {dim(desc)}")

        return "\n".join(lines)
