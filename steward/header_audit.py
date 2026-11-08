"""
Program: GitHub Portfolio Steward - Codebase Header Auditor
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Inspects source code files for compliant Ethan-da-Tech-Wizard header docstrings and outputs detailed compliance reports.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Set, Dict, Any

from steward.models import HeaderAuditResult, HeaderAuditReport


class HeaderAuditor:
    """
    ## Scans source code files in a repository to verify compliance with the Ethan-da-Tech-Wizard header standard.
    ## Evaluates Program name, Programmer identity, Last Modified date, and Purpose statement.
    """

    ## Supported source code file extensions.
    DEFAULT_EXTENSIONS = {
        ".py", ".rs", ".js", ".ts", ".jsx", ".tsx",
        ".c", ".cpp", ".cc", ".h", ".hpp", ".go",
        ".sh", ".bash"
    }

    ## Ignored directory names during recursive audits.
    DEFAULT_IGNORED_DIRS = {
        ".git", ".svn", ".hg", "__pycache__", "node_modules",
        "venv", ".venv", "env", "target", "build", "dist",
        ".pytest_cache", ".mypy_cache"
    }

    ## Regular expressions for detecting standard header key-value fields.
    _PROGRAM_PATTERN = re.compile(r"Program:\s*(.+)", re.IGNORECASE)
    _PROGRAMMER_PATTERN = re.compile(r"Programmer:\s*(.+)", re.IGNORECASE)
    _LAST_MODIFIED_PATTERN = re.compile(r"Last Modified:\s*(.+)", re.IGNORECASE)
    _PURPOSE_PATTERN = re.compile(r"Purpose:\s*(.+)", re.IGNORECASE)

    ## Regex for extracting Python docstrings at the beginning of a file.
    _PYTHON_DOCSTRING_PATTERN = re.compile(r'^\s*(?:#.*?\n)*\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', re.DOTALL)

    ## Regex for extracting C-style block comments /* ... */ at top of file.
    _C_BLOCK_COMMENT_PATTERN = re.compile(r'^\s*(?:#.*?\n|//.*?\n)*\s*/\*(.*?)\*/', re.DOTALL)

    def audit_content(self, content: str, file_path: str, ext: str) -> HeaderAuditResult:
        """
        ## Evaluates a single file's text content for header compliance.
        """
        lang = self._get_language_label(ext)
        header_text = self._extract_header_text(content, ext)

        if not header_text:
            return HeaderAuditResult(
                file_path=file_path,
                language=lang,
                is_compliant=False,
                missing_fields=["Program", "Programmer", "Last Modified", "Purpose"],
                error_message="No header docstring or comment block found at file start."
            )

        program_match = self._PROGRAM_PATTERN.search(header_text)
        programmer_match = self._PROGRAMMER_PATTERN.search(header_text)
        last_modified_match = self._LAST_MODIFIED_PATTERN.search(header_text)
        purpose_match = self._PURPOSE_PATTERN.search(header_text)

        program_val = program_match.group(1).strip() if program_match else None
        programmer_val = programmer_match.group(1).strip() if programmer_match else None
        last_mod_val = last_modified_match.group(1).strip() if last_modified_match else None
        purpose_val = purpose_match.group(1).strip() if purpose_match else None

        missing_fields: List[str] = []
        if not program_val:
            missing_fields.append("Program")
        if not programmer_val:
            missing_fields.append("Programmer")
        if not last_mod_val:
            missing_fields.append("Last Modified")
        if not purpose_val:
            missing_fields.append("Purpose")

        ## Verify Programmer is specifically Ethan-da-Tech-Wizard.
        error_msg = None
        if programmer_val and "ethan-da-tech-wizard" not in programmer_val.lower():
            missing_fields.append("Programmer (Must be Ethan-da-Tech-Wizard)")
            error_msg = f"Programmer specified as '{programmer_val}', expected 'Ethan-da-Tech-Wizard'."

        is_compliant = len(missing_fields) == 0

        return HeaderAuditResult(
            file_path=file_path,
            language=lang,
            is_compliant=is_compliant,
            program_name=program_val,
            programmer=programmer_val,
            last_modified=last_mod_val,
            purpose=purpose_val,
            missing_fields=missing_fields,
            error_message=error_msg
        )

    def audit_file(self, file_path: str) -> HeaderAuditResult:
        """
        ## Reads and audits an individual file from disk.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            return HeaderAuditResult(
                file_path=str(path),
                language="Unknown",
                is_compliant=False,
                error_message=f"File not found: {file_path}"
            )

        ext = path.suffix.lower()
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.audit_content(content, str(path), ext)
        except Exception as err:
            return HeaderAuditResult(
                file_path=str(path),
                language=self._get_language_label(ext),
                is_compliant=False,
                error_message=f"Failed to read file: {err}"
            )

    def audit_directory(
        self,
        directory_path: str,
        extensions: Optional[Set[str]] = None,
        ignored_dirs: Optional[Set[str]] = None
    ) -> HeaderAuditReport:
        """
        ## Recursively audits all matching source files in a target directory tree.
        """
        root = Path(directory_path).resolve()
        target_exts = extensions or self.DEFAULT_EXTENSIONS
        ignore = ignored_dirs or self.DEFAULT_IGNORED_DIRS

        results: List[HeaderAuditResult] = []

        for current_root, dirs, files in os.walk(root):
            ## Prune ignored directories.
            dirs[:] = [d for d in dirs if d not in ignore]

            for fname in sorted(files):
                fpath = Path(current_root) / fname
                ext = fpath.suffix.lower()

                if ext in target_exts:
                    rel_path = str(fpath.relative_to(root))
                    res = self.audit_file(str(fpath))
                    res.file_path = rel_path
                    results.append(res)

        total = len(results)
        compliant = sum(1 for r in results if r.is_compliant)
        non_compliant = total - compliant
        percentage = (compliant / total * 100.0) if total > 0 else 100.0

        return HeaderAuditReport(
            root_path=str(root),
            total_files=total,
            compliant_files=compliant,
            non_compliant_files=non_compliant,
            compliance_percentage=round(percentage, 2),
            results=results
        )

    def _extract_header_text(self, content: str, ext: str) -> Optional[str]:
        """
        ## Extracts the leading header comment or docstring block according to language syntax.
        """
        if ext == ".py":
            match = self._PYTHON_DOCSTRING_PATTERN.search(content)
            if match:
                return match.group(1)

        ## C, C++, Rust, JavaScript, TypeScript, Go block comment.
        if ext in (".c", ".cpp", ".cc", ".h", ".hpp", ".rs", ".js", ".ts", ".jsx", ".tsx", ".go"):
            match = self._C_BLOCK_COMMENT_PATTERN.search(content)
            if match:
                return match.group(1)

        ## Shell or generic hash comments at file head.
        lines = content.splitlines()[:30]
        hash_lines: List[str] = []
        found_header = False

        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("#!"):
                continue
            if trimmed.startswith("#"):
                found_header = True
                hash_lines.append(trimmed.lstrip("#").strip())
            elif found_header:
                ## Stop once hash comment block ends.
                break

        if hash_lines:
            return "\n".join(hash_lines)

        return None

    def _get_language_label(self, ext: str) -> str:
        """
        ## Maps file extension to human-readable language name.
        """
        mapping = {
            ".py": "Python",
            ".rs": "Rust",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".c": "C",
            ".cpp": "C++",
            ".cc": "C++",
            ".h": "C Header",
            ".hpp": "C++ Header",
            ".go": "Go",
            ".sh": "Shell",
            ".bash": "Shell",
        }
        return mapping.get(ext, "Unknown")
