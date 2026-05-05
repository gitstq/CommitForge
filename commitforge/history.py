"""
Commit history analysis and learning for CommitForge.

Analyzes recent commit history to learn preferred commit style,
detect patterns, and generate statistics reports.
"""

import re
import subprocess
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .conventional import (
    STANDARD_TYPES,
    ConventionalCommit,
    parse_commit,
    validate_commit,
)
from .utils import Table, bold, cyan, dim, green, red, yellow, magenta


# ─── Constants ────────────────────────────────────────────────────────────────

# Git log format for parsing
GIT_LOG_FORMAT = "%H%n%s%n%b%n---COMMIT_END---"
GIT_LOG_SEPARATOR = "---COMMIT_END---"

# Type distribution bar chart characters
BAR_FULL = "█"
BAR_EMPTY = "░"
BAR_WIDTH = 30


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class CommitRecord:
    """A single commit record from history.

    Attributes:
        hash: Full commit hash.
        short_hash: Abbreviated commit hash.
        subject: Subject line.
        body: Full body text.
        parsed: Parsed ConventionalCommit (if valid format).
        is_valid: Whether the commit follows conventional format.
        validation_errors: List of validation error messages.
    """
    hash: str
    short_hash: str = ""
    subject: str = ""
    body: str = ""
    parsed: Optional[ConventionalCommit] = None
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class HistoryStats:
    """Statistics derived from commit history analysis.

    Attributes:
        total_commits: Total number of commits analyzed.
        valid_commits: Number of commits following conventional format.
        invalid_commits: Number of commits not following conventional format.
        type_distribution: Counter of commit types.
        scope_distribution: Counter of scopes used.
        avg_subject_length: Average subject line length.
        avg_body_lines: Average number of body lines.
        has_breaking: Number of commits with breaking changes.
        top_scopes: Most commonly used scopes.
        style_patterns: Detected style patterns.
    """
    total_commits: int = 0
    valid_commits: int = 0
    invalid_commits: int = 0
    type_distribution: Counter = field(default_factory=Counter)
    scope_distribution: Counter = field(default_factory=Counter)
    avg_subject_length: float = 0.0
    avg_body_lines: float = 0.0
    has_breaking: int = 0
    top_scopes: List[Tuple[str, int]] = field(default_factory=list)
    style_patterns: Dict[str, any] = field(default_factory=dict)

    @property
    def compliance_rate(self) -> float:
        """Return the percentage of commits following conventional format."""
        if self.total_commits == 0:
            return 0.0
        return (self.valid_commits / self.total_commits) * 100.0

    @property
    def most_common_type(self) -> Optional[str]:
        """Return the most commonly used commit type."""
        if self.type_distribution:
            return self.type_distribution.most_common(1)[0][0]
        return None


@dataclass
class HistorySuggestions:
    """Suggestions based on history analysis.

    Attributes:
        preferred_type: Most commonly used commit type.
        preferred_scopes: Commonly used scopes.
        avg_description_length: Average description length.
        body_usage_rate: How often body is used.
        scope_usage_rate: How often scope is used.
        suggestions: List of improvement suggestions.
    """
    preferred_type: str = "chore"
    preferred_scopes: List[str] = field(default_factory=list)
    avg_description_length: int = 0
    body_usage_rate: float = 0.0
    scope_usage_rate: float = 0.0
    suggestions: List[str] = field(default_factory=list)


# ─── Git History Operations ───────────────────────────────────────────────────

