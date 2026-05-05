"""
Git change analyzer for CommitForge.

Parses git diff output to extract changed files, classify changes by type,
detect affected scope/module, and calculate change statistics.
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ─── Constants ────────────────────────────────────────────────────────────────

# File extension to commit type mapping
EXTENSION_TYPE_MAP = {
    # Documentation
    ".md": "docs",
    ".mdx": "docs",
    ".rst": "docs",
    ".txt": "docs",
    ".adoc": "docs",
    # Configuration / CI
    ".yml": "ci",
    ".yaml": "ci",
    ".toml": "ci",
    ".ini": "ci",
    ".cfg": "ci",
    ".conf": "ci",
    # Build
    "Makefile": "build",
    "Dockerfile": "build",
    ".dockerignore": "build",
    "CMakeLists.txt": "build",
    ".gradle": "build",
    # Tests
    "_test.py": "test",
    "_test.js": "test",
    "_test.ts": "test",
    "_test.go": "test",
    "_test.rs": "test",
    ".test.js": "test",
    ".test.ts": "test",
    ".spec.js": "test",
    ".spec.ts": "test",
    ".test.jsx": "test",
    ".test.tsx": "test",
    ".spec.jsx": "test",
    ".spec.tsx": "test",
    "test_": "test",
    "__tests__": "test",
    "__mocks__": "test",
    "conftest.py": "test",
    "pytest.ini": "test",
    "jest.config.js": "test",
    ".eslintrc": "ci",
    ".prettierrc": "ci",
    ".editorconfig": "ci",
    ".gitignore": "chore",
    ".gitattributes": "chore",
    "LICENSE": "docs",
    "LICENSE.md": "docs",
    "COPYING": "docs",
}

# Directory name to commit type mapping
DIRECTORY_TYPE_MAP = {
    "docs": "docs",
    "doc": "docs",
    "documentation": "docs",
    "test": "test",
    "tests": "test",
    "spec": "test",
    "specs": "test",
    "examples": "docs",
    "demo": "docs",
    "demos": "docs",
    "scripts": "chore",
    "tools": "chore",
    "ci": "ci",
    ".github": "ci",
    ".circleci": "ci",
    ".gitlab-ci": "ci",
    ".travis": "ci",
    "jenkins": "ci",
    "build": "build",
    "dist": "build",
    "release": "build",
    "assets": "chore",
    "static": "chore",
    "public": "chore",
    "media": "chore",
    "fonts": "chore",
    "images": "chore",
    "img": "chore",
    "i18n": "feat",
    "locales": "feat",
    "translations": "feat",
}

# Keyword patterns for change classification
KEYWORD_PATTERNS = {
    "feat": [
        r"\badd\b", r"\bnew\b", r"\bimplement\b", r"\bcreate\b",
        r"\bsupport\b", r"\bintroduce\b", r"\benable\b", r"\bfeature\b",
        r"\b新增\b", r"\b实现\b", r"\b添加\b", r"\b支持\b",
    ],
    "fix": [
        r"\bfix\b", r"\bbug\b", r"\berror\b", r"\bissue\b",
        r"\bpatch\b", r"\bresolve\b", r"\bcorrect\b", r"\brepair\b",
        r"\b修复\b", r"\b修正\b", r"\b解决\b", r"\bbug\b",
    ],
    "perf": [
        r"\boptimiz\w*\b", r"\bperform\w*\b", r"\bspeed\b", r"\bfaster\b",
        r"\bslow\b", r"\bcach\w*\b", r"\blazy\b", r"\bmemoi\w*\b",
        r"\b优化\b", r"\b性能\b", r"\b加速\b",
    ],
    "refactor": [
        r"\brefactor\b", r"\bclean\b", r"\brestructur\w*\b", r"\breorgani\w*\b",
        r"\bsimplif\w*\b", r"\bextract\b", r"\bmove\b", r"\brename\b",
        r"\b重构\b", r"\b清理\b", r"\b整理\b",
    ],
    "docs": [
        r"\bdoc\b", r"\bcomment\b", r"\breadme\b", r"\bdocument\w*\b",
        r"\b文档\b", r"\b注释\b", r"\b说明\b",
    ],
    "test": [
        r"\btest\b", r"\bassert\b", r"\bexpect\b", r"\bmock\b",
        r"\bstub\b", r"\bcoverage\b", r"\b测试\b", r"\b断言\b",
    ],
    "style": [
        r"\bformat\b", r"\blint\b", r"\bwhitespace\b", r"\bindent\b",
        r"\bstyle\b", r"\bprettier\b", r"\beslint\b",
        r"\b格式\b", r"\b样式\b",
    ],
    "ci": [
        r"\bci\b", r"\bdeploy\b", r"\bpipeline\b", r"\bworkflow\b",
        r"\bgithub.action\b", r"\bjenkins\b", r"\btravis\b",
    ],
    "build": [
        r"\bbuild\b", r"\bcompil\w*\b", r"\bdepend\w*\b", r"\bpackage\b",
        r"\bdocker\b", r"\bwebpack\b", r"\bvite\b", r"\bgradle\b",
        r"\bmaven\b", r"\bmakefile\b",
    ],
    "chore": [
        r"\bchore\b", r"\bmaintain\b", r"\bupdate\s+depend\w*\b",
        r"\bbump\b", r"\bversion\b", r"\bupgrade\b",
        r"\b维护\b", r"\b升级\b",
    ],
}

# Diff parsing patterns
DIFF_FILE_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")
DIFF_NEW_FILE = re.compile(r"^new file mode")
DIFF_DELETED_FILE = re.compile(r"^deleted file mode")
DIFF_INDEX = re.compile(r"^index [0-9a-f]+\.\.([0-9a-f]+)")
DIFF_HUNK_HEADER = re.compile(r"^@@ .+\+(\d+)(?:,(\d+))? @@")
DIFF_ADDED_LINE = re.compile(r"^\+(?!\+)")
DIFF_REMOVED_LINE = re.compile(r"^\-(?!\-)")
DIFF_BINARY_FILE = re.compile(r"^Binary files")


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class FileChange:
    """Represents a single file's changes.

    Attributes:
        path: File path relative to repository root.
        old_path: Previous file path (for renames).
        status: Change status ('added', 'modified', 'deleted', 'renamed').
        extension: File extension.
        added_lines: Number of lines added.
        removed_lines: Number of lines removed.
        is_binary: Whether the file is binary.
        diff_content: Raw diff content for this file.
    """
    path: str
    status: str = "modified"
    old_path: Optional[str] = None
    extension: str = ""
    added_lines: int = 0
    removed_lines: int = 0
    is_binary: bool = False
    diff_content: str = ""

    def __post_init__(self) -> None:
        """Automatically compute extension from path if not set."""
        if not self.extension and self.path:
            _, ext = os.path.splitext(self.path)
            object.__setattr__(self, 'extension', ext.lower())

    @property
    def total_changes(self) -> int:
        """Return total number of changed lines."""
        return self.added_lines + self.removed_lines


@dataclass
class ChangeAnalysis:
    """Result of analyzing git staged changes.

    Attributes:
        files: List of file changes.
        commit_type: Inferred commit type.
        scope: Inferred scope/module.
        description_keywords: Keywords extracted from changes.
        total_insertions: Total lines added across all files.
        total_deletions: Total lines removed across all files.
        total_files: Total number of files changed.
        has_breaking_change: Whether breaking changes are detected.
        is_large_change: Whether this is a large change.
    """
    files: List[FileChange] = field(default_factory=list)
    commit_type: str = "chore"
    scope: str = ""
    description_keywords: List[str] = field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0
    total_files: int = 0
    has_breaking_change: bool = False
    is_large_change: bool = False

    @property
    def total_changes(self) -> int:
        """Return total number of changed lines."""
        return self.total_insertions + self.total_deletions

    @property
    def change_summary(self) -> str:
        """Return a human-readable change summary."""
        parts: List[str] = []
        parts.append(f"{self.total_files} file(s)")
        parts.append(f"+{self.total_insertions}")
        parts.append(f"-{self.total_deletions}")
        return ", ".join(parts)


# ─── Git Operations ───────────────────────────────────────────────────────────

def get_staged_diff() -> str:
    """Get the git diff for staged changes.

    Returns:
        The diff output string, or empty string if no staged changes.

    Raises:
        RuntimeError: If git command fails.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--diff-algorithm=histogram"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("git command not found. Please ensure git is installed.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git diff timed out. Please try again.")


