"""Tests for git_analyzer module."""

import os
import sys
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commitforge.git_analyzer import (
    ChangeAnalysis,
    FileChange,
    analyze_changes,
    classify_change_type,
    detect_breaking_changes,
    detect_monorepo_scope,
    detect_scope,
    extract_keywords,
    parse_diff,
)


# ─── Sample Diff Data ─────────────────────────────────────────────────────────

SAMPLE_DIFF_SINGLE_FILE = """diff --git a/src/main.py b/src/main.py
index abc1234..def5678 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,5 +1,10 @@
 import os
 import sys
 
+def new_function():
+    \"\"\"A new function.\"\"\"
+    return True
+
 def main():
     print("Hello, World!")
"""

SAMPLE_DIFF_MULTIPLE_FILES = """diff --git a/src/app.py b/src/app.py
index abc1234..def5678 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,5 @@
 # Application entry point
+import logging
+
 def run():
     pass
diff --git a/tests/test_app.py b/tests/test_app.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/tests/test_app.py
@@ -0,0 +1,10 @@
+import unittest
+
+class TestApp(unittest.TestCase):
+    def test_run(self):
+        self.assertTrue(True)
diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,4 @@
 # My Project
+A great project for doing things.
 
 ## Installation
diff --git a/old_module.py b/old_module.py
deleted file mode 100644
index 3333333..0000000
--- a/old_module.py
+++ /dev/null
@@ -1,5 +0,0 @@
-# Old module
-def old_func():
-    pass
-
-old_data = {}
"""

SAMPLE_DIFF_BINARY = """diff --git a/assets/logo.png b/assets/logo.png
index 1111111..2222222 100644
Binary files a/assets/logo.png and b/assets/logo.png differ
"""

SAMPLE_DIFF_WITH_KEYWORDS = """diff --git a/src/auth.py b/src/auth.py
index abc1234..def5678 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,5 +1,12 @@
 import os
 
+# TODO: implement OAuth2 support
+# FIXME: token refresh not working
 def authenticate(user):
-    return True
+    # BUG: this always returns True
+    if user.valid:
+        return create_token(user)
+    return False
+
+def create_token(user):
+    return generate_jwt(user)
"""

SAMPLE_DIFF_BREAKING = """diff --git a/src/api.py b/src/api.py
index abc1234..def5678 100644
--- a/src/api.py
+++ b/src/api.py
@@ -1,10 +1,8 @@
 class API:
-    def get_user(self, user_id):
-        return db.query(user_id)
-
-    def create_user(self, data):
-        return db.insert(data)
+    def get_user(self, user_id, include_deleted=False):
+        return db.query(user_id, include_deleted)
"""

SAMPLE_DIFF_MONOREPO = """diff --git a/packages/web/src/App.tsx b/packages/web/src/App.tsx
index abc1234..def5678 100644
--- a/packages/web/src/App.tsx
+++ b/packages/web/src/App.tsx
@@ -1,3 +1,5 @@
 import React from 'react'
+import { Button } from './components'
 
 function App() {
diff --git a/packages/web/src/components/Button.tsx b/packages/web/src/components/Button.tsx
new file mode 100644
--- /dev/null
+++ b/packages/web/src/components/Button.tsx
@@ -0,0 +1,5 @@
+import React from 'react'
+
+export function Button({ children }) {
+  return <button>{children}</button>
+}
diff --git a/packages/api/src/routes.ts b/packages/api/src/routes.ts
index 1111111..2222222 100644
--- a/packages/api/src/routes.ts
+++ b/packages/api/src/routes.ts
@@ -1,3 +1,4 @@
 import express from 'express'
+router.get('/health', healthCheck)
"""


