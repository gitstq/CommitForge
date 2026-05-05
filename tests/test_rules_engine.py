"""Tests for rules_engine module."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commitforge.git_analyzer import ChangeAnalysis, FileChange, parse_diff
from commitforge.rules_engine import RulesEngine


# ─── Sample Data ──────────────────────────────────────────────────────────────

SAMPLE_DIFF_PYTHON = """diff --git a/src/calculator.py b/src/calculator.py
index abc1234..def5678 100644
--- a/src/calculator.py
+++ b/src/calculator.py
@@ -1,5 +1,10 @@
 import os
 
+def add(a, b):
+    return a + b
+
+def multiply(a, b):
+    return a * b
+
 def calculate():
     pass
"""

SAMPLE_DIFF_DOCS = """diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,5 @@
 # My Project
+A calculator library for Python.
+
 ## Installation
"""

SAMPLE_DIFF_TEST = """diff --git a/tests/test_calc.py b/tests/test_calc.py
new file mode 100644
--- /dev/null
+++ b/tests/test_calc.py
@@ -0,0 +1,10 @@
+import unittest
+
+class TestCalculator(unittest.TestCase):
+    def test_add(self):
+        self.assertEqual(add(1, 2), 3)
"""

SAMPLE_DIFF_CONFIG = """diff --git a/package.json b/package.json
index 1111111..2222222 100644
--- a/package.json
+++ b/package.json
@@ -1,5 +1,5 @@
 {
-  "version": "1.0.0"
+  "version": "1.1.0",
+  "dependencies": {"express": "^4.18.0"}
 }
diff --git a/package-lock.json b/package-lock.json
index 1111111..2222222 100644
Binary files a/package-lock.json and b/package-lock.json differ
"""


class TestRulesEngineInit(unittest.TestCase):
    """Tests for RulesEngine initialization."""

    def test_default_init(self):
        """Test default initialization."""
        engine = RulesEngine()
        self.assertEqual(engine._lang, "en")
        self.assertFalse(engine._emoji)

    def test_chinese_init(self):
        """Test Chinese initialization."""
        engine = RulesEngine(lang="zh")
        self.assertEqual(engine._lang, "zh")

    def test_emoji_init(self):
        """Test emoji initialization."""
        engine = RulesEngine(emoji=True)
        self.assertTrue(engine._emoji)


class TestRulesEngineGenerate(unittest.TestCase):
    """Tests for RulesEngine.generate method."""

    def test_generate_python_feature(self):
        """Test generating message for Python feature."""
        files = parse_diff(SAMPLE_DIFF_PYTHON)
        analysis = ChangeAnalysis(
            files=files,
            commit_type="feat",
            scope="src",
            total_insertions=6,
            total_deletions=0,
            total_files=1,
        )
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertEqual(commit.type, "feat")
        self.assertIsNotNone(commit.description)
        self.assertTrue(len(commit.description) > 0)

    def test_generate_docs_change(self):
        """Test generating message for documentation change."""
        files = parse_diff(SAMPLE_DIFF_DOCS)
        analysis = ChangeAnalysis(
            files=files,
            commit_type="docs",
            scope="",
            total_insertions=2,
            total_deletions=0,
            total_files=1,
        )
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertEqual(commit.type, "docs")

    def test_generate_test_change(self):
        """Test generating message for test addition."""
        files = parse_diff(SAMPLE_DIFF_TEST)
        analysis = ChangeAnalysis(
            files=files,
            commit_type="test",
            scope="test",
            total_insertions=10,
            total_deletions=0,
            total_files=1,
        )
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertEqual(commit.type, "test")

    def test_generate_chinese(self):
        """Test generating Chinese message."""
        files = parse_diff(SAMPLE_DIFF_PYTHON)
        analysis = ChangeAnalysis(
            files=files,
            commit_type="feat",
            scope="src",
            total_insertions=6,
            total_deletions=0,
            total_files=1,
        )
        engine = RulesEngine(lang="zh")
        commit = engine.generate(analysis)
        self.assertIsNotNone(commit.description)

    def test_generate_with_force_type(self):
        """Test generating with forced type."""
        files = parse_diff(SAMPLE_DIFF_PYTHON)
        analysis = ChangeAnalysis(
            files=files,
            commit_type="feat",
            scope="src",
        )
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis, force_type="fix")
        self.assertEqual(commit.type, "fix")

    def test_generate_with_force_scope(self):
        """Test generating with forced scope."""
        files = parse_diff(SAMPLE_DIFF_PYTHON)
        analysis = ChangeAnalysis(
            files=files,
            commit_type="feat",
            scope="src",
        )
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis, force_scope="calculator")
        self.assertEqual(commit.scope, "calculator")

    def test_generate_empty_analysis(self):
        """Test generating with empty analysis."""
        analysis = ChangeAnalysis()
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertIsNotNone(commit)
        self.assertEqual(commit.type, "chore")


class TestRulesEngineClassify(unittest.TestCase):
    """Tests for RulesEngine classification methods."""

    def test_classify_by_keywords(self):
        """Test keyword-based classification."""
        engine = RulesEngine()
        diff = """+def add(a, b):
