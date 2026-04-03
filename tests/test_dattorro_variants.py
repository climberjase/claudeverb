"""Tests for Dattorro topology variants.

TestSingleLoop: Tests for DattorroSingleLoop (Plan 02)
TestTripleDiffuser: Tests for DattorroTripleDiffuser (Plan 04)
TestAsymmetric: Tests for DattorroAsymmetric (Plan 04)
"""

from __future__ import annotations

import numpy as np
import pytest

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.config import SAMPLE_RATE


class TestSingleLoop:
    """Tests for DattorroSingleLoop algorithm."""

    def _make_algo(self):
        from claudeverb.algorithms.dattorro_single_loop import DattorroSingleLoop
        return DattorroSingleLoop()

    def test_registered_in_algorithm_registry(self):
        """DattorroSingleLoop appears in ALGORITHM_REGISTRY as 'dattorro_single_loop'."""
        assert "dattorro_single_loop" in ALGORITHM_REGISTRY

    def test_param_specs_has_6_knobs_and_2_switches(self):
        """param_specs has 6 knobs + 2 switches."""
        algo = self._make_algo()
        specs = algo.param_specs
        knobs = [k for k, v in specs.items() if v["type"] == "knob"]
        switches = [k for k, v in specs.items() if v["type"] == "switch"]
        assert len(knobs) == 6, f"Expected 6 knobs, got {len(knobs)}: {knobs}"
        assert len(switches) == 2, f"Expected 2 switches, got {len(switches)}: {switches}"
        # Check specific knob names
        expected_knobs = {"decay", "loop_length", "damping", "mod", "mix", "pre_delay"}
        assert set(knobs) == expected_knobs

    def test_processes_mono_to_stereo(self):
        """Processes mono float32 input and returns stereo (2, N) float32 output."""
        algo = self._make_algo()
        mono_input = np.random.randn(4800).astype(np.float32) * 0.5
        output = algo.process(mono_input)
        assert output.shape == (2, 4800), f"Expected (2, 4800), got {output.shape}"
        assert output.dtype == np.float32

    def test_stability_at_parameter_extremes(self):
        """Output is stable (no blowup) for 10 seconds of white noise at all parameter extremes."""
        algo = self._make_algo()
        noise = np.random.randn(SAMPLE_RATE * 10).astype(np.float32) * 0.5

        # Test at all extreme combinations
        extreme_params = [
            {"decay": 0, "loop_length": 0, "damping": 0, "mod": 0, "mix": 100, "pre_delay": 0},
            {"decay": 100, "loop_length": 100, "damping": 100, "mod": 100, "mix": 100, "pre_delay": 100},
            {"decay": 100, "loop_length": 0, "damping": 0, "mod": 100, "mix": 100, "pre_delay": 0},
            {"decay": 0, "loop_length": 100, "damping": 100, "mod": 0, "mix": 100, "pre_delay": 100},
        ]

        for params in extreme_params:
            algo.reset()
            algo.update_params(params)
            output = algo.process(noise)
            max_val = np.max(np.abs(output))
            assert max_val <= 1.0, f"Output blew up (max={max_val}) with params {params}"
            assert np.all(np.isfinite(output)), f"Non-finite output with params {params}"

    def test_loop_length_changes_spectral_content(self):
        """Loop Length knob at 0 vs 100 produces different spectral content."""
        algo = self._make_algo()
        impulse = np.zeros(SAMPLE_RATE, dtype=np.float32)
        impulse[0] = 1.0

        # Short loop
        algo.reset()
        algo.update_params({"loop_length": 0, "decay": 70, "mix": 100})
        out_short = algo.process(impulse)

        # Long loop
        algo.reset()
        algo.update_params({"loop_length": 100, "decay": 70, "mix": 100})
        out_long = algo.process(impulse)

        # Spectral content should differ
        fft_short = np.abs(np.fft.rfft(out_short[0]))
        fft_long = np.abs(np.fft.rfft(out_long[0]))

        # Normalize and compare -- should be meaningfully different
        if np.max(fft_short) > 0:
            fft_short /= np.max(fft_short)
        if np.max(fft_long) > 0:
            fft_long /= np.max(fft_long)

        spectral_diff = np.mean(np.abs(fft_short - fft_long))
        assert spectral_diff > 0.01, (
            f"Loop length 0 vs 100 should produce different spectra, diff={spectral_diff}"
        )

    def test_freeze_preserves_energy(self):
        """Freeze mode preserves energy (tail energy > 0.5 * initial after 5s)."""
        algo = self._make_algo()

        # Feed in 1 second of noise
        noise = np.random.randn(SAMPLE_RATE).astype(np.float32) * 0.3
        algo.update_params({"decay": 70, "mix": 100})
        initial_out = algo.process(noise)
        initial_energy = np.mean(initial_out ** 2)

        # Enable freeze and process 5 seconds of silence
        algo.update_params({"switch1": -1})  # Freeze
        silence = np.zeros(SAMPLE_RATE * 5, dtype=np.float32)
        frozen_out = algo.process(silence)

        # Check energy in the last second
        tail_energy = np.mean(frozen_out[:, -SAMPLE_RATE:] ** 2)
        assert tail_energy > 0.5 * initial_energy, (
            f"Freeze mode lost too much energy: tail={tail_energy:.6f}, "
            f"initial={initial_energy:.6f}, ratio={tail_energy/max(initial_energy, 1e-10):.3f}"
        )

    def test_reset_produces_deterministic_output(self):
        """Reset produces deterministic output."""
        algo = self._make_algo()
        impulse = np.zeros(4800, dtype=np.float32)
        impulse[0] = 1.0

        out1 = algo.process(impulse)
        algo.reset()
        out2 = algo.process(impulse)

        np.testing.assert_array_almost_equal(out1, out2, decimal=6)

    def test_c_export_methods_return_nonempty(self):
        """to_c_struct() and to_c_process_fn() return non-empty strings."""
        algo = self._make_algo()
        c_struct = algo.to_c_struct()
        c_process = algo.to_c_process_fn()
        assert isinstance(c_struct, str) and len(c_struct) > 50
        assert isinstance(c_process, str) and len(c_process) > 50

    def test_output_differs_from_dattorro_plate(self):
        """Output differs from DattorroPlate on same input (distinct algorithm)."""
        from claudeverb.algorithms.dattorro_plate import DattorroPlate

        impulse = np.zeros(SAMPLE_RATE, dtype=np.float32)
        impulse[0] = 1.0

        single_loop = self._make_algo()
        single_loop.update_params({"decay": 60, "mix": 100})
        out_sl = single_loop.process(impulse)

        plate = DattorroPlate()
        plate.update_params({"decay": 60, "mod_depth": 30})
        out_plate = plate.process(impulse)

        # Outputs must be meaningfully different
        diff = np.mean(np.abs(out_sl - out_plate))
        assert diff > 0.001, f"Single-loop output too similar to Plate, diff={diff}"


