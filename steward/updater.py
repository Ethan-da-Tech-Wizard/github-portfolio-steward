# Program: github-portfolio-steward - updater.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Builds and runs 'gh repo edit' commands that apply a recommended description and topics to a GitHub repository, with a safe dry-run mode.

"""
Program: GitHub Portfolio Steward - Hands-Free Updater
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Applies synthesized descriptions and topics to GitHub repositories via the gh CLI with dry-run and apply modes.
"""

# ============================================================
# IMPORTS
# ============================================================
# subprocess lets us run the external gh (GitHub CLI) program.
import subprocess
# Type names used only to document what the functions take and return.
from typing import Dict, Any, List, Tuple
# MetadataRecommendation holds the proposed description and topics.
from steward.models import MetadataRecommendation


class PortfolioUpdater:
    """
    ## Applies recommended metadata changes directly to remote GitHub repositories.
    ## Supports both dry-run inspection mode and live execution via the gh CLI.
    """

    def __init__(self, gh_executable: str = "gh"):
        """Remember which gh executable to call (default is 'gh', found on PATH)."""
        ## Store the binary name or path for gh CLI invocations.
        # Saved on the object so every command uses the same program.
        self.gh_executable = gh_executable

    def _execute_gh(self, args: List[str]) -> Tuple[int, str, str]:
        """
        ## Helper to execute a gh command in a subprocess safely.
        ## Captures stdout and stderr without raising unhandled subprocess exceptions.
        """
        # The full command is the program name plus its arguments, as a list (no shell is involved, which is safer).
        cmd = [self.gh_executable] + args
        try:
            # Run the command and wait for it to finish.
            # capture_output and text: collect stdout/stderr as strings.
            # check=False: do not raise on a non-zero exit code; we inspect it ourselves.
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            # Hand back the exit code and the output with surrounding whitespace trimmed.
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except FileNotFoundError:
            return 127, "", f"Executable '{self.gh_executable}' not found in PATH."

    def build_gh_edit_command(
        self,
        recommendation: MetadataRecommendation,
        update_description: bool = True,
        update_topics: bool = True
    ) -> List[str]:
        """
        ## Assembles the gh repo edit command arguments based on recommendation deltas.
        """
        # Start with 'gh repo edit <repo name>'; flags are added below only for real changes.
        args = ["repo", "edit", recommendation.repo_name]

        ## Add description flag if requested and modified.
        if update_description and recommendation.description_changed:
            args.extend(["--description", recommendation.proposed_description])

        ## Add topics flags for new topics to add.
        if update_topics and recommendation.topics_to_add:
            # gh needs one --add-topic flag per topic.
            for topic in recommendation.topics_to_add:
                args.extend(["--add-topic", topic])

        # Return the argument list; the caller decides whether to actually run it.
        return args

    def apply(
        self,
        recommendation: MetadataRecommendation,
        dry_run: bool = True,
        update_description: bool = True,
        update_topics: bool = True
    ) -> Dict[str, Any]:
        """
        ## Applies metadata changes to GitHub or simulates execution in dry-run mode.
        """
        ## Check if there are any actionable changes.
        # Work out what really needs changing: the caller must want it AND it must differ from what is on GitHub.
        needs_desc_update = update_description and recommendation.description_changed
        needs_topic_update = update_topics and bool(recommendation.topics_to_add)

        # Nothing to do: return a 'noop' result so the caller can say the repo is already up to date.
        if not needs_desc_update and not needs_topic_update:
            return {
                "repo": recommendation.repo_name,
                "status": "noop",
                "message": "Repository metadata is already up to date.",
                "changes_applied": False,
                "dry_run": dry_run,
            }

        # Build the gh command once; it is used for both the dry-run preview and the live run.
        cmd_args = self.build_gh_edit_command(
            recommendation,
            update_description=update_description,
            update_topics=update_topics
        )

        ## Handle dry-run mode without modifying remote GitHub state.
        if dry_run:
            return {
                "repo": recommendation.repo_name,
                "status": "planned",
                "message": "Dry-run mode: changes calculated but not applied.",
                "command": f"{self.gh_executable} " + " ".join(f'"{a}"' if " " in a else a for a in cmd_args),
                "proposed_description": recommendation.proposed_description if needs_desc_update else None,
                "topics_to_add": recommendation.topics_to_add if needs_topic_update else [],
                "changes_applied": False,
                "dry_run": True,
            }

        ## Execute the edit command live on GitHub.
        # Live mode: actually run the command against GitHub.
        returncode, stdout, stderr = self._execute_gh(cmd_args)
        # A non-zero exit code means gh failed; report the error text and say nothing was applied.
        if returncode != 0:
            return {
                "repo": recommendation.repo_name,
                "status": "error",
                "message": f"GitHub API update failed: {stderr or stdout}",
                "changes_applied": False,
                "dry_run": False,
                "returncode": returncode,
            }

        return {
            "repo": recommendation.repo_name,
            "status": "success",
            "message": "Successfully updated repository description and topics on GitHub.",
            "changes_applied": True,
            "dry_run": False,
            "updated_description": recommendation.proposed_description if needs_desc_update else None,
            "added_topics": recommendation.topics_to_add if needs_topic_update else [],
        }