def get_commit_log(count: int = 50, author: Optional[str] = None,
                   since: Optional[str] = None,
                   branch: Optional[str] = None) -> str:
    """Get commit log from git.

    Args:
        count: Number of commits to retrieve.
        author: Optional author filter (email or name).
        since: Optional date filter (e.g., '2 weeks ago').
        branch: Optional branch to analyze.

    Returns:
        Raw git log output string.
    """
    cmd = [
        "git", "log",
        f"-{count}",
        "--format=" + GIT_LOG_FORMAT,
    ]

    if author:
        cmd.extend(["--author", author])
    if since:
        cmd.extend(["--since", since])
    if branch:
        cmd.append(branch)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def parse_commit_log(log_text: str) -> List[CommitRecord]:
    """Parse git log output into CommitRecord objects.

    Args:
        log_text: Raw git log output.

    Returns:
        List of CommitRecord objects.
    """
    if not log_text or not log_text.strip():
        return []

    records: List[CommitRecord] = []
    entries = log_text.split(GIT_LOG_SEPARATOR)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        lines = entry.split("\n")
        if not lines:
            continue

        commit_hash = lines[0].strip()
        short_hash = commit_hash[:7] if len(commit_hash) >= 7 else commit_hash

        # Find subject line (first non-empty line after hash)
        subject = ""
        body_start = 1
        for i in range(1, len(lines)):
            if lines[i].strip():
                subject = lines[i].strip()
                body_start = i + 1
                break

        # Body is everything after subject
        body_lines = []
        for i in range(body_start, len(lines)):
            line = lines[i].strip()
            if line:
                body_lines.append(line)

        body = "\n".join(body_lines)

        # Parse as conventional commit
        parsed = parse_commit(subject)
        is_valid = parsed is not None

        # Get validation details
        validation_errors: List[str] = []
        if not is_valid:
            result = validate_commit(subject)
            validation_errors = result.errors

        record = CommitRecord(
            hash=commit_hash,
            short_hash=short_hash,
            subject=subject,
            body=body,
            parsed=parsed,
            is_valid=is_valid,
            validation_errors=validation_errors,
        )
        records.append(record)

    return records


# ─── History Analysis ─────────────────────────────────────────────────────────

def analyze_history(records: List[CommitRecord]) -> HistoryStats:
    """Analyze commit history and compute statistics.

    Args:
        records: List of CommitRecord objects.

    Returns:
        HistoryStats with computed statistics.
    """
    stats = HistoryStats(total_commits=len(records))

    if not records:
        return stats

    type_counter: Counter = Counter()
    scope_counter: Counter = Counter()
    subject_lengths: List[int] = []
    body_line_counts: List[int] = []
    breaking_count = 0
    scope_used = 0
    body_used = 0

    for record in records:
        if record.is_valid and record.parsed:
            stats.valid_commits += 1
            type_counter[record.parsed.type] += 1

            if record.parsed.scope:
                scope_counter[record.parsed.scope] += 1
                scope_used += 1

            if record.parsed.body:
                body_used += 1
                body_line_counts.append(len(record.parsed.body.split("\n")))

            if record.parsed.breaking_change:
                breaking_count += 1
        else:
            stats.invalid_commits += 1

        subject_lengths.append(len(record.subject))

    stats.type_distribution = type_counter
    stats.scope_distribution = scope_counter
    stats.has_breaking = breaking_count

    # Calculate averages
    if subject_lengths:
        stats.avg_subject_length = sum(subject_lengths) / len(subject_lengths)

    if body_line_counts:
        stats.avg_body_lines = sum(body_line_counts) / len(body_line_counts)

    # Top scopes
    stats.top_scopes = scope_counter.most_common(10)

    # Style patterns
    stats.style_patterns = {
        "scope_usage_rate": scope_used / len(records) if records else 0,
        "body_usage_rate": body_used / len(records) if records else 0,
        "avg_description_length": _calc_avg_description_length(records),
    }

    return stats


def _calc_avg_description_length(records: List[CommitRecord]) -> float:
    """Calculate average description length from valid commits.

    Args:
        records: List of CommitRecord objects.

    Returns:
        Average description length.
    """
    lengths: List[int] = []
    for record in records:
        if record.parsed and record.parsed.description:
            lengths.append(len(record.parsed.description))

    return sum(lengths) / len(lengths) if lengths else 0.0


