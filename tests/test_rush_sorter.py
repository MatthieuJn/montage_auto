"""
Tests for montage_auto.rush_sorter.

These tests only touch the filesystem with lightweight empty files – no video
decoding libraries are needed.
"""

import os
import time
import tempfile
from pathlib import Path

import pytest

from montage_auto.rush_sorter import (
    get_video_files,
    sort_by_name,
    sort_by_date,
    sort_rushes,
    VIDEO_EXTENSIONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _touch(directory, name):
    """Create an empty file at *directory/name* and return its Path."""
    p = Path(directory) / name
    p.touch()
    return p


# ---------------------------------------------------------------------------
# get_video_files
# ---------------------------------------------------------------------------

class TestGetVideoFiles:
    def test_returns_only_video_files(self, tmp_path):
        video_names = ["rush1.mp4", "rush2.avi", "clip.mov"]
        other_names = ["notes.txt", "image.png", "script.py"]
        for name in video_names + other_names:
            _touch(tmp_path, name)

        result = get_video_files(tmp_path)
        assert {f.name for f in result} == set(video_names)

    def test_empty_directory(self, tmp_path):
        assert get_video_files(tmp_path) == []

    def test_all_supported_extensions(self, tmp_path):
        for ext in VIDEO_EXTENSIONS:
            _touch(tmp_path, f"video{ext}")
        result = get_video_files(tmp_path)
        assert len(result) == len(VIDEO_EXTENSIONS)

    def test_case_insensitive_extension(self, tmp_path):
        _touch(tmp_path, "video.MP4")
        _touch(tmp_path, "video.Avi")
        result = get_video_files(tmp_path)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# sort_by_name
# ---------------------------------------------------------------------------

class TestSortByName:
    def test_alphabetical_order(self):
        files = [Path("c_video.mp4"), Path("a_video.mp4"), Path("b_video.mp4")]
        assert [f.name for f in sort_by_name(files)] == [
            "a_video.mp4",
            "b_video.mp4",
            "c_video.mp4",
        ]

    def test_case_insensitive(self):
        files = [Path("B_video.mp4"), Path("a_video.mp4"), Path("C_video.mp4")]
        sorted_names = [f.name for f in sort_by_name(files)]
        assert sorted_names == ["a_video.mp4", "B_video.mp4", "C_video.mp4"]

    def test_single_file(self):
        files = [Path("only.mp4")]
        assert sort_by_name(files) == files

    def test_empty_list(self):
        assert sort_by_name([]) == []


# ---------------------------------------------------------------------------
# sort_by_date
# ---------------------------------------------------------------------------

class TestSortByDate:
    def test_oldest_first(self, tmp_path):
        # Create files with deliberately different mtime values.
        files = []
        for i, name in enumerate(["c.mp4", "a.mp4", "b.mp4"]):
            p = _touch(tmp_path, name)
            os.utime(p, (i * 10, i * 10))
            files.append(p)

        sorted_files = sort_by_date(files)
        assert [f.name for f in sorted_files] == ["c.mp4", "a.mp4", "b.mp4"]


# ---------------------------------------------------------------------------
# sort_rushes
# ---------------------------------------------------------------------------

class TestSortRushes:
    def test_sort_by_name(self, tmp_path):
        for name in ["c_rush.mp4", "a_rush.mp4", "b_rush.mp4"]:
            _touch(tmp_path, name)
        result = sort_rushes(tmp_path, sort_method="name")
        assert [f.name for f in result] == ["a_rush.mp4", "b_rush.mp4", "c_rush.mp4"]

    def test_sort_by_date(self, tmp_path):
        names = ["c_rush.mp4", "a_rush.mp4", "b_rush.mp4"]
        for i, name in enumerate(names):
            p = _touch(tmp_path, name)
            os.utime(p, (i * 10, i * 10))
        result = sort_rushes(tmp_path, sort_method="date")
        assert [f.name for f in result] == names  # order matches creation order

    def test_invalid_sort_method(self, tmp_path):
        _touch(tmp_path, "test.mp4")
        with pytest.raises(ValueError, match="Unknown sort method"):
            sort_rushes(tmp_path, sort_method="invalid")

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert sort_rushes(tmp_path) == []

    def test_non_video_files_ignored(self, tmp_path):
        _touch(tmp_path, "readme.txt")
        _touch(tmp_path, "image.jpg")
        assert sort_rushes(tmp_path) == []
