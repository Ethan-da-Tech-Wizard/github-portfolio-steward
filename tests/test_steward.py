"""
Program: GitHub Portfolio Steward - Unit Test Suite
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Comprehensive unit test suite validating scanner, synthesizer, updater, header auditor, models, and CLI subcommands.
"""

import io
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from steward.models import (
    RepoSummary,
    CodebaseFacts,
    MetadataRecommendation,
    HeaderAuditResult,
    HeaderAuditReport,
)
from steward.scanner import RepositoryScanner
from steward.synthesizer import MetadataSynthesizer
from steward.updater import PortfolioUpdater
from steward.header_audit import HeaderAuditor
from steward.cli import main, create_parser


class TestModels(unittest.TestCase):
    """
    ## Verifies serialization, initialization, and defaults of core data models.
    """

    def test_repo_summary_to_dict(self):
        ## Test RepoSummary serialization to dictionary.
        repo = RepoSummary(
            name="test-repo",
            full_name="Ethan-da-Tech-Wizard/test-repo",
            description="A test repository.",
            primary_language="Python",
            topics=["python", "cli"],
            default_branch="main"
        )
        d = repo.to_dict()
        self.assertEqual(d["name"], "test-repo")
        self.assertEqual(d["full_name"], "Ethan-da-Tech-Wizard/test-repo")
        self.assertEqual(d["primary_language"], "Python")
        self.assertEqual(d["topics"], ["python", "cli"])
        self.assertFalse(d["is_fork"])

    def test_codebase_facts_defaults(self):
        ## Test CodebaseFacts default values and serialization.
        facts = CodebaseFacts()
        self.assertEqual(facts.file_count, 0)
        self.assertEqual(facts.detected_frameworks, [])
        self.assertFalse(facts.has_readme)
        d = facts.to_dict()
        self.assertIsInstance(d, dict)

    def test_metadata_recommendation(self):
        ## Test MetadataRecommendation initialization and delta properties.
        rec = MetadataRecommendation(
            repo_name="Ethan-da-Tech-Wizard/sample",
            current_description="Old desc",
            proposed_description="New desc",
            description_changed=True,
            current_topics=["python"],
            proposed_topics=["python", "cli"],
            topics_to_add=["cli"]
        )
        self.assertTrue(rec.description_changed)
        self.assertEqual(rec.topics_to_add, ["cli"])
        self.assertEqual(rec.to_dict()["confidence_score"], 1.0)


