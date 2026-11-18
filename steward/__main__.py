# ==============================================================================
# Program: __main__.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Package executable entrypoint invoking the portfolio steward command-line interface when executed as a module via python3 -m steward.
# ==============================================================================
import sys
from steward.cli import main

## Execute primary CLI dispatch when invoked as python3 -m steward.
if __name__ == "__main__":
    sys.exit(main())
