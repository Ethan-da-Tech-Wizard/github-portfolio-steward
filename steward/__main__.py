"""
Program: GitHub Portfolio Steward - Package Executable Entrypoint
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Invokes the portfolio steward command-line interface when executed as a module via python3 -m steward.
"""

import sys
from steward.cli import main

## Execute primary CLI dispatch when invoked as python3 -m steward.
if __name__ == "__main__":
    sys.exit(main())
