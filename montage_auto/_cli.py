"""
_cli - Command-line interface for montage_auto.
"""

import argparse
import sys

from montage_auto.montage import create_montage


def main(argv=None):
    """
    Parse command-line arguments and run the montage pipeline.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    parser = argparse.ArgumentParser(
        prog="montage_auto",
        description=(
            "Automatic video montage: sort rushes and remove silences, "
            "then concatenate them into a single video."
        ),
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing the raw video rush files.",
    )
    parser.add_argument(
        "output",
        help="Output video file path (e.g. montage.mp4).",
    )
    parser.add_argument(
        "--sort",
        choices=["name", "date"],
        default="name",
        metavar="METHOD",
        help=(
            "How to sort the rushes before assembling the montage. "
            "'name' (default) sorts alphabetically; 'date' sorts by "
            "modification time."
        ),
    )
    parser.add_argument(
        "--no-silence-removal",
        action="store_true",
        default=False,
        help="Disable silence removal (keep all audio as-is).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.01,
        metavar="FLOAT",
        help=(
            "Normalised amplitude threshold for silence detection "
            "(default: 0.01).  Samples below this value are treated as silent."
        ),
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help=(
            "Minimum continuous silence duration in seconds that will be "
            "removed (default: 0.5)."
        ),
    )

    args = parser.parse_args(argv)

    try:
        output = create_montage(
            input_directory=args.input_dir,
            output_path=args.output,
            sort_method=args.sort,
            remove_silences=not args.no_silence_removal,
            silence_threshold=args.threshold,
            min_silence_duration=args.min_silence,
        )
        print(f"Montage created successfully: {output}")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0
