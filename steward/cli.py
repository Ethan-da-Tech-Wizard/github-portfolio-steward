# Program: github-portfolio-steward - cli.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Defines the portfolio-steward command-line interface: parses arguments for the scan, describe, sync, audit and header-check subcommands and runs the matching handler.

"""
Program: GitHub Portfolio Steward - Command-Line Interface
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Dispatches CLI arguments to scanner, synthesizer, updater, and header audit subcommands.
"""

# ============================================================
# IMPORTS
# ============================================================
# argparse builds the command-line interface; json prints machine-readable output;
# sys gives access to stderr and exit codes; Path handles folder paths.
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# The worker classes each subcommand uses.
from steward.scanner import RepositoryScanner
from steward.synthesizer import MetadataSynthesizer
from steward.updater import PortfolioUpdater
from steward.header_audit import HeaderAuditor
# RepoSummary is used to describe a repo when we only know its name.
from steward.models import RepoSummary


def create_parser() -> argparse.ArgumentParser:
    """
    ## Configures and returns the top-level CLI argument parser with subcommands.
    """
    # ============================================================
    # ARGUMENT PARSER
    # ============================================================
    # Top-level parser; each subcommand below adds its own options (flags).
    parser = argparse.ArgumentParser(
        prog="portfolio-steward",
        description="Autonomous GitHub portfolio curator, metadata synthesizer, and header auditor."
    )
    # Subparsers let the user pick a command word such as 'scan' or 'sync'.
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    ## Subcommand: scan
    # action="store_true" options are on/off switches: present means True.
    scan_parser = subparsers.add_parser("scan", help="Scan GitHub repositories or local directory")
    scan_parser.add_argument("--owner", type=str, help="GitHub user or organization name")
    scan_parser.add_argument("--repo", type=str, help="Specific repository name (e.g. owner/repo)")
    scan_parser.add_argument("--local", type=str, help="Scan local directory path instead of GitHub")
    scan_parser.add_argument("--limit", type=int, default=50, help="Maximum repositories to fetch (default: 50)")
    scan_parser.add_argument("--include-forks", action="store_true", help="Include forked repositories")
    scan_parser.add_argument("--include-archived", action="store_true", help="Include archived repositories")
    scan_parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")

    ## Subcommand: describe
    desc_parser = subparsers.add_parser("describe", help="Synthesize description and topics for a repository")
    desc_parser.add_argument("--repo", type=str, help="Target remote repository (e.g. owner/repo)")
    desc_parser.add_argument("--local", type=str, help="Target local directory path")
    desc_parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON recommendation")

    ## Subcommand: sync
    sync_parser = subparsers.add_parser("sync", help="Synchronize repository metadata on GitHub")
    sync_parser.add_argument("--owner", type=str, help="GitHub user or org to synchronize")
    sync_parser.add_argument("--repo", type=str, help="Specific repository name to synchronize")
    sync_parser.add_argument("--apply", action="store_true", help="Apply changes live to GitHub (default is dry-run)")
    sync_parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate changes without modifying GitHub")
    sync_parser.add_argument("--exclude", type=str, help="Comma-separated regex patterns or names to exclude")
    sync_parser.add_argument("--topics-only", action="store_true", help="Only synchronize topics, ignore descriptions")
    sync_parser.add_argument("--desc-only", action="store_true", help="Only synchronize descriptions, ignore topics")
    sync_parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON results")

    ## Subcommand: audit
    audit_parser = subparsers.add_parser("audit", help="Audit portfolio completeness (descriptions, topics, READMEs)")
    audit_parser.add_argument("--owner", type=str, help="GitHub user or organization name")
    audit_parser.add_argument("--limit", type=int, default=100, help="Maximum repositories to audit")
    audit_parser.add_argument("--json", action="store_true", dest="json_output", help="Output audit report as JSON")

    ## Subcommand: header-check
    header_parser = subparsers.add_parser("header-check", help="Audit source files for Ethan-da-Tech-Wizard header blocks")
    header_parser.add_argument("--path", type=str, default=".", help="Root directory or file to audit (default: .)")
    # Exit code 1 if the compliance percentage falls below this number (useful in CI).
    header_parser.add_argument("--fail-under", type=float, default=100.0, help="Fail if compliance percentage is below this (default: 100)")
    header_parser.add_argument("--format", choices=["table", "json", "markdown"], default="table", help="Output format")

    # Give the finished parser back to main().
    return parser