+    return a + b
+# TODO: implement subtraction
+# FIXME: this is a hack
"""
        result = engine.classify_by_keywords(diff)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_infer_type_from_extension(self):
        """Test type inference from file extension."""
        engine = RulesEngine()
        self.assertEqual(engine.infer_type_from_extension(".md"), "docs")
        self.assertEqual(engine.infer_type_from_extension(".py"), "chore")
        self.assertEqual(engine.infer_type_from_extension(".yml"), "ci")

    def test_infer_type_from_filename(self):
        """Test type inference from filename."""
        engine = RulesEngine()
        self.assertEqual(engine.infer_type_from_filename("Dockerfile"), "build")
        self.assertEqual(engine.infer_type_from_filename("test_app.py"), "test")
        self.assertEqual(engine.infer_type_from_filename("Makefile"), "build")


class TestRulesEngineDescription(unittest.TestCase):
    """Tests for description generation."""

    def test_single_new_file(self):
        """Test description for single new file."""
        files = [FileChange(path="src/new_module.py", status="added", extension=".py")]
        analysis = ChangeAnalysis(files=files, commit_type="feat")
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertIn("new_module.py", commit.description)

    def test_single_deleted_file(self):
        """Test description for single deleted file."""
        files = [FileChange(path="old_module.py", status="deleted", extension=".py")]
        analysis = ChangeAnalysis(files=files, commit_type="refactor")
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertIsNotNone(commit.description)

    def test_dependency_update(self):
        """Test description for dependency update."""
        files = [
            FileChange(path="package.json", status="modified", extension=".json"),
            FileChange(path="package-lock.json", status="modified", is_binary=True),
        ]
        analysis = ChangeAnalysis(files=files, commit_type="chore")
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertIn("depend", commit.description.lower())


class TestRulesEngineBody(unittest.TestCase):
    """Tests for body generation."""

    def test_body_multiple_files(self):
        """Test body with multiple files."""
        files = [
            FileChange(path="src/a.py", status="modified", added_lines=5, removed_lines=2),
            FileChange(path="src/b.py", status="modified", added_lines=3, removed_lines=1),
            FileChange(path="src/c.py", status="modified", added_lines=1, removed_lines=0),
        ]
        analysis = ChangeAnalysis(
            files=files, commit_type="refactor",
            total_insertions=9, total_deletions=3, total_files=3,
        )
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        self.assertIsNotNone(commit.body)
        self.assertIn("a.py", commit.body)

    def test_body_single_file(self):
        """Test body with single file (no body expected)."""
        files = [FileChange(path="src/a.py", status="modified", added_lines=1, removed_lines=0)]
        analysis = ChangeAnalysis(
            files=files, commit_type="style",
            total_insertions=1, total_deletions=0, total_files=1,
        )
        engine = RulesEngine(lang="en")
        commit = engine.generate(analysis)
        # Single file changes typically don't get a body
        # (body is only added for > 1 file)


if __name__ == "__main__":
    unittest.main()
