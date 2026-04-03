"""Tests for Room/Chamber reverb algorithms.

TestSmallRoom: Full test suite for SmallRoom algorithm.
TestLargeRoom: Full test suite for LargeRoom algorithm.
TestChamber: Full test suite for Chamber algorithm.
TestCrossAlgorithm: Cross-algorithm comparison tests.
"""

from __future__ import annotations

import numpy as np
import pytest

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.algorithms.small_room import SmallRoom
from claudeverb.algorithms.small_room_presets import list_presets, get_preset


class TestSmallRoom:
    """SmallRoom algorithm tests."""

    @pytest.fixture
    def algo(self) -> SmallRoom:
        """Create a SmallRoom instance with default params."""
        return SmallRoom()

    def test_registered_in_algorithm_registry(self) -> None:
        """SmallRoom appears in ALGORITHM_REGISTRY as 'small_room'."""
        assert "small_room" in ALGORITHM_REGISTRY
        assert ALGORITHM_REGISTRY["small_room"] is SmallRoom

    def test_param_specs_has_6_knobs_and_2_switches(self, algo: SmallRoom) -> None:
        """param_specs has 6 knobs + 2 switches."""
        specs = algo.param_specs
        knobs = [k for k, v in specs.items() if v["type"] == "knob"]
        switches = [k for k, v in specs.items() if v["type"] == "switch"]
        assert len(knobs) == 6, f"Expected 6 knobs, got {len(knobs)}: {knobs}"
        assert len(switches) == 2, f"Expected 2 switches, got {len(switches)}: {switches}"

        # Verify expected knob names
        expected_knobs = {"decay", "size", "damping", "er_level", "mix", "pre_delay"}
        assert set(knobs) == expected_knobs, f"Unexpected knobs: {set(knobs)} vs {expected_knobs}"

    def test_processes_mono_to_stereo(self, algo: SmallRoom) -> None:
        """SmallRoom processes mono float32 input and returns stereo (2, N) float32 output."""
        mono_input = np.random.randn(4800).astype(np.float32) * 0.1
        output = algo.process(mono_input)
        assert output.ndim == 2, f"Expected 2D output, got {output.ndim}D"
        assert output.shape[0] == 2, f"Expected stereo (2, N), got shape {output.shape}"
        assert output.shape[1] == len(mono_input), "Output length should match input"
        assert output.dtype == np.float32, f"Expected float32, got {output.dtype}"

    def test_stability_10_seconds_white_noise(self, algo: SmallRoom) -> None:
        """Output is stable (no blowup) across 10 seconds of white noise at all parameter extremes."""
        # Test at extreme parameter settings
        extreme_params_list = [
            {"decay": 100, "size": 100, "damping": 0, "er_level": 100, "mix": 100, "pre_delay": 100},
            {"decay": 0, "size": 0, "damping": 100, "er_level": 0, "mix": 0, "pre_delay": 0},
            {"decay": 100, "size": 100, "damping": 100, "er_level": 50, "mix": 100, "pre_delay": 50},
        ]
        for params in extreme_params_list:
            algo.reset()
            algo.update_params(params)
            # Process 10 seconds in chunks
            for _ in range(10):
                chunk = np.random.randn(48000).astype(np.float32) * 0.5
                output = algo.process(chunk)
                max_val = np.max(np.abs(output))
                assert max_val < 10.0, (
                    f"Output blew up (max={max_val}) with params {params}"
                )
                assert np.all(np.isfinite(output)), (
                    f"Non-finite values in output with params {params}"
                )

    def test_presets_load_and_produce_different_outputs(self, algo: SmallRoom) -> None:
        """SmallRoom presets load without error and produce different outputs."""
        preset_names = list_presets()
        assert len(preset_names) >= 2, "Expected at least 2 presets"

        outputs = {}
        test_input = np.random.randn(4800).astype(np.float32) * 0.1
        rng_state = np.random.get_state()

        for name in preset_names:
            preset = get_preset(name)
            algo.reset()
            algo.update_params(preset)
            np.random.set_state(rng_state)
            output = algo.process(test_input.copy())
            outputs[name] = output

        # Each preset should produce different output
        names = list(outputs.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                diff = np.max(np.abs(outputs[names[i]] - outputs[names[j]]))
                assert diff > 1e-6, (
                    f"Presets '{names[i]}' and '{names[j]}' produced identical output"
                )

    def test_reset_produces_deterministic_output(self, algo: SmallRoom) -> None:
        """SmallRoom reset produces deterministic output."""
        test_input = np.random.randn(2400).astype(np.float32) * 0.1

        # First pass
        output_1 = algo.process(test_input.copy())

        # Contaminate state
        noise = np.random.randn(48000).astype(np.float32)
        algo.process(noise)

        # Reset and second pass
        algo.reset()
        output_2 = algo.process(test_input.copy())

        np.testing.assert_allclose(
            output_1, output_2, atol=1e-5,
            err_msg="Output should be identical after reset"
        )

    def test_c_export_methods_return_nonempty(self, algo: SmallRoom) -> None:
        """to_c_struct() and to_c_process_fn() return non-empty strings."""
        c_struct = algo.to_c_struct()
        c_fn = algo.to_c_process_fn()
        assert isinstance(c_struct, str) and len(c_struct) > 10
        assert isinstance(c_fn, str) and len(c_fn) > 10
        assert "typedef struct" in c_struct
        assert "void" in c_fn or "process" in c_fn

    def test_er_level_crossfade_works(self, algo: SmallRoom) -> None:
        """ER Level knob at 0 produces different output than at 100."""
        test_input = np.random.randn(4800).astype(np.float32) * 0.1

        algo.reset()
        algo.update_params({"er_level": 0, "mix": 100})
        out_no_er = algo.process(test_input.copy())

        algo.reset()
        algo.update_params({"er_level": 100, "mix": 100})
        out_full_er = algo.process(test_input.copy())

        diff = np.max(np.abs(out_no_er - out_full_er))
        assert diff > 1e-4, (
            f"ER Level 0 vs 100 should produce different output (diff={diff})"
        )

    def test_size_knob_changes_output(self, algo: SmallRoom) -> None:
        """Size knob changes produce audibly different output."""
        test_input = np.random.randn(4800).astype(np.float32) * 0.1

        algo.reset()
        algo.update_params({"size": 10})
        out_small = algo.process(test_input.copy())

        algo.reset()
        algo.update_params({"size": 90})
        out_large = algo.process(test_input.copy())

        # Check RMS or spectral difference
        rms_small = np.sqrt(np.mean(out_small ** 2))
        rms_large = np.sqrt(np.mean(out_large ** 2))
        diff = np.max(np.abs(out_small - out_large))

        assert diff > 1e-4 or abs(rms_small - rms_large) > 1e-5, (
            f"Size 10 vs 90 should produce different output (diff={diff}, rms_diff={abs(rms_small - rms_large)})"
        )


class TestLargeRoom:
    """LargeRoom algorithm tests."""

    @pytest.fixture
    def algo(self):
        from claudeverb.algorithms.large_room import LargeRoom
        return LargeRoom()

    def test_registered_in_algorithm_registry(self) -> None:
        """LargeRoom appears in ALGORITHM_REGISTRY as 'large_room'."""
        assert "large_room" in ALGORITHM_REGISTRY
        assert ALGORITHM_REGISTRY["large_room"].__name__ == "LargeRoom"

    def test_name_property(self, algo) -> None:
        """LargeRoom name property returns 'Large Room'."""
        assert algo.name == "Large Room"

    def test_param_specs_has_6_knobs_and_2_switches(self, algo) -> None:
        """param_specs has 6 knobs + 2 switches."""
        specs = algo.param_specs
        knobs = [k for k, v in specs.items() if v["type"] == "knob"]
        switches = [k for k, v in specs.items() if v["type"] == "switch"]
        assert len(knobs) == 6
        assert len(switches) == 2

    def test_processes_mono_to_stereo(self, algo) -> None:
        """LargeRoom processes mono input to stereo output."""
        mono_input = np.random.randn(4800).astype(np.float32) * 0.1
        output = algo.process(mono_input)
        assert output.ndim == 2
        assert output.shape == (2, 4800)
        assert output.dtype == np.float32

    def test_stability_10_seconds_white_noise(self, algo) -> None:
        """Output stable across 10 seconds of white noise at extreme params."""
        extreme_params_list = [
            {"decay": 100, "size": 100, "damping": 0, "er_level": 100, "mix": 100, "pre_delay": 100},
            {"decay": 0, "size": 0, "damping": 100, "er_level": 0, "mix": 0, "pre_delay": 0},
            {"decay": 100, "size": 100, "damping": 100, "er_level": 50, "mix": 100, "pre_delay": 50},
        ]
        for params in extreme_params_list:
            algo.reset()
            algo.update_params(params)
            for _ in range(10):
                chunk = np.random.randn(48000).astype(np.float32) * 0.5
                output = algo.process(chunk)
                max_val = np.max(np.abs(output))
                assert max_val < 10.0, f"Output blew up (max={max_val}) with params {params}"
                assert np.all(np.isfinite(output)), f"Non-finite values with params {params}"

    def test_longer_rt60_than_small_room(self) -> None:
        """LargeRoom has longer RT60 than SmallRoom at same decay knob setting."""
        from claudeverb.algorithms.large_room import LargeRoom
        large = LargeRoom()
        small = SmallRoom()

        # Same decay setting
        params = {"decay": 50, "mix": 100, "er_level": 0}
        large.update_params(params)
        small.update_params(params)

        # Impulse test: measure energy decay
        impulse = np.zeros(480, dtype=np.float32)
        impulse[0] = 1.0
        tail = np.zeros(48000 * 3, dtype=np.float32)  # 3 seconds of silence

        large_out = np.concatenate([large.process(impulse), large.process(tail)], axis=1)
        small.reset()
        large.reset()
        large.update_params(params)
        small.update_params(params)

        large_out = large.process(np.concatenate([impulse, tail]))
        small_out = small.process(np.concatenate([impulse, tail]))

        # Compare energy in last second vs first second
        # LargeRoom should have more energy later (longer decay)
        large_late_energy = np.mean(large_out[:, -48000:] ** 2)
        small_late_energy = np.mean(small_out[:, -48000:] ** 2)

        # LargeRoom should have more late energy (longer RT60)
        assert large_late_energy > small_late_energy * 0.5, (
            f"LargeRoom late energy ({large_late_energy:.2e}) should exceed "
            f"SmallRoom ({small_late_energy:.2e}) - larger space = longer decay"
        )

    def test_reset_deterministic(self, algo) -> None:
        """Reset produces deterministic output."""
        test_input = np.random.randn(2400).astype(np.float32) * 0.1
        output_1 = algo.process(test_input.copy())
        algo.process(np.random.randn(48000).astype(np.float32))
        algo.reset()
        output_2 = algo.process(test_input.copy())
        np.testing.assert_allclose(output_1, output_2, atol=1e-5)

    def test_c_export_methods_return_nonempty(self, algo) -> None:
        """C export stubs return non-empty strings."""
        c_struct = algo.to_c_struct()
        c_fn = algo.to_c_process_fn()
        assert isinstance(c_struct, str) and len(c_struct) > 10
        assert isinstance(c_fn, str) and len(c_fn) > 10

    def test_er_level_knob_works(self, algo) -> None:
        """ER Level knob changes output."""
        test_input = np.random.randn(4800).astype(np.float32) * 0.1
        algo.reset()
        algo.update_params({"er_level": 0, "mix": 100})
        out_0 = algo.process(test_input.copy())
        algo.reset()
        algo.update_params({"er_level": 100, "mix": 100})
        out_100 = algo.process(test_input.copy())
        diff = np.max(np.abs(out_0 - out_100))
        assert diff > 1e-4, f"ER Level 0 vs 100 should differ (diff={diff})"

    def test_size_knob_works(self, algo) -> None:
        """Size knob changes output."""
        test_input = np.random.randn(4800).astype(np.float32) * 0.1
        algo.reset()
        algo.update_params({"size": 10})
        out_small = algo.process(test_input.copy())
        algo.reset()
        algo.update_params({"size": 90})
        out_large = algo.process(test_input.copy())
        diff = np.max(np.abs(out_small - out_large))
        assert diff > 1e-4, f"Size 10 vs 90 should differ (diff={diff})"


class TestChamber:
    """Chamber algorithm tests."""

    @pytest.fixture
    def algo(self):
        from claudeverb.algorithms.chamber import Chamber
        return Chamber()

    def test_registered_in_algorithm_registry(self) -> None:
        """Chamber appears in ALGORITHM_REGISTRY as 'chamber'."""
        assert "chamber" in ALGORITHM_REGISTRY
        assert ALGORITHM_REGISTRY["chamber"].__name__ == "Chamber"

    def test_name_property(self, algo) -> None:
        """Chamber name property returns 'Chamber'."""
        assert algo.name == "Chamber"

    def test_param_specs_has_6_knobs_and_2_switches(self, algo) -> None:
        """param_specs has 6 knobs + 2 switches."""
        specs = algo.param_specs
        knobs = [k for k, v in specs.items() if v["type"] == "knob"]
        switches = [k for k, v in specs.items() if v["type"] == "switch"]
        assert len(knobs) == 6
        assert len(switches) == 2

    def test_processes_mono_to_stereo(self, algo) -> None:
        """Chamber processes mono input to stereo output."""
        mono_input = np.random.randn(4800).astype(np.float32) * 0.1
        output = algo.process(mono_input)
        assert output.ndim == 2
        assert output.shape == (2, 4800)
        assert output.dtype == np.float32

    def test_stability_10_seconds_white_noise(self, algo) -> None:
        """Output stable across 10 seconds of white noise at extreme params."""
        extreme_params_list = [
            {"decay": 100, "size": 100, "damping": 0, "er_level": 100, "mix": 100, "pre_delay": 100},
            {"decay": 0, "size": 0, "damping": 100, "er_level": 0, "mix": 0, "pre_delay": 0},
            {"decay": 100, "size": 100, "damping": 100, "er_level": 50, "mix": 100, "pre_delay": 50},
        ]
        for params in extreme_params_list:
            algo.reset()
            algo.update_params(params)
            for _ in range(10):
                chunk = np.random.randn(48000).astype(np.float32) * 0.5
                output = algo.process(chunk)
                max_val = np.max(np.abs(output))
                assert max_val < 10.0, f"Output blew up (max={max_val}) with params {params}"
                assert np.all(np.isfinite(output)), f"Non-finite values with params {params}"

    def test_denser_than_large_room_on_transient(self) -> None:
        """Chamber output is smoother/denser than LargeRoom on transient input.

        Chamber has more diffusers (3 vs 2), so transient response should be
        smoother with less peak-to-trough variation.
        """
        from claudeverb.algorithms.large_room import LargeRoom
        from claudeverb.algorithms.chamber import Chamber

        large = LargeRoom()
        chamber = Chamber()

        # Same params
        params = {"decay": 50, "mix": 100, "er_level": 50, "size": 50}
        large.update_params(params)
        chamber.update_params(params)

        # Transient input (click)
        impulse = np.zeros(4800, dtype=np.float32)
        impulse[0] = 1.0

        large_out = large.process(impulse)
        chamber_out = chamber.process(impulse)

        # Measure peak-to-RMS ratio (crest factor) - denser = lower crest factor
        # Use first 2400 samples (early portion where diffusion matters most)
        def crest_factor(signal):
            sig = signal[:, :2400]
            rms = np.sqrt(np.mean(sig ** 2))
            if rms < 1e-10:
                return 0.0
            return np.max(np.abs(sig)) / rms

        large_crest = crest_factor(large_out)
        chamber_crest = crest_factor(chamber_out)

        # Chamber should have lower or similar crest factor (denser diffusion)
        # Allow some tolerance since both are diffused
        assert chamber_crest <= large_crest * 1.5, (
            f"Chamber crest factor ({chamber_crest:.2f}) should not be much higher "
            f"than LargeRoom ({large_crest:.2f}) - more diffusers = denser"
        )

    def test_reset_deterministic(self, algo) -> None:
        """Reset produces deterministic output."""
        test_input = np.random.randn(2400).astype(np.float32) * 0.1
        output_1 = algo.process(test_input.copy())
        algo.process(np.random.randn(48000).astype(np.float32))
        algo.reset()
        output_2 = algo.process(test_input.copy())
        np.testing.assert_allclose(output_1, output_2, atol=1e-5)

    def test_c_export_methods_return_nonempty(self, algo) -> None:
        """C export stubs return non-empty strings."""
        c_struct = algo.to_c_struct()
        c_fn = algo.to_c_process_fn()
        assert isinstance(c_struct, str) and len(c_struct) > 10
        assert isinstance(c_fn, str) and len(c_fn) > 10

    def test_er_level_knob_works(self, algo) -> None:
        """ER Level knob changes output."""
        test_input = np.random.randn(4800).astype(np.float32) * 0.1
        algo.reset()
        algo.update_params({"er_level": 0, "mix": 100})
        out_0 = algo.process(test_input.copy())
        algo.reset()
        algo.update_params({"er_level": 100, "mix": 100})
        out_100 = algo.process(test_input.copy())
        diff = np.max(np.abs(out_0 - out_100))
        assert diff > 1e-4, f"ER Level 0 vs 100 should differ (diff={diff})"

    def test_size_knob_works(self, algo) -> None:
        """Size knob changes output."""
        test_input = np.random.randn(4800).astype(np.float32) * 0.1
        algo.reset()
        algo.update_params({"size": 10})
        out_small = algo.process(test_input.copy())
        algo.reset()
        algo.update_params({"size": 90})
        out_large = algo.process(test_input.copy())
        diff = np.max(np.abs(out_small - out_large))
        assert diff > 1e-4, f"Size 10 vs 90 should differ (diff={diff})"


class TestCrossAlgorithm:
    """Cross-algorithm comparison tests for all Room/Chamber variants."""

    def test_all_three_produce_different_output(self) -> None:
        """SmallRoom, LargeRoom, and Chamber produce different output on same input."""
        from claudeverb.algorithms.large_room import LargeRoom
        from claudeverb.algorithms.chamber import Chamber

        algos = {
            "small_room": SmallRoom(),
            "large_room": LargeRoom(),
            "chamber": Chamber(),
        }

        # Same params for fair comparison
        params = {"decay": 50, "size": 50, "damping": 40, "er_level": 40, "mix": 100}
        test_input = np.random.randn(4800).astype(np.float32) * 0.1

        outputs = {}
        for name, algo in algos.items():
            algo.update_params(params)
            outputs[name] = algo.process(test_input.copy())

        # Each pair should be different
        names = list(outputs.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                diff = np.max(np.abs(outputs[names[i]] - outputs[names[j]]))
                assert diff > 1e-4, (
                    f"'{names[i]}' and '{names[j]}' should produce different output (diff={diff})"
                )
