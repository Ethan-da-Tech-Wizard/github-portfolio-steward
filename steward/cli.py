# ==============================================================================
# Program: cli.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Command-line interface entry point and argument parsing engine. Dispatches CLI commands across scanner, synthesizer, updater, and header audit subcommands with rich console formatting.
# ==============================================================================
# Layout: create_parser() declares the subcommands (scan, describe, sync, audit,
# header-check); main() parses argv and dispatches to the matching handle_* function.
# Handlers return process exit codes and never call sys.exit themselves, so tests can call
# them directly. Output is plain text by default, JSON with --json (header-check: --format).
# Only `sync --apply` can modify anything on GitHub, and only via PortfolioUpdater.
# Run: python -m steward <command> --help    Test: python3 -m unittest discover -s tests -v
# Imports: stdlib first, then the package modules this CLI wires together
# (scanner -> synthesizer -> updater, plus the header auditor).
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from steward.scanner import RepositoryScanner
from steward.synthesizer import MetadataSynthesizer
from steward.updater import PortfolioUpdater
from steward.header_audit import HeaderAuditor
from steward.models import RepoSummary


def create_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for every subcommand.

    Called once by main(). Each subcommand's handler (handle_scan, handle_describe, ...)
    reads only the options declared here, so adding an option means touching both places.

    Returns:
        The configured ArgumentParser; subcommand name lands in args.command.
    """
    parser = argparse.ArgumentParser(
        prog="portfolio-steward",
        description="Autonomous GitHub portfolio curator, metadata synthesizer, and header auditor."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    ## Subcommand: scan
    # --owner/--repo/--local select the mode (see handle_scan); forks and archived repos are
    # excluded unless asked for, to keep the portfolio view focused on live projects.
    scan_parser = subparsers.add_parser("scan", help="Scan GitHub repositories or local directory")
    scan_parser.add_argument("--owner", type=str, help="GitHub user or organization name")
    scan_parser.add_argument("--repo", type=str, help="Specific repository name (e.g. owner/repo)")
    scan_parser.add_argument("--local", type=str, help="Scan local directory path instead of GitHub")
    scan_parser.add_argument("--limit", type=int, default=50, help="Maximum repositories to fetch (default: 50)")
    scan_parser.add_argument("--include-forks", action="store_true", help="Include forked repositories")
    scan_parser.add_argument("--include-archived", action="store_true", help="Include archived repositories")
    scan_parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")

    ## Subcommand: describe
    # describe works on exactly one target, remote (--repo) or local (--local).
    desc_parser = subparsers.add_parser("describe", help="Synthesize description and topics for a repository")
    desc_parser.add_argument("--repo", type=str, help="Target remote repository (e.g. owner/repo)")
    desc_parser.add_argument("--local", type=str, help="Target local directory path")
    desc_parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON recommendation")

    ## Subcommand: sync
    # Dry-run is the default: nothing changes on GitHub unless --apply is passed.
    # --topics-only and --desc-only narrow what is synchronized; --exclude takes names or regexes to skip.
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
    # audit is read-only; --limit caps how many repos are fetched (GitHub API paging cost).
    audit_parser = subparsers.add_parser("audit", help="Audit portfolio completeness (descriptions, topics, READMEs)")
    audit_parser.add_argument("--owner", type=str, help="GitHub user or organization name")
    audit_parser.add_argument("--limit", type=int, default=100, help="Maximum repositories to audit")
    audit_parser.add_argument("--json", action="store_true", dest="json_output", help="Output audit report as JSON")

    ## Subcommand: header-check
    # header-check mirrors the CI step; --fail-under sets the pass threshold (percent).
    header_parser = subparsers.add_parser("header-check", help="Audit source files for Ethan-da-Tech-Wizard header blocks")
    header_parser.add_argument("--path", type=str, default=".", help="Root directory or file to audit (default: .)")
    header_parser.add_argument("--fail-under", type=float, default=100.0, help="Fail if compliance percentage is below this (default: 100)")
    header_parser.add_argument("--format", choices=["table", "json", "markdown"], default="table", help="Output format")

    return parser


def handle_scan(args: argparse.Namespace) -> int:
    """Run `scan`: inspect one local dir, one remote repo, or list an owner's repos.

    Precedence is --local, then --repo, then the owner listing, so only one mode ever runs.
    Network access (via the scanner's GitHub calls) happens for the --repo and listing modes.

    Args:
        args: Parsed namespace with local, repo, owner, limit, include_forks,
            include_archived and json_output.

    Returns:
        Process exit code; always 0 (scan errors surface as exceptions from the scanner).
    """
    # The scanner is the only component that talks to GitHub or the filesystem for facts.
    scanner = RepositoryScanner()

    # --local wins over --repo so a developer can scan an uncommitted checkout without network access.
    if args.local:
        ## Local directory scan.
        facts = scanner.inspect_local_directory(args.local)
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
        return 0

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
    repos = scanner.fetch_github_repos(
        owner=args.owner,
        limit=args.limit,
        include_forks=args.include_forks,
        include_archived=args.include_archived
    )

    if args.json_output:
        print(json.dumps([r.to_dict() for r in repos], indent=2))
    else:
        # Fixed-width columns so the table lines up in a terminal; descriptions are cut to 40 chars to stay on one line.
        print(f"\nFound {len(repos)} repositories:\n")
        print(f"{'Repository':<40} {'Language':<15} {'Topics':<5} {'Description'}")
        print("-" * 100)
        for r in repos:
            desc = (r.description[:40] + "...") if r.description and len(r.description) > 40 else (r.description or "")
            print(f"{r.full_name:<40} {r.primary_language or 'None':<15} {len(r.topics):<5} {desc}")

    return 0


def handle_describe(args: argparse.Namespace) -> int:
    """Run `describe`: synthesize a description and topic recommendation for one repo.

    Args:
        args: Parsed namespace with local or repo (one is required) and json_output.

    Returns:
        0 on success, 1 if neither --repo nor --local was given (message on stderr).
    """
    scanner = RepositoryScanner()
    synthesizer = MetadataSynthesizer()

    if args.local:
        facts = scanner.inspect_local_directory(args.local)
        folder_name = Path(args.local).resolve().name
        # A local folder has no GitHub record, so a stand-in summary is built from the folder name and its most common detected language.
        dummy_repo = RepoSummary(
            name=folder_name,
            full_name=folder_name,
            primary_language=facts.detected_languages[0] if facts.detected_languages else None
        )
        rec = synthesizer.recommend(dummy_repo, facts)
    elif args.repo:
        # Look the repo up in the first 100 owned repos to reuse its real description/topics; falls back to a bare summary if not found.
        repos = scanner.fetch_github_repos(limit=100)
        matched = [r for r in repos if r.name == args.repo or r.full_name == args.repo]
        if matched:
            target_repo = matched[0]
        else:
            target_repo = RepoSummary(name=args.repo.split("/")[-1], full_name=args.repo)
        facts = scanner.inspect_remote_repo(args.repo)
        rec = synthesizer.recommend(target_repo, facts)
    else:
        print("Error: Specify either --repo or --local path to describe.", file=sys.stderr)
        return 1

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
    """Run `sync`: recommend metadata for each repo and push it to GitHub.

    Safe by default: unless --apply is passed the updater only reports what it would
    change (dry run). --dry-run exists for symmetry but --apply is what decides the mode.

    Args:
        args: Parsed namespace with owner, repo, apply, exclude, topics_only,
            desc_only and json_output.

    Returns:
        Always 0; per-repo outcomes are printed (and collected into the --json output).
    """
    # Comma-separated --exclude values; the synthesizer treats each as a name or regex to skip.
    exclusions = [e.strip() for e in args.exclude.split(",")] if args.exclude else []
    synthesizer = MetadataSynthesizer(exclusions=exclusions)
    scanner = RepositoryScanner()
    updater = PortfolioUpdater()

    # Safety default: only --apply turns off dry-run.
    is_dry_run = not args.apply

    if args.repo:
        repos_to_sync = [RepoSummary(name=args.repo.split("/")[-1], full_name=args.repo)]
    else:
        repos_to_sync = scanner.fetch_github_repos(owner=args.owner, limit=100)

    results = []
    print(f"\n--- Synchronizing Metadata (Mode: {'APPLY' if not is_dry_run else 'DRY-RUN'}) ---")

    for repo in repos_to_sync:
        # Check both short and owner/name forms so users can exclude either way.
        if synthesizer.is_excluded(repo.name) or synthesizer.is_excluded(repo.full_name):
            print(f"[SKIP] Excluded: {repo.full_name}")
            continue

        try:
            facts = scanner.inspect_remote_repo(repo.full_name)
        except Exception:
            facts = CodebaseFacts()

        rec = synthesizer.recommend(repo, facts)

        # The two --*-only flags are inverse switches: skipping one half means updating the other.
        update_desc = not args.topics_only
        update_topics = not args.desc_only

        res = updater.apply(
            rec,
            dry_run=is_dry_run,
            update_description=update_desc,
            update_topics=update_topics
        )
        results.append(res)

        # Status tag is padded to 10 chars so repo names align down the console.
        status_tag = f"[{res['status'].upper()}]"
        print(f"{status_tag:<10} {repo.full_name}: {res['message']}")
        if res.get("command"):
            print(f"           Command: {res['command']}")

    if args.json_output:
        print(json.dumps(results, indent=2))

    return 0


def handle_audit(args: argparse.Namespace) -> int:
    """Run `audit`: report how many repos have a description and topics.

    Read-only. An empty portfolio reports 100% coverage rather than dividing by zero.

    Args:
        args: Parsed namespace with owner, limit and json_output.

    Returns:
        Always 0.
    """
    scanner = RepositoryScanner()
    repos = scanner.fetch_github_repos(owner=args.owner, limit=args.limit)

    missing_desc = []
    missing_topics = []

    for r in repos:
        if not r.description or len(r.description.strip()) == 0:
            missing_desc.append(r.full_name)
        if not r.topics or len(r.topics) == 0:
            missing_topics.append(r.full_name)

    total = len(repos)
    # Percent coverage; an empty portfolio counts as fully covered instead of raising ZeroDivisionError.
    desc_pct = ((total - len(missing_desc)) / total * 100) if total > 0 else 100
    topic_pct = ((total - len(missing_topics)) / total * 100) if total > 0 else 100

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

        # Show at most 10 offenders per list so the console summary stays readable; --json lists them all.
        if missing_desc:
            print(f"\nRepositories Missing Descriptions ({len(missing_desc)}):")
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
    """Run `header-check`: verify every source file carries the standard header block.

    This is the same command CI runs with --fail-under 100, so a non-zero return here
    is what turns the CI job red.

    Args:
        args: Parsed namespace with path, fail_under and format (table/json/markdown).

    Returns:
        1 if the compliance percentage is below --fail-under, else 0.
    """
    auditor = HeaderAuditor()
    target_path = Path(args.path)

    # A single file is audited directly; the directory report is then reduced to that one result so the counts and percentage describe just that file.
    if target_path.is_file():
        res = auditor.audit_file(str(target_path))
        report = auditor.audit_directory(str(target_path.parent))
        report.results = [res]
        report.total_files = 1
        report.compliant_files = 1 if res.is_compliant else 0
        report.non_compliant_files = 0 if res.is_compliant else 1
        report.compliance_percentage = 100.0 if res.is_compliant else 0.0
    else:
        report = auditor.audit_directory(str(target_path))

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

    # Non-zero exit when below threshold; this is how CI fails on missing headers.
    if report.compliance_percentage < args.fail_under:
        print(
            f"\nAudit failed: Compliance {report.compliance_percentage}% is below threshold {args.fail_under}%.",
            file=sys.stderr
        )
        return 1

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point (used by `python -m steward` and the console script).

    Args:
        argv: Argument list to parse; None means sys.argv[1:]. Tests pass an explicit list.

    Returns:
        The chosen handler's exit code; prints help and returns 0 when no subcommand is given.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Plain dispatch table; unknown commands cannot reach here because argparse rejects them.
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


if __name__ == "__main__":
    sys.exit(main())
