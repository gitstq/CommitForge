"""
Shared utilities for CommitForge.

Provides terminal colors, formatting helpers, progress indicators,
table rendering, and other common utilities used across the project.
"""

import os
import sys
import textwrap
import time
from typing import List, Optional, Tuple


# ─── Terminal Color Support ───────────────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output with auto-detection."""

    # Reset
    RESET = "\033[0m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    ITALIC = "\033[3m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    @classmethod
    def disable(cls) -> None:
        """Disable all colors by replacing codes with empty strings."""
        for attr in dir(cls):
            if attr.startswith("_") or attr in ("disable", "enabled", "strip"):
                continue
            val = getattr(cls, attr)
            if isinstance(val, str):
                setattr(cls, attr, "")

    @classmethod
    def enabled(cls) -> bool:
        """Check if colors are currently enabled."""
        return cls.RESET != ""

    @classmethod
    def strip(cls, text: str) -> str:
        """Remove all ANSI color codes from text."""
        import re
        return re.sub(r"\033\[[0-9;]*m", "", text)

    @classmethod
    def auto_detect(cls) -> None:
        """Auto-detect terminal color support and disable if unsupported."""
        # Check NO_COLOR environment variable (https://no-color.org/)
        if os.environ.get("NO_COLOR"):
            cls.disable()
            return

        # Check if running in a terminal
        if not sys.stdout.isatty():
            cls.disable()
            return

        # Check for common terminals that don't support colors
        term = os.environ.get("TERM", "").lower()
        if term in ("dumb", "unknown"):
            cls.disable()
            return

        # Check for Windows and try to enable ANSI support
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # STD_OUTPUT_HANDLE = -11
                handle = kernel32.GetStdHandle(-11)
                mode = ctypes.c_ulong()
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            except Exception:
                cls.disable()


# Auto-detect color support on import
Colors.auto_detect()


# ─── Color Formatting Helpers ─────────────────────────────────────────────────

def style(text: str, *styles: str) -> str:
    """Apply one or more color/style codes to text.

    Args:
        text: The text to style.
        *styles: Color/style attribute names from Colors class.

    Returns:
        Styled text string.
    """
    result = ""
    for s in styles:
        code = getattr(Colors, s.upper(), "")
        result += code
    result += text
    result += Colors.RESET
    return result


def bold(text: str) -> str:
    """Return text in bold."""
    return style(text, "BOLD")


def red(text: str) -> str:
    """Return text in red."""
    return style(text, "RED")


def green(text: str) -> str:
    """Return text in green."""
    return style(text, "GREEN")


def yellow(text: str) -> str:
    """Return text in yellow."""
    return style(text, "YELLOW")


def blue(text: str) -> str:
    """Return text in blue."""
    return style(text, "BLUE")


def cyan(text: str) -> str:
    """Return text in cyan."""
    return style(text, "CYAN")


def magenta(text: str) -> str:
    """Return text in magenta."""
    return style(text, "MAGENTA")


def dim(text: str) -> str:
    """Return text in dim style."""
    return style(text, "DIM")


def bright(text: str) -> str:
    """Return text in bright white."""
    return style(text, "BRIGHT_WHITE")


# ─── Progress Indicator ───────────────────────────────────────────────────────

class Spinner:
    """A simple terminal spinner for progress indication."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    INTERVAL = 0.08  # seconds between frames

    def __init__(self, message: str = "Loading..."):
        """Initialize spinner with a message.

        Args:
            message: The message to display alongside the spinner.
        """
        self._message = message
        self._running = False
        self._frame_idx = 0

    def _render(self) -> None:
        """Render the current spinner frame."""
        frame = self.FRAMES[self._frame_idx % len(self.FRAMES)]
        sys.stdout.write(f"\r{cyan(frame)} {self._message}")
        sys.stdout.flush()
        self._frame_idx += 1

    def __enter__(self) -> "Spinner":
        """Start the spinner."""
        self._running = True
        self._render()
        # Start a background thread for animation
        import threading
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def _spin(self) -> None:
        """Spin animation loop."""
        while self._running:
            self._render()
            time.sleep(self.INTERVAL)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the spinner and clear the line."""
        self._running = False
        if hasattr(self, "_thread"):
            self._thread.join(timeout=0.5)
        # Clear the line
        sys.stdout.write("\r" + " " * (len(self._message) + 3) + "\r")
        sys.stdout.flush()

    def update_message(self, message: str) -> None:
        """Update the spinner message.

        Args:
            message: New message to display.
        """
        self._message = message


# ─── Table Formatting ─────────────────────────────────────────────────────────

class Table:
    """Simple terminal table renderer with alignment support."""

    def __init__(self, headers: List[str], title: str = ""):
        """Initialize a table.

        Args:
            headers: List of column header strings.
            title: Optional table title.
        """
        self._headers = headers
        self._rows: List[List[str]] = []
        self._alignments: List[str] = ["left"] * len(headers)
        self._title = title
        self._col_widths: List[int] = [len(h) for h in headers]

    def set_alignment(self, col: int, align: str) -> "Table":
        """Set alignment for a column.

        Args:
            col: Column index (0-based).
            align: 'left', 'right', or 'center'.

        Returns:
            Self for method chaining.
        """
        if 0 <= col < len(self._alignments):
            self._alignments[col] = align
        return self

    def add_row(self, *values: str) -> "Table":
        """Add a row to the table.

        Args:
            *values: Column values as strings.

        Returns:
            Self for method chaining.
        """
        row = list(values)
        self._rows.append(row)
        for i, val in enumerate(row):
            if i < len(self._col_widths):
                display_len = len(Colors.strip(str(val)))
                if display_len > self._col_widths[i]:
                    self._col_widths[i] = display_len
        return self

    def _align_cell(self, value: str, width: int, align: str) -> str:
        """Align a cell value within the given width.

        Args:
            value: The cell value string.
            width: The column width (in display characters).
            align: Alignment type.

        Returns:
            Padded cell string.
        """
        display_len = len(Colors.strip(value))
        padding = max(0, width - display_len)
        if align == "right":
            return " " * padding + value
        elif align == "center":
            left_pad = padding // 2
            right_pad = padding - left_pad
            return " " * left_pad + value + " " * right_pad
        else:
            return value + " " * padding

    def render(self) -> str:
        """Render the table as a formatted string.

        Returns:
            The rendered table string.
        """
        lines: List[str] = []

        # Title
        if self._title:
            lines.append(bold(self._title))
            lines.append("")

        # Separator line
        sep = "+" + "+".join("-" * (w + 2) for w in self._col_widths) + "+"
        lines.append(sep)

        # Header row
        header_cells = []
        for i, h in enumerate(self._headers):
            header_cells.append(self._align_cell(bold(h), self._col_widths[i], "left"))
        lines.append("| " + " | ".join(header_cells) + " |")
        lines.append(sep)

        # Data rows
        for row in self._rows:
            cells = []
            for i, val in enumerate(row):
                align = self._alignments[i] if i < len(self._alignments) else "left"
                width = self._col_widths[i] if i < len(self._col_widths) else 10
                cells.append(self._align_cell(str(val), width, align))
            lines.append("| " + " | ".join(cells) + " |")

        lines.append(sep)
        return "\n".join(lines)

    def __str__(self) -> str:
        """Return the rendered table string."""
        return self.render()


# ─── Progress Bar ─────────────────────────────────────────────────────────────

class ProgressBar:
    """A simple terminal progress bar."""

    def __init__(self, total: int, width: int = 40, label: str = ""):
        """Initialize progress bar.

        Args:
            total: Total number of items/steps.
            width: Width of the progress bar in characters.
            label: Optional label to display.
        """
        self._total = total
        self._width = width
        self._label = label
        self._current = 0

    def update(self, current: int) -> None:
        """Update the progress bar.

        Args:
            current: Current progress value.
        """
        self._current = min(current, self._total)
        self._render()

    def _render(self) -> None:
        """Render the progress bar to stdout."""
        if self._total == 0:
            return
        ratio = self._current / self._total
        filled = int(self._width * ratio)
        empty = self._width - filled

        bar = green("█" * filled) + dim("░" * empty)
        percent = f"{ratio * 100:.0f}%"

        label_part = f"{self._label} " if self._label else ""
        sys.stdout.write(f"\r{label_part}[{bar}] {percent} ({self._current}/{self._total})")
        sys.stdout.flush()

    def finish(self) -> None:
        """Complete the progress bar and print a newline."""
        self.update(self._total)
        sys.stdout.write("\n")
        sys.stdout.flush()


# ─── String Utilities ─────────────────────────────────────────────────────────

def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum display length, preserving ANSI codes.

    Args:
        text: The text to truncate.
        max_length: Maximum display length (excluding suffix).
        suffix: Suffix to append when truncated.

    Returns:
        Truncated text string.
    """
    display_text = Colors.strip(text)
    if len(display_text) <= max_length:
        return text

    # Find where to cut in the original text (accounting for ANSI codes)
    result_chars = []
    display_count = 0
    in_escape = False
    for char in text:
        if char == "\033":
            in_escape = True
            result_chars.append(char)
            continue
        if in_escape:
            result_chars.append(char)
            if char == "m":
                in_escape = False
            continue
        if display_count >= max_length - len(suffix):
            break
        result_chars.append(char)
        display_count += 1

    result = "".join(result_chars) + dim(suffix)
    return result


def wrap_text(text: str, width: int = 72, indent: str = "") -> str:
    """Wrap text to a specified width with optional indent.

    Args:
        text: The text to wrap.
        width: Maximum line width.
        indent: Indent string for wrapped lines.

    Returns:
        Wrapped text string.
    """
    lines = text.split("\n")
    wrapped_lines = []
    for line in lines:
        if not line.strip():
            wrapped_lines.append("")
            continue
        wrapped = textwrap.wrap(
            line, width=width,
            initial_indent=indent,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if wrapped:
            wrapped_lines.extend(wrapped)
        else:
            wrapped_lines.append("")
    return "\n".join(wrapped_lines)


def format_file_size(size_bytes: int) -> str:
    """Format a file size in human-readable format.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Human-readable file size string.
    """
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_idx = 0
    size = float(size_bytes)
    while size >= 1024.0 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1
    if unit_idx == 0:
        return f"{int(size)} {units[unit_idx]}"
    return f"{size:.1f} {units[unit_idx]}"


def pluralize(count: int, singular: str, plural: str = "") -> str:
    """Return the singular or plural form based on count.

    Args:
        count: The count to base the form on.
        singular: Singular form of the word.
        plural: Plural form. If empty, appends 's' to singular.

    Returns:
        The appropriate form of the word.
    """
    if not plural:
        plural = singular + "s"
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural}"


def box(text: str, title: str = "", color: str = "CYAN") -> str:
    """Draw a box around text.

    Args:
        text: The text to box.
        title: Optional title for the box.
        color: Color name from Colors class.

    Returns:
        Boxed text string.
    """
    color_code = getattr(Colors, color.upper(), "")
    lines = text.split("\n")
    max_width = max(len(Colors.strip(line)) for line in lines) if lines else 0

    if title:
        title_display = f" {title} "
        max_width = max(max_width, len(title_display))

    top = color_code + "┌" + "─" * (max_width + 2) + "┐" + Colors.RESET
    bottom = color_code + "└" + "─" * (max_width + 2) + "┘" + Colors.RESET

    result_lines = [top]

    if title:
        title_line = color_code + "├" + title_display + "─" * (max_width - len(title_display) + 2) + "┤" + Colors.RESET
        result_lines.append(title_line)

    for line in lines:
        display_len = len(Colors.strip(line))
        padding = max_width - display_len
        result_lines.append(
            color_code + "│ " + Colors.RESET + line + " " * padding + color_code + " │" + Colors.RESET
        )

    result_lines.append(bottom)
    return "\n".join(result_lines)


def print_success(message: str) -> None:
    """Print a success message with a checkmark.

    Args:
        message: The success message.
    """
    print(f"  {green('✓')} {message}")


def print_error(message: str) -> None:
    """Print an error message with an X mark.

    Args:
        message: The error message.
    """
    print(f"  {red('✗')} {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message with a warning sign.

    Args:
        message: The warning message.
    """
    print(f"  {yellow('⚠')} {message}")


def print_info(message: str) -> None:
    """Print an info message with an arrow.

    Args:
        message: The info message.
    """
    print(f"  {blue('→')} {message}")


def print_header(message: str) -> None:
    """Print a section header.

    Args:
        message: The header message.
    """
    print()
    print(bold(cyan(f"━━ {message} ━━")))
    print()


def separator(char: str = "─", width: int = 50) -> str:
    """Create a horizontal separator line.

    Args:
        char: Character to use for the separator.
        width: Width of the separator.

    Returns:
        Separator string.
    """
    return dim(char * width)