class TestTripleDiffuser:
    """Tests for DattorroTripleDiffuser algorithm."""

    def _make_algo(self):
        from claudeverb.algorithms.dattorro_triple_diffuser import DattorroTripleDiffuser
        return DattorroTripleDiffuser()

    def test_registered_in_algorithm_registry(self):
        """DattorroTripleDiffuser appears in ALGORITHM_REGISTRY as 'dattorro_triple_diffuser'."""
        assert "dattorro_triple_diffuser" in ALGORITHM_REGISTRY

    def test_param_specs_has_6_knobs_and_2_switches(self):
        """param_specs has 6 knobs (decay, diffusion_density, damping, mod, mix, pre_delay) + 2 switches."""
        algo = self._make_algo()
        specs = algo.param_specs
        knobs = [k for k, v in specs.items() if v["type"] == "knob"]
        switches = [k for k, v in specs.items() if v["type"] == "switch"]
        assert len(knobs) == 6, f"Expected 6 knobs, got {len(knobs)}: {knobs}"
        assert len(switches) == 2, f"Expected 2 switches, got {len(switches)}: {switches}"
        expected_knobs = {"decay", "diffusion_density", "damping", "mod", "mix", "pre_delay"}
        assert set(knobs) == expected_knobs

    def test_processes_mono_to_stereo(self):
        """Processes mono float32 input and returns stereo (2, N) float32 output."""
        algo = self._make_algo()
        mono_input = np.random.randn(4800).astype(np.float32) * 0.5
        output = algo.process(mono_input)
        assert output.shape == (2, 4800), f"Expected (2, 4800), got {output.shape}"
        assert output.dtype == np.float32

    def test_stability_at_parameter_extremes(self):
        """Output is stable (no blowup) for 10 seconds of white noise at all parameter extremes."""
        algo = self._make_algo()
        noise = np.random.randn(SAMPLE_RATE * 10).astype(np.float32) * 0.5

        extreme_params = [
            {"decay": 0, "diffusion_density": 0, "damping": 0, "mod": 0, "mix": 100, "pre_delay": 0},
            {"decay": 100, "diffusion_density": 100, "damping": 100, "mod": 100, "mix": 100, "pre_delay": 100},
            {"decay": 100, "diffusion_density": 0, "damping": 0, "mod": 100, "mix": 100, "pre_delay": 0},
            {"decay": 0, "diffusion_density": 100, "damping": 100, "mod": 0, "mix": 100, "pre_delay": 100},
        ]

        for params in extreme_params:
            algo.reset()
            algo.update_params(params)
            output = algo.process(noise)
            max_val = np.max(np.abs(output))
            assert max_val <= 1.0, f"Output blew up (max={max_val}) with params {params}"
            assert np.all(np.isfinite(output)), f"Non-finite output with params {params}"

    def test_diffusion_density_changes_onset_character(self):
        """Diffusion Density at 0 (2 diffusers) vs 100 (6 diffusers) produces different onset transient character."""
        algo = self._make_algo()
        impulse = np.zeros(SAMPLE_RATE, dtype=np.float32)
        impulse[0] = 1.0

        # Low density (fewer diffusers active)
        algo.reset()
        algo.update_params({"diffusion_density": 0, "decay": 60, "mix": 100})
        out_low = algo.process(impulse)

        # High density (all 6 diffusers active)
        algo.reset()
        algo.update_params({"diffusion_density": 100, "decay": 60, "mix": 100})
        out_high = algo.process(impulse)

        # Onset (first 50ms) should differ meaningfully
        onset_samples = int(0.05 * SAMPLE_RATE)  # 50ms
        onset_low = out_low[0, :onset_samples]
        onset_high = out_high[0, :onset_samples]

        onset_diff = np.mean(np.abs(onset_low - onset_high))
        assert onset_diff > 0.001, (
            f"Diffusion density 0 vs 100 should produce different onsets, diff={onset_diff}"
        )

    def test_output_differs_from_dattorro_plate(self):
        """Output differs from DattorroPlate on same input (distinct algorithm)."""
        from claudeverb.algorithms.dattorro_plate import DattorroPlate

        impulse = np.zeros(SAMPLE_RATE, dtype=np.float32)
        impulse[0] = 1.0

        triple = self._make_algo()
        triple.update_params({"decay": 60, "mix": 100})
        out_triple = triple.process(impulse)

        plate = DattorroPlate()
        plate.update_params({"decay": 60, "mod_depth": 30})
        out_plate = plate.process(impulse)

        diff = np.mean(np.abs(out_triple - out_plate))
        assert diff > 0.001, f"Triple-diffuser output too similar to Plate, diff={diff}"

    def test_freeze_preserves_energy(self):
        """Freeze mode preserves energy."""
        algo = self._make_algo()

        noise = np.random.randn(SAMPLE_RATE).astype(np.float32) * 0.3
        algo.update_params({"decay": 70, "mix": 100})
        initial_out = algo.process(noise)
        initial_energy = np.mean(initial_out ** 2)

        algo.update_params({"switch1": -1})  # Freeze
        silence = np.zeros(SAMPLE_RATE * 5, dtype=np.float32)
        frozen_out = algo.process(silence)

        tail_energy = np.mean(frozen_out[:, -SAMPLE_RATE:] ** 2)
        assert tail_energy > 0.3 * initial_energy, (
            f"Freeze mode lost too much energy: tail={tail_energy:.6f}, "
            f"initial={initial_energy:.6f}"
        )

    def test_reset_produces_deterministic_output(self):
        """Reset produces deterministic output."""
        algo = self._make_algo()
        impulse = np.zeros(4800, dtype=np.float32)
        impulse[0] = 1.0

        out1 = algo.process(impulse)
        algo.reset()
        out2 = algo.process(impulse)

        np.testing.assert_array_almost_equal(out1, out2, decimal=6)

    def test_c_export_methods_return_nonempty(self):
        """to_c_struct() and to_c_process_fn() return non-empty strings."""
        algo = self._make_algo()
        c_struct = algo.to_c_struct()
        c_process = algo.to_c_process_fn()
        assert isinstance(c_struct, str) and len(c_struct) > 50
        assert isinstance(c_process, str) and len(c_process) > 50


