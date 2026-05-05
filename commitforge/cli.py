"""
CommitForge CLI - Main command-line interface.

Provides all user-facing commands for generating, validating, and
managing Git commit messages.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional

from . import __version__
from .ai_generator import (
    BACKEND_REGISTRY,
    generate_commit_message,
    parse_ai_response,
)
from .config import Config, create_default_config
from .conventional import (
    ConventionalCommit,
    fix_commit_message,
    get_type_description,
    is_conventional,
    parse_commit,
    validate_commit,
)
from .git_analyzer import (
    ChangeAnalysis,
    analyze_changes,
    format_analysis_summary,
    get_last_commit_message,
    get_staged_diff,
    has_staged_changes,
    is_git_repository,
)
from .history import (
    format_history_report,
    format_recent_commits,
    run_history_analysis,
)
from .hook import (
    format_hook_status,
    get_hook_status,
    install_hook,
    is_hook_installed,
    uninstall_hook,
)
from .rules_engine import RulesEngine
from .templates import TemplateEngine
from .utils import (
    Colors,
    Spinner,
    bold,
    box,
    cyan,
    dim,
    green,
    magenta,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
    red,
    separator,
    yellow,
)


# ─── Command Handlers ─────────────────────────────────────────────────────────

def cmd_gen(args: argparse.Namespace) -> int:
    """Handle the 'gen' command - generate commit message.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    lang = args.lang or "en"

    # Check if in git repo
    if not is_git_repository():
        if lang == "zh":
            print_error("当前目录不在 Git 仓库中")
        else:
            print_error("Not in a git repository")
        return 1

    # Check for staged changes (unless in hook mode)
    if not args.hook_mode and not has_staged_changes():
        if lang == "zh":
            print_warning("没有暂存的变更。请先使用 git add 暂存文件。")
        else:
            print_warning("No staged changes. Please stage files with git add first.")
        return 1

    # Load configuration
    config = Config({
        "backend": args.backend,
        "language": lang,
        "emoji": args.emoji,
        "verbose": args.verbose,
        "dry_run": args.dry_run,
    })

    actual_lang = config.language
    backend_name = args.backend if args.no_ai else config.backend

    # If --no-ai, use rules engine
    if args.no_ai:
        backend_name = "rules"

    if args.verbose:
        if actual_lang == "zh":
            print_info(f"使用后端: {backend_name}")
        else:
            print_info(f"Using backend: {backend_name}")

    # Analyze changes
    if args.verbose:
        if actual_lang == "zh":
            print_info("正在分析变更...")
        else:
            print_info("Analyzing changes...")

    analysis = analyze_changes(
        scope_rules=config.get("scope_rules"),
    )

    if not analysis.files:
        if actual_lang == "zh":
            print_warning("没有检测到变更")
        else:
            print_warning("No changes detected")
        return 1

    # Show analysis summary if verbose
    if args.verbose:
        print()
        print(format_analysis_summary(analysis, actual_lang))
        print()

    # Generate commit message
    commit: Optional[ConventionalCommit] = None

    if backend_name == "rules":
        # Use rules engine (offline)
        if args.verbose:
            if actual_lang == "zh":
                print_info("使用规则引擎生成提交消息...")
            else:
                print_info("Generating commit message with rules engine...")

        engine = RulesEngine(
            lang=actual_lang,
            emoji=config.use_emoji,
            scope_rules=config.get("scope_rules"),
        )
        commit = engine.generate(
            analysis,
            force_type=args.type,
            force_scope=args.scope,
        )
    else:
        # Use AI backend
        try:
            backend_config = config.get_backend_config(backend_name)
            system_prompt = config.get("system_prompt", "")

            # Set language-specific system prompt if not custom
            if not system_prompt:
                if actual_lang == "zh":
                    from .ai_generator import DEFAULT_SYSTEM_PROMPT_ZH
                    system_prompt = DEFAULT_SYSTEM_PROMPT_ZH
                else:
                    from .ai_generator import DEFAULT_SYSTEM_PROMPT_EN
                    system_prompt = DEFAULT_SYSTEM_PROMPT_EN

            if args.verbose:
                if actual_lang == "zh":
                    print_info(f"正在使用 {backend_name} 生成提交消息...")
                else:
                    print_info(f"Generating commit message with {backend_name}...")

            with Spinner("Generating commit message..." if actual_lang == "en" else "正在生成提交消息..."):
                response = generate_commit_message(
                    analysis=analysis,
                    backend_name=backend_name,
                    backend_config=backend_config,
                    lang=actual_lang,
                    force_type=args.type,
                    force_scope=args.scope,
                    system_prompt=system_prompt,
                    streaming=False,
                )

            commit = parse_ai_response(response)

        except ValueError as e:
            print_error(str(e))
            if actual_lang == "zh":
                print_info("回退到规则引擎...")
            else:
                print_info("Falling back to rules engine...")

            engine = RulesEngine(
                lang=actual_lang,
                emoji=config.use_emoji,
                scope_rules=config.get("scope_rules"),
            )
            commit = engine.generate(
                analysis,
                force_type=args.type,
                force_scope=args.scope,
            )
        except Exception as e:
            print_error(f"{e}")
            if actual_lang == "zh":
                print_info("回退到规则引擎...")
            else:
                print_info("Falling back to rules engine...")

            engine = RulesEngine(
                lang=actual_lang,
                emoji=config.use_emoji,
                scope_rules=config.get("scope_rules"),
            )
            commit = engine.generate(
                analysis,
                force_type=args.type,
                force_scope=args.scope,
            )

    if commit is None:
        if actual_lang == "zh":
            print_error("无法生成提交消息")
        else:
            print_error("Failed to generate commit message")
        return 1

    # Format the message
    message = commit.format(emoji=config.use_emoji)

    # Handle output
    if args.hook_mode and args.output_file:
        # Write to file (hook mode)
        try:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(message + "\n")
        except (IOError, OSError) as e:
            print_error(f"Failed to write to {args.output_file}: {e}")
            return 1
        return 0

    # Display the generated message
    print()
    print(box(message, title="Generated Commit Message" if actual_lang == "en" else "生成的提交消息"))
    print()

    if args.dry_run:
        if actual_lang == "zh":
            print_info("试运行模式 - 未执行任何操作")
        else:
            print_info("Dry run mode - no changes made")
        return 0

    # Copy to clipboard option
    if actual_lang == "zh":
        print_info("使用以下命令提交:")
        print(dim(f'  git commit -m "{commit.description}"'))
    else:
        print_info("Use the following to commit:")
        print(dim(f'  git commit -m "{commit.description}"'))

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Handle the 'check' command - validate last commit message.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for valid, non-zero for invalid).
    """
    lang = args.lang or "en"

    # Get last commit message
    message = get_last_commit_message()
    if not message:
        if lang == "zh":
            print_error("无法获取最后一次提交消息")
        else:
            print_error("Could not get last commit message")
        return 1

    # Validate
    result = validate_commit(message, lang=lang)

    if result.is_valid:
        if lang == "zh":
            print_success("提交消息符合 Conventional Commits 规范")
        else:
            print_success("Commit message follows Conventional Commits specification")

        if result.warnings:
            for warning in result.warnings:
                print_warning(warning)
            print()

        # Show parsed commit info
        parsed = parse_commit(message)
        if parsed:
            if lang == "zh":
                print_header("提交信息")
                print(f"  类型:     {cyan(parsed.type)}")
                print(f"  描述:     {parsed.description}")
                if parsed.scope:
                    print(f"  范围:     {cyan(parsed.scope)}")
                if parsed.breaking_change:
                    print(f"  破坏性:   {yellow('是')}")
                if parsed.body:
                    print(f"  正文:     {dim(parsed.body[:100])}")
            else:
                print_header("Commit Info")
                print(f"  Type:     {cyan(parsed.type)}")
                print(f"  Desc:     {parsed.description}")
                if parsed.scope:
                    print(f"  Scope:    {cyan(parsed.scope)}")
                if parsed.breaking_change:
                    print(f"  Breaking: {yellow('Yes')}")
                if parsed.body:
                    print(f"  Body:     {dim(parsed.body[:100])}")

        return 0
    else:
        if lang == "zh":
            print_error("提交消息不符合 Conventional Commits 规范")
        else:
            print_error("Commit message does not follow Conventional Commits specification")

        print()
        for error in result.errors:
            print_error(error)
        for warning in result.warnings:
            print_warning(warning)

        if result.suggestions:
            print()
            if lang == "zh":
                print(bold("修复建议:"))
            else:
                print(bold("Suggestions:"))
            for suggestion in result.suggestions:
                print_info(suggestion)

            # Show auto-fixed version
            fixed = fix_commit_message(message, lang=lang)
            if fixed != message:
                print()
                if lang == "zh":
                    print(bold("自动修复版本:"))
                else:
                    print(bold("Auto-fixed version:"))
                print(dim(fixed))

        return 1


def cmd_history(args: argparse.Namespace) -> int:
    """Handle the 'history' command - show commit history analysis.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    lang = args.lang or "en"
    count = args.count or 50

    if not is_git_repository():
        if lang == "zh":
            print_error("当前目录不在 Git 仓库中")
        else:
            print_error("Not in a git repository")
        return 1

    if lang == "zh":
        print_info(f"正在分析最近 {count} 次提交...")
    else:
        print_info(f"Analyzing last {count} commits...")

    stats, suggestions, records = run_history_analysis(count=count, lang=lang)

    if not records:
        if lang == "zh":
            print_warning("没有找到提交记录")
        else:
            print_warning("No commits found")
        return 0

    # Show report
    print()
    print(format_history_report(stats, suggestions, lang=lang))

    # Show recent commits table
    if not args.stats_only:
        print()
        print(format_recent_commits(records, count=min(15, len(records)), lang=lang))
        print()

    return 0


