"""Tests for CLI argument parsing."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commitforge.cli import build_parser


class TestCLIParser(unittest.TestCase):
    """Tests for the CLI argument parser."""

    def setUp(self):
        """Set up parser for tests."""
        self.parser = build_parser()

    def test_no_args_defaults_to_gen(self):
        """Test that no arguments defaults to gen command."""
        args = self.parser.parse_args([])
        # When no command is given, command is None and main() defaults to gen
        self.assertIsNone(args.command)

    def test_gen_command(self):
        """Test parsing gen command."""
        args = self.parser.parse_args(["gen"])
        self.assertEqual(args.command, "gen")

    def test_generate_alias(self):
        """Test that 'generate' is an alias for 'gen'."""
        args = self.parser.parse_args(["generate"])
        self.assertEqual(args.command, "generate")

    def test_gen_backend_flag(self):
        """Test --backend flag."""
        args = self.parser.parse_args(["gen", "--backend", "openai"])
        self.assertEqual(args.backend, "openai")

    def test_gen_no_ai_flag(self):
        """Test --no-ai flag."""
        args = self.parser.parse_args(["gen", "--no-ai"])
        self.assertTrue(args.no_ai)

    def test_gen_type_flag(self):
        """Test --type flag."""
        args = self.parser.parse_args(["gen", "--type", "feat"])
        self.assertEqual(args.type, "feat")

    def test_gen_scope_flag(self):
        """Test --scope flag."""
        args = self.parser.parse_args(["gen", "--scope", "api"])
        self.assertEqual(args.scope, "api")

    def test_gen_emoji_flag(self):
        """Test --emoji flag."""
        args = self.parser.parse_args(["gen", "--emoji"])
        self.assertTrue(args.emoji)

    def test_gen_dry_run_flag(self):
        """Test --dry-run flag."""
        args = self.parser.parse_args(["gen", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_gen_verbose_flag(self):
        """Test --verbose flag."""
        args = self.parser.parse_args(["gen", "--verbose"])
        self.assertTrue(args.verbose)

    def test_gen_verbose_short(self):
        """Test -v short flag."""
        args = self.parser.parse_args(["gen", "-v"])
        self.assertTrue(args.verbose)

    def test_gen_lang_flag(self):
        """Test --lang flag."""
        args = self.parser.parse_args(["--lang", "zh", "gen"])
        self.assertEqual(args.lang, "zh")

    def test_check_command(self):
        """Test check command."""
        args = self.parser.parse_args(["check"])
        self.assertEqual(args.command, "check")

    def test_history_command(self):
        """Test history command."""
        args = self.parser.parse_args(["history"])
        self.assertEqual(args.command, "history")

    def test_history_count(self):
        """Test history --count flag."""
        args = self.parser.parse_args(["history", "--count", "100"])
        self.assertEqual(args.count, 100)

    def test_history_count_short(self):
        """Test history -n short flag."""
        args = self.parser.parse_args(["history", "-n", "20"])
        self.assertEqual(args.count, 20)

    def test_history_stats_only(self):
        """Test history --stats-only flag."""
        args = self.parser.parse_args(["history", "--stats-only"])
        self.assertTrue(args.stats_only)

    def test_hook_install(self):
        """Test hook install."""
        args = self.parser.parse_args(["hook", "install"])
        self.assertEqual(args.command, "hook")
        self.assertEqual(args.action, "install")

    def test_hook_install_type(self):
        """Test hook install with type."""
        args = self.parser.parse_args(["hook", "install", "--hook-type", "python"])
        self.assertEqual(args.hook_type, "python")

    def test_hook_uninstall(self):
        """Test hook uninstall."""
        args = self.parser.parse_args(["hook", "uninstall"])
        self.assertEqual(args.action, "uninstall")

    def test_hook_status(self):
        """Test hook status."""
        args = self.parser.parse_args(["hook", "status"])
        self.assertEqual(args.action, "status")

    def test_config_show(self):
        """Test config show."""
        args = self.parser.parse_args(["config", "show"])
        self.assertEqual(args.command, "config")
        self.assertEqual(args.action, "show")

    def test_config_init(self):
        """Test config init."""
        args = self.parser.parse_args(["config", "init"])
        self.assertEqual(args.action, "init")

    def test_config_set(self):
        """Test config set."""
        args = self.parser.parse_args(["config", "set", "--key", "backend", "--value", "openai"])
        self.assertEqual(args.action, "set")
        self.assertEqual(args.key, "backend")
        self.assertEqual(args.value, "openai")

    def test_init_command(self):
        """Test init command."""
        args = self.parser.parse_args(["init"])
        self.assertEqual(args.command, "init")

    def test_init_with_hook(self):
        """Test init with --install-hook."""
        args = self.parser.parse_args(["init", "--install-hook"])
        self.assertTrue(args.install_hook)

    def test_examples_command(self):
        """Test examples command."""
        args = self.parser.parse_args(["examples"])
        self.assertEqual(args.command, "examples")

    def test_examples_emoji(self):
        """Test examples with emoji."""
        args = self.parser.parse_args(["examples", "--emoji"])
        self.assertTrue(args.emoji)

    def test_version_flag(self):
        """Test -V version flag."""
        args = self.parser.parse_args(["-V"])
        self.assertTrue(args.version)

    def test_version_long_flag(self):
        """Test --version flag."""
        args = self.parser.parse_args(["--version"])
        self.assertTrue(args.version)

    def test_global_lang(self):
        """Test global --lang flag."""
        args = self.parser.parse_args(["--lang", "zh", "gen"])
        self.assertEqual(args.lang, "zh")

    def test_multiple_flags_combined(self):
        """Test combining multiple flags."""
        args = self.parser.parse_args([
            "--lang", "zh", "gen", "--backend", "anthropic", "--no-ai",
            "--type", "fix", "--scope", "auth",
            "--emoji", "--dry-run", "--verbose"
        ])
        self.assertEqual(args.command, "gen")
        self.assertEqual(args.backend, "anthropic")
        self.assertTrue(args.no_ai)
        self.assertEqual(args.type, "fix")
        self.assertEqual(args.scope, "auth")
        self.assertTrue(args.emoji)
        self.assertTrue(args.dry_run)
        self.assertTrue(args.verbose)
        self.assertEqual(args.lang, "zh")


if __name__ == "__main__":
    unittest.main()
