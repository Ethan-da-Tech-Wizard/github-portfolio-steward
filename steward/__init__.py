"""
Program: GitHub Portfolio Steward - Package Root
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Package initialization and public interface exposure for GitHub Portfolio Steward.
"""

## Export primary models and classes for direct module consumption.
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

## Semantic versioning identifier.
__version__ = "1.0.0"
__author__ = "Ethan-da-Tech-Wizard"

__all__ = [
    "RepoSummary",
    "CodebaseFacts",
    "MetadataRecommendation",
    "HeaderAuditResult",
    "HeaderAuditReport",
    "RepositoryScanner",
    "MetadataSynthesizer",
    "PortfolioUpdater",
    "HeaderAuditor",
]