class TestAsymmetric:
    """Tests for DattorroAsymmetric algorithm."""

    def _make_algo(self):
        from claudeverb.algorithms.dattorro_asymmetric import DattorroAsymmetric
        return DattorroAsymmetric()

    def test_registered_in_algorithm_registry(self):
        """DattorroAsymmetric appears in ALGORITHM_REGISTRY as 'dattorro_asymmetric'."""
        assert "dattorro_asymmetric" in ALGORITHM_REGISTRY

    def test_param_specs_has_6_knobs_and_2_switches(self):
        """param_specs has 6 knobs (decay, spread, damping, mod, mix, pre_delay) + 2 switches."""
        algo = self._make_algo()
        specs = algo.param_specs
        knobs = [k for k, v in specs.items() if v["type"] == "knob"]
        switches = [k for k, v in specs.items() if v["type"] == "switch"]
        assert len(knobs) == 6, f"Expected 6 knobs, got {len(knobs)}: {knobs}"
        assert len(switches) == 2, f"Expected 2 switches, got {len(switches)}: {switches}"
        expected_knobs = {"decay", "spread", "damping", "mod", "mix", "pre_delay"}
        assert set(knobs) == expected_knobs

    def test_processes_mono_to_stereo(self):
        """Processes mono float32 input and returns stereo (2, N) float32 output."""
        algo = self._make_algo()
        mono_input = np.random.randn(4800).astype(np.float32) * 0.5
        output = algo.process(mono_input)
        assert output.shape == (2, 4800), f"Expected (2, 4800), got {output.shape}"
        assert output.dtype == np.float32

    def test_stability_at_parameter_extremes(self):
        """Output is stable (no blowup) for 10 seconds of white noise at all parameter extremes."""
        algo = self._make_algo()
        noise = np.random.randn(SAMPLE_RATE * 10).astype(np.float32) * 0.5

        extreme_params = [
            {"decay": 0, "spread": 0, "damping": 0, "mod": 0, "mix": 100, "pre_delay": 0},
            {"decay": 100, "spread": 100, "damping": 100, "mod": 100, "mix": 100, "pre_delay": 100},
            {"decay": 100, "spread": 0, "damping": 0, "mod": 100, "mix": 100, "pre_delay": 0},
            {"decay": 0, "spread": 100, "damping": 100, "mod": 0, "mix": 100, "pre_delay": 100},
        ]

        for params in extreme_params:
            algo.reset()
            algo.update_params(params)
            output = algo.process(noise)
            max_val = np.max(np.abs(output))
            assert max_val <= 1.0, f"Output blew up (max={max_val}) with params {params}"
            assert np.all(np.isfinite(output)), f"Non-finite output with params {params}"

    def test_spread_zero_near_symmetric(self):
        """Spread at 0 produces near-symmetric L/R energy balance (standard plate proportions)."""
        algo = self._make_algo()
        impulse = np.zeros(SAMPLE_RATE, dtype=np.float32)
        impulse[0] = 1.0

        algo.update_params({"spread": 0, "decay": 60, "mix": 100})
        output = algo.process(impulse)

        # At spread=0, L and R energy should be similar (balanced)
        # Note: Dattorro figure-eight inherently has different L/R base delays,
        # so channels are decorrelated but should have similar energy levels.
        left_energy = np.mean(output[0] ** 2)
        right_energy = np.mean(output[1] ** 2)
        energy_ratio = min(left_energy, right_energy) / max(left_energy, right_energy + 1e-20)
        assert energy_ratio > 0.3, (
            f"Spread=0 should produce balanced L/R energy, ratio={energy_ratio:.3f}"
        )

    def test_spread_100_wider_stereo(self):
        """Spread at 100 produces wider stereo image (L and R channels more different)."""
        algo = self._make_algo()
        impulse = np.zeros(SAMPLE_RATE, dtype=np.float32)
        impulse[0] = 1.0

        # Spread=0
        algo.reset()
        algo.update_params({"spread": 0, "decay": 60, "mix": 100})
        out_narrow = algo.process(impulse)

        # Spread=100
        algo.reset()
        algo.update_params({"spread": 100, "decay": 60, "mix": 100})
        out_wide = algo.process(impulse)

        # Cross-correlation should be lower at spread=100
        corr_narrow = np.corrcoef(out_narrow[0], out_narrow[1])[0, 1]
        corr_wide = np.corrcoef(out_wide[0], out_wide[1])[0, 1]
        assert corr_wide < corr_narrow, (
            f"Spread=100 should have lower L/R correlation than spread=0: "
            f"corr_narrow={corr_narrow:.3f}, corr_wide={corr_wide:.3f}"
        )

    def test_mono_compatibility_at_max_spread(self):
        """Mono compatibility at Spread=100: sum of L+R is not near-zero (no phase cancellation)."""
        algo = self._make_algo()
        noise = np.random.randn(SAMPLE_RATE).astype(np.float32) * 0.3

        algo.update_params({"spread": 100, "decay": 60, "mix": 100})
        output = algo.process(noise)

        # Sum L+R (mono downmix)
        mono_sum = output[0] + output[1]
        mono_energy = np.mean(mono_sum ** 2)
        stereo_energy = np.mean(output ** 2)

        # Mono energy should be at least 20% of stereo energy (no phase cancellation)
        assert mono_energy > 0.2 * stereo_energy, (
            f"Mono compatibility failed at spread=100: mono_energy={mono_energy:.6f}, "
            f"stereo_energy={stereo_energy:.6f}, ratio={mono_energy / max(stereo_energy, 1e-10):.3f}"
        )

    def test_reset_produces_deterministic_output(self):
        """Reset produces deterministic output."""
        algo = self._make_algo()
        impulse = np.zeros(4800, dtype=np.float32)
        impulse[0] = 1.0

        out1 = algo.process(impulse)
        algo.reset()
        out2 = algo.process(impulse)

        np.testing.assert_array_almost_equal(out1, out2, decimal=6)

    def test_c_export_methods_return_nonempty(self):
        """to_c_struct() and to_c_process_fn() return non-empty strings."""
        algo = self._make_algo()
        c_struct = algo.to_c_struct()
        c_process = algo.to_c_process_fn()
        assert isinstance(c_struct, str) and len(c_struct) > 50
        assert isinstance(c_process, str) and len(c_process) > 50