def get_unstaged_diff() -> str:
    """Get the git diff for unstaged changes.

    Returns:
        The diff output string, or empty string if no unstaged changes.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--diff-algorithm=histogram"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def get_last_commit_message() -> str:
    """Get the last commit message.

    Returns:
        The last commit message string, or empty string.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def is_git_repository() -> bool:
    """Check if the current directory is inside a git repository.

    Returns:
        True if inside a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def has_staged_changes() -> bool:
    """Check if there are staged changes.

    Returns:
        True if there are staged changes.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode != 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_repository_root() -> Optional[str]:
    """Get the root directory of the git repository.

    Returns:
        Path to the repository root, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# ─── Diff Parser ──────────────────────────────────────────────────────────────

def parse_diff(diff_text: str) -> List[FileChange]:
    """Parse git diff output into a list of FileChange objects.

    Args:
        diff_text: The raw git diff output.

    Returns:
        List of FileChange objects.
    """
    if not diff_text or not diff_text.strip():
        return []

    files: List[FileChange] = []
    current_file: Optional[FileChange] = None
    diff_lines: List[str] = []

    lines = diff_text.split("\n")

    for line in lines:
        # New file diff header
        file_match = DIFF_FILE_HEADER.match(line)
        if file_match:
            # Save previous file
            if current_file is not None:
                current_file.diff_content = "\n".join(diff_lines)
                files.append(current_file)

            new_path = file_match.group(2)
            old_path = file_match.group(1)

            # Determine file extension
            _, ext = os.path.splitext(new_path)

            current_file = FileChange(
                path=new_path,
                old_path=old_path if old_path != new_path else None,
                extension=ext.lower(),
            )
            diff_lines = [line]
            continue

        if current_file is None:
            continue

        diff_lines.append(line)

        # Check file status
        if DIFF_NEW_FILE.match(line):
            current_file.status = "added"
        elif DIFF_DELETED_FILE.match(line):
            current_file.status = "deleted"
        elif DIFF_BINARY_FILE.match(line):
            current_file.is_binary = True

        # Count added/removed lines
        if DIFF_ADDED_LINE.match(line):
            current_file.added_lines += 1
        elif DIFF_REMOVED_LINE.match(line):
            current_file.removed_lines += 1

    # Don't forget the last file
    if current_file is not None:
        current_file.diff_content = "\n".join(diff_lines)
        files.append(current_file)

    return files


# ─── Change Classifier ────────────────────────────────────────────────────────

def classify_change_type(files: List[FileChange], scope_rules: Optional[Dict[str, str]] = None) -> str:
    """Classify the overall change type based on file changes.

    Uses a scoring system that considers:
    1. File extensions
    2. Directory names
    3. Keywords in changed lines
    4. Change magnitude

    Args:
        files: List of FileChange objects.
        scope_rules: Optional custom scope rules from config.

    Returns:
        The inferred commit type string.
    """
    if not files:
        return "chore"

    scores: Dict[str, float] = {
        "feat": 0.0,
        "fix": 0.0,
        "docs": 0.0,
        "style": 0.0,
        "refactor": 0.0,
        "perf": 0.0,
        "test": 0.0,
        "build": 0.0,
        "ci": 0.0,
        "chore": 0.0,
    }

    for file_change in files:
        path = file_change.path
        ext = file_change.extension
        filename = os.path.basename(path)
        dirname = os.path.dirname(path).split(os.sep)[0] if os.path.dirname(path) else ""

        # Score by file extension
        if ext in EXTENSION_TYPE_MAP:
            scores[EXTENSION_TYPE_MAP[ext]] += 2.0

        # Score by filename patterns (for test files)
        for pattern, commit_type in EXTENSION_TYPE_MAP.items():
            if not pattern.startswith(".") and pattern in filename:
                scores[commit_type] += 3.0

        # Score by directory name
        if dirname in DIRECTORY_TYPE_MAP:
            scores[DIRECTORY_TYPE_MAP[dirname]] += 2.0

        # Score by keywords in diff content
        if file_change.diff_content and not file_change.is_binary:
            for commit_type, patterns in KEYWORD_PATTERNS.items():
                for pattern in patterns:
                    matches = re.findall(pattern, file_change.diff_content, re.IGNORECASE)
                    scores[commit_type] += len(matches) * 0.5

        # Bonus for deleted files (often refactor or fix)
        if file_change.status == "deleted":
            scores["refactor"] += 1.0

        # Bonus for new files (often feat or test)
        if file_change.status == "added":
            scores["feat"] += 0.5

    # Find the highest scoring type
    max_score = 0.0
    best_type = "chore"
    for commit_type, score in scores.items():
        if score > max_score:
            max_score = score
            best_type = commit_type

    # If all scores are 0, default to chore
    if max_score == 0.0:
        best_type = "chore"

    return best_type


def detect_scope(files: List[FileChange], scope_rules: Optional[Dict[str, str]] = None) -> str:
    """Detect the scope/module affected by the changes.

    Uses file paths and custom scope rules to determine the most
    appropriate scope.

    Args:
        files: List of FileChange objects.
        scope_rules: Optional custom scope rules mapping paths to scopes.

    Returns:
        The detected scope string, or empty string if no clear scope.
    """
    if not files:
        return ""

    scope_counts: Dict[str, int] = {}

    for file_change in files:
        path = file_change.path
        parts = path.split(os.sep)

        # Try custom scope rules first
        if scope_rules:
            for rule_path, scope_name in scope_rules.items():
                if path.startswith(rule_path) or path == rule_path:
                    scope_counts[scope_name] = scope_counts.get(scope_name, 0) + 1
                    break
            else:
                # Use first directory as scope
                if len(parts) > 1 and parts[0]:
                    scope = parts[0]
                    scope_counts[scope] = scope_counts.get(scope, 0) + 1
        else:
            # Use first directory as scope
            if len(parts) > 1 and parts[0]:
                scope = parts[0]
                scope_counts[scope] = scope_counts.get(scope, 0) + 1

    if not scope_counts:
        return ""

    # Return the most common scope
    best_scope = max(scope_counts, key=scope_counts.get)
    # Only return scope if it covers a significant portion of changes
    total = sum(scope_counts.values())
    if scope_counts[best_scope] >= total * 0.5:
        return best_scope

    return ""


def detect_monorepo_scope(files: List[FileChange]) -> Optional[str]:
    """Detect scope in a monorepo by looking for common monorepo patterns.

    Checks for patterns like 'packages/<name>', 'apps/<name>', 'libs/<name>'.

    Args:
        files: List of FileChange objects.

    Returns:
        Detected monorepo scope, or None.
    """
    if not files:
        return None

    monorepo_patterns = [
        r"^(packages|libs|apps|modules|services)/([^/]+)/",
    ]

    scope_counts: Dict[str, int] = {}

    for file_change in files:
        for pattern in monorepo_patterns:
            match = re.match(pattern, file_change.path)
            if match:
                scope = match.group(2)
                scope_counts[scope] = scope_counts.get(scope, 0) + 1
                break

    if not scope_counts:
        return None

    best_scope = max(scope_counts, key=scope_counts.get)
    total = sum(scope_counts.values())
    if scope_counts[best_scope] >= total * 0.5:
        return best_scope

    return None


def extract_keywords(files: List[FileChange]) -> List[str]:
    """Extract meaningful keywords from changed code.

    Looks at added lines for function names, class names, variable names,
    and other identifiers that describe the change.

    Args:
        files: List of FileChange objects.

    Returns:
        List of extracted keyword strings.
    """
    keywords: List[str] = []
    seen: set = set()

    for file_change in files:
        if file_change.is_binary or not file_change.diff_content:
            continue

        for line in file_change.diff_content.split("\n"):
            # Only look at added lines
            if not line.startswith("+") or line.startswith("+++"):
                continue

            line = line[1:]  # Remove the '+' prefix

            # Look for function definitions
            func_match = re.search(
                r"(?:def|function|func|fn|public\s+(?:static\s+)?(?:async\s+)?)\s+(\w+)",
                line
            )
            if func_match:
                name = func_match.group(1)
                if name not in seen and not name.startswith("_"):
                    keywords.append(name)
                    seen.add(name)

            # Look for class definitions
            class_match = re.search(
                r"(?:class|struct|interface|type|enum)\s+(\w+)",
                line
            )
            if class_match:
                name = class_match.group(1)
                if name not in seen:
                    keywords.append(name)
                    seen.add(name)

            # Look for TODO/FIXME/HACK/BUG/NEW comments
            comment_keywords = re.findall(
                r"#\s*(TODO|FIXME|HACK|BUG|NEW|NOTE|XXX|DEPRECATED)\b[:\s]*(.+)",
                line
            )
            for kw, desc in comment_keywords:
                keyword = f"{kw}: {desc.strip()}"
                if keyword not in seen:
                    keywords.append(keyword)
                    seen.add(keyword)

            # Also check // style comments
            comment_keywords2 = re.findall(
                r"//\s*(TODO|FIXME|HACK|BUG|NEW|NOTE|XXX|DEPRECATED)\b[:\s]*(.+)",
                line
            )
            for kw, desc in comment_keywords2:
                keyword = f"{kw}: {desc.strip()}"
                if keyword not in seen:
                    keywords.append(keyword)
                    seen.add(keyword)

    return keywords[:10]  # Limit to 10 keywords


def detect_breaking_changes(files: List[FileChange]) -> bool:
    """Detect potential breaking changes in the diff.

    Looks for patterns that commonly indicate breaking changes:
    - Removed public functions/classes
    - Changed function signatures
    - Removed exports
    - Version bumps

    Args:
        files: List ofFileChange objects.

    Returns:
        True if potential breaking changes are detected.
    """
    breaking_patterns = [
        r"^-.*(?:def |function |func |class |interface |export )",
        r"^-.*(?:public |protected )\s*(?:static\s+)?(?:async\s+)?\w+\s*\(",
        r"^-.*BREAKING",
        r"^-.*@deprecated",
        r"^\+.*breaking[_\s]?change",
        r"^\+.*version\s*[:=]\s*\d+\.\d+\.0",
    ]

    for file_change in files:
        if file_change.is_binary or not file_change.diff_content:
            continue

        for line in file_change.diff_content.split("\n"):
            # Check removed lines for breaking patterns
            if line.startswith("-") and not line.startswith("---"):
                for pattern in breaking_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        return True

    return False


def analyze_changes(
    diff_text: Optional[str] = None,
    scope_rules: Optional[Dict[str, str]] = None,
) -> ChangeAnalysis:
    """Perform a complete analysis of git staged changes.

    This is the main entry point for change analysis. It parses the diff,
    classifies the change type, detects scope, extracts keywords, and
    calculates statistics.

    Args:
        diff_text: Optional pre-fetched diff text. If None, fetches from git.
        scope_rules: Optional custom scope rules from config.

    Returns:
        ChangeAnalysis with all analysis results.
    """
    # Get diff if not provided
    if diff_text is None:
        diff_text = get_staged_diff()

    if not diff_text or not diff_text.strip():
        return ChangeAnalysis()

    # Parse the diff
    files = parse_diff(diff_text)

    if not files:
        return ChangeAnalysis()

    # Classify change type
    commit_type = classify_change_type(files, scope_rules)

    # Detect scope
    scope = detect_scope(files, scope_rules)

    # Also check for monorepo scope
    monorepo_scope = detect_monorepo_scope(files)
    if monorepo_scope:
        scope = monorepo_scope

    # Extract keywords
    keywords = extract_keywords(files)

    # Calculate statistics
    total_insertions = sum(f.added_lines for f in files)
    total_deletions = sum(f.removed_lines for f in files)
    total_files = len(files)

    # Detect breaking changes
    has_breaking = detect_breaking_changes(files)

    # Determine if this is a large change
    is_large = total_insertions + total_deletions > 200 or total_files > 10

    return ChangeAnalysis(
        files=files,
        commit_type=commit_type,
        scope=scope,
        description_keywords=keywords,
        total_insertions=total_insertions,
        total_deletions=total_deletions,
        total_files=total_files,
        has_breaking_change=has_breaking,
        is_large_change=is_large,
    )


def format_analysis_summary(analysis: ChangeAnalysis, lang: str = "en") -> str:
    """Format a change analysis summary for display.

    Args:
        analysis: The ChangeAnalysis result.
        lang: Language ('en' or 'zh').

    Returns:
        Formatted summary string.
    """
    from .utils import green, red, yellow, cyan, bold, dim, pluralize

    lines: List[str] = []

    if lang == "zh":
        lines.append(bold("变更分析:"))
        lines.append(f"  文件: {analysis.total_files} 个")
        lines.append(f"  插入: {green(f'+{analysis.total_insertions}')}")
        lines.append(f"  删除: {red(f'-{analysis.total_deletions}')}")
        lines.append(f"  类型: {cyan(analysis.commit_type)}")
        if analysis.scope:
            lines.append(f"  范围: {cyan(analysis.scope)}")
        if analysis.has_breaking_change:
            lines.append(f"  {yellow('⚠ 检测到可能的破坏性变更')}")
        if analysis.is_large_change:
            lines.append(f"  {yellow('⚠ 这是一个较大的变更')}")
        if analysis.description_keywords:
            lines.append(f"  关键词: {', '.join(analysis.description_keywords[:5])}")
    else:
        lines.append(bold("Change Analysis:"))
        lines.append(f"  Files: {analysis.total_files}")
        lines.append(f"  Insertions: {green(f'+{analysis.total_insertions}')}")
        lines.append(f"  Deletions: {red(f'-{analysis.total_deletions}')}")
        lines.append(f"  Type: {cyan(analysis.commit_type)}")
        if analysis.scope:
            lines.append(f"  Scope: {cyan(analysis.scope)}")
        if analysis.has_breaking_change:
            lines.append(f"  {yellow('⚠ Potential breaking changes detected')}")
        if analysis.is_large_change:
            lines.append(f"  {yellow('⚠ This is a large change')}")
        if analysis.description_keywords:
            lines.append(f"  Keywords: {', '.join(analysis.description_keywords[:5])}")

    return "\n".join(lines)