# ============================================================
# SUBCOMMAND HANDLERS
# ============================================================
# Each handler returns an exit code: 0 for success, non-zero for failure.
def handle_scan(args: argparse.Namespace) -> int:
    """
    ## Handles execution of the 'scan' subcommand.
    """
    # --- scan ---
    scanner = RepositoryScanner()

    # Case 1: scan a folder on this computer.
    if args.local:
        ## Local directory scan.
        # Look at the files and collect the facts.
        facts = scanner.inspect_local_directory(args.local)
        # Print JSON for scripts, or a readable report for people.
        if args.json_output:
            print(json.dumps(facts.to_dict(), indent=2))
        else:
            print(f"\n--- Local Codebase Scan: {args.local} ---")
            print(f"Files Counted:       {facts.file_count}")
            print(f"Detected Languages:  {', '.join(facts.detected_languages) or 'None'}")
            print(f"Detected Frameworks: {', '.join(facts.detected_frameworks) or 'None'}")
            print(f"Has README:          {'Yes' if facts.has_readme else 'No'}")
            print(f"Has License:         {'Yes' if facts.has_license else 'No'}")
            print(f"Has Tests:           {'Yes' if facts.has_tests else 'No'}")
            print(f"Has CI/CD:           {'Yes' if facts.has_ci else 'No'}")
            if facts.readme_snippet:
                print(f"README Summary:      {facts.readme_snippet}")
        # Success.
        return 0

    # Case 2: inspect one remote repository through the GitHub API.
    if args.repo:
        ## Single remote repo inspection.
        facts = scanner.inspect_remote_repo(args.repo)
        if args.json_output:
            print(json.dumps(facts.to_dict(), indent=2))
        else:
            print(f"\n--- Remote Repository Scan: {args.repo} ---")
            print(f"Files Counted:       {facts.file_count}")
            print(f"Detected Languages:  {', '.join(facts.detected_languages) or 'None'}")
            print(f"Detected Frameworks: {', '.join(facts.detected_frameworks) or 'None'}")
            print(f"Has README:          {'Yes' if facts.has_readme else 'No'}")
            if facts.readme_snippet:
                print(f"README Summary:      {facts.readme_snippet}")
        return 0

    ## Listing remote repositories.
    # Case 3 (default): list the owner's repositories.
    repos = scanner.fetch_github_repos(
        owner=args.owner,
        limit=args.limit,
        include_forks=args.include_forks,
        include_archived=args.include_archived
    )

    if args.json_output:
        print(json.dumps([r.to_dict() for r in repos], indent=2))
    else:
        print(f"\nFound {len(repos)} repositories:\n")
        # Table header; '<40' pads each column to a fixed width so rows line up.
        print(f"{'Repository':<40} {'Language':<15} {'Topics':<5} {'Description'}")
        print("-" * 100)
        for r in repos:
            # Shorten long descriptions to 40 characters so the table stays tidy.
            desc = (r.description[:40] + "...") if r.description and len(r.description) > 40 else (r.description or "")
            print(f"{r.full_name:<40} {r.primary_language or 'None':<15} {len(r.topics):<5} {desc}")

    return 0


def handle_describe(args: argparse.Namespace) -> int:
    """
    ## Handles execution of the 'describe' subcommand.
    """
    scanner = RepositoryScanner()
    # --- describe ---
    synthesizer = MetadataSynthesizer()

    if args.local:
        facts = scanner.inspect_local_directory(args.local)
        folder_name = Path(args.local).resolve().name
        # A local folder has no GitHub record, so make a stand-in RepoSummary named after the folder.
        dummy_repo = RepoSummary(
            name=folder_name,
            full_name=folder_name,
            primary_language=facts.detected_languages[0] if facts.detected_languages else None
        )
        # Ask the synthesizer for a description and topics.
        rec = synthesizer.recommend(dummy_repo, facts)
    elif args.repo:
        # Remote repo: look it up in the owner's list to get its current description and topics.
        repos = scanner.fetch_github_repos(limit=100)
        # Match by short name or by 'owner/name'.
        matched = [r for r in repos if r.name == args.repo or r.full_name == args.repo]
        if matched:
            target_repo = matched[0]
        else:
            # Not found in the list: fall back to a minimal record built from the name.
            target_repo = RepoSummary(name=args.repo.split("/")[-1], full_name=args.repo)
        facts = scanner.inspect_remote_repo(args.repo)
        rec = synthesizer.recommend(target_repo, facts)
    else:
        # Neither --repo nor --local was given, so there is nothing to describe.
        print("Error: Specify either --repo or --local path to describe.", file=sys.stderr)
        return 1

    # Show the recommendation as JSON or as a readable summary.
    if args.json_output:
        print(json.dumps(rec.to_dict(), indent=2))
    else:
        print(f"\n=== Metadata Recommendation: {rec.repo_name} ===")
        print(f"Current Description:  {rec.current_description or '(None)'}")
        print(f"Proposed Description: {rec.proposed_description}")
        print(f"Description Changed:  {'Yes' if rec.description_changed else 'No'}")
        print(f"Current Topics:       {', '.join(rec.current_topics) or '(None)'}")
        print(f"Proposed Topics:      {', '.join(rec.proposed_topics)}")
        print(f"Topics to Add:        {', '.join(rec.topics_to_add) or '(None)'}")
        print(f"Confidence Score:     {rec.confidence_score * 100:.0f}%")
        if rec.reasoning:
            print("Reasoning:")
            for reason in rec.reasoning:
                print(f"  - {reason}")

    return 0


