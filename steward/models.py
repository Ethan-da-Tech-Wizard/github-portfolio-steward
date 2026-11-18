# Program: github-portfolio-steward - models.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Defines the dataclasses that carry repository info, scan facts, metadata recommendations and header-audit results between the other modules.

"""
Program: GitHub Portfolio Steward - Data Models
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Strongly-typed dataclasses representing repository state, scan results, metadata recommendations, and header audit metrics.
"""

# ============================================================
# IMPORTS
# ============================================================
# dataclass auto-writes __init__ for simple data holders; asdict turns one into a dict.
# field(default_factory=list) gives each object its own fresh list.
from dataclasses import dataclass, field, asdict
# Type hints only; they document the expected types.
from typing import List, Optional, Dict, Any


# ============================================================
# REPOSITORY SUMMARY
# ============================================================
# @dataclass writes the constructor for us from the annotated fields below.
@dataclass
class RepoSummary:
    """
    ## Represents core metadata for a remote GitHub repository.
    ## Mirrors output fields retrieved from the GitHub CLI (gh repo list).
    """
    # Fields without a default (name, full_name) are required; the rest are optional.
    name: str
    full_name: str
    description: Optional[str] = None
    # Simple yes/no flags describing the repository.
    is_private: bool = False
    is_fork: bool = False
    is_archived: bool = False
    primary_language: Optional[str] = None
    # Topic tags already on GitHub; default_factory avoids sharing one list between objects.
    topics: List[str] = field(default_factory=list)
    default_branch: str = "main"
    updated_at: str = ""
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return this object's fields as a plain dictionary (handy for JSON output)."""
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


# ============================================================
# CODEBASE FACTS
# ============================================================
# Everything the scanner learned by looking at a repo's files.
@dataclass
class CodebaseFacts:
    """
    ## Represents concrete facts extracted from static inspection of a repository tree.
    ## Contains detected frameworks, languages, documentation markers, and entrypoints.
    """
    # Frameworks/tools found by marker files, and languages found by file extension.
    detected_frameworks: List[str] = field(default_factory=list)
    detected_languages: List[str] = field(default_factory=list)
    # Total number of files seen, plus yes/no flags for README, license, tests and CI.
    file_count: int = 0
    has_readme: bool = False
    readme_snippet: Optional[str] = None
    has_license: bool = False
    has_tests: bool = False
    has_ci: bool = False
    # Paths of files that look like program starting points (main.py, index.js, ...).
    entrypoints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return this object's fields as a plain dictionary (handy for JSON output)."""
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


# ============================================================
# METADATA RECOMMENDATION
# ============================================================
# The synthesizer's suggestion for one repository, compared with what exists now.
@dataclass
class MetadataRecommendation:
    """
    ## Represents proposed metadata updates for a target repository.
    ## Includes proposed description, topic deltas, and audit rationale.
    """
    repo_name: str
    current_description: Optional[str]
    proposed_description: str
    # True when the proposed description differs from the current one.
    description_changed: bool
    current_topics: List[str] = field(default_factory=list)
    proposed_topics: List[str] = field(default_factory=list)
    # Only the topics that are new (proposed but not already on the repo).
    topics_to_add: List[str] = field(default_factory=list)
    # A number from 0 to 1 saying how sure we are (higher when a README exists).
    confidence_score: float = 1.0
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return this object's fields as a plain dictionary (handy for JSON output)."""
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


# ============================================================
# HEADER AUDIT RESULT
# ============================================================
# The outcome of checking one source file for the standard header.
@dataclass
class HeaderAuditResult:
    """
    ## Captures the header compliance state of an individual source file.
    """
    file_path: str
    language: str
    # True only if every required header field was found.
    is_compliant: bool
    program_name: Optional[str] = None
    programmer: Optional[str] = None
    last_modified: Optional[str] = None
    purpose: Optional[str] = None
    # Names of required header fields that were absent or wrong.
    missing_fields: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return this object's fields as a plain dictionary (handy for JSON output)."""
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


# ============================================================
# HEADER AUDIT REPORT
# ============================================================
# Totals for a whole folder plus the per-file results.
@dataclass
class HeaderAuditReport:
    """
    ## Aggregates header compliance metrics across an entire codebase tree.
    """
    root_path: str
    total_files: int = 0
    compliant_files: int = 0
    non_compliant_files: int = 0
    # Share of files that passed, from 0 to 100.
    compliance_percentage: float = 0.0
    results: List[HeaderAuditResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return this object's fields as a plain dictionary (handy for JSON output)."""
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)