def generate_suggestions(stats: HistoryStats, lang: str = "en") -> HistorySuggestions:
    """Generate improvement suggestions based on history analysis.

    Args:
        stats: The history statistics.
        lang: Language ('en' or 'zh').

    Returns:
        HistorySuggestions with improvement suggestions.
    """
    suggestions: List[str] = []

    # Compliance rate suggestion
    if stats.compliance_rate < 50:
        if lang == "zh":
            suggestions.append(
                f"只有 {stats.compliance_rate:.0f}% 的提交遵循 Conventional Commits 格式。"
                f"建议团队统一使用标准格式。"
            )
        else:
            suggestions.append(
                f"Only {stats.compliance_rate:.0f}% of commits follow Conventional Commits. "
                f"Consider adopting the standard format."
            )
    elif stats.compliance_rate < 80:
        if lang == "zh":
            suggestions.append(
                f"Conventional Commits 合规率为 {stats.compliance_rate:.0f}%，还有提升空间。"
            )
        else:
            suggestions.append(
                f"Conventional Commits compliance is {stats.compliance_rate:.0f}%. "
                f"There's room for improvement."
            )

    # Scope usage suggestion
    scope_rate = stats.style_patterns.get("scope_usage_rate", 0)
    if scope_rate < 0.3 and stats.total_commits > 10:
        if lang == "zh":
            suggestions.append("很少使用 scope，建议为变更添加模块范围以提升可读性。")
        else:
            suggestions.append(
                "Scope is rarely used. Consider adding module scope for better readability."
            )

    # Body usage suggestion
    body_rate = stats.style_patterns.get("body_usage_rate", 0)
    if body_rate < 0.2 and stats.total_commits > 10:
        if lang == "zh":
            suggestions.append("很少使用提交正文，建议为复杂变更添加详细说明。")
        else:
            suggestions.append(
                "Commit body is rarely used. Consider adding details for complex changes."
            )

    # Subject length suggestion
    if stats.avg_subject_length > 72:
        if lang == "zh":
            suggestions.append(
                f"平均主题行长度为 {stats.avg_subject_length:.0f} 字符，"
                f"建议控制在 72 字符以内。"
            )
        else:
            suggestions.append(
                f"Average subject length is {stats.avg_subject_length:.0f} chars. "
                f"Consider keeping it under 72 characters."
            )

    # Type distribution suggestion
    if stats.type_distribution:
        top_type, top_count = stats.type_distribution.most_common(1)[0]
        top_ratio = top_count / stats.total_commits
        if top_ratio > 0.5:
            if lang == "zh":
                suggestions.append(
                    f"'{top_type}' 类型占比过高 ({top_ratio:.0%})，"
                    f"请检查是否有其他类型的变更被错误分类。"
                )
            else:
                suggestions.append(
                    f"Type '{top_type}' is overrepresented ({top_ratio:.0%}). "
                    f"Check if other types are being miscategorized."
                )

    # Breaking change awareness
    if stats.has_breaking > 0:
        if lang == "zh":
            suggestions.append(
                f"检测到 {stats.has_breaking} 个破坏性变更，"
                f"确保在 CHANGELOG 中记录。"
            )
        else:
            suggestions.append(
                f"Found {stats.has_breaking} breaking change(s). "
                f"Make sure they're documented in the CHANGELOG."
            )

    return HistorySuggestions(
        preferred_type=stats.most_common_type or "chore",
        preferred_scopes=[s for s, _ in stats.top_scopes[:5]],
        avg_description_length=int(stats.style_patterns.get("avg_description_length", 0)),
        body_usage_rate=body_rate,
        scope_usage_rate=scope_rate,
        suggestions=suggestions,
    )


# ─── Report Generation ────────────────────────────────────────────────────────

def format_type_distribution_chart(stats: HistoryStats) -> str:
    """Format a terminal bar chart of type distribution.

    Args:
        stats: The history statistics.

    Returns:
        Formatted bar chart string.
    """
    if not stats.type_distribution:
        return dim("  No commit type data available.")

    lines: List[str] = []
    total = sum(stats.type_distribution.values())
    max_count = max(stats.type_distribution.values())

    for commit_type in STANDARD_TYPES:
        count = stats.type_distribution.get(commit_type, 0)
        if count == 0:
            continue

        ratio = count / max_count if max_count > 0 else 0
        filled = int(BAR_WIDTH * ratio)
        empty = BAR_WIDTH - filled
        bar = green(BAR_FULL * filled) + dim(BAR_EMPTY * empty)
        percent = (count / total * 100) if total > 0 else 0

        lines.append(f"  {commit_type:<10} {bar} {count:>3} ({percent:5.1f}%)")

    return "\n".join(lines)


