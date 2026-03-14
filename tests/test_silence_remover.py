"""
Tests for montage_auto.silence_remover.detect_silence.

These tests operate on synthetic numpy arrays only – no real video files are
needed, so there is no dependency on FFmpeg or MoviePy here.
"""

import numpy as np
import pytest

from montage_auto.silence_remover import detect_silence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio(fps, segments):
    """
    Build a 1-D numpy audio array from a list of (duration_s, amplitude)
    pairs.

    Example::

        _make_audio(100, [(2.0, 0.5), (1.0, 0.0), (3.0, 0.8)])
    """
    parts = []
    for duration, amplitude in segments:
        frames = int(duration * fps)
        parts.append(np.full(frames, amplitude, dtype=float))
    return np.concatenate(parts)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDetectSilenceBasic:
    def test_entirely_silent(self):
        """A completely silent clip should yield one interval covering everything."""
        fps = 100
        audio = np.zeros(500)
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert len(intervals) == 1
        start, end = intervals[0]
        assert start == pytest.approx(0.0)
        assert end == pytest.approx(5.0)

    def test_no_silence(self):
        """A clip with amplitude always above the threshold should return no intervals."""
        fps = 100
        audio = np.ones(1000) * 0.5
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert intervals == []

    def test_silence_in_middle(self):
        """Silence in the middle of the clip should be detected exactly once."""
        fps = 100
        # 2 s loud | 2 s silent | 2 s loud
        audio = _make_audio(fps, [(2.0, 0.5), (2.0, 0.0), (2.0, 0.5)])
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert len(intervals) == 1
        start, end = intervals[0]
        assert start == pytest.approx(2.0)
        assert end == pytest.approx(4.0)

    def test_silence_at_start(self):
        """Silence at the beginning of the clip should be detected."""
        fps = 100
        audio = _make_audio(fps, [(1.0, 0.0), (3.0, 0.5)])
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert len(intervals) == 1
        start, end = intervals[0]
        assert start == pytest.approx(0.0)
        assert end == pytest.approx(1.0)

    def test_silence_at_end(self):
        """Silence at the end of the clip should be detected."""
        fps = 100
        audio = _make_audio(fps, [(3.0, 0.5), (1.0, 0.0)])
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert len(intervals) == 1
        start, end = intervals[0]
        assert start == pytest.approx(3.0)
        assert end == pytest.approx(4.0)

    def test_multiple_silent_regions(self):
        """Multiple long silences should all be detected."""
        fps = 100
        # loud | silence1 | loud | silence2 | loud
        audio = _make_audio(
            fps,
            [(1.0, 0.5), (2.0, 0.0), (1.0, 0.5), (1.5, 0.0), (1.0, 0.5)],
        )
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert len(intervals) == 2
        assert intervals[0][0] == pytest.approx(1.0)
        assert intervals[0][1] == pytest.approx(3.0)
        assert intervals[1][0] == pytest.approx(4.0)
        assert intervals[1][1] == pytest.approx(5.5)


class TestDetectSilenceMinDuration:
    def test_short_silence_ignored(self):
        """Silences shorter than min_silence_duration should not be returned."""
        fps = 100
        # 0.2 s silence is shorter than the 0.5 s minimum
        audio = _make_audio(fps, [(1.0, 0.5), (0.2, 0.0), (1.0, 0.5)])
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert intervals == []

    def test_silence_exactly_at_minimum(self):
        """Silence exactly equal to min_silence_duration should be detected."""
        fps = 100
        audio = _make_audio(fps, [(1.0, 0.5), (0.5, 0.0), (1.0, 0.5)])
        intervals = detect_silence(audio, fps, threshold=0.01, min_silence_duration=0.5)
        assert len(intervals) == 1


class TestDetectSilenceStereo:
    def test_stereo_audio(self):
        """Stereo (2-D) arrays should be handled by averaging channels."""
        fps = 100
        mono = _make_audio(fps, [(1.0, 0.5), (1.0, 0.0), (1.0, 0.5)])
        # Stack as stereo (identical channels)
        stereo = np.stack([mono, mono], axis=1)
        intervals = detect_silence(stereo, fps, threshold=0.01, min_silence_duration=0.5)
        assert len(intervals) == 1
        assert intervals[0][0] == pytest.approx(1.0)
        assert intervals[0][1] == pytest.approx(2.0)
