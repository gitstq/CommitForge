"""
Offline rules-based commit message generation engine for CommitForge.

Generates conventional commit messages without requiring any AI backend,
using pattern matching, keyword detection, and template-based generation.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

from .conventional import (
    STANDARD_TYPES,
    TYPE_DESCRIPTIONS_EN,
    TYPE_DESCRIPTIONS_ZH,
    TYPE_EMOJIS,
    ConventionalCommit,
)
from .git_analyzer import (
    ChangeAnalysis,
    FileChange,
    classify_change_type,
    detect_scope,
    extract_keywords,
)


# ─── Constants ────────────────────────────────────────────────────────────────

# Action verb mapping for generating descriptions
ACTION_VERBS_EN = {
    "feat": ["add", "implement", "introduce", "create", "support"],
    "fix": ["fix", "resolve", "correct", "patch", "repair"],
    "docs": ["update", "improve", "add", "expand", "clarify"],
    "style": ["format", "clean up", "adjust", "align", "standardize"],
    "refactor": ["refactor", "restructure", "simplify", "reorganize", "clean up"],
    "perf": ["optimize", "improve performance of", "speed up", "accelerate", "streamline"],
    "test": ["add tests for", "update tests for", "fix tests for", "extend tests for"],
    "build": ["update build config", "update dependencies", "configure build"],
    "ci": ["update CI config", "configure pipeline", "update workflow"],
    "chore": ["update", "clean up", "maintain", "synchronize", "bump"],
}

ACTION_VERBS_ZH = {
    "feat": ["添加", "实现", "引入", "创建", "支持"],
    "fix": ["修复", "解决", "修正", "修补"],
    "docs": ["更新", "完善", "添加", "补充", "澄清"],
    "style": ["格式化", "整理", "调整", "对齐", "统一"],
    "refactor": ["重构", "重组", "简化", "整理", "清理"],
    "perf": ["优化", "提升性能", "加速", "精简"],
    "test": ["添加测试", "更新测试", "修复测试", "扩展测试"],
    "build": ["更新构建配置", "更新依赖", "配置构建"],
    "ci": ["更新 CI 配置", "配置流水线", "更新工作流"],
    "chore": ["更新", "清理", "维护", "同步", "升级"],
}

# File type to subject noun mapping
FILE_TYPE_NOUNS_EN = {
    ".py": "Python module",
    ".js": "JavaScript module",
    ".ts": "TypeScript module",
    ".jsx": "React component",
    ".tsx": "React component",
    ".go": "Go package",
    ".rs": "Rust module",
    ".java": "Java class",
    ".kt": "Kotlin class",
    ".rb": "Ruby module",
    ".php": "PHP file",
    ".c": "C source file",
    ".cpp": "C++ source file",
    ".h": "C/C++ header file",
    ".cs": "C# class",
    ".swift": "Swift file",
    ".md": "documentation",
    ".rst": "documentation",
    ".yaml": "YAML configuration",
    ".yml": "YAML configuration",
    ".toml": "TOML configuration",
    ".json": "JSON configuration",
    ".xml": "XML configuration",
    ".html": "HTML template",
    ".css": "CSS stylesheet",
    ".scss": "SCSS stylesheet",
    ".sql": "SQL migration",
    ".sh": "shell script",
    ".bash": "bash script",
    ".dockerfile": "Docker configuration",
    "Makefile": "Makefile",
}

FILE_TYPE_NOUNS_ZH = {
    ".py": "Python 模块",
    ".js": "JavaScript 模块",
    ".ts": "TypeScript 模块",
    ".jsx": "React 组件",
    ".tsx": "React 组件",
    ".go": "Go 包",
    ".rs": "Rust 模块",
    ".java": "Java 类",
    ".kt": "Kotlin 类",
    ".rb": "Ruby 模块",
    ".php": "PHP 文件",
    ".c": "C 源文件",
    ".cpp": "C++ 源文件",
    ".h": "C/C++ 头文件",
    ".cs": "C# 类",
    ".swift": "Swift 文件",
    ".md": "文档",
    ".rst": "文档",
    ".yaml": "YAML 配置",
    ".yml": "YAML 配置",
    ".toml": "TOML 配置",
    ".json": "JSON 配置",
    ".xml": "XML 配置",
    ".html": "HTML 模板",
    ".css": "CSS 样式表",
    ".scss": "SCSS 样式表",
    ".sql": "SQL 迁移",
    ".sh": "Shell 脚本",
    ".bash": "Bash 脚本",
}

# Description templates for common patterns
DESCRIPTION_TEMPLATES_EN = {
    "new_file": "add {noun} {file}",
    "delete_file": "remove {noun} {file}",
    "modify_file": "update {noun} {file}",
    "rename_file": "rename {old_file} to {new_file}",
    "new_test": "add tests for {scope}",
    "fix_import": "fix import in {file}",
    "update_dep": "update {package} dependency",
    "update_config": "update {config_type} configuration",
    "fix_typo": "fix typo in {file}",
    "refactor_large": "refactor {scope} module",
}

DESCRIPTION_TEMPLATES_ZH = {
    "new_file": "添加 {noun} {file}",
    "delete_file": "移除 {noun} {file}",
    "modify_file": "更新 {noun} {file}",
    "rename_file": "将 {old_file} 重命名为 {new_file}",
    "new_test": "为 {scope} 添加测试",
    "fix_import": "修复 {file} 中的导入",
    "update_dep": "更新 {package} 依赖",
    "update_config": "更新 {config_type} 配置",
    "fix_typo": "修复 {file} 中的拼写错误",
    "refactor_large": "重构 {scope} 模块",
}


# ─── Rules Engine ─────────────────────────────────────────────────────────────

class RulesEngine:
    """Offline rule-based commit message generator.

    Generates conventional commit messages using pattern matching,
    keyword detection, and template-based generation without requiring
    any AI backend.
    """

    def __init__(self, lang: str = "en", emoji: bool = False,
                 scope_rules: Optional[Dict[str, str]] = None):
        """Initialize the rules engine.

        Args:
            lang: Output language ('en' or 'zh').
            emoji: Whether to include emoji in commit messages.
            scope_rules: Optional custom scope rules.
        """
        self._lang = lang
        self._emoji = emoji
        self._scope_rules = scope_rules or {}

    def generate(self, analysis: ChangeAnalysis,
                 force_type: Optional[str] = None,
                 force_scope: Optional[str] = None) -> ConventionalCommit:
        """Generate a commit message based on change analysis.

        Args:
            analysis: The change analysis result.
            force_type: Override the detected commit type.
            force_scope: Override the detected scope.

        Returns:
            A ConventionalCommit with the generated message.
        """
        # Determine commit type
        commit_type = force_type or analysis.commit_type

        # Determine scope
        scope = force_scope or analysis.scope

        # Generate description
        description = self._generate_description(analysis, commit_type, scope)

        # Generate body
        body = self._generate_body(analysis, commit_type)

        # Generate footers
        footers = self._generate_footers(analysis)

        # Detect breaking changes
        breaking = analysis.has_breaking_change
        breaking_desc = None
        if breaking:
            breaking_desc = self._generate_breaking_description(analysis, self._lang)
            footers.insert(0, ("BREAKING CHANGE", breaking_desc))

        return ConventionalCommit(
            type=commit_type,
            scope=scope if scope else None,
            description=description,
            body=body,
            footers=footers,
            breaking_change=breaking,
            breaking_description=breaking_desc,
        )

    def _generate_description(self, analysis: ChangeAnalysis,
                              commit_type: str, scope: str) -> str:
        """Generate the commit description line.

        Args:
            analysis: The change analysis result.
            commit_type: The commit type.
            scope: The detected scope.

        Returns:
            Description string.
        """
        files = analysis.files
        if not files:
            if self._lang == "zh":
                return "更新代码"
            return "update code"

        # Single file change - be specific
        if len(files) == 1:
            return self._describe_single_file(files[0], commit_type)

        # All files are the same type (all new, all deleted, etc.)
        statuses = set(f.status for f in files)
        if len(statuses) == 1:
            status = statuses.pop()
            if status == "added":
                return self._describe_added_files(files, commit_type, scope)
            elif status == "deleted":
                return self._describe_deleted_files(files, commit_type, scope)

        # Check for keywords in changes
        if analysis.description_keywords:
            return self._describe_from_keywords(analysis, commit_type)

        # Check for specific patterns
        pattern_desc = self._detect_pattern(files, commit_type)
        if pattern_desc:
            return pattern_desc

        # Default description based on type
        return self._default_description(analysis, commit_type, scope)

    def _describe_single_file(self, file_change: FileChange,
                               commit_type: str) -> str:
        """Generate description for a single file change.

        Args:
            file_change: The file change.
            commit_type: The commit type.

        Returns:
            Description string.
        """
        filename = os.path.basename(file_change.path)
        ext = file_change.extension
        is_zh = self._lang == "zh"
        nouns = FILE_TYPE_NOUNS_ZH if is_zh else FILE_TYPE_NOUNS_EN
        verbs = ACTION_VERBS_ZH if is_zh else ACTION_VERBS_EN
        templates = DESCRIPTION_TEMPLATES_ZH if is_zh else DESCRIPTION_TEMPLATES_EN

        verb = verbs.get(commit_type, verbs["chore"])[0]
        noun = nouns.get(ext, filename)

        if file_change.status == "added":
            if is_zh:
                return f"{verb}{noun} {filename}"
            return f"{verb} {noun} {filename}"

        elif file_change.status == "deleted":
            if is_zh:
                return f"移除{noun} {filename}"
            return f"remove {noun} {filename}"

        elif file_change.status == "renamed" and file_change.old_path:
            old_name = os.path.basename(file_change.old_path)
            template = templates.get("rename_file", "rename {old_file} to {new_file}")
            return template.format(old_file=old_name, new_file=filename)

        else:
            if is_zh:
                return f"{verb}{noun} {filename}"
            return f"{verb} {noun} {filename}"

    def _describe_added_files(self, files: List[FileChange],
                               commit_type: str, scope: str) -> str:
        """Generate description for multiple added files.

        Args:
            files: List of file changes (all added).
            commit_type: The commit type.
            scope: The detected scope.

        Returns:
            Description string.
        """
        is_zh = self._lang == "zh"

        # Check if all are test files
        all_tests = all(
            any(p in f.path for p in ["test", "spec", "__tests__"])
            for f in files
        )
        if all_tests:
            if is_zh:
                return f"为 {scope} 添加测试" if scope else "添加测试"
            return f"add tests for {scope}" if scope else "add tests"

        # Check if all are doc files
        all_docs = all(
            f.extension in (".md", ".rst", ".txt", ".adoc")
            for f in files
        )
        if all_docs:
            if is_zh:
                return "更新文档"
            return "update documentation"

        if is_zh:
            return f"添加 {len(files)} 个文件"
        return f"add {len(files)} files"

    def _describe_deleted_files(self, files: List[FileChange],
                                 commit_type: str, scope: str) -> str:
        """Generate description for multiple deleted files.

        Args:
            files: List of file changes (all deleted).
            commit_type: The commit type.
            scope: The detected scope.

        Returns:
            Description string.
        """
        is_zh = self._lang == "zh"
        if is_zh:
            return f"移除 {len(files)} 个文件"
        return f"remove {len(files)} files"

    def _describe_from_keywords(self, analysis: ChangeAnalysis,
                                 commit_type: str) -> str:
        """Generate description based on extracted keywords.

        Args:
            analysis: The change analysis result.
            commit_type: The commit type.

        Returns:
            Description string.
        """
        is_zh = self._lang == "zh"
        verbs = ACTION_VERBS_ZH if is_zh else ACTION_VERBS_EN
        verb = verbs.get(commit_type, verbs["chore"])[0]

        keywords = analysis.description_keywords[:3]
        keyword_str = ", ".join(keywords)

        if is_zh:
            return f"{verb} {keyword_str}"
        return f"{verb} {keyword_str}"

    def _detect_pattern(self, files: List[FileChange],
                         commit_type: str) -> Optional[str]:
        """Detect common change patterns and generate description.

        Args:
            files: List of file changes.
            commit_type: The commit type.

        Returns:
            Description string, or None if no pattern detected.
        """
        is_zh = self._lang == "zh"
        paths = [f.path for f in files]

        # Dependency update pattern
        lock_files = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                      "poetry.lock", "Pipfile.lock", "Cargo.lock", "go.sum",
                      "composer.lock", "Gemfile.lock"}
        if any(os.path.basename(p) in lock_files for p in paths):
            if is_zh:
                return "更新依赖"
            return "update dependencies"

        # Config file pattern
        config_files = {".eslintrc", ".prettierrc", ".editorconfig",
                        "tsconfig.json", "jest.config.js", "webpack.config.js",
                        "vite.config.ts", ".babelrc", ".pylintrc"}
        config_basenames = {os.path.basename(p) for p in paths}
        if config_basenames & config_files:
            if is_zh:
                return "更新配置文件"
            return "update configuration files"

        # License change
        if any(os.path.basename(p).upper() in ("LICENSE", "COPYING") for p in paths):
            if is_zh:
                return "更新许可证"
            return "update license"

        return None

    def _default_description(self, analysis: ChangeAnalysis,
                              commit_type: str, scope: str) -> str:
        """Generate a default description based on change type and scope.

        Args:
            analysis: The change analysis result.
            commit_type: The commit type.
            scope: The detected scope.

        Returns:
            Description string.
        """
        is_zh = self._lang == "zh"
        verbs = ACTION_VERBS_ZH if is_zh else ACTION_VERBS_EN
        verb = verbs.get(commit_type, verbs["chore"])[0]

        # Get the most changed file for context
        if analysis.files:
            most_changed = max(analysis.files, key=lambda f: f.total_changes)
            filename = os.path.basename(most_changed.path)
            if scope:
                if is_zh:
                    return f"{verb} {scope} 中的 {filename}"
                return f"{verb} {filename} in {scope}"
            else:
                if is_zh:
                    return f"{verb} {filename}"
                return f"{verb} {filename}"

        if is_zh:
            return f"{verb}代码"
        return f"{verb} code"

    def _generate_body(self, analysis: ChangeAnalysis,
                        commit_type: str) -> Optional[str]:
        """Generate the commit body text.

        Args:
            analysis: The change analysis result.
            commit_type: The commit type.

        Returns:
            Body text string, or None.
        """
        is_zh = self._lang == "zh"
        lines: List[str] = []

        # List changed files
        if analysis.total_files > 1 and analysis.total_files <= 10:
            if is_zh:
                lines.append("变更文件:")
            else:
                lines.append("Changed files:")
            for f in analysis.files:
                status_icon = {"added": "+", "deleted": "-", "modified": "~",
                               "renamed": "->"}.get(f.status, "~")
                lines.append(f"  {status_icon} {f.path}")

        # Add change statistics
        if analysis.total_files > 1:
            if is_zh:
                lines.append(f"\n统计: {analysis.total_files} 个文件, "
                             f"+{analysis.total_insertions} -{analysis.total_deletions}")
            else:
                lines.append(f"\nStats: {analysis.total_files} files, "
                             f"+{analysis.total_insertions} -{analysis.total_deletions}")

        return "\n".join(lines) if lines else None

    def _generate_footers(self, analysis: ChangeAnalysis) -> List[Tuple[str, str]]:
        """Generate commit footers.

        Args:
            analysis: The change analysis result.

        Returns:
            List of footer (key, value) tuples.
        """
        footers: List[Tuple[str, str]] = []

        # Add reviewed-by if we detect it (placeholder for future use)
        # Add co-authored-by if we detect it (placeholder for future use)

        return footers

    def _generate_breaking_description(self, analysis: ChangeAnalysis,
                                        lang: str) -> str:
        """Generate a breaking change description.

        Args:
            analysis: The change analysis result.
            lang: Language ('en' or 'zh').

        Returns:
            Breaking change description string.
        """
        if lang == "zh":
            if analysis.files:
                filenames = ", ".join(os.path.basename(f.path) for f in analysis.files[:3])
                return f"以下文件的变更可能包含破坏性变更: {filenames}"
            return "此提交包含破坏性变更"
        else:
            if analysis.files:
                filenames = ", ".join(os.path.basename(f.path) for f in analysis.files[:3])
                return f"Changes in the following files may contain breaking changes: {filenames}"
            return "This commit contains breaking changes"

    def classify_by_keywords(self, diff_content: str) -> Optional[str]:
        """Classify change type based on keywords in diff content.

        This is a standalone method that can be used without full analysis.

        Args:
            diff_content: The raw diff content string.

        Returns:
            Detected commit type, or None.
        """
        from .git_analyzer import KEYWORD_PATTERNS

        scores: Dict[str, int] = {}
        for commit_type, patterns in KEYWORD_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, diff_content, re.IGNORECASE)
                scores[commit_type] = scores.get(commit_type, 0) + len(matches)

        if not scores:
            return None

        best_type = max(scores, key=scores.get)
        return best_type if scores[best_type] > 0 else None

    def infer_type_from_extension(self, extension: str) -> str:
        """Infer commit type from file extension.

        Args:
            extension: File extension (e.g., '.py', '.md').

        Returns:
            Inferred commit type.
        """
        from .git_analyzer import EXTENSION_TYPE_MAP
        return EXTENSION_TYPE_MAP.get(extension, "chore")

    def infer_type_from_filename(self, filename: str) -> str:
        """Infer commit type from filename patterns.

        Args:
            filename: The filename (e.g., 'test_app.py', 'Dockerfile').

        Returns:
            Inferred commit type.
        """
        from .git_analyzer import EXTENSION_TYPE_MAP

        # Check exact match first
        if filename in EXTENSION_TYPE_MAP:
            return EXTENSION_TYPE_MAP[filename]

        # Check pattern match
        for pattern, commit_type in EXTENSION_TYPE_MAP.items():
            if not pattern.startswith(".") and pattern in filename:
                return commit_type

        return "chore"
