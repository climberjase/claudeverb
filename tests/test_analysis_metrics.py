"""Tests for claudeverb.analysis.metrics -- acoustic analysis functions."""

import math

import numpy as np
import pytest

from claudeverb.analysis.metrics import (
    compute_clarity,
    compute_drr,
    measure_rt60,
    measure_rt60_bands,
    spectral_centroid_delta,
)
from claudeverb.config import SAMPLE_RATE


class TestRT60:
    """Tests for broadband RT60 measurement."""

    def test_rt60_comb_filter(self, comb_ir: np.ndarray) -> None:
        """RT60 of comb filter IR matches analytical formula within 10%.

        Analytical RT60 = -3.0 * (delay / sr) / log10(feedback)
                       = -3.0 * (1557 / 48000) / log10(0.84)
                       ~ 1.28s
        """
        analytical_rt60 = -3.0 * (1557 / SAMPLE_RATE) / math.log10(0.84)
        measured = measure_rt60(comb_ir, sr=SAMPLE_RATE)
        assert measured > 0, "RT60 should be positive for decaying signal"
        assert abs(measured - analytical_rt60) / analytical_rt60 < 0.10, (
            f"RT60 {measured:.3f}s not within 10% of analytical {analytical_rt60:.3f}s"
        )

    def test_rt60_short_signal(self) -> None:
        """Returns 0.0 for a signal too short to measure decay."""
        short = np.zeros(100, dtype=np.float32)
        short[0] = 1.0
        result = measure_rt60(short, sr=SAMPLE_RATE)
        assert result == 0.0


class TestRT60Bands:
    """Tests for per-band RT60 measurement."""

    def test_rt60_per_band(self, comb_ir: np.ndarray) -> None:
        """measure_rt60_bands returns dict with low, mid, high keys."""
        result = measure_rt60_bands(comb_ir, sr=SAMPLE_RATE)
        assert isinstance(result, dict)
        for key in ("low", "mid", "high"):
            assert key in result, f"Missing key: {key}"
            assert isinstance(result[key], float), f"{key} should be float"
            assert result[key] >= 0.0, f"{key} RT60 should be non-negative"


class TestDRR:
    """Tests for Direct-to-Reverberant Ratio."""

    def test_drr(self) -> None:
        """DRR of a known IR matches hand-calculated value within 0.5 dB.

        First 120 samples (2.5ms at 48kHz) have amplitude 1.0,
        remaining have amplitude 0.1.
        """
        n_total = SAMPLE_RATE  # 1 second
        n_direct = 120  # 2.5ms at 48kHz
        ir = np.full(n_total, 0.1, dtype=np.float32)
        ir[:n_direct] = 1.0

        # Hand-calculated: DRR = 10*log10(sum(direct^2) / sum(reverb^2))
        direct_energy = n_direct * 1.0**2
        reverb_energy = (n_total - n_direct) * 0.1**2
        expected_drr = 10.0 * math.log10(direct_energy / reverb_energy)

        measured = compute_drr(ir, sr=SAMPLE_RATE, direct_ms=2.5)
        assert abs(measured - expected_drr) < 0.5, (
            f"DRR {measured:.2f} dB not within 0.5 dB of expected {expected_drr:.2f} dB"
        )


class TestClarity:
    """Tests for C80 and C50 clarity measures."""

    def test_c80(self) -> None:
        """C80 of a known IR matches hand-calculated value within 0.5 dB.

        First 3840 samples (80ms at 48kHz) have amplitude 1.0,
        remaining have amplitude 0.01.
        """
        n_total = SAMPLE_RATE
        n_early = 3840  # 80ms at 48kHz
        ir = np.full(n_total, 0.01, dtype=np.float32)
        ir[:n_early] = 1.0

        early_energy = n_early * 1.0**2
        late_energy = (n_total - n_early) * 0.01**2
        expected_c80 = 10.0 * math.log10(early_energy / late_energy)

        measured = compute_clarity(ir, sr=SAMPLE_RATE, early_ms=80.0)
        assert abs(measured - expected_c80) < 0.5, (
            f"C80 {measured:.2f} dB not within 0.5 dB of expected {expected_c80:.2f} dB"
        )

    def test_c50(self) -> None:
        """C50 of a known IR matches hand-calculated value within 0.5 dB.

        First 2400 samples (50ms at 48kHz) have amplitude 1.0,
        remaining have amplitude 0.01.
        """
        n_total = SAMPLE_RATE
        n_early = 2400  # 50ms at 48kHz
        ir = np.full(n_total, 0.01, dtype=np.float32)
        ir[:n_early] = 1.0

        early_energy = n_early * 1.0**2
        late_energy = (n_total - n_early) * 0.01**2
        expected_c50 = 10.0 * math.log10(early_energy / late_energy)

        measured = compute_clarity(ir, sr=SAMPLE_RATE, early_ms=50.0)
        assert abs(measured - expected_c50) < 0.5, (
            f"C50 {measured:.2f} dB not within 0.5 dB of expected {expected_c50:.2f} dB"
        )


class TestSpectralCentroidDelta:
    """Tests for spectral centroid delta."""

    def test_spectral_centroid_delta(self, mono_sine: np.ndarray) -> None:
        """For identical signals, spectral centroid delta is approximately 0."""
        delta = spectral_centroid_delta(mono_sine, mono_sine, sr=SAMPLE_RATE)
        assert isinstance(delta, float)
        assert abs(delta) < 50.0, f"Delta {delta:.1f} Hz should be near 0 for identical signals"


class TestStereoHandling:
    """All metrics accept (2, N) stereo arrays without error."""

    def test_rt60_stereo(self, stereo_sine: np.ndarray) -> None:
        result = measure_rt60(stereo_sine, sr=SAMPLE_RATE)
        assert isinstance(result, float)

    def test_rt60_bands_stereo(self, stereo_sine: np.ndarray) -> None:
        result = measure_rt60_bands(stereo_sine, sr=SAMPLE_RATE)
        assert isinstance(result, dict)

    def test_drr_stereo(self, stereo_sine: np.ndarray) -> None:
        result = compute_drr(stereo_sine, sr=SAMPLE_RATE)
        assert isinstance(result, float)

    def test_clarity_stereo(self, stereo_sine: np.ndarray) -> None:
        result = compute_clarity(stereo_sine, sr=SAMPLE_RATE)
        assert isinstance(result, float)

    def test_spectral_centroid_delta_stereo(self, stereo_sine: np.ndarray) -> None:
        result = spectral_centroid_delta(stereo_sine, stereo_sine, sr=SAMPLE_RATE)
        assert isinstance(result, float)
