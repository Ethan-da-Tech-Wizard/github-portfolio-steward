# GitHub Portfolio Steward

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20(stdlib%20only)-brightgreen.svg)]()
[![Code Compliance](https://img.shields.io/badge/header--compliance-100%25-success.svg)]()

> **Zero-dependency autonomous GitHub portfolio curator and codebase analyzer for hands-free description, topic, and docstring governance.**

GitHub Portfolio Steward provides deterministic, autonomous static analysis of repositories on GitHub and local disk clones. It inspects repository trees, discovers key build markers (Cargo, pip, npm, cmake, docker, systemd), synthesizes punchy descriptions under GitHub character limits (<250 chars), recommends searchable topics, and enforces file-level Ethan-da-Tech-Wizard header docstring compliance across codebases.

---

## Architecture Overview

```
                          +-------------------------------+
                          |   GitHub Portfolio Steward    |
                          |       CLI (steward/cli.py)    |
                          +---------------+---------------+
                                          |
                +-------------------------+-------------------------+
                |                         |                         |
                v                         v                         v
     +--------------------+    +--------------------+    +--------------------+
     | Repository Scanner |    | Metadata Synthesizer|   | Header Auditor     |
     | (steward/scanner)  |    | (steward/synthesizer|   | (header_audit.py)  |
     +---------+----------+    +----------+---------+    +---------+----------+
               |                          |                        |
        [gh CLI / Local]           [Fact Synthesis]         [Docstring AST/Regex]
               |                          |                        |
               v                          v                        v
     +--------------------+    +--------------------+    +--------------------+
     |   Codebase Facts   |--->| Recommendation Plan|    | Compliance Report  |
     +--------------------+    +----------+---------+    +--------------------+
                                          |
                                          v
                               +--------------------+
                               | Hands-Free Updater |
                               | (steward/updater)  |
                               +----------+---------+
                                          |
                                   (gh repo edit)
                                          |
                                          v
                               +--------------------+
                               | GitHub Remote API  |
                               +--------------------+
```

---

## Core Capabilities

1. **Zero External Dependencies**:
   - Built exclusively on the Python 3 standard library (`subprocess`, `json`, `os`, `sys`, `pathlib`, `re`, `argparse`, `dataclasses`).
   - Interacts with GitHub via the authenticated `gh` CLI — zero third-party token handling or OAuth credential exposure.

2. **Deep Static Codebase Inspection**:
   - Automatically detects languages and package ecosystems:
     - **Cargo / Rust**: `Cargo.toml`, `Cargo.lock`
     - **Pip / Python**: `pyproject.toml`, `setup.py`, `requirements.txt`
     - **Npm / Node**: `package.json`, `yarn.lock`, `pnpm-lock.yaml`
     - **C / C++**: `CMakeLists.txt`, `Makefile`
     - **Docker**: `Dockerfile`, `docker-compose.yml`
     - **Linux System Services**: `*.service`, `*.timer`, `*.socket`
     - **CI/CD Workflows**: `.github/workflows/*.yml`
   - Strips badges, markdown links, and HTML to extract clean README summary paragraphs.

3. **Deterministic Metadata Synthesis**:
   - Generates active-voice descriptions strictly within GitHub's limits (`< 250` characters).
   - Generates normalized, deduplicated GitHub topics adhering to topic slug constraints (`^[a-z0-9]+(-[a-z0-9]+)*$`).
   - Supports robust exclusion lists via regex patterns (e.g. ignoring private repos, client projects, or specific orgs).

4. **Hands-Free Remote Synchronization**:
   - Safely prepares batch updates via `--dry-run` plans before touching remote repositories.
   - Executes atomic updates via `gh repo edit` with `--apply`.

5. **Codebase Header Docstring Governance**:
   - Recursively verifies that every source file (`.py`, `.c`, `.cpp`, `.rs`, `.js`, `.ts`, `.go`, `.sh`) contains the standard Ethan-da-Tech-Wizard header block:
     ```python
     """
     Program: <Component Name>
     Programmer: Ethan-da-Tech-Wizard
     Last Modified: MM/DD/YYYY
     Purpose: <Clear, plain English explanation>
     """
     ```
   - Enforces configurable compliance thresholds (`--fail-under 100`) for CI/CD gates.

---

## Installation & Requirements

### Prerequisites
- Python 3.8 or higher.
- [GitHub CLI (`gh`)](https://cli.github.com/) authenticated via `gh auth login`.

### Quick Installation
Clone the repository and install locally:
```bash
git clone https://github.com/Ethan-da-Tech-Wizard/github-portfolio-steward.git
cd github-portfolio-steward

# Install console script in editable mode or user path
pip install -e .
```

Or run directly without installation:
```bash
python3 -m steward --help
```

---

## Command-Line Interface Guide

### 1. `scan`: Inspect Remote or Local Repositories
Scan a local directory to view detected languages, frameworks, and README summaries:
```bash
python3 -m steward scan --local .
```

Output:
```
--- Local Codebase Scan: . ---
Files Counted:       11
Detected Languages:  Python
Detected Frameworks: pip
Has README:          Yes
Has License:         No
Has Tests:           Yes
Has CI/CD:           No
README Summary:      Zero-dependency autonomous GitHub portfolio curator and codebase analyzer for hands-free description, topic, and docstring governance.
```

List your remote GitHub repositories with topic counts:
```bash
python3 -m steward scan --limit 20
```

Output JSON format for automated pipelines:
```bash
python3 -m steward scan --local . --json
```

---

### 2. `describe`: Synthesize Optimal Metadata
Generate a description and recommended topics for a local codebase or remote repo:
```bash
python3 -m steward describe --local .
```

Output:
```
=== Metadata Recommendation: github-portfolio-steward ===
Current Description:  (None)
Proposed Description: Zero-dependency autonomous GitHub portfolio curator and codebase analyzer for hands-free description, topic, and docstring governance.
Description Changed:  Yes
Current Topics:       (None)
Proposed Topics:      automation, codebase-analysis, devops, github-api, pip, portfolio, python, zero-dependencies
Topics to Add:        automation, codebase-analysis, devops, github-api, pip, portfolio, python, zero-dependencies
Confidence Score:     95%
Reasoning:
  - Repository lacks a description; synthesized from codebase analysis.
  - Identified 8 missing searchable topics based on file markers.
```

---

### 3. `sync`: Apply Changes to GitHub
Run in **dry-run** mode to inspect planned updates across your portfolio:
```bash
python3 -m steward sync --owner Ethan-da-Tech-Wizard --dry-run
```

Apply updates live to a specific repository:
```bash
python3 -m steward sync --repo Ethan-da-Tech-Wizard/github-portfolio-steward --apply
```

Exclude repositories matching regex patterns:
```bash
python3 -m steward sync --owner Ethan-da-Tech-Wizard --exclude ".*-internal,archived-.*" --apply
```

---

### 4. `audit`: Portfolio Readiness Inspection
Evaluate metadata completeness across all your repositories:
```bash
python3 -m steward audit --limit 50
```

Output:
```
=== Portfolio Metadata Readiness Audit ===
Total Repositories Analyzed: 14
Description Coverage:        92.9% (13/14)
Topics Coverage:             85.7% (12/14)

Repositories Missing Descriptions (1):
  - Ethan-da-Tech-Wizard/scratch-eval
```

---

### 5. `header-check`: Docstring & Header Compliance
Audit source files in a local directory to verify Ethan-da-Tech-Wizard headers:
```bash
python3 -m steward header-check --path . --fail-under 100
```

Output:
```
=== Codebase Header Compliance Audit ===
Root:                  /home/user/EXAMPLE_ORG/exports/github-portfolio-steward
Total Source Files:    10
Compliant Files:       10
Non-Compliant Files:   0
Compliance Percentage: 100.0%

Status   Language     File                                          Missing Fields / Notes
-----------------------------------------------------------------------------------------------
PASS     Python       steward/__init__.py                           Compliant
PASS     Python       steward/__main__.py                           Compliant
PASS     Python       steward/cli.py                                Compliant
PASS     Python       steward/header_audit.py                       Compliant
PASS     Python       steward/models.py                             Compliant
PASS     Python       steward/scanner.py                            Compliant
PASS     Python       steward/synthesizer.py                        Compliant
PASS     Python       steward/updater.py                            Compliant
PASS     Python       tests/__init__.py                             Compliant
PASS     Python       tests/test_steward.py                         Compliant
```

Output Markdown format for GitHub Actions PR summaries:
```bash
python3 -m steward header-check --path . --format markdown
```

---

## Test Suite Execution

Exhaustive unit tests cover models, scanner, synthesizer, updater, header auditor, and CLI dispatch:
```bash
python3 -m unittest discover -s tests -v
```

Expected output:
```
Ran 27 tests in 0.011s

OK
```

---

## Technical Interview Defense (STAR Method)

### Situation
> *"Managing a growing portfolio of tens of engineering repositories leads to documentation entropy: repos lack standardized searchable topics, descriptions are missing or inconsistent, and source files lack authorship governance headers required by enterprise standards."*

### Task
> *"Design and engineer an autonomous, hands-free tool that curates GitHub repository metadata, extracts structural facts from code trees, generates professional descriptions adhering to GitHub length limits, and enforces docstring compliance across local source files — with zero pip dependencies."*

### Action
> 1. **Zero-Dependency Architecture**: Leveraged Python's standard library (`subprocess`, `argparse`, `json`, `dataclasses`, `pathlib`) and delegated remote GitHub mutations to the authenticated `gh` CLI. This prevents credential leakage and ensures instant portability across Linux and macOS environments without virtual environment overhead.
> 2. **Multi-Ecosystem Static Analysis**: Built deterministic marker detection for Cargo, pip, npm, cmake, docker, and systemd units, coupled with a robust Markdown parser that cleans HTML and badge noise to extract authentic README overviews.
> 3. **Defensive Metadata Synthesis**: Enforced hard character boundaries (<250 chars) and RFC-compliant topic slug normalization (`^[a-z0-9]+(-[a-z0-9]+)*$`) with configurable regex exclusion lists.
> 4. **Header Governance Engine**: Engineered a multi-language header auditor that validates `Program`, `Programmer`, `Last Modified`, and `Purpose` across Python docstrings, C/Rust block comments, and shell scripts with customizable CI failure gates.

### Result
> *"A production-ready CLI that audits and synchronizes portfolio metadata in milliseconds, verifies 100% docstring compliance across source trees, and runs anywhere with Python 3 and gh CLI installed."*

---

## Key Technical Decisions & FAQ

### Why use `gh` CLI instead of PyGithub or Requests?
1. **Security & Zero Credentials**: `gh` uses the system's secure keyring. No personal access tokens (PATs) or secrets are stored in configuration files or memory.
2. **Zero Dependencies**: PyGithub requires `requests`, `urllib3`, `certifi`, etc. Relying on `gh` maintains a pure standard-library footprint with 0 installation dependencies.
3. **Enterprise Compliance**: Respects enterprise SSO, two-factor authentication, and GitHub token scopes automatically.

### How does the tool avoid GitHub API rate limits?
- In local mode (`--local`), zero API calls are made.
- In remote mode, `gh repo list --json` aggregates full portfolio metadata in a single network round-trip.
- Remote tree queries utilize the recursive Git Trees API (`/git/trees/HEAD?recursive=1`), retrieving the entire repository hierarchy in a single call rather than walking directories individually.

---

## License
MIT License. Copyright (c) 2026 Ethan-da-Tech-Wizard.
