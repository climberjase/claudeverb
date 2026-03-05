"""Tests that block-based processing matches single-buffer processing.

For each primitive, processing a 480-sample signal in 48-sample chunks
(BUFFER_SIZE) must produce identical output to processing as one block.
This proves the primitives are correctly stateful across block boundaries.
"""

import numpy as np
import pytest

from claudeverb.algorithms.filters import (
    AllpassFilter,
    Biquad,
    CombFilter,
    DelayLine,
)
from claudeverb.config import BUFFER_SIZE


def _process_chunked(primitive, signal: np.ndarray) -> np.ndarray:
    """Process a signal in BUFFER_SIZE chunks through a primitive."""
    outputs = []
    for start in range(0, len(signal), BUFFER_SIZE):
        chunk = signal[start : start + BUFFER_SIZE]
        outputs.append(primitive.process(chunk))
    return np.concatenate(outputs)


class TestBlockProcessing:
    """Block-chunked processing matches single-buffer for all primitives."""

    def test_delay_line_block_consistency(self):
        """DelayLine: chunked == single-buffer."""
        signal = np.zeros(480, dtype=np.float32)
        signal[0] = 1.0

        dl_single = DelayLine(max_delay=64)
        out_single = dl_single.process(signal)

        dl_chunked = DelayLine(max_delay=64)
        out_chunked = _process_chunked(dl_chunked, signal)

        np.testing.assert_allclose(out_chunked, out_single, atol=0)

    def test_comb_filter_block_consistency(self):
        """CombFilter: chunked == single-buffer."""
        signal = np.zeros(480, dtype=np.float32)
        signal[0] = 1.0

        cf_single = CombFilter(delay_length=64, feedback=0.5, damp=0.2)
        out_single = cf_single.process(signal)

        cf_chunked = CombFilter(delay_length=64, feedback=0.5, damp=0.2)
        out_chunked = _process_chunked(cf_chunked, signal)

        np.testing.assert_allclose(out_chunked, out_single, atol=0)

    def test_allpass_filter_block_consistency(self):
        """AllpassFilter: chunked == single-buffer."""
        signal = np.zeros(480, dtype=np.float32)
        signal[0] = 1.0

        ap_single = AllpassFilter(delay_length=64, feedback=0.5)
        out_single = ap_single.process(signal)

        ap_chunked = AllpassFilter(delay_length=64, feedback=0.5)
        out_chunked = _process_chunked(ap_chunked, signal)

        np.testing.assert_allclose(out_chunked, out_single, atol=0)

    def test_biquad_block_consistency(self):
        """Biquad: chunked == single-buffer."""
        signal = np.zeros(480, dtype=np.float32)
        signal[0] = 1.0

        bq_single = Biquad.lowpass(1000, 0.707)
        out_single = bq_single.process(signal)

        bq_chunked = Biquad.lowpass(1000, 0.707)
        out_chunked = _process_chunked(bq_chunked, signal)

        np.testing.assert_allclose(out_chunked, out_single, atol=0)
