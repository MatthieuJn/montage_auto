"""
Command-line entry point for montage_auto.

Usage:
    python -m montage_auto <input_dir> <output_file> [options]
"""

import sys
from montage_auto._cli import main

if __name__ == "__main__":
    sys.exit(main())
