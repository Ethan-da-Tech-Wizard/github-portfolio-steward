# ==============================================================================
# Program: models.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Strongly-typed dataclasses representing repository state, scan results, metadata recommendations, and header audit metrics. Defines structured schemas for repository inventory, language breakdowns, and compliance scores.
# ==============================================================================
"""
Domain models and schema definitions for the Portfolio Steward subsystem.

Architecture & Design Rationale:
- Utilizes Python dataclasses with `asdict()` serialization to provide lightweight,
  strongly-typed value objects without heavy ORM or Pydantic dependencies.
- Enforces explicit default factory bindings for mutable collection attributes (`field(default_factory=list)`)
  to prevent inadvertent state sharing across instances.
- Structures repository introspection facts into isolated domains: Remote Inventory (`RepoSummary`),
  Static AST / File Tree Heuristics (`CodebaseFacts`), Proposed Modifications (`MetadataRecommendation`),
  and Documentation Standard Audits (`HeaderAuditResult`, `HeaderAuditReport`).
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class RepoSummary:
    """
    ## Represents core metadata for a remote GitHub repository.
    ## Mirrors output fields retrieved from the GitHub CLI (gh repo list).
    
    Attributes:
        name: Short repository name (e.g., 'portfolio-steward').
        full_name: Canonical owner/name identifier (e.g., 'Ethan-da-Tech-Wizard/portfolio-steward').
        description: Current repository summary or None if unset.
        is_private: True if access is restricted to authorized collaborators.
        is_fork: True if this repository was forked from an upstream repository.
        is_archived: True if repository is marked read-only on GitHub.
        primary_language: Top detected language reported by GitHub Linguist.
        topics: Collection of alphanumeric topic tags assigned to the repo.
        default_branch: Primary integration branch (typically 'main' or 'master').
        updated_at: ISO-8601 timestamp representing latest commit or metadata mutation.
        url: Canonical web URL pointing to the repository on github.com.
    """
    name: str
    full_name: str
    description: Optional[str] = None
    is_private: bool = False
    is_fork: bool = False
    is_archived: bool = False
    primary_language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    default_branch: str = "main"
    updated_at: str = ""
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class CodebaseFacts:
    """
    ## Represents concrete facts extracted from static inspection of a repository tree.
    ## Contains detected frameworks, languages, documentation markers, and entrypoints.
    
    Design Note:
        All fact collections maintain deterministic lexicographical ordering to ensure
        reproducible hash generation and consistent downstream synthesizer behavior.
    """
    detected_frameworks: List[str] = field(default_factory=list)
    detected_languages: List[str] = field(default_factory=list)
    file_count: int = 0
    has_readme: bool = False
    readme_snippet: Optional[str] = None
    has_license: bool = False
    has_tests: bool = False
    has_ci: bool = False
    entrypoints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class MetadataRecommendation:
    """
    ## Represents proposed metadata updates for a target repository.
    ## Includes proposed description, topic deltas, and audit rationale.
    
    State Invariants:
        - `proposed_description` length must not exceed GitHub's maximum boundary (245 chars).
        - `topics_to_add` represents strictly the set difference: `proposed_topics - current_topics`.
        - `confidence_score` is a normalized float within the bounded range [0.0, 1.0].
    """
    repo_name: str
    current_description: Optional[str]
    proposed_description: str
    description_changed: bool
    current_topics: List[str] = field(default_factory=list)
    proposed_topics: List[str] = field(default_factory=list)
    topics_to_add: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class HeaderAuditResult:
    """
    ## Captures the header compliance state of an individual source file.
    
    Evaluation Model:
        A file is compliant (`is_compliant=True`) if and only if all four mandatory
        standard header fields (Program, Programmer, Last Modified, Purpose) are
        present and contain valid non-empty values matching specification constraints.
    """
    file_path: str
    language: str
    is_compliant: bool
    program_name: Optional[str] = None
    programmer: Optional[str] = None
    last_modified: Optional[str] = None
    purpose: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class HeaderAuditReport:
    """
    ## Aggregates header compliance metrics across an entire codebase tree.
    
    Calculates overall compliance ratio:
        compliance_percentage = (compliant_files / total_files) * 100.0
    """
    root_path: str
    total_files: int = 0
    compliant_files: int = 0
    non_compliant_files: int = 0
    compliance_percentage: float = 0.0
    results: List[HeaderAuditResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)
