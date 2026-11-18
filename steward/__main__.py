# Program: github-portfolio-steward - __main__.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Lets the package be run with 'python3 -m steward' by handing control to the command-line interface in steward.cli.

"""
Program: GitHub Portfolio Steward - Package Executable Entrypoint
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Invokes the portfolio steward command-line interface when executed as a module via python3 -m steward.
"""

# sys is used for sys.exit so the program's return code reaches the shell.
import sys
# main() parses the command-line arguments and runs the chosen subcommand.
from steward.cli import main

## Execute primary CLI dispatch when invoked as python3 -m steward.
# This only runs when the file is executed directly, not when it is imported.
# sys.exit passes main()'s return value (0 = success) to the operating system.
if __name__ == "__main__":
    sys.exit(main())