class TestParseDiff(unittest.TestCase):
    """Tests for the parse_diff function."""

    def test_parse_single_file(self):
        """Test parsing a diff with a single file."""
        files = parse_diff(SAMPLE_DIFF_SINGLE_FILE)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].path, "src/main.py")
        self.assertEqual(files[0].extension, ".py")
        self.assertEqual(files[0].status, "modified")
        self.assertEqual(files[0].added_lines, 4)
        self.assertTrue(files[0].added_lines > 0)

    def test_parse_multiple_files(self):
        """Test parsing a diff with multiple files."""
        files = parse_diff(SAMPLE_DIFF_MULTIPLE_FILES)
        self.assertEqual(len(files), 4)

        paths = [f.path for f in files]
        self.assertIn("src/app.py", paths)
        self.assertIn("tests/test_app.py", paths)
        self.assertIn("README.md", paths)
        self.assertIn("old_module.py", paths)

    def test_parse_new_file(self):
        """Test detecting new files."""
        files = parse_diff(SAMPLE_DIFF_MULTIPLE_FILES)
        test_file = next(f for f in files if f.path == "tests/test_app.py")
        self.assertEqual(test_file.status, "added")

    def test_parse_deleted_file(self):
        """Test detecting deleted files."""
        files = parse_diff(SAMPLE_DIFF_MULTIPLE_FILES)
        old_file = next(f for f in files if f.path == "old_module.py")
        self.assertEqual(old_file.status, "deleted")

    def test_parse_binary_file(self):
        """Test detecting binary files."""
        files = parse_diff(SAMPLE_DIFF_BINARY)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].is_binary)

    def test_parse_empty_diff(self):
        """Test parsing empty diff."""
        files = parse_diff("")
        self.assertEqual(len(files), 0)

    def test_parse_none_diff(self):
        """Test parsing None diff."""
        files = parse_diff(None)
        self.assertEqual(len(files), 0)

    def test_file_change_total(self):
        """Test FileChange.total_changes property."""
        fc = FileChange(path="test.py", added_lines=10, removed_lines=5)
        self.assertEqual(fc.total_changes, 15)

    def test_file_change_extension(self):
        """Test file extension detection."""
        fc = FileChange(path="src/app.py")
        self.assertEqual(fc.extension, ".py")

        fc2 = FileChange(path="Makefile")
        self.assertEqual(fc2.extension, "")


class TestClassifyChange(unittest.TestCase):
    """Tests for the classify_change_type function."""

    def test_classify_doc_change(self):
        """Test classifying documentation changes."""
        files = [FileChange(path="README.md", extension=".md")]
        self.assertEqual(classify_change_type(files), "docs")

    def test_classify_test_change(self):
        """Test classifying test changes."""
        files = [FileChange(path="tests/test_app.py", extension=".py")]
        result = classify_change_type(files)
        self.assertIn(result, ["test", "feat"])

    def test_classify_yaml_change(self):
        """Test classifying YAML config changes."""
        files = [FileChange(path=".github/workflows/ci.yml", extension=".yml")]
        result = classify_change_type(files)
        self.assertIn(result, ["ci", "chore"])

    def test_classify_mixed_changes(self):
        """Test classifying mixed changes."""
        files = parse_diff(SAMPLE_DIFF_MULTIPLE_FILES)
        result = classify_change_type(files)
        self.assertIn(result, ["feat", "test", "docs", "refactor", "chore"])

    def test_classify_empty_files(self):
        """Test classifying with no files."""
        self.assertEqual(classify_change_type([]), "chore")


class TestDetectScope(unittest.TestCase):
    """Tests for the detect_scope function."""

    def test_detect_scope_single_dir(self):
        """Test scope detection from single directory."""
        files = [FileChange(path="src/main.py")]
        scope = detect_scope(files)
        self.assertEqual(scope, "src")

    def test_detect_scope_multiple_dirs(self):
        """Test scope detection with multiple directories."""
        files = [
            FileChange(path="src/app.py"),
            FileChange(path="src/utils.py"),
            FileChange(path="src/models.py"),
        ]
        scope = detect_scope(files)
        self.assertEqual(scope, "src")

    def test_detect_scope_custom_rules(self):
        """Test scope detection with custom rules."""
        files = [FileChange(path="src/core/engine.py")]
        rules = {"src/": "core"}
        scope = detect_scope(files, scope_rules=rules)
        self.assertEqual(scope, "core")

    def test_detect_scope_no_files(self):
        """Test scope detection with no files."""
        scope = detect_scope([])
        self.assertEqual(scope, "")

    def test_detect_scope_root_file(self):
        """Test scope detection for root-level files."""
        files = [FileChange(path="Makefile")]
        scope = detect_scope(files)
        self.assertEqual(scope, "")


