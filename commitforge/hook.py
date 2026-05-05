"""
Git hook integration for CommitForge.

Manages the prepare-commit-msg git hook to automatically generate
commit messages before each commit.
"""

import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ─── Constants ────────────────────────────────────────────────────────────────

HOOK_FILE_NAME = "prepare-commit-msg"

# The hook script content
HOOK_SCRIPT = """#!/usr/bin/env bash
# CommitForge prepare-commit-msg hook
# This hook is automatically installed by CommitForge.
# To bypass, use: git commit --no-verify

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"

# Only generate message for regular commits (not merge, squash, etc.)
if [ -n "$COMMIT_SOURCE" ]; then
    exit 0
fi

# Check if the commit message file already has content (user provided)
# If the user has already written a message, don't overwrite it
if [ -s "$COMMIT_MSG_FILE" ]; then
    # Check if the content is just comments (git default template)
    FIRST_LINE=$(head -n 1 "$COMMIT_MSG_FILE" 2>/dev/null)
    if [ -n "$FIRST_LINE" ] && [ "${FIRST_LINE#\#}" != "$FIRST_LINE" ]; then
        # File only contains comments, safe to generate
        :
    else
        # User has written content, don't overwrite
        exit 0
    fi
fi

# Check if commitforge is available
if ! command -v commitforge &> /dev/null; then
    # Try python -m commitforge as fallback
    if ! python -m commitforge gen --hook-mode --output-file "$COMMIT_MSG_FILE" 2>/dev/null; then
        if ! python3 -m commitforge gen --hook-mode --output-file "$COMMIT_MSG_FILE" 2>/dev/null; then
            exit 0
        fi
    fi
else
    commitforge gen --hook-mode --output-file "$COMMIT_MSG_FILE" 2>/dev/null
fi

exit 0
"""

HOOK_SCRIPT_PYTHON = """#!/usr/bin/env python3
\"\"\"CommitForge prepare-commit-msg hook.

This hook is automatically installed by CommitForge.
To bypass, use: git commit --no-verify
\"\"\"

import os
import subprocess
import sys


def main():
    commit_msg_file = sys.argv[1] if len(sys.argv) > 1 else ""
    commit_source = sys.argv[2] if len(sys.argv) > 2 else ""

    # Only generate for regular commits
    if commit_source:
        sys.exit(0)

    # Check if user has already written a message
    if commit_msg_file and os.path.isfile(commit_msg_file):
        with open(commit_msg_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        # If there's real content (not just comments), don't overwrite
        if content and not all(line.startswith("#") for line in content.split("\\n") if line.strip()):
            sys.exit(0)

    # Try to run commitforge
    try:
        result = subprocess.run(
            [sys.executable, "-m", "commitforge", "gen",
             "--hook-mode", "--output-file", commit_msg_file],
            capture_output=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
"""


# ─── Hook Management ──────────────────────────────────────────────────────────