def cmd_hook(args: argparse.Namespace) -> int:
    """Handle the 'hook' command - manage git hooks.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    lang = args.lang or "en"

    if args.action == "install":
        hook_type = args.hook_type or "bash"
        success = install_hook(hook_type=hook_type)
        return 0 if success else 1

    elif args.action == "uninstall":
        success = uninstall_hook()
        return 0 if success else 1

    elif args.action == "status":
        status = get_hook_status()
        print()
        print(format_hook_status(status, lang=lang))
        print()
        return 0

    else:
        if lang == "zh":
            print_error(f"未知操作: {args.action}")
        else:
            print_error(f"Unknown action: {args.action}")
        return 1


def cmd_config(args: argparse.Namespace) -> int:
    """Handle the 'config' command - show/edit configuration.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    lang = args.lang or "en"

    if args.action == "show":
        config = Config()
        print()
        print(config.show())
        print()
        return 0

    elif args.action == "init":
        path = create_default_config()
        if lang == "zh":
            print_success(f"配置文件已创建: {path}")
        else:
            print_success(f"Configuration file created: {path}")
        return 0

    elif args.action == "set":
        if not args.key or not args.value:
            if lang == "zh":
                print_error("请提供 --key 和 --value 参数")
            else:
                print_error("Please provide --key and --value parameters")
            return 1

        config = Config()
        config.set(args.key, args.value)
        saved_path = config.save_project_config()

        if lang == "zh":
            print_success(f"已保存配置: {args.key} = {args.value}")
            print_info(f"配置文件: {saved_path}")
        else:
            print_success(f"Configuration saved: {args.key} = {args.value}")
            print_info(f"Config file: {saved_path}")
        return 0

    else:
        if lang == "zh":
            print_error(f"未知操作: {args.action}")
        else:
            print_error(f"Unknown action: {args.action}")
        return 1


