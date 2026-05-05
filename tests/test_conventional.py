"""Tests for conventional module."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commitforge.conventional import (
    ConventionalCommit,
    TYPE_DESCRIPTIONS_EN,
    TYPE_DESCRIPTIONS_ZH,
    TYPE_EMOJIS,
    STANDARD_TYPES,
    fix_commit_message,
    get_type_description,
    get_type_emoji,
    is_conventional,
    parse_commit,
    validate_commit,
)


class TestParseCommit(unittest.TestCase):
    """Tests for parse_commit function."""

    def test_parse_simple(self):
        """Test parsing a simple conventional commit."""
        msg = "feat: add new feature"
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "feat")
        self.assertIsNone(result.scope)
        self.assertEqual(result.description, "add new feature")

    def test_parse_with_scope(self):
        """Test parsing with scope."""
        msg = "fix(api): handle null response"
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "fix")
        self.assertEqual(result.scope, "api")
        self.assertEqual(result.description, "handle null response")

    def test_parse_with_body(self):
        """Test parsing with body."""
        msg = "feat(auth): add OAuth2 support\n\nThis adds OAuth2 authentication\nsupport for third-party login."
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "feat")
        self.assertEqual(result.scope, "auth")
        self.assertIsNotNone(result.body)
        self.assertIn("OAuth2", result.body)

    def test_parse_with_breaking_change_marker(self):
        """Test parsing with breaking change marker (!)."""
        msg = "feat(api)!: change response format"
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertTrue(result.breaking_change)

    def test_parse_with_breaking_change_footer(self):
        """Test parsing with BREAKING CHANGE footer."""
        msg = "feat(api): change response format\n\nBREAKING CHANGE: response format changed from XML to JSON"
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertTrue(result.breaking_change)
        self.assertEqual(result.breaking_description, "response format changed from XML to JSON")

    def test_parse_with_footers(self):
        """Test parsing with footers."""
        msg = "feat: add feature\n\nCo-Authored-By: John <john@example.com>\nRefs: #123"
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.footers), 2)

    def test_parse_empty(self):
        """Test parsing empty message."""
        result = parse_commit("")
        self.assertIsNone(result)

    def test_parse_none(self):
        """Test parsing None."""
        result = parse_commit(None)
        self.assertIsNone(result)

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        result = parse_commit("this is not a conventional commit")
        self.assertIsNone(result)

    def test_parse_uppercase_type(self):
        """Test that uppercase types are not parsed."""
        result = parse_commit("Feat: add feature")
        self.assertIsNone(result)

    def test_parse_complex_scope(self):
        """Test parsing with hyphenated scope."""
        msg = "fix(user-profile): update avatar upload"
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.scope, "user-profile")

    def test_parse_revert(self):
        """Test parsing revert commit."""
        msg = "revert: feat(auth): add OAuth2 support"
        result = parse_commit(msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "revert")


class TestValidateCommit(unittest.TestCase):
    """Tests for validate_commit function."""

    def test_valid_simple(self):
        """Test validating a valid simple commit."""
        result = validate_commit("feat: add new feature")
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_valid_with_scope(self):
        """Test validating with scope."""
        result = validate_commit("fix(api): handle null response")
        self.assertTrue(result.is_valid)

    def test_valid_with_breaking(self):
        """Test validating breaking change."""
        result = validate_commit("feat(api)!: change response format")
        self.assertTrue(result.is_valid)

    def test_invalid_empty(self):
        """Test validating empty message."""
        result = validate_commit("")
        self.assertFalse(result.is_valid)

    def test_invalid_format(self):
        """Test validating invalid format."""
        result = validate_commit("added some stuff")
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.errors) > 0)

    def test_warning_uppercase_description(self):
        """Test warning for uppercase description."""
        result = validate_commit("feat: Add new feature")
        self.assertTrue(result.is_valid)  # Still valid, just a warning
        self.assertTrue(len(result.warnings) > 0)

    def test_warning_trailing_period(self):
        """Test warning for trailing period."""
        result = validate_commit("feat: add new feature.")
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)

    def test_warning_non_standard_type(self):
        """Test warning for non-standard type."""
        result = validate_commit("custom: do something")
        self.assertTrue(result.is_valid)  # Valid format, non-standard type
        self.assertTrue(len(result.warnings) > 0)

    def test_invalid_scope_format(self):
        """Test invalid scope format."""
        result = validate_commit("feat(API): add endpoint")
        self.assertFalse(result.is_valid)

    def test_long_subject_warning(self):
        """Test warning for long subject line."""
        long_desc = "a" * 80
        result = validate_commit(f"feat: {long_desc}")
        self.assertTrue(result.is_valid)
        self.assertTrue(any("long" in w.lower() for w in result.warnings))

    def test_validation_chinese(self):
        """Test validation with Chinese messages."""
        result = validate_commit("feat: 添加新功能", lang="zh")
        self.assertTrue(result.is_valid)

    def test_breaking_marker_without_footer_warning(self):
        """Test warning for breaking marker without footer."""
        msg = "feat!: some change"
        result = validate_commit(msg)
        self.assertTrue(result.is_valid)
        self.assertTrue(any("breaking" in w.lower() for w in result.warnings))


class TestFixCommitMessage(unittest.TestCase):
    """Tests for fix_commit_message function."""

    def test_fix_uppercase_description(self):
        """Test fixing uppercase description."""
        result = fix_commit_message("feat: Add new feature")
        self.assertEqual(result, "feat: add new feature")

    def test_fix_trailing_period(self):
        """Test fixing trailing period."""
        result = fix_commit_message("feat: add new feature.")
        self.assertEqual(result, "feat: add new feature")

    def test_fix_missing_space(self):
        """Test fixing missing space after colon."""
        result = fix_commit_message("feat:add feature")
        self.assertEqual(result, "feat: add feature")

    def test_fix_uppercase_type(self):
        """Test fixing uppercase type."""
        result = fix_commit_message("Feat: add feature")
        self.assertEqual(result, "feat: add feature")

    def test_fix_bracket_notation(self):
        """Test fixing bracket notation."""
        result = fix_commit_message("[feat] add feature")
        self.assertEqual(result, "feat: add feature")

    def test_fix_empty(self):
        """Test fixing empty message."""
        result = fix_commit_message("")
        self.assertEqual(result, "")

    def test_fix_already_valid(self):
        """Test that valid messages are unchanged."""
        msg = "feat: add new feature"
        result = fix_commit_message(msg)
        self.assertEqual(result, msg)


class TestHelperFunctions(unittest.TestCase):
    """Tests for helper functions."""

    def test_is_conventional_valid(self):
        """Test is_conventional with valid message."""
        self.assertTrue(is_conventional("feat: add feature"))
        self.assertTrue(is_conventional("fix(api): handle error"))

    def test_is_conventional_invalid(self):
        """Test is_conventional with invalid message."""
        self.assertFalse(is_conventional("random message"))
        self.assertFalse(is_conventional(""))
        self.assertFalse(is_conventional("feat add feature"))

    def test_get_type_description_en(self):
        """Test getting English type descriptions."""
        desc = get_type_description("feat", "en")
        self.assertEqual(desc, TYPE_DESCRIPTIONS_EN["feat"])

    def test_get_type_description_zh(self):
        """Test getting Chinese type descriptions."""
        desc = get_type_description("feat", "zh")
        self.assertEqual(desc, TYPE_DESCRIPTIONS_ZH["feat"])

    def test_get_type_description_unknown(self):
        """Test getting description for unknown type."""
        desc = get_type_description("unknown", "en")
        self.assertEqual(desc, "unknown")

    def test_get_type_emoji(self):
        """Test getting type emoji."""
        emoji = get_type_emoji("feat")
        self.assertEqual(emoji, TYPE_EMOJIS["feat"])

    def test_get_type_emoji_unknown(self):
        """Test getting emoji for unknown type."""
        emoji = get_type_emoji("unknown")
        self.assertEqual(emoji, "")


class TestConventionalCommit(unittest.TestCase):
    """Tests for ConventionalCommit dataclass."""

    def test_subject_no_scope(self):
        """Test subject without scope."""
        commit = ConventionalCommit(type="feat", description="add feature")
        self.assertEqual(commit.subject, "feat: add feature")

    def test_subject_with_scope(self):
        """Test subject with scope."""
        commit = ConventionalCommit(type="feat", scope="api", description="add endpoint")
        self.assertEqual(commit.subject, "feat(api): add endpoint")

    def test_subject_breaking(self):
        """Test subject with breaking change."""
        commit = ConventionalCommit(
            type="feat", scope="api", description="change format",
            breaking_change=True
        )
        self.assertEqual(commit.subject, "feat!(api): change format")

    def test_format_basic(self):
        """Test basic formatting."""
        commit = ConventionalCommit(type="feat", description="add feature")
        result = commit.format()
        self.assertEqual(result, "feat: add feature")

    def test_format_with_body(self):
        """Test formatting with body."""
        commit = ConventionalCommit(
            type="feat", description="add feature",
            body="This adds a new feature."
        )
        result = commit.format()
        self.assertIn("feat: add feature", result)
        self.assertIn("This adds a new feature.", result)

    def test_format_with_emoji(self):
        """Test formatting with emoji."""
        commit = ConventionalCommit(type="feat", description="add feature")
        result = commit.format(emoji=True)
        self.assertTrue(result.startswith(TYPE_EMOJIS["feat"]))

    def test_format_without_body(self):
        """Test formatting without body."""
        commit = ConventionalCommit(
            type="feat", description="add feature",
            body="Some body text"
        )
        result = commit.format(include_body=False)
        self.assertEqual(result, "feat: add feature")

    def test_format_with_footers(self):
        """Test formatting with footers."""
        commit = ConventionalCommit(
            type="feat", description="add feature",
            footers=[("Co-Authored-By", "John <john@example.com>")]
        )
        result = commit.format()
        self.assertIn("Co-Authored-By: John <john@example.com>", result)


class TestStandardTypes(unittest.TestCase):
    """Tests for standard type constants."""

    def test_all_standard_types_present(self):
        """Test that all standard types are defined."""
        expected = {"feat", "fix", "docs", "style", "refactor",
                    "perf", "test", "build", "ci", "chore", "revert"}
        self.assertEqual(set(STANDARD_TYPES), expected)

    def test_all_types_have_descriptions(self):
        """Test that all types have English descriptions."""
        for t in STANDARD_TYPES:
            self.assertIn(t, TYPE_DESCRIPTIONS_EN)

    def test_all_types_have_emojis(self):
        """Test that all types have emojis."""
        for t in STANDARD_TYPES:
            self.assertIn(t, TYPE_EMOJIS)


if __name__ == "__main__":
    unittest.main()
