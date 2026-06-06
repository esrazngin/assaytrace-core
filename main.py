"""Enables `python -m assaytrace ...`."""
import sys

from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())