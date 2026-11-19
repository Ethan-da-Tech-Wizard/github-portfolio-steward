# ==============================================================================
# Program: scanner.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Inspects remote repositories via gh CLI and local disk clones to extract language, framework markers, and documentation snippets. Traverses file trees to identify manifest files (package.json, Cargo.toml, requirements.txt) and parses structure to extract architectural facts.
# ==============================================================================
# How this module fits in: steward/cli.py calls fetch_github_repos() to build
# the inventory, then inspect_local_directory() (when a clone exists on disk) or
# inspect_remote_repo() (when it does not) to produce CodebaseFacts, which
# steward/synthesizer.py turns into README text and steward/header_audit.py
# audits. Everything goes through the `gh` CLI so no token handling or HTTP
# client lives in this tool.
#
# Known limits: detection is purely filename/extension based (no parsing of
# manifests), so a repo with vendored code can over-report languages; the
# remote path is capped by the GitHub tree API (truncated for huge repos).
# Tested by tests/test_steward.py with a fake gh executable.
import json
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from steward.models import RepoSummary, CodebaseFacts


class RepositoryScanner:
    """
    ## Orchestrates static analysis across remote GitHub repositories and local working trees.
    ## Uses the official GitHub CLI (gh) for zero-dependency remote API interactions.
    """

    ## Regex for cleaning markdown syntax from extracted README snippets.
    # Compiled once at class level: extract_readme_summary runs per repo and these
    # four patterns are applied to every candidate paragraph.
    _MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    _MARKDOWN_HEADER_PATTERN = re.compile(r"^#+\s*", re.MULTILINE)
    _MARKDOWN_FORMATTING_PATTERN = re.compile(r"[*_`~]")
    _HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

    ## Map of file extensions to canonical language names.
    # Extension -> display name. Deliberately small: only languages the portfolio
    # actually contains. Header-only extensions get their own label so a C++ repo
    # is not mislabelled as C. Anything unmapped is simply not counted.
    _EXTENSION_LANGUAGE_MAP = {
        ".py": "Python",
        ".rs": "Rust",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JavaScript",
        ".tsx": "TypeScript",
        ".c": "C",
        ".cpp": "C++",
        ".cc": "C++",
        ".h": "C/C++ Header",
        ".hpp": "C++ Header",
        ".go": "Go",
        ".java": "Java",
        ".sh": "Shell",
        ".bash": "Shell",
        ".rb": "Ruby",
        ".php": "PHP",
        ".html": "HTML",
        ".css": "CSS",
    }

    def __init__(self, gh_executable: str = "gh"):
        ## Store the binary name or path for gh CLI invocations.
        # Injectable so tests can point at a stub script instead of the real gh.
        self.gh_executable = gh_executable

    def _execute_gh(self, args: List[str]) -> Tuple[int, str, str]:
        """
        ## Helper to execute a gh command in a subprocess safely.
        ## Captures stdout and stderr without raising unhandled subprocess exceptions.
        """
        # List form (never a shell string) so repo names with odd characters cannot
        # be interpreted by a shell.
        cmd = [self.gh_executable] + args
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                # check=False: callers inspect the return code themselves and decide whether
                # a failure is fatal (list) or recoverable (tree -> contents fallback).
                check=False
            )
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except FileNotFoundError:
            # 127 mirrors the shell's 'command not found' so callers treat it like any
            # other gh failure without a special exception type.
            ## Return failure if gh CLI is missing from the environment PATH.
            return 127, "", f"Executable '{self.gh_executable}' not found in PATH."

    def fetch_github_repos(
        self,
        owner: Optional[str] = None,
        limit: int = 100,
        include_forks: bool = False,
        include_archived: bool = False
    ) -> List[RepoSummary]:
        """
        ## Queries GitHub for repository inventory using gh repo list.
        ## Parses JSON responses into strongly-typed RepoSummary models.
        """
        # Request only the JSON fields RepoSummary needs; asking for more makes gh
        # slower and wastes API rate limit on large accounts.
        ## Construct argument list requesting standardized JSON fields.
        args = [
            "repo", "list",
            "--limit", str(limit),
            "--json", "name,nameWithOwner,description,isPrivate,isFork,isArchived,primaryLanguage,repositoryTopics,defaultBranchRef,updatedAt,url"
        ]
        if owner:
            # gh requires the owner positionally right after `repo list`, before flags.
            args.insert(2, owner)

        returncode, stdout, stderr = self._execute_gh(args)
        if returncode != 0:
            raise RuntimeError(f"Failed to fetch repositories via gh: {stderr or stdout}")

        # gh prints nothing (not '[]') for an account with zero repos.
        if not stdout:
            return []

        try:
            raw_data = json.loads(stdout)
        except json.JSONDecodeError as err:
            raise ValueError(f"Invalid JSON returned by gh repo list: {err}")

        # Forks and archived repos are skipped by default because they are not the
        # owner's authored work and would pollute the portfolio README.
        summaries: List[RepoSummary] = []
        for item in raw_data:
            ## Filter forks and archived repos unless explicitly requested.
            if not include_forks and item.get("isFork", False):
                continue
            if not include_archived and item.get("isArchived", False):
                continue

            ## Extract primary language safely from nested structure.
            primary_lang = None
            if item.get("primaryLanguage"):
                primary_lang = item["primaryLanguage"].get("name")

            ## Extract topic names from repositoryTopics list.
            topics: List[str] = []
            if item.get("repositoryTopics"):
                for t in item["repositoryTopics"]:
                    topic_name = t.get("name")
                    if topic_name:
                        topics.append(topic_name)

            ## Extract default branch name safely.
            default_branch = "main"
            if item.get("defaultBranchRef") and item["defaultBranchRef"].get("name"):
                default_branch = item["defaultBranchRef"]["name"]

            summaries.append(
                RepoSummary(
                    name=item.get("name", ""),
                    full_name=item.get("nameWithOwner", ""),
                    description=item.get("description"),
                    is_private=item.get("isPrivate", False),
                    is_fork=item.get("isFork", False),
                    is_archived=item.get("isArchived", False),
                    primary_language=primary_lang,
                    topics=topics,
                    default_branch=default_branch,
                    updated_at=item.get("updatedAt", ""),
                    url=item.get("url", "")
                )
            )

        return summaries

    def inspect_local_directory(self, root_dir: str) -> CodebaseFacts:
        """
        ## Performs comprehensive static analysis on a local directory.
        ## Walks directory paths to detect languages, framework markers, licenses, and tests.
        """
        path = Path(root_dir).resolve()
        if not path.is_dir():
            raise NotADirectoryError(f"Directory not found: {root_dir}")

        # Directories that are never authored source: VCS metadata, caches, virtualenvs
        # and build output. Pruned in place below so os.walk never descends into them
        # (this is what keeps scans of big clones fast).
        ignored_dirs = {
            ".git", ".svn", ".hg", "__pycache__", "node_modules",
            "venv", ".venv", "env", "target", "build", "dist",
            ".pytest_cache", ".mypy_cache", ".ruff_cache", "site-packages"
        }

        # Sets, not lists: the same marker file appears in many subdirectories and
        # each should only be reported once.
        frameworks = set()
        languages = set()
        file_count = 0
        has_readme = False
        readme_path: Optional[Path] = None
        has_license = False
        has_tests = False
        has_ci = False
        entrypoints: List[str] = []

        ## Traverse directory structure.
        for root, dirs, files in os.walk(path):
            ## Prune ignored directories in-place.
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            rel_root = Path(root).relative_to(path)

            ## Check for GitHub Actions CI.
            if str(rel_root).startswith(".github/workflows") and files:
                # Any file under .github/workflows counts; the workflow content is not parsed.
                has_ci = True

            ## Check for test directories.
            if any(part in ("tests", "test", "spec") for part in rel_root.parts):
                has_tests = True

            for fname in files:
                file_count += 1
                fpath = Path(root) / fname
                lower_fname = fname.lower()

                # Prefer an exact README.md over README.rst/README.txt when several exist,
                # because extract_readme_summary expects Markdown.
                ## README detection.
                if lower_fname.startswith("readme"):
                    has_readme = True
                    if readme_path is None or lower_fname == "readme.md":
                        readme_path = fpath

                ## License detection.
                if lower_fname.startswith("license") or lower_fname.startswith("copying"):
                    has_license = True

                ## Test file detection.
                if (lower_fname.startswith("test_") or lower_fname.endswith("_test.py") or
                        lower_fname.endswith(".test.js") or lower_fname.endswith(".spec.ts")):
                    has_tests = True

                ## Language detection via extension.
                ext = fpath.suffix.lower()
                if ext in self._EXTENSION_LANGUAGE_MAP:
                    languages.add(self._EXTENSION_LANGUAGE_MAP[ext])

                ## Framework and tool markers.
                # Marker files double as language evidence: a repo can have a Cargo.toml
                # before any .rs file is matched (e.g. only a workspace manifest).
                if fname in ("Cargo.toml", "Cargo.lock"):
                    frameworks.add("cargo")
                    languages.add("Rust")
                elif fname in ("pyproject.toml", "setup.py", "requirements.txt", "Pipfile"):
                    frameworks.add("pip")
                    languages.add("Python")
                elif fname in ("package.json", "yarn.lock", "pnpm-lock.yaml"):
                    frameworks.add("npm")
                    languages.add("JavaScript")
                elif fname in ("CMakeLists.txt", "Makefile"):
                    frameworks.add("cmake" if fname == "CMakeLists.txt" else "make")
                elif fname in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"):
                    frameworks.add("docker")
                elif fname.endswith(".service") or fname.endswith(".timer") or fname.endswith(".socket"):
                    frameworks.add("systemd")
                elif fname == "go.mod":
                    frameworks.add("go-modules")
                    languages.add("Go")

                # Entry points are recorded relative to the repo root so the synthesizer can
                # print 'run python -m ...' style hints without leaking absolute paths.
                ## Common entrypoint detection.
                if fname in ("main.py", "__main__.py", "main.rs", "index.js", "index.ts", "main.go", "cli.py"):
                    entrypoints.append(str(Path(root).relative_to(path) / fname))

        ## Extract README snippet if README exists.
        # A README that is unreadable must not abort the whole scan; the snippet is
        # optional metadata and has_readme is already recorded.
        readme_snippet = None
        if readme_path and readme_path.is_file():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
                readme_snippet = self.extract_readme_summary(content)
            except Exception:
                readme_snippet = None

        # sorted() so output is deterministic: the generated README is diffed against
        # the committed one and set ordering would cause spurious 'changed' results.
        return CodebaseFacts(
            detected_frameworks=sorted(list(frameworks)),
            detected_languages=sorted(list(languages)),
            file_count=file_count,
            has_readme=has_readme,
            readme_snippet=readme_snippet,
            has_license=has_license,
            has_tests=has_tests,
            has_ci=has_ci,
            entrypoints=sorted(entrypoints)
        )

    def inspect_remote_repo(self, repo_full_name: str, branch: Optional[str] = None) -> CodebaseFacts:
        """
        ## Inspects a remote repository tree without local cloning using gh API.
        ## Retrieves git tree recursively and extracts framework markers and README.
        """
        target_branch = branch or "HEAD"
        # One recursive tree call replaces cloning; truncated=true responses are
        # possible for very large repos, in which case counts are lower bounds.
        endpoint = f"repos/{repo_full_name}/git/trees/{target_branch}?recursive=1"
        returncode, stdout, stderr = self._execute_gh(["api", endpoint])

        if returncode != 0:
            ## If recursive tree fails, fallback to repo info and basic root content list.
            # Tree endpoint failed (empty repo, rate limit, bad branch): degrade to the
            # shallower contents listing instead of failing the whole run.
            return self._inspect_remote_root_fallback(repo_full_name)

        try:
            tree_data = json.loads(stdout)
        except json.JSONDecodeError:
            return self._inspect_remote_root_fallback(repo_full_name)

        frameworks = set()
        languages = set()
        file_count = 0
        has_readme = False
        has_license = False
        has_tests = False
        has_ci = False
        entrypoints: List[str] = []

        tree_entries = tree_data.get("tree", [])
        for entry in tree_entries:
            path_str = entry.get("path", "")
            lower_path = path_str.lower()
            fname = os.path.basename(path_str)
            lower_fname = fname.lower()

            # Only blobs are files; 'tree' entries are directories and must not inflate
            # file_count.
            if entry.get("type") == "blob":
                file_count += 1

                if lower_fname.startswith("readme"):
                    has_readme = True
                if lower_fname.startswith("license") or lower_fname.startswith("copying"):
                    has_license = True
                if (lower_fname.startswith("test_") or lower_fname.endswith("_test.py") or
                        # Remote scans have no directory walk, so test directories are recognised by
                        # path substring instead.
                        "tests/" in lower_path or "test/" in lower_path):
                    has_tests = True

                ext = os.path.splitext(fname)[1].lower()
                if ext in self._EXTENSION_LANGUAGE_MAP:
                    languages.add(self._EXTENSION_LANGUAGE_MAP[ext])

                if fname in ("Cargo.toml", "Cargo.lock"):
                    frameworks.add("cargo")
                    languages.add("Rust")
                elif fname in ("pyproject.toml", "setup.py", "requirements.txt"):
                    frameworks.add("pip")
                    languages.add("Python")
                elif fname in ("package.json", "yarn.lock"):
                    frameworks.add("npm")
                    languages.add("JavaScript")
                elif fname in ("CMakeLists.txt", "Makefile"):
                    frameworks.add("cmake" if fname == "CMakeLists.txt" else "make")
                elif fname in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"):
                    frameworks.add("docker")
                elif fname.endswith(".service") or fname.endswith(".timer"):
                    frameworks.add("systemd")

                if path_str.startswith(".github/workflows/"):
                    has_ci = True

                if fname in ("main.py", "__main__.py", "main.rs", "index.js", "index.ts", "main.go", "cli.py"):
                    entrypoints.append(path_str)

        ## Fetch README content via gh api repos/{repo}/readme.
        readme_snippet = self._fetch_remote_readme(repo_full_name)

        return CodebaseFacts(
            detected_frameworks=sorted(list(frameworks)),
            detected_languages=sorted(list(languages)),
            file_count=file_count,
            has_readme=has_readme,
            readme_snippet=readme_snippet,
            has_license=has_license,
            has_tests=has_tests,
            has_ci=has_ci,
            entrypoints=sorted(entrypoints)
        )

    def _fetch_remote_readme(self, repo_full_name: str) -> Optional[str]:
        """
        ## Fetches and decodes the repository README markdown via the GitHub API.
        """
        endpoint = f"repos/{repo_full_name}/readme"
        returncode, stdout, _ = self._execute_gh(["api", endpoint, "--jq", ".content"])
        if returncode == 0 and stdout:
            # Imported lazily: only this rarely used path needs it.
            import base64
            try:
                # The contents API returns base64 with embedded newlines; b64decode ignores them.
                decoded = base64.b64decode(stdout).decode("utf-8", errors="replace")
                return self.extract_readme_summary(decoded)
            except Exception:
                return None
        return None

    def _inspect_remote_root_fallback(self, repo_full_name: str) -> CodebaseFacts:
        """
        ## Fallback inspection when git tree recursive endpoint is unavailable.
        """
        endpoint = f"repos/{repo_full_name}/contents"
        returncode, stdout, _ = self._execute_gh(["api", endpoint])
        if returncode != 0 or not stdout:
            return CodebaseFacts()

        try:
            items = json.loads(stdout)
        except json.JSONDecodeError:
            return CodebaseFacts()

        frameworks = set()
        languages = set()
        # Fallback only sees the root directory, so these numbers are a floor, not a
        # real count; the steward treats the result as 'good enough to describe'.
        file_count = len(items)
        has_readme = False
        has_license = False

        for item in items:
            name = item.get("name", "")
            lower_name = name.lower()
            if lower_name.startswith("readme"):
                has_readme = True
            if lower_name.startswith("license"):
                has_license = True
            if name == "Cargo.toml":
                frameworks.add("cargo")
                languages.add("Rust")
            elif name in ("pyproject.toml", "setup.py", "requirements.txt"):
                frameworks.add("pip")
                languages.add("Python")
            elif name == "package.json":
                frameworks.add("npm")
                languages.add("JavaScript")
            elif name == "Dockerfile":
                frameworks.add("docker")

        return CodebaseFacts(
            detected_frameworks=sorted(list(frameworks)),
            detected_languages=sorted(list(languages)),
            file_count=file_count,
            has_readme=has_readme,
            readme_snippet=self._fetch_remote_readme(repo_full_name),
            has_license=has_license
        )

    def extract_readme_summary(self, markdown_content: str) -> Optional[str]:
        """
        ## Extracts the primary descriptive paragraph from README content.
        ## Cleans markdown markup, strips headers and badges, and returns clean text.
        """
        if not markdown_content:
            return None

        lines = markdown_content.splitlines()
        # Two-pass: first split into paragraphs, then pick the first one that looks
        # like prose. Doing it in one pass would make badges mid-paragraph hard to drop.
        candidate_paragraphs: List[str] = []
        current_para: List[str] = []

        for line in lines:
            trimmed = line.strip()
            ## Skip markdown headers, image badges, and blank lines.
            if not trimmed or trimmed.startswith("#") or trimmed.startswith("[![") or trimmed.startswith("!["):
                if current_para:
                    candidate_paragraphs.append(" ".join(current_para))
                    current_para = []
                continue

            ## Skip blockquotes or list items for primary overview summary.
            # Lists and quotes are usually feature bullets or notes, not the one-line
            # description we want for a portfolio blurb.
            if trimmed.startswith(">") or trimmed.startswith("- ") or trimmed.startswith("* "):
                continue

            current_para.append(trimmed)

        if current_para:
            candidate_paragraphs.append(" ".join(current_para))

        for para in candidate_paragraphs:
            ## Strip markdown links: [text](url) -> text.
            cleaned = self._MARKDOWN_LINK_PATTERN.sub(r"\1", para)
            ## Strip html tags.
            cleaned = self._HTML_TAG_PATTERN.sub("", cleaned)
            ## Strip formatting chars (*, _, `, ~).
            cleaned = self._MARKDOWN_FORMATTING_PATTERN.sub("", cleaned)
            cleaned = " ".join(cleaned.split())

            ## Check if paragraph is substantial and informative.
            # 20 chars filters out taglines like 'MIT License' while accepting real
            # sentences; the TOC check avoids picking the contents list of long READMEs.
            if len(cleaned) >= 20 and not cleaned.lower().startswith("table of contents"):
                return cleaned

        return None
