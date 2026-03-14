"""
silence_remover - Detect and remove silent portions from a video clip.
"""

import numpy as np
from moviepy import VideoFileClip, concatenate_videoclips


def detect_silence(audio_array, fps, threshold=0.01, min_silence_duration=0.5):
    """
    Detect silent intervals in an audio array.

    Silence is defined as every sample whose absolute normalised amplitude
    is below *threshold*.  Only runs of silence that are at least
    *min_silence_duration* seconds long are returned.

    Args:
        audio_array: 1-D or 2-D (stereo) numpy array of audio samples.
        fps: Audio sample rate (frames per second).
        threshold: Normalised amplitude below which a sample is considered
                   silent.  Value in ``[0, 1]``.  Default ``0.01``.
        min_silence_duration: Minimum silence duration in seconds.
                              Shorter silent runs are ignored.
                              Default ``0.5``.

    Returns:
        List of ``(start, end)`` tuples in seconds representing detected
        silent intervals.
    """
    # Convert stereo to mono by averaging channels.
    if audio_array.ndim > 1:
        mono = np.mean(audio_array, axis=1)
    else:
        mono = audio_array.copy()

    # Normalise so that the threshold is amplitude-independent of recording
    # level.  Skip normalisation when the array is completely silent to
    # avoid a divide-by-zero.
    max_val = np.max(np.abs(mono))
    if max_val > 0:
        mono = mono / max_val

    is_silent = np.abs(mono) < threshold
    min_frames = int(min_silence_duration * fps)

    silent_intervals = []
    in_silence = False
    silence_start = 0

    for i, silent in enumerate(is_silent):
        if silent and not in_silence:
            in_silence = True
            silence_start = i
        elif not silent and in_silence:
            in_silence = False
            if i - silence_start >= min_frames:
                silent_intervals.append((silence_start / fps, i / fps))

    # Handle silence that extends all the way to the end.
    if in_silence and (len(is_silent) - silence_start) >= min_frames:
        silent_intervals.append((silence_start / fps, len(is_silent) / fps))

    return silent_intervals


def remove_silence(
    video_path,
    output_path=None,
    threshold=0.01,
    min_silence_duration=0.5,
):
    """
    Remove silent portions from a video file.

    Args:
        video_path: Path to the input video file.
        output_path: Optional path where the processed video will be written.
                     When ``None`` the clip is only returned in memory without
                     being written to disk.
        threshold: Normalised amplitude threshold for silence detection.
                   Default ``0.01``.
        min_silence_duration: Minimum silence length (seconds) to remove.
                              Default ``0.5``.

    Returns:
        A :class:`moviepy.editor.VideoClip` with silences removed.
    """
    clip = VideoFileClip(str(video_path))

    if clip.audio is None:
        # No audio track – nothing to remove.
        if output_path:
            clip.write_videofile(str(output_path))
        return clip

    audio_array = clip.audio.to_soundarray()
    fps = clip.audio.fps

    silent_intervals = detect_silence(audio_array, fps, threshold, min_silence_duration)

    if not silent_intervals:
        # No silence found – return the original clip unchanged.
        if output_path:
            clip.write_videofile(str(output_path))
        return clip

    # Build the list of non-silent intervals by inverting silent_intervals.
    non_silent = []
    prev_end = 0.0

    for start, end in silent_intervals:
        if start > prev_end:
            non_silent.append((prev_end, start))
        prev_end = end

    if prev_end < clip.duration:
        non_silent.append((prev_end, clip.duration))

    if not non_silent:
        # The entire clip is silent – return the original.
        if output_path:
            clip.write_videofile(str(output_path))
        return clip

    subclips = [clip.subclip(start, end) for start, end in non_silent]
    result = concatenate_videoclips(subclips)

    if output_path:
        result.write_videofile(str(output_path))

    return result