def format_history_report(stats: HistoryStats, suggestions: HistorySuggestions,
                          lang: str = "en") -> str:
    """Format a complete history analysis report.

    Args:
        stats: The history statistics.
        suggestions: The improvement suggestions.
        lang: Language ('en' or 'zh').

    Returns:
        Formatted report string.
    """
    lines: List[str] = []

    # Header
    lines.append(bold(cyan("━━ Commit History Analysis ━━")))
    lines.append("")

    # Overview
    if lang == "zh":
        lines.append(bold("概览:"))
        lines.append(f"  总提交数:     {stats.total_commits}")
        lines.append(f"  合规提交:     {green(str(stats.valid_commits))}")
        lines.append(f"  非合规提交:   {red(str(stats.invalid_commits))}")
        lines.append(f"  合规率:       {stats.compliance_rate:.1f}%")
        lines.append(f"  破坏性变更:   {stats.has_breaking}")
        lines.append(f"  平均主题长度: {stats.avg_subject_length:.0f} 字符")
    else:
        lines.append(bold("Overview:"))
        lines.append(f"  Total commits:    {stats.total_commits}")
        lines.append(f"  Valid commits:    {green(str(stats.valid_commits))}")
        lines.append(f"  Invalid commits:  {red(str(stats.invalid_commits))}")
        lines.append(f"  Compliance rate:  {stats.compliance_rate:.1f}%")
        lines.append(f"  Breaking changes: {stats.has_breaking}")
        lines.append(f"  Avg subject len:  {stats.avg_subject_length:.0f} chars")

    lines.append("")

    # Type distribution
    if lang == "zh":
        lines.append(bold("类型分布:"))
    else:
        lines.append(bold("Type Distribution:"))
    lines.append(format_type_distribution_chart(stats))
    lines.append("")

    # Scope distribution
    if stats.top_scopes:
        if lang == "zh":
            lines.append(bold("常用范围:"))
        else:
            lines.append(bold("Top Scopes:"))
        for scope, count in stats.top_scopes[:8]:
            lines.append(f"  {cyan(scope):<20} {count:>3}")
        lines.append("")

    # Style patterns
    if lang == "zh":
        lines.append(bold("风格模式:"))
        lines.append(f"  Scope 使用率: {stats.style_patterns.get('scope_usage_rate', 0) * 100:.0f}%")
        lines.append(f"  Body 使用率:  {stats.style_patterns.get('body_usage_rate', 0) * 100:.0f}%")
        lines.append(f"  平均描述长度: {stats.style_patterns.get('avg_description_length', 0):.0f} 字符")
    else:
        lines.append(bold("Style Patterns:"))
        lines.append(f"  Scope usage:    {stats.style_patterns.get('scope_usage_rate', 0) * 100:.0f}%")
        lines.append(f"  Body usage:     {stats.style_patterns.get('body_usage_rate', 0) * 100:.0f}%")
        lines.append(f"  Avg desc len:   {stats.style_patterns.get('avg_description_length', 0):.0f} chars")
    lines.append("")

    # Suggestions
    if suggestions.suggestions:
        if lang == "zh":
            lines.append(bold(yellow("改进建议:")))
        else:
            lines.append(bold(yellow("Suggestions:")))
        for i, suggestion in enumerate(suggestions, 1):
            lines.append(f"  {yellow(str(i) + '.')} {suggestion}")
        lines.append("")

    return "\n".join(lines)


def format_recent_commits(records: List[CommitRecord], count: int = 10,
                           lang: str = "en") -> str:
    """Format a table of recent commits.

    Args:
        records: List of CommitRecord objects.
        count: Maximum number of commits to show.
        lang: Language ('en' or 'zh').

    Returns:
        Formatted table string.
    """
    if not records:
        if lang == "zh":
            return dim("  没有找到提交记录。")
        return dim("  No commits found.")

    table = Table(
        ["Hash", "Type", "Scope", "Description"],
        title=bold("Recent Commits") if lang == "en" else bold("最近提交")
    )
    table.set_alignment(0, "left")
    table.set_alignment(3, "left")

    for record in records[:count]:
        if record.parsed:
            commit_type = record.parsed.type
            scope = record.parsed.scope or "-"
            description = record.parsed.description
            # Truncate long descriptions
            if len(description) > 50:
                description = description[:47] + "..."
        else:
            commit_type = red("invalid")
            scope = "-"
            description = record.subject[:50]
            if len(record.subject) > 50:
                description += "..."

        table.add_row(
            dim(record.short_hash),
            commit_type,
            cyan(scope) if scope != "-" else dim(scope),
            description,
        )

    return table.render()


def run_history_analysis(count: int = 50, lang: str = "en") -> Tuple[HistoryStats, HistorySuggestions, List[CommitRecord]]:
    """Run a complete history analysis.

    Args:
        count: Number of commits to analyze.
        lang: Language ('en' or 'zh').

    Returns:
        Tuple of (HistoryStats, HistorySuggestions, List[CommitRecord]).
    """
    log_text = get_commit_log(count=count)
    records = parse_commit_log(log_text)
    stats = analyze_history(records)
    suggestions = generate_suggestions(stats, lang)

    return stats, suggestions, records