class TestScanner(unittest.TestCase):
    """
    ## Verifies scanner logic across local directory trees, README extraction, and remote mocking.
    """

    def setUp(self):
        ## Create an isolated temporary directory for file tree analysis.
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        ## Clean up temporary test files.
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_extract_readme_summary_basic(self):
        ## Verify markdown cleaning: strip badges, links, headers.
        markdown = """# Project Title
[![Build Status](https://img.shields.io/travis/repo.svg)](https://travis-ci.org/repo)

A zero-dependency [autonomous](https://en.wikipedia.org/wiki/Autonomous) GitHub portfolio curator.
It inspects repositories and applies standardized topics and descriptions.

## Features
- Feature 1
- Feature 2
"""
        scanner = RepositoryScanner()
        summary = scanner.extract_readme_summary(markdown)
        self.assertIsNotNone(summary)
        self.assertTrue("zero-dependency autonomous GitHub portfolio curator" in summary)
        self.assertNotIn("Build Status", summary)
        self.assertNotIn("#", summary)

    def test_extract_readme_summary_empty(self):
        ## Verify graceful handling of empty or blank README.
        scanner = RepositoryScanner()
        self.assertIsNone(scanner.extract_readme_summary(""))
        self.assertIsNone(scanner.extract_readme_summary("# Title only\n"))

    def test_inspect_local_directory_markers(self):
        ## Verify detection of Python, Cargo, Docker, Systemd, CI, and test markers.
        d = Path(self.test_dir)
        (d / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
        (d / "Cargo.toml").write_text("[package]\nname='test'\n", encoding="utf-8")
        (d / "Dockerfile").write_text("FROM alpine\n", encoding="utf-8")
        (d / "service.service").write_text("[Unit]\nDescription=Test\n", encoding="utf-8")
        (d / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (d / "README.md").write_text("# Test\n\nHigh-performance systems utility for autonomous tasks.\n", encoding="utf-8")

        tests_dir = d / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("def test_dummy(): pass\n", encoding="utf-8")

        ci_dir = d / ".github" / "workflows"
        ci_dir.mkdir(parents=True)
        (ci_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")

        ## Add ignored directory to verify it gets pruned.
        node_modules = d / "node_modules"
        node_modules.mkdir()
        (node_modules / "junk.js").write_text("console.log('skip');\n", encoding="utf-8")

        scanner = RepositoryScanner()
        facts = scanner.inspect_local_directory(self.test_dir)

        self.assertIn("cargo", facts.detected_frameworks)
        self.assertIn("pip", facts.detected_frameworks)
        self.assertIn("docker", facts.detected_frameworks)
        self.assertIn("systemd", facts.detected_frameworks)
        self.assertIn("Python", facts.detected_languages)
        self.assertIn("Rust", facts.detected_languages)
        self.assertTrue(facts.has_readme)
        self.assertTrue(facts.has_license)
        self.assertTrue(facts.has_tests)
        self.assertTrue(facts.has_ci)
        self.assertIsNotNone(facts.readme_snippet)
        ## Ensure node_modules was ignored (JavaScript not detected).
        self.assertNotIn("JavaScript", facts.detected_languages)

    @patch("steward.scanner.subprocess.run")
    def test_fetch_github_repos_mock(self, mock_run):
        ## Verify parsing of gh repo list JSON output.
        mock_output = [
            {
                "name": "my-tool",
                "nameWithOwner": "Ethan-da-Tech-Wizard/my-tool",
                "description": "A developer tool.",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "primaryLanguage": {"name": "Python"},
                "repositoryTopics": [{"name": "cli"}, {"name": "python"}],
                "defaultBranchRef": {"name": "main"},
                "updatedAt": "2026-11-08T00:00:00Z",
                "url": "https://github.com/Ethan-da-Tech-Wizard/my-tool"
            },
            {
                "name": "forked-repo",
                "nameWithOwner": "Ethan-da-Tech-Wizard/forked-repo",
                "isFork": True,
                "isArchived": False
            }
        ]
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(mock_output)
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        scanner = RepositoryScanner()
        repos = scanner.fetch_github_repos(include_forks=False)

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0].name, "my-tool")
        self.assertEqual(repos[0].primary_language, "Python")
        self.assertEqual(repos[0].topics, ["cli", "python"])


class TestSynthesizer(unittest.TestCase):
    """
    ## Verifies metadata synthesis, exclusion rules, topic normalization, and length constraints.
    """

    def test_normalize_topic(self):
        ## Verify topic standardization into valid GitHub tags.
        synth = MetadataSynthesizer()
        self.assertEqual(synth.normalize_topic("Python"), "python")
        self.assertEqual(synth.normalize_topic("C++"), "c")
        self.assertEqual(synth.normalize_topic("Machine Learning"), "machine-learning")
        self.assertEqual(synth.normalize_topic("---leading-trailing---"), "leading-trailing")
        self.assertEqual(synth.normalize_topic("multiple___underscores"), "multiple-underscores")
        self.assertIsNone(synth.normalize_topic(""))
        self.assertIsNone(synth.normalize_topic("a" * 36))  ## Over 35 char limit

    def test_exclusion_patterns(self):
        ## Verify exclusion filtering via exact names and regex patterns.
        synth = MetadataSynthesizer(exclusions=["EXAMPLE_ORG", r".*-private$", "archived-.*"])
        self.assertTrue(synth.is_excluded("EXAMPLE_ORG"))
        self.assertTrue(synth.is_excluded("org/EXAMPLE_ORG"))
        self.assertTrue(synth.is_excluded("secret-private"))
        self.assertTrue(synth.is_excluded("archived-legacy-code"))
        self.assertFalse(synth.is_excluded("github-portfolio-steward"))

    def test_synthesize_description_length_limit(self):
        ## Verify generated description is strictly under 250 characters.
        synth = MetadataSynthesizer()
        repo = RepoSummary(name="test-repo", full_name="user/test-repo")
        long_snippet = "This is an extremely long README summary that goes on and on detailing complex architectural patterns and subsystems across multiple distributed systems until it exceeds the standard limit allowed for GitHub repository descriptions by a substantial margin."
        facts = CodebaseFacts(
            detected_languages=["Python"],
            has_readme=True,
            readme_snippet=long_snippet
        )

        desc = synth.synthesize_description(repo, facts)
        self.assertLess(len(desc), 250)
        self.assertTrue(desc.endswith("..."))

    def test_recommendation_delta(self):
        ## Verify recommendation produces correct delta between current and proposed metadata.
        synth = MetadataSynthesizer()
        repo = RepoSummary(
            name="github-portfolio-steward",
            full_name="Ethan-da-Tech-Wizard/github-portfolio-steward",
            description=None,
            primary_language="Python",
            topics=["python"]
        )
        facts = CodebaseFacts(
            detected_frameworks=["cargo", "docker"],
            detected_languages=["Python", "Rust"],
            has_readme=True,
            readme_snippet="Autonomous GitHub portfolio curator and codebase analyzer."
        )

        rec = synth.recommend(repo, facts)
        self.assertTrue(rec.description_changed)
        self.assertIn("cargo", rec.topics_to_add)
        self.assertIn("docker", rec.topics_to_add)
        self.assertNotIn("python", rec.topics_to_add)  ## Already in current_topics


class TestUpdater(unittest.TestCase):
    """
    ## Verifies dry-run command generation and live application.
    """

    def test_build_gh_edit_command(self):
        ## Verify CLI command assembly for gh repo edit.
        updater = PortfolioUpdater()
        rec = MetadataRecommendation(
            repo_name="Ethan-da-Tech-Wizard/test-repo",
            current_description="Old",
            proposed_description="New clean description",
            description_changed=True,
            topics_to_add=["automation", "devops"]
        )
        cmd = updater.build_gh_edit_command(rec)
        self.assertEqual(cmd[0], "repo")
        self.assertEqual(cmd[1], "edit")
        self.assertEqual(cmd[2], "Ethan-da-Tech-Wizard/test-repo")
        self.assertIn("--description", cmd)
        self.assertIn("New clean description", cmd)
        self.assertIn("--add-topic", cmd)
        self.assertIn("automation", cmd)

    def test_apply_dry_run(self):
        ## Verify dry-run returns planned status without executing subprocess.
        updater = PortfolioUpdater()
        rec = MetadataRecommendation(
            repo_name="Ethan-da-Tech-Wizard/test-repo",
            current_description="Old",
            proposed_description="New desc",
            description_changed=True,
            topics_to_add=["automation"]
        )
        res = updater.apply(rec, dry_run=True)
        self.assertEqual(res["status"], "planned")
        self.assertTrue(res["dry_run"])
        self.assertFalse(res["changes_applied"])

    @patch("steward.updater.subprocess.run")
    def test_apply_live_success(self, mock_run):
        ## Verify live execution handling when gh command succeeds.
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "https://github.com/Ethan-da-Tech-Wizard/test-repo"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        updater = PortfolioUpdater()
        rec = MetadataRecommendation(
            repo_name="Ethan-da-Tech-Wizard/test-repo",
            current_description="Old",
            proposed_description="New desc",
            description_changed=True,
            topics_to_add=["automation"]
        )
        res = updater.apply(rec, dry_run=False)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["changes_applied"])


    def test_apply_live_failure(self):
        ## Verify handling of gh CLI failure.
        with patch("steward.updater.subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "HTTP 403: Forbidden"
            mock_run.return_value = mock_proc

            updater = PortfolioUpdater()
            rec = MetadataRecommendation(
                repo_name="Ethan-da-Tech-Wizard/test-repo",
                current_description="Old",
                proposed_description="New desc",
                description_changed=True
            )
            res = updater.apply(rec, dry_run=False)
            self.assertEqual(res["status"], "error")
            self.assertFalse(res["changes_applied"])
            self.assertIn("403", res["message"])

    def test_apply_noop(self):
        ## Verify noop when metadata matches.
        updater = PortfolioUpdater()
        rec = MetadataRecommendation(
            repo_name="Ethan-da-Tech-Wizard/test-repo",
            current_description="Same",
            proposed_description="Same",
            description_changed=False,
            topics_to_add=[]
        )
        res = updater.apply(rec, dry_run=False)
        self.assertEqual(res["status"], "noop")
        self.assertFalse(res["changes_applied"])


class TestHeaderAuditor(unittest.TestCase):
    """
    ## Verifies detection of compliant and non-compliant Ethan-da-Tech-Wizard header blocks.
    """

    def setUp(self):
        self.auditor = HeaderAuditor()

    def test_compliant_python_header(self):
        ## Test valid Python docstring header.
        content = '''"""
Program: Test Component
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: A test module for validating headers.
"""

def foo():
    pass
'''
        res = self.auditor.audit_content(content, "test.py", ".py")
        self.assertTrue(res.is_compliant)
        self.assertEqual(res.program_name, "Test Component")
        self.assertEqual(res.programmer, "Ethan-da-Tech-Wizard")
        self.assertEqual(res.last_modified, "11/08/2026")
        self.assertEqual(res.purpose, "A test module for validating headers.")
        self.assertEqual(len(res.missing_fields), 0)

    def test_compliant_c_style_header(self):
        ## Test valid C/Rust/JS block comment header.
        content = '''/*
Program: Core Engine
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Provides low-level primitives.
*/

int main() { return 0; }
'''
        res = self.auditor.audit_content(content, "engine.c", ".c")
        self.assertTrue(res.is_compliant)
        self.assertEqual(res.program_name, "Core Engine")

    def test_missing_fields_detection(self):
        ## Test detection of missing fields.
        content = '''"""
Program: Only Program Name
"""
'''
        res = self.auditor.audit_content(content, "bad.py", ".py")
        self.assertFalse(res.is_compliant)
        self.assertIn("Programmer", res.missing_fields)
        self.assertIn("Last Modified", res.missing_fields)
        self.assertIn("Purpose", res.missing_fields)

    def test_non_ethan_programmer(self):
        ## Test that non-Ethan-da-Tech-Wizard programmer fails compliance.
        content = '''"""
Program: Some Tool
Programmer: John Doe
Last Modified: 11/08/2026
Purpose: Tool purpose.
"""
'''
        res = self.auditor.audit_content(content, "other.py", ".py")
        self.assertFalse(res.is_compliant)
        self.assertTrue(any("Ethan-da-Tech-Wizard" in f for f in res.missing_fields))

    def test_directory_audit(self):
        ## Test recursive audit of a directory with compliant and non-compliant files.
        with tempfile.TemporaryDirectory() as temp_dir:
            td = Path(temp_dir)
            good_file = td / "good.py"
            good_file.write_text('''"""
Program: Good
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Good file.
"""
''', encoding="utf-8")

            bad_file = td / "bad.py"
            bad_file.write_text("x = 1\n", encoding="utf-8")

            report = self.auditor.audit_directory(temp_dir)
            self.assertEqual(report.total_files, 2)
            self.assertEqual(report.compliant_files, 1)
            self.assertEqual(report.non_compliant_files, 1)
            self.assertEqual(report.compliance_percentage, 50.0)


class TestCLI(unittest.TestCase):
    """
    ## Verifies command-line interface execution, flag handling, and exit codes.
    """

    def test_create_parser(self):
        ## Verify parser builds with all subcommands and parses valid args.
        parser = create_parser()
        args = parser.parse_args(["scan", "--limit", "25", "--json"])
        self.assertEqual(args.command, "scan")
        self.assertEqual(args.limit, 25)
        self.assertTrue(args.json_output)

    def test_scan_local_cli(self):
        ## Verify scan --local outputs expected text and returns 0.
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "README.md").write_text("# Test\n\nSample test repo overview.\n", encoding="utf-8")
            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                code = main(["scan", "--local", temp_dir])
                self.assertEqual(code, 0)
                out = fake_out.getvalue()
                self.assertIn("Local Codebase Scan", out)
                self.assertIn("Has README:          Yes", out)

    def test_header_check_cli_pass_and_fail(self):
        ## Verify header-check exit code complies with fail-under threshold.
        with tempfile.TemporaryDirectory() as temp_dir:
            td = Path(temp_dir)
            (td / "good.py").write_text('''"""
Program: CLI Test
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Test CLI header checking.
"""
''', encoding="utf-8")

            ## 100% compliant: returns 0.
            code = main(["header-check", "--path", temp_dir, "--fail-under", "100"])
            self.assertEqual(code, 0)

            ## Add non-compliant file.
            (td / "bad.py").write_text("# No header\n", encoding="utf-8")

            ## Now 50% compliant: fail-under 100 returns 1.
            code = main(["header-check", "--path", temp_dir, "--fail-under", "100"])
            self.assertEqual(code, 1)

            ## But fail-under 40 returns 0.
            code = main(["header-check", "--path", temp_dir, "--fail-under", "40"])
            self.assertEqual(code, 0)


    def test_describe_local_cli(self):
        ## Verify describe subcommand with --local directory.
        with tempfile.TemporaryDirectory() as temp_dir:
            td = Path(temp_dir)
            (td / "README.md").write_text("# Demo Project\n\nHigh-speed parser for abstract syntax trees.\n", encoding="utf-8")
            (td / "parser.py").write_text("class Parser: pass\n", encoding="utf-8")

            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                code = main(["describe", "--local", temp_dir, "--json"])
                self.assertEqual(code, 0)
                out = fake_out.getvalue()
                data = json.loads(out)
                self.assertIn("proposed_description", data)
                self.assertTrue(data["description_changed"])

    @patch("steward.scanner.subprocess.run")
    def test_audit_cli(self, mock_run):
        ## Verify audit subcommand against remote repository list.
        mock_output = [
            {
                "name": "good-repo",
                "nameWithOwner": "Ethan-da-Tech-Wizard/good-repo",
                "description": "Valid description",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "primaryLanguage": {"name": "Python"},
                "repositoryTopics": [{"name": "cli"}],
                "defaultBranchRef": {"name": "main"},
                "updatedAt": "2026-11-08T00:00:00Z",
                "url": "https://github.com/Ethan-da-Tech-Wizard/good-repo"
            },
            {
                "name": "empty-repo",
                "nameWithOwner": "Ethan-da-Tech-Wizard/empty-repo",
                "description": None,
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "primaryLanguage": None,
                "repositoryTopics": [],
                "defaultBranchRef": {"name": "main"},
                "updatedAt": "2026-11-08T00:00:00Z",
                "url": "https://github.com/Ethan-da-Tech-Wizard/empty-repo"
            }
        ]
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(mock_output)
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = main(["audit", "--json"])
            self.assertEqual(code, 0)
            data = json.loads(fake_out.getvalue())
            self.assertEqual(data["total_repositories"], 2)
            self.assertEqual(data["description_coverage_pct"], 50.0)
            self.assertIn("Ethan-da-Tech-Wizard/empty-repo", data["missing_description"])

    def test_header_check_formats(self):
        ## Verify markdown and json output formats for header-check.
        with tempfile.TemporaryDirectory() as temp_dir:
            td = Path(temp_dir)
            (td / "mod.py").write_text('''"""
Program: Format Test
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Validate output formats.
"""
''', encoding="utf-8")

            ## Test JSON format.
            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                code = main(["header-check", "--path", temp_dir, "--format", "json"])
                self.assertEqual(code, 0)
                data = json.loads(fake_out.getvalue())
                self.assertEqual(data["compliance_percentage"], 100.0)

            ## Test Markdown format.
            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                code = main(["header-check", "--path", temp_dir, "--format", "markdown"])
                self.assertEqual(code, 0)
                out = fake_out.getvalue()
                self.assertIn("# Codebase Header Compliance Audit", out)
                self.assertIn("100.0%", out)


if __name__ == "__main__":
    unittest.main()