class TestDetectMonorepoScope(unittest.TestCase):
    """Tests for monorepo scope detection."""

    def test_detect_monorepo_packages(self):
        """Test detecting monorepo package scope."""
        files = parse_diff(SAMPLE_DIFF_MONOREPO)
        scope = detect_monorepo_scope(files)
        self.assertEqual(scope, "web")

    def test_detect_monorepo_no_match(self):
        """Test with non-monorepo structure."""
        files = [FileChange(path="src/main.py")]
        scope = detect_monorepo_scope(files)
        self.assertIsNone(scope)


class TestExtractKeywords(unittest.TestCase):
    """Tests for keyword extraction."""

    def test_extract_function_names(self):
        """Test extracting function names from added lines."""
        files = parse_diff(SAMPLE_DIFF_WITH_KEYWORDS)
        keywords = extract_keywords(files)
        # Should find function names
        self.assertTrue(len(keywords) > 0)

    def test_extract_todo_keywords(self):
        """Test extracting TODO/FIXME comments."""
        files = parse_diff(SAMPLE_DIFF_WITH_KEYWORDS)
        keywords = extract_keywords(files)
        keyword_str = " ".join(keywords)
        # Check for TODO/FIXME
        has_todo = any("TODO" in kw or "FIXME" in kw for kw in keywords)
        self.assertTrue(has_todo)

    def test_extract_empty(self):
        """Test extracting from no files."""
        keywords = extract_keywords([])
        self.assertEqual(len(keywords), 0)


class TestDetectBreakingChanges(unittest.TestCase):
    """Tests for breaking change detection."""

    def test_detect_breaking_removed_function(self):
        """Test detecting removed public functions."""
        files = parse_diff(SAMPLE_DIFF_BREAKING)
        self.assertTrue(detect_breaking_changes(files))

    def test_detect_no_breaking(self):
        """Test when no breaking changes exist."""
        files = parse_diff(SAMPLE_DIFF_SINGLE_FILE)
        self.assertFalse(detect_breaking_changes(files))

    def test_detect_binary_no_breaking(self):
        """Test binary files don't trigger breaking detection."""
        files = parse_diff(SAMPLE_DIFF_BINARY)
        self.assertFalse(detect_breaking_changes(files))


class TestChangeAnalysis(unittest.TestCase):
    """Tests for the ChangeAnalysis dataclass."""

    def test_change_analysis_defaults(self):
        """Test default values."""
        analysis = ChangeAnalysis()
        self.assertEqual(analysis.total_files, 0)
        self.assertEqual(analysis.total_insertions, 0)
        self.assertEqual(analysis.total_deletions, 0)
        self.assertFalse(analysis.has_breaking_change)
        self.assertFalse(analysis.is_large_change)

    def test_change_summary(self):
        """Test change summary string."""
        analysis = ChangeAnalysis(
            total_files=3,
            total_insertions=10,
            total_deletions=5,
        )
        summary = analysis.change_summary
        self.assertIn("3", summary)
        self.assertIn("+10", summary)
        self.assertIn("-5", summary)


class TestAnalyzeChanges(unittest.TestCase):
    """Tests for the main analyze_changes function."""

    def test_analyze_with_diff_text(self):
        """Test analysis with provided diff text."""
        analysis = analyze_changes(diff_text=SAMPLE_DIFF_MULTIPLE_FILES)
        self.assertEqual(analysis.total_files, 4)
        self.assertTrue(analysis.total_insertions > 0)
        self.assertTrue(analysis.total_deletions > 0)

    def test_analyze_empty_diff(self):
        """Test analysis with empty diff."""
        analysis = analyze_changes(diff_text="")
        self.assertEqual(analysis.total_files, 0)

    def test_analyze_none_diff(self):
        """Test analysis with None diff."""
        # When diff_text is None and not in a git repo, it should handle gracefully
        try:
            analysis = analyze_changes(diff_text=None)
            self.assertIsInstance(analysis, ChangeAnalysis)
        except RuntimeError:
            # Expected when not in a git repo
            pass


if __name__ == "__main__":
    unittest.main()
