"""
montage - Orchestrate rush sorting, silence removal, and concatenation.
"""

from pathlib import Path

from moviepy import VideoFileClip, concatenate_videoclips

from montage_auto.rush_sorter import sort_rushes
from montage_auto.silence_remover import remove_silence


def create_montage(
    input_directory,
    output_path,
    sort_method="name",
    remove_silences=True,
    silence_threshold=0.01,
    min_silence_duration=0.5,
):
    """
    Create a montage from all video rushes in *input_directory*.

    The rushes are sorted according to *sort_method*, optionally stripped of
    silent portions, and then concatenated into a single output video.

    Args:
        input_directory: Directory that contains the raw video rush files.
        output_path: Destination path for the final montage video.
        sort_method: ``'name'`` (default) for alphabetical order or
                     ``'date'`` for chronological order.
        remove_silences: Whether to remove silent portions from each rush.
                         Default ``True``.
        silence_threshold: Normalised amplitude threshold used by the silence
                           detector.  Default ``0.01``.
        min_silence_duration: Minimum duration of silence (seconds) that will
                              be removed.  Default ``0.5``.

    Returns:
        :class:`pathlib.Path` pointing to the written output file.

    Raises:
        ValueError: If *input_directory* contains no supported video files.
    """
    sorted_rushes = sort_rushes(input_directory, sort_method)

    if not sorted_rushes:
        raise ValueError(f"No video files found in '{input_directory}'.")

    clips = []
    for rush_path in sorted_rushes:
        if remove_silences:
            clip = remove_silence(
                str(rush_path),
                threshold=silence_threshold,
                min_silence_duration=min_silence_duration,
            )
        else:
            clip = VideoFileClip(str(rush_path))
        clips.append(clip)

    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(str(output_path))

    return Path(output_path)
