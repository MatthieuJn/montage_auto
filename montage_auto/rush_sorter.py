"""
rush_sorter - Sort video rush files from a directory.
"""

from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}


def get_video_files(directory):
    """
    Return all video files found in *directory* (non-recursive).

    Args:
        directory: Path-like object or string pointing to the directory.

    Returns:
        List of :class:`pathlib.Path` objects for each video file found.
    """
    path = Path(directory)
    return [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]


def sort_by_name(video_files):
    """
    Sort *video_files* alphabetically (case-insensitive) by filename.

    Args:
        video_files: Iterable of :class:`pathlib.Path` objects.

    Returns:
        Sorted list of :class:`pathlib.Path` objects.
    """
    return sorted(video_files, key=lambda f: f.name.lower())


def sort_by_date(video_files):
    """
    Sort *video_files* by last-modification time (oldest first).

    Args:
        video_files: Iterable of :class:`pathlib.Path` objects.

    Returns:
        Sorted list of :class:`pathlib.Path` objects.
    """
    return sorted(video_files, key=lambda f: f.stat().st_mtime)


def sort_rushes(directory, sort_method="name"):
    """
    Collect and sort all video rushes in *directory*.

    Args:
        directory: Path to the directory containing video files.
        sort_method: ``'name'`` for alphabetical order (default) or
                     ``'date'`` for chronological order.

    Returns:
        Sorted list of :class:`pathlib.Path` objects.

    Raises:
        ValueError: If *sort_method* is not ``'name'`` or ``'date'``.
    """
    video_files = get_video_files(directory)

    if sort_method == "name":
        return sort_by_name(video_files)
    elif sort_method == "date":
        return sort_by_date(video_files)
    else:
        raise ValueError(
            f"Unknown sort method: '{sort_method}'. Use 'name' or 'date'."
        )