def handle_sync(args: argparse.Namespace) -> int:
    """
    ## Handles execution of the 'sync' subcommand.
    """
    # --- sync ---
    # Split the comma-separated --exclude text into a clean list of patterns.
    exclusions = [e.strip() for e in args.exclude.split(",")] if args.exclude else []
    synthesizer = MetadataSynthesizer(exclusions=exclusions)
    scanner = RepositoryScanner()
    updater = PortfolioUpdater()

    # Safety: nothing is changed on GitHub unless --apply is given.
    is_dry_run = not args.apply

    # Sync one named repository, or every repository from the owner's list.
    if args.repo:
        repos_to_sync = [RepoSummary(name=args.repo.split("/")[-1], full_name=args.repo)]
    else:
        repos_to_sync = scanner.fetch_github_repos(owner=args.owner, limit=100)

    # Collect each repo's outcome so it can be printed as JSON at the end.
    results = []
    print(f"\n--- Synchronizing Metadata (Mode: {'APPLY' if not is_dry_run else 'DRY-RUN'}) ---")

    # Process one repository at a time.
    for repo in repos_to_sync:
        # Skip anything matching an --exclude pattern.
        if synthesizer.is_excluded(repo.name) or synthesizer.is_excluded(repo.full_name):
            print(f"[SKIP] Excluded: {repo.full_name}")
            continue

        try:
            # Inspect the repo; on any error fall back to empty facts so one failure does not stop the run.
            facts = scanner.inspect_remote_repo(repo.full_name)
        except Exception:
            facts = CodebaseFacts()

        # Work out what the description and topics should be.
        rec = synthesizer.recommend(repo, facts)

        # --topics-only and --desc-only narrow which parts are updated.
        update_desc = not args.topics_only
        update_topics = not args.desc_only

        # Plan (dry run) or perform (apply) the change.
        res = updater.apply(
            rec,
            dry_run=is_dry_run,
            update_description=update_desc,
            update_topics=update_topics
        )
        results.append(res)

        # Print a one-line outcome such as [PLANNED] or [SUCCESS], plus the gh command when there is one.
        status_tag = f"[{res['status'].upper()}]"
        print(f"{status_tag:<10} {repo.full_name}: {res['message']}")
        if res.get("command"):
            print(f"           Command: {res['command']}")

    if args.json_output:
        print(json.dumps(results, indent=2))

    return 0


def handle_audit(args: argparse.Namespace) -> int:
    """
    ## Handles execution of the 'audit' subcommand for portfolio readiness.
    """
    # --- audit ---
    scanner = RepositoryScanner()
    repos = scanner.fetch_github_repos(owner=args.owner, limit=args.limit)

    # Lists of repositories that lack a description or any topics.
    missing_desc = []
    missing_topics = []

    # Check every repository.
    for r in repos:
        if not r.description or len(r.description.strip()) == 0:
            missing_desc.append(r.full_name)
        if not r.topics or len(r.topics) == 0:
            missing_topics.append(r.full_name)

    # Coverage percentages; with zero repos we report 100 to avoid dividing by zero.
    total = len(repos)
    desc_pct = ((total - len(missing_desc)) / total * 100) if total > 0 else 100
    topic_pct = ((total - len(missing_topics)) / total * 100) if total > 0 else 100

    # JSON report for scripts.
    if args.json_output:
        report = {
            "total_repositories": total,
            "description_coverage_pct": round(desc_pct, 2),
            "topics_coverage_pct": round(topic_pct, 2),
            "missing_description": missing_desc,
            "missing_topics": missing_topics
        }
        print(json.dumps(report, indent=2))
    else:
        print("\n=== Portfolio Metadata Readiness Audit ===")
        print(f"Total Repositories Analyzed: {total}")
        print(f"Description Coverage:        {desc_pct:.1f}% ({total - len(missing_desc)}/{total})")
        print(f"Topics Coverage:             {topic_pct:.1f}% ({total - len(missing_topics)}/{total})")

        if missing_desc:
            print(f"\nRepositories Missing Descriptions ({len(missing_desc)}):")
            # Show at most 10 names so the output stays short.
            for name in missing_desc[:10]:
                print(f"  - {name}")
            if len(missing_desc) > 10:
                print(f"    ... and {len(missing_desc) - 10} more.")

        if missing_topics:
            print(f"\nRepositories Missing Topics ({len(missing_topics)}):")
            for name in missing_topics[:10]:
                print(f"  - {name}")
            if len(missing_topics) > 10:
                print(f"    ... and {len(missing_topics) - 10} more.")

    return 0


