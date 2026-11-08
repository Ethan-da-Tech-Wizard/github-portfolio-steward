"""
Program: GitHub Portfolio Steward - Hands-Free Updater
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Applies synthesized descriptions and topics to GitHub repositories via the gh CLI with dry-run and apply modes.
"""

import subprocess
from typing import Dict, Any, List, Tuple
from steward.models import MetadataRecommendation


class PortfolioUpdater:
    """
    ## Applies recommended metadata changes directly to remote GitHub repositories.
    ## Supports both dry-run inspection mode and live execution via the gh CLI.
    """

    def __init__(self, gh_executable: str = "gh"):
        ## Store the binary name or path for gh CLI invocations.
        self.gh_executable = gh_executable

    def _execute_gh(self, args: List[str]) -> Tuple[int, str, str]:
        """
        ## Helper to execute a gh command in a subprocess safely.
        ## Captures stdout and stderr without raising unhandled subprocess exceptions.
        """
        cmd = [self.gh_executable] + args
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
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
        args = ["repo", "edit", recommendation.repo_name]

        ## Add description flag if requested and modified.
        if update_description and recommendation.description_changed:
            args.extend(["--description", recommendation.proposed_description])

        ## Add topics flags for new topics to add.
        if update_topics and recommendation.topics_to_add:
            for topic in recommendation.topics_to_add:
                args.extend(["--add-topic", topic])

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
        needs_desc_update = update_description and recommendation.description_changed
        needs_topic_update = update_topics and bool(recommendation.topics_to_add)

        if not needs_desc_update and not needs_topic_update:
            return {
                "repo": recommendation.repo_name,
                "status": "noop",
                "message": "Repository metadata is already up to date.",
                "changes_applied": False,
                "dry_run": dry_run,
            }

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
        returncode, stdout, stderr = self._execute_gh(cmd_args)
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