def cmd_init(args: argparse.Namespace) -> int:
    """Handle the 'init' command - initialize CommitForge configuration.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    lang = args.lang or "en"

    # Create config file
    path = create_default_config()
    if lang == "zh":
        print_success(f"配置文件已创建: {path}")
    else:
        print_success(f"Configuration file created: {path}")

    # Optionally install hook
    if args.install_hook:
        install_hook()

    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Handle the 'version' command - show version info.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    print(f"CommitForge v{__version__}")
    return 0


def cmd_examples(args: argparse.Namespace) -> int:
    """Handle the 'examples' command - show example commit messages.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    lang = args.lang or "en"
    engine = TemplateEngine(lang=lang, emoji=args.emoji)
    examples = engine.get_examples()

    if lang == "zh":
        print_header("Conventional Commits 示例")
    else:
        print_header("Conventional Commits Examples")

    for example in examples:
        print(f"  {example}")

    print()
    return 0


# ─── Argument Parser ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the main argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="commitforge",
        description="CommitForge - Intelligent Git commit message generator",
        epilog="Use 'commitforge <command> --help' for more information on a command.",
    )
    parser.add_argument(
        "-V", "--version",
        action="store_true",
        help="Show version and exit",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default=None,
        help="Output language (en/zh)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── gen command ──
    gen_parser = subparsers.add_parser(
        "gen",
        help="Generate commit message for staged changes",
        aliases=["generate"],
    )
    gen_parser.add_argument(
        "--backend",
        choices=list(BACKEND_REGISTRY.keys()) + ["rules"],
        default=None,
        help="AI backend to use",
    )
    gen_parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Use rules engine only (no AI)",
    )
    gen_parser.add_argument(
        "--type",
        default=None,
        help="Force commit type",
    )
    gen_parser.add_argument(
        "--scope",
        default=None,
        help="Force commit scope",
    )
    gen_parser.add_argument(
        "--emoji",
        action="store_true",
        help="Include emoji in commit message",
    )
    gen_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show generated message without committing",
    )
    gen_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    gen_parser.add_argument(
        "--hook-mode",
        action="store_true",
        help=argparse.SUPPRESS,  # Internal use by git hook
    )
    gen_parser.add_argument(
        "--output-file",
        default=None,
        help=argparse.SUPPRESS,  # Internal use by git hook
    )

    # ── check command ──
    check_parser = subparsers.add_parser(
        "check",
        help="Validate last commit message",
    )
    check_parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default=None,
        help="Output language",
    )

    # ── history command ──
    history_parser = subparsers.add_parser(
        "history",
        help="Show commit history analysis",
    )
    history_parser.add_argument(
        "--count", "-n",
        type=int,
        default=50,
        help="Number of commits to analyze (default: 50)",
    )
    history_parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Show only statistics, no commit table",
    )
    history_parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default=None,
        help="Output language",
    )

    # ── hook command ──
    hook_parser = subparsers.add_parser(
        "hook",
        help="Manage git hooks",
    )
    hook_subparsers = hook_parser.add_subparsers(dest="action", help="Hook actions")

    hook_install = hook_subparsers.add_parser("install", help="Install git hook")
    hook_install.add_argument(
        "--hook-type",
        choices=["bash", "python"],
        default="bash",
        help="Hook script type (default: bash)",
    )

    hook_subparsers.add_parser("uninstall", help="Uninstall git hook")
    hook_subparsers.add_parser("status", help="Show hook status")

    # ── config command ──
    config_parser = subparsers.add_parser(
        "config",
        help="Show/edit configuration",
    )
    config_subparsers = config_parser.add_subparsers(dest="action", help="Config actions")

    config_subparsers.add_parser("show", help="Show current configuration")
    config_subparsers.add_parser("init", help="Create default config file")

    config_set = config_subparsers.add_parser("set", help="Set a configuration value")
    config_set.add_argument("--key", required=True, help="Configuration key (dot notation)")
    config_set.add_argument("--value", required=True, help="Configuration value")

    # ── init command ──
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize CommitForge configuration",
    )
    init_parser.add_argument(
        "--install-hook",
        action="store_true",
        help="Also install git hook",
    )

    # ── examples command ──
    examples_parser = subparsers.add_parser(
        "examples",
        help="Show example commit messages",
    )
    examples_parser.add_argument(
        "--emoji",
        action="store_true",
        help="Show emoji in examples",
    )

    return parser


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CommitForge CLI.

    Args:
        argv: Optional command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle version flag
    if args.version:
        print(f"CommitForge v{__version__}")
        return 0

    # Handle no command (default to gen)
    if args.command is None or args.command in ("gen", "generate"):
        return cmd_gen(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "history":
        return cmd_history(args)
    elif args.command == "hook":
        return cmd_hook(args)
    elif args.command == "config":
        return cmd_config(args)
    elif args.command == "init":
        return cmd_init(args)
    elif args.command == "examples":
        return cmd_examples(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
