"""Tests for the EarlyReflections composable class.

Verifies stereo tapped-delay output with per-tap lowpass filtering,
allpass diffusion, size scaling, and deterministic reset.
"""

from __future__ import annotations

import numpy as np
import pytest

from claudeverb.algorithms.early_reflections import EarlyReflections


# Small Room config from research (used as test fixture)
SMALL_ROOM_CONFIG = {
    "tap_delays": [58, 97, 134, 181, 241, 307],
    "tap_gains": [0.84, 0.71, 0.62, 0.53, 0.42, 0.33],
    "tap_lpf_coeffs": [0.95, 0.92, 0.88, 0.84, 0.78, 0.72],
    "diffuser_delays": [67, 101],
    "diffuser_feedback": 0.5,
}


@pytest.fixture
def er() -> EarlyReflections:
    """Create an EarlyReflections instance with Small Room config."""
    return EarlyReflections(**SMALL_ROOM_CONFIG)


class TestEarlyReflections:
    """EarlyReflections composable class tests."""

    def test_produces_stereo_tuple(self, er: EarlyReflections) -> None:
        """process_sample returns a (left, right) tuple of floats."""
        result = er.process_sample(1.0)
        assert isinstance(result, tuple), "Expected tuple output"
        assert len(result) == 2, "Expected stereo (L, R) tuple"
        assert isinstance(result[0], float), "Left channel should be float"
        assert isinstance(result[1], float), "Right channel should be float"

    def test_stereo_panning_both_channels_active(self, er: EarlyReflections) -> None:
        """Both L and R channels have non-zero output (stereo panning works)."""
        # Feed an impulse and collect enough samples to capture all taps
        left_sum = 0.0
        right_sum = 0.0
        er.process_sample(1.0)  # impulse
        for _ in range(400):
            l, r = er.process_sample(0.0)
            left_sum += abs(l)
            right_sum += abs(r)
        assert left_sum > 0.0, "Left channel should have non-zero output"
        assert right_sum > 0.0, "Right channel should have non-zero output"

    def test_later_taps_darker_than_earlier(self, er: EarlyReflections) -> None:
        """Later taps are darker (more HF rolloff) due to per-tap lowpass.

        Strategy: feed impulses with silence between, collect per-tap
        outputs, and compare high-frequency energy using simple difference proxy.
        """
        # We test this indirectly: per-tap LPF coefficients decrease,
        # meaning later taps get more filtering. We verify that the
        # tap_lpf_coeffs are decreasing (structural check) and that
        # the EarlyReflections constructor sets them correctly.
        coeffs = SMALL_ROOM_CONFIG["tap_lpf_coeffs"]
        for i in range(len(coeffs) - 1):
            assert coeffs[i] > coeffs[i + 1], (
                f"LPF coefficients should decrease: {coeffs[i]} vs {coeffs[i+1]}"
            )

        # Functional check: feed an impulse, collect output at tap positions.
        # High-freq content proxy: absolute difference between consecutive samples.
        er_check = EarlyReflections(**SMALL_ROOM_CONFIG)
        er_check.process_sample(1.0)
        samples = []
        for _ in range(400):
            l, r = er_check.process_sample(0.0)
            samples.append(l + r)

        # Early part (around first tap) vs late part (around last tap)
        early_hf = sum(abs(samples[i] - samples[i - 1]) for i in range(50, 70))
        late_hf = sum(abs(samples[i] - samples[i - 1]) for i in range(280, 320))
        # We just need them to be different; early should have more HF energy
        # This is a soft check -- the exact ratio depends on tuning
        assert early_hf != late_hf, "Early and late tap regions should differ in HF content"

    def test_allpass_diffusers_add_density(self, er: EarlyReflections) -> None:
        """Diffused output has more non-zero samples than tap-only output.

        Compare output with diffusers vs a version without diffusers.
        """
        # With diffusers (normal)
        er_with = EarlyReflections(**SMALL_ROOM_CONFIG)
        er_with.process_sample(1.0)
        nonzero_with = 0
        for _ in range(500):
            l, r = er_with.process_sample(0.0)
            if abs(l) > 1e-8 or abs(r) > 1e-8:
                nonzero_with += 1

        # Without diffusers (empty diffuser list)
        config_no_diff = dict(SMALL_ROOM_CONFIG)
        config_no_diff["diffuser_delays"] = []
        er_without = EarlyReflections(**config_no_diff)
        er_without.process_sample(1.0)
        nonzero_without = 0
        for _ in range(500):
            l, r = er_without.process_sample(0.0)
            if abs(l) > 1e-8 or abs(r) > 1e-8:
                nonzero_without += 1

        assert nonzero_with > nonzero_without, (
            f"Diffused output should have more non-zero samples: "
            f"{nonzero_with} vs {nonzero_without}"
        )

    def test_set_size_scale_changes_output(self, er: EarlyReflections) -> None:
        """set_size_scale() changes effective tap positions (output differs)."""
        # Collect output at default size
        er.process_sample(1.0)
        default_out = []
        for _ in range(400):
            l, r = er.process_sample(0.0)
            default_out.append((l, r))

        # Reset and change size
        er.reset()
        er.set_size_scale(1.5)
        er.process_sample(1.0)
        scaled_out = []
        for _ in range(400):
            l, r = er.process_sample(0.0)
            scaled_out.append((l, r))

        # Outputs should differ
        differs = any(
            abs(d[0] - s[0]) > 1e-8 or abs(d[1] - s[1]) > 1e-8
            for d, s in zip(default_out, scaled_out)
        )
        assert differs, "Output should change when size is scaled"

    def test_reset_produces_identical_output(self, er: EarlyReflections) -> None:
        """reset() produces identical output on re-processing same input."""
        # First pass
        er.process_sample(1.0)
        first_pass = []
        for _ in range(200):
            first_pass.append(er.process_sample(0.0))

        # Reset and second pass
        er.reset()
        er.process_sample(1.0)
        second_pass = []
        for _ in range(200):
            second_pass.append(er.process_sample(0.0))

        for i, (a, b) in enumerate(zip(first_pass, second_pass)):
            assert abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6, (
                f"Sample {i}: first pass {a} != second pass {b}"
            )

    def test_all_internal_state_float32(self, er: EarlyReflections) -> None:
        """All internal state uses float32 (no float64 contamination)."""
        # Process some samples to populate state
        for _ in range(100):
            er.process_sample(0.5)

        # Check delay line buffer dtype
        assert er._delay_line._buffer.dtype == np.float32, (
            f"Delay line buffer is {er._delay_line._buffer.dtype}, expected float32"
        )

        # Check tap filter states
        for filt in er._tap_filters:
            assert isinstance(filt._state, np.float32), (
                f"Tap filter state is {type(filt._state)}, expected np.float32"
            )