def get_hooks_dir() -> Optional[str]:
    """Get the git hooks directory path.

    Returns:
        Path to the .git/hooks directory, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            git_dir = result.stdout.strip()
            hooks_dir = os.path.join(git_dir, "hooks")
            return hooks_dir
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def get_hook_path() -> Optional[str]:
    """Get the full path to the prepare-commit-msg hook.

    Returns:
        Path to the hook file, or None if not in a git repo.
    """
    hooks_dir = get_hooks_dir()
    if hooks_dir:
        return os.path.join(hooks_dir, HOOK_FILE_NAME)
    return None


def is_hook_installed() -> bool:
    """Check if the CommitForge hook is already installed.

    Returns:
        True if the hook is installed.
    """
    hook_path = get_hook_path()
    if not hook_path or not os.path.isfile(hook_path):
        return False

    try:
        with open(hook_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for our marker
        return "CommitForge" in content or "commitforge" in content
    except (IOError, OSError):
        return False


def install_hook(hook_type: str = "bash") -> bool:
    """Install the prepare-commit-msg hook.

    Args:
        hook_type: Type of hook script ('bash' or 'python').

    Returns:
        True if installation was successful.
    """
    hooks_dir = get_hooks_dir()
    if not hooks_dir:
        print("Error: Not in a git repository.", file=sys.stderr)
        return False

    # Create hooks directory if it doesn't exist
    os.makedirs(hooks_dir, exist_ok=True)

    hook_path = os.path.join(hooks_dir, HOOK_FILE_NAME)

    # Check if a hook already exists
    if os.path.isfile(hook_path):
        if is_hook_installed():
            # Already our hook, just update it
            pass
        else:
            # Back up existing hook
            backup_path = hook_path + ".backup"
            try:
                import shutil
                shutil.copy2(hook_path, backup_path)
                print(f"Backed up existing hook to: {backup_path}")
            except (IOError, OSError) as e:
                print(f"Warning: Could not back up existing hook: {e}", file=sys.stderr)

    # Write the hook script
    if hook_type == "python":
        script_content = HOOK_SCRIPT_PYTHON
    else:
        script_content = HOOK_SCRIPT

    try:
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Make the hook executable
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        print(f"Hook installed successfully: {hook_path}")
        return True
    except (IOError, OSError) as e:
        print(f"Error installing hook: {e}", file=sys.stderr)
        return False


def uninstall_hook() -> bool:
    """Uninstall the CommitForge prepare-commit-msg hook.

    Returns:
        True if uninstallation was successful.
    """
    hook_path = get_hook_path()
    if not hook_path:
        print("Error: Not in a git repository.", file=sys.stderr)
        return False

    if not os.path.isfile(hook_path):
        print("Hook is not installed.")
        return True

    if not is_hook_installed():
        print("Hook exists but was not installed by CommitForge. Not removing.")
        return False

    try:
        os.remove(hook_path)
        print(f"Hook uninstalled: {hook_path}")

        # Check if there's a backup
        backup_path = hook_path + ".backup"
        if os.path.isfile(backup_path):
            import shutil
            shutil.copy2(backup_path, hook_path)
            os.remove(backup_path)
            print(f"Restored previous hook from backup.")

        return True
    except (IOError, OSError) as e:
        print(f"Error uninstalling hook: {e}", file=sys.stderr)
        return False


def get_hook_status() -> dict:
    """Get the current status of the git hook.

    Returns:
        Dictionary with hook status information.
    """
    hook_path = get_hook_path()
    hooks_dir = get_hooks_dir()

    status = {
        "in_git_repo": hooks_dir is not None,
        "hooks_dir": hooks_dir,
        "hook_path": hook_path,
        "installed": False,
        "is_commitforge": False,
        "is_executable": False,
        "backup_exists": False,
    }

    if hook_path and os.path.isfile(hook_path):
        status["installed"] = True
        status["is_commitforge"] = is_hook_installed()

        # Check if executable
        try:
            st = os.stat(hook_path)
            status["is_executable"] = bool(st.st_mode & stat.S_IEXEC)
        except OSError:
            pass

        # Check for backup
        backup_path = hook_path + ".backup"
        status["backup_exists"] = os.path.isfile(backup_path)

    return status


def format_hook_status(status: dict, lang: str = "en") -> str:
    """Format hook status for display.

    Args:
        status: The hook status dictionary.
        lang: Language ('en' or 'zh').

    Returns:
        Formatted status string.
    """
    from .utils import green, red, yellow, dim, bold

    lines: List[str] = []

    if lang == "zh":
        lines.append(bold("Git Hook 状态:"))
        lines.append(f"  Git 仓库:     {'是' if status['in_git_repo'] else '否'}")
        lines.append(f"  Hook 目录:    {status['hooks_dir'] or '未找到'}")
        lines.append(f"  Hook 文件:    {status['hook_path'] or '未找到'}")

        if status["installed"]:
            lines.append(f"  已安装:       {green('是')}")
            lines.append(f"  CommitForge:  {'是' if status['is_commitforge'] else '否 (其他来源)'}")
            lines.append(f"  可执行:       {'是' if status['is_executable'] else yellow('否')}")
            if status["backup_exists"]:
                lines.append(f"  备份存在:     是")
        else:
            lines.append(f"  已安装:       {red('否')}")
    else:
        lines.append(bold("Git Hook Status:"))
        lines.append(f"  Git repo:      {'Yes' if status['in_git_repo'] else 'No'}")
        lines.append(f"  Hooks dir:     {status['hooks_dir'] or 'Not found'}")
        lines.append(f"  Hook file:     {status['hook_path'] or 'Not found'}")

        if status["installed"]:
            lines.append(f"  Installed:     {green('Yes')}")
            lines.append(f"  CommitForge:   {'Yes' if status['is_commitforge'] else 'No (other source)'}")
            lines.append(f"  Executable:    {'Yes' if status['is_executable'] else yellow('No')}")
            if status["backup_exists"]:
                lines.append(f"  Backup exists: Yes")
        else:
            lines.append(f"  Installed:     {red('No')}")

    return "\n".join(lines)
