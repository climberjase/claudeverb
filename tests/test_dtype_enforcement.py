"""Tests that all DSP primitives reject float64 input.

Every primitive with a process() method must:
1. Reject float64 ndarray with TypeError
2. Return float32 ndarray when given float32 input
"""

import numpy as np
import pytest

from claudeverb.algorithms.filters import (
    AllpassFilter,
    Biquad,
    CombFilter,
    DelayLine,
)


class TestDtypeEnforcement:
    """All primitives reject float64 and produce float32."""

    def test_delay_line_rejects_float64(self):
        """DelayLine.process() rejects float64."""
        dl = DelayLine(max_delay=64)
        with pytest.raises(TypeError):
            dl.process(np.zeros(16, dtype=np.float64))

    def test_delay_line_returns_float32(self):
        """DelayLine.process() returns float32."""
        dl = DelayLine(max_delay=64)
        out = dl.process(np.zeros(16, dtype=np.float32))
        assert out.dtype == np.float32

    def test_comb_filter_rejects_float64(self):
        """CombFilter.process() rejects float64."""
        cf = CombFilter(delay_length=64, feedback=0.5, damp=0.2)
        with pytest.raises(TypeError):
            cf.process(np.zeros(16, dtype=np.float64))

    def test_comb_filter_returns_float32(self):
        """CombFilter.process() returns float32."""
        cf = CombFilter(delay_length=64, feedback=0.5, damp=0.2)
        out = cf.process(np.zeros(16, dtype=np.float32))
        assert out.dtype == np.float32

    def test_allpass_filter_rejects_float64(self):
        """AllpassFilter.process() rejects float64."""
        ap = AllpassFilter(delay_length=64, feedback=0.5)
        with pytest.raises(TypeError):
            ap.process(np.zeros(16, dtype=np.float64))

    def test_allpass_filter_returns_float32(self):
        """AllpassFilter.process() returns float32."""
        ap = AllpassFilter(delay_length=64, feedback=0.5)
        out = ap.process(np.zeros(16, dtype=np.float32))
        assert out.dtype == np.float32

    def test_biquad_rejects_float64(self):
        """Biquad.process() rejects float64."""
        bq = Biquad.lowpass(1000, 0.707)
        with pytest.raises(TypeError):
            bq.process(np.zeros(16, dtype=np.float64))

    def test_biquad_returns_float32(self):
        """Biquad.process() returns float32."""
        bq = Biquad.lowpass(1000, 0.707)
        out = bq.process(np.zeros(16, dtype=np.float32))
        assert out.dtype == np.float32