def handle_header_check(args: argparse.Namespace) -> int:
    """
    ## Handles execution of the 'header-check' subcommand.
    """
    # --- header-check ---
    auditor = HeaderAuditor()
    target_path = Path(args.path)

    # A single file was given: audit just that file and build a one-file report.
    if target_path.is_file():
        res = auditor.audit_file(str(target_path))
        report = auditor.audit_directory(str(target_path.parent))
        report.results = [res]
        report.total_files = 1
        report.compliant_files = 1 if res.is_compliant else 0
        report.non_compliant_files = 0 if res.is_compliant else 1
        report.compliance_percentage = 100.0 if res.is_compliant else 0.0
    else:
        # A folder was given: audit every source file in it.
        report = auditor.audit_directory(str(target_path))

    # Choose the output style: json, markdown or the default table.
    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif args.format == "markdown":
        print(f"# Codebase Header Compliance Audit\n")
        print(f"- **Path**: `{report.root_path}`")
        print(f"- **Compliance**: **{report.compliance_percentage}%** ({report.compliant_files}/{report.total_files} files)")
        print(f"\n| File | Language | Compliant | Missing Fields / Notes |")
        print(f"| --- | --- | --- | --- |")
        for r in report.results:
            status = "✅ PASS" if r.is_compliant else "❌ FAIL"
            notes = ", ".join(r.missing_fields) if r.missing_fields else (r.error_message or "OK")
            print(f"| `{r.file_path}` | {r.language} | {status} | {notes} |")
    else:
        ## Default table output.
        print(f"\n=== Codebase Header Compliance Audit ===")
        print(f"Root:                  {report.root_path}")
        print(f"Total Source Files:    {report.total_files}")
        print(f"Compliant Files:       {report.compliant_files}")
        print(f"Non-Compliant Files:   {report.non_compliant_files}")
        print(f"Compliance Percentage: {report.compliance_percentage}%\n")

        print(f"{'Status':<8} {'Language':<12} {'File':<45} {'Missing Fields / Notes'}")
        print("-" * 95)
        for r in report.results:
            status = "PASS" if r.is_compliant else "FAIL"
            notes = ", ".join(r.missing_fields) if r.missing_fields else (r.error_message or "Compliant")
            fpath = r.file_path if len(r.file_path) <= 43 else ("..." + r.file_path[-40:])
            print(f"{status:<8} {r.language:<12} {fpath:<45} {notes}")

    # Return exit code 1 (and a message on stderr) if too few files comply.
    if report.compliance_percentage < args.fail_under:
        print(
            f"\nAudit failed: Compliance {report.compliance_percentage}% is below threshold {args.fail_under}%.",
            file=sys.stderr
        )
        return 1

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """
    ## Top-level CLI entrypoint dispatching parsed arguments.
    """
    # --- main ---
    # Build the parser and read the command line (argv=None means use the real arguments).
    parser = create_parser()
    args = parser.parse_args(argv)

    # No subcommand given: show the help text.
    if not args.command:
        parser.print_help()
        return 0

    # Send the request to the handler for the chosen subcommand.
    if args.command == "scan":
        return handle_scan(args)
    elif args.command == "describe":
        return handle_describe(args)
    elif args.command == "sync":
        return handle_sync(args)
    elif args.command == "audit":
        return handle_audit(args)
    elif args.command == "header-check":
        return handle_header_check(args)

    return 0


# Run main() when the file is executed directly.
if __name__ == "__main__":
    sys.exit(main())
