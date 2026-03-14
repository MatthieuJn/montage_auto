"""
montage_auto - Automatic video montage: sort rushes and remove silences.
"""

from montage_auto.silence_remover import remove_silence, detect_silence
from montage_auto.rush_sorter import sort_rushes, get_video_files
from montage_auto.montage import create_montage

__all__ = [
    "remove_silence",
    "detect_silence",
    "sort_rushes",
    "get_video_files",
    "create_montage",
]
