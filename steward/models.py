"""
Program: GitHub Portfolio Steward - Data Models
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Strongly-typed dataclasses representing repository state, scan results, metadata recommendations, and header audit metrics.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class RepoSummary:
    """
    ## Represents core metadata for a remote GitHub repository.
    ## Mirrors output fields retrieved from the GitHub CLI (gh repo list).
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
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


@dataclass
class CodebaseFacts:
    """
    ## Represents concrete facts extracted from static inspection of a repository tree.
    ## Contains detected frameworks, languages, documentation markers, and entrypoints.
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
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


@dataclass
class MetadataRecommendation:
    """
    ## Represents proposed metadata updates for a target repository.
    ## Includes proposed description, topic deltas, and audit rationale.
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
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


@dataclass
class HeaderAuditResult:
    """
    ## Captures the header compliance state of an individual source file.
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
        ## Convert instance to a JSON-serializable dictionary.
        return asdict(self)


@dataclass
class HeaderAuditReport:
    """
    ## Aggregates header compliance metrics across an entire codebase tree.
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
