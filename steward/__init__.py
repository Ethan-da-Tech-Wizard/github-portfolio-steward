# Program: github-portfolio-steward - __init__.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Makes the steward folder a Python package and re-exports its main classes and data models so other code can import them from one place.

"""
Program: GitHub Portfolio Steward - Package Root
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Package initialization and public interface exposure for GitHub Portfolio Steward.
"""

## Export primary models and classes for direct module consumption.
# ============================================================
# IMPORTS: pull the main classes into the package namespace
# ============================================================
# Data models (plain containers that hold information).
from steward.models import (
    RepoSummary,
    CodebaseFacts,
    MetadataRecommendation,
    HeaderAuditResult,
    HeaderAuditReport,
)
# The scanner inspects repositories (remote through gh, or local folders).
from steward.scanner import RepositoryScanner
# The synthesizer turns scan facts into a description and topics.
from steward.synthesizer import MetadataSynthesizer
# The updater applies those recommendations to GitHub.
from steward.updater import PortfolioUpdater
# The auditor checks that source files carry the standard header.
from steward.header_audit import HeaderAuditor

## Semantic versioning identifier.
# Package version and author, readable as steward.__version__.
__version__ = "1.0.0"
__author__ = "Ethan-da-Tech-Wizard"

# __all__ lists the names that 'from steward import *' will expose.
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
