"""Tests for Room/Chamber reverb algorithms.

TestSmallRoom: Full test suite for SmallRoom algorithm.
TestLargeRoom/TestChamber: Scaffolds for Plan 03.
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


@pytest.mark.skip(reason="LargeRoom not yet implemented (Plan 03)")
class TestLargeRoom:
    """LargeRoom algorithm test scaffold for Plan 03."""

    def test_registered_in_algorithm_registry(self) -> None:
        pass

    def test_param_specs(self) -> None:
        pass

    def test_processes_mono_to_stereo(self) -> None:
        pass

    def test_stability(self) -> None:
        pass

    def test_presets(self) -> None:
        pass


@pytest.mark.skip(reason="Chamber not yet implemented (Plan 03)")
class TestChamber:
    """Chamber algorithm test scaffold for Plan 03."""

    def test_registered_in_algorithm_registry(self) -> None:
        pass

    def test_param_specs(self) -> None:
        pass

    def test_processes_mono_to_stereo(self) -> None:
        pass

    def test_stability(self) -> None:
        pass

    def test_presets(self) -> None:
        pass
