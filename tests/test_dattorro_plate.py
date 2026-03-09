"""Tests for DattorroPlate reverb algorithm (ALG-02).

TDD RED phase: all tests written before implementation.
Covers ALG-02 subtests 1-14.
"""

import numpy as np
import pytest

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.config import SAMPLE_RATE


# ---------------------------------------------------------------------------
# ALG-02.1  Registry
# ---------------------------------------------------------------------------

def test_registry():
    """DattorroPlate appears in ALGORITHM_REGISTRY as 'dattorro_plate'."""
    assert "dattorro_plate" in ALGORITHM_REGISTRY
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    assert isinstance(plate, ReverbAlgorithm)


# ---------------------------------------------------------------------------
# ALG-02.2  Param specs
# ---------------------------------------------------------------------------

def test_param_specs():
    """param_specs returns 6 knobs and 2 switches with correct structure."""
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    specs = plate.param_specs

    knob_names = ["decay", "bandwidth", "tank_damping", "diffusion",
                  "pre_delay", "mod_depth"]
    for name in knob_names:
        assert name in specs, f"Missing knob: {name}"
        assert specs[name]["type"] == "knob"
        assert specs[name]["min"] == 0
        assert specs[name]["max"] == 100

    # Switch 1: Freeze/Normal/Shimmer
    assert "switch1" in specs
    assert specs["switch1"]["type"] == "switch"
    assert specs["switch1"]["labels"] == ["Freeze", "Normal", "Shimmer"]

    # Switch 2: Mono/Stereo/Wide
    assert "switch2" in specs
    assert specs["switch2"]["type"] == "switch"
    assert specs["switch2"]["labels"] == ["Mono", "Stereo", "Wide"]


# ---------------------------------------------------------------------------
# ALG-02.14  Delay scaling (29761 -> 48000)
# ---------------------------------------------------------------------------

def test_delay_scaling():
    """All delay lengths correctly scaled from 29761 Hz to 48 kHz."""
    from claudeverb.algorithms.dattorro_plate import DattorroPlate

    # Input AP lengths at 29761: [142, 107, 379, 277]
    # Expected at 48000: round(length * 48000 / 29761)
    expected = [229, 173, 611, 447]
    for orig, exp in zip([142, 107, 379, 277], expected):
        assert DattorroPlate._scale_length(orig) == exp


# ---------------------------------------------------------------------------
# ALG-02.3  Mono impulse -> stereo reverb tail
# ---------------------------------------------------------------------------

def test_process_mono_impulse():
    """Feed mono impulse, expect stereo (2, N) output with reverb tail."""
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    n = 48000
    impulse = np.zeros(n, dtype=np.float32)
    impulse[0] = 1.0

    output = plate.process(impulse)

    assert output.shape == (2, n)
    assert output.dtype == np.float32

    # Reverb tail: energy exists beyond first 1000 samples
    tail_energy = np.sum(output[:, 1000:] ** 2)
    assert tail_energy > 1e-6, "No reverb tail detected"


# ---------------------------------------------------------------------------
# ALG-02.4  Stereo processing
# ---------------------------------------------------------------------------

def test_process_stereo():
    """Feed stereo input, expect stereo output."""
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    n = 24000
    stereo_in = np.random.RandomState(42).randn(2, n).astype(np.float32) * 0.1

    output = plate.process(stereo_in)

    assert output.shape == (2, n)
    assert output.dtype == np.float32


# ---------------------------------------------------------------------------
# ALG-02.5  Extreme knobs stability
# ---------------------------------------------------------------------------

def test_extreme_knobs_stable():
    """All extreme knob positions produce stable output (no NaN/inf)."""
    knob_names = ["decay", "bandwidth", "tank_damping", "diffusion",
                  "pre_delay", "mod_depth"]

    impulse = np.zeros(48000, dtype=np.float32)
    impulse[0] = 1.0

    for knob in knob_names:
        for value in [0, 100]:
            plate = ALGORITHM_REGISTRY["dattorro_plate"]()
            plate.update_params({knob: value})
            output = plate.process(impulse)

            assert not np.any(np.isnan(output)), \
                f"NaN with {knob}={value}"
            assert not np.any(np.isinf(output)), \
                f"Inf with {knob}={value}"
            assert np.all(np.abs(output) <= 1.0), \
                f"Output exceeds [-1,1] with {knob}={value}"


# ---------------------------------------------------------------------------
# ALG-02.6  No DC offset at high decay
# ---------------------------------------------------------------------------

def test_no_dc_offset():
    """No DC offset accumulation at high decay values."""
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate.update_params({"decay": 95})

    n = 96000
    impulse = np.zeros(n, dtype=np.float32)
    impulse[0] = 1.0
    output = plate.process(impulse)

    # Mean of last 24000 samples of each channel should be near zero
    for ch in range(2):
        dc = abs(np.mean(output[ch, -24000:]))
        assert dc < 0.01, f"DC offset {dc:.4f} in channel {ch}"


# ---------------------------------------------------------------------------
# ALG-02.7  Freeze mode
# ---------------------------------------------------------------------------

def test_freeze_mode():
    """Freeze mode sustains reverb tail energy."""
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()

    # Process impulse in normal mode first
    impulse = np.zeros(12000, dtype=np.float32)
    impulse[0] = 1.0
    plate.process(impulse)

    # Switch to freeze mode
    plate.update_params({"switch1": -1})

    # Process more silence -- energy should be sustained
    silence = np.zeros(48000, dtype=np.float32)
    output = plate.process(silence)

    # Energy at end should still be significant (not decayed away)
    early_energy = np.sum(output[:, :12000] ** 2)
    late_energy = np.sum(output[:, -12000:] ** 2)
    assert late_energy > early_energy * 0.5, \
        f"Freeze not sustaining: early={early_energy:.6f}, late={late_energy:.6f}"


# ---------------------------------------------------------------------------
# ALG-02.8  Shimmer mode
# ---------------------------------------------------------------------------

def test_shimmer_mode():
    """Shimmer mode produces more high-frequency content than normal."""
    n = 96000  # 2 seconds to let shimmer build in feedback loop

    # Normal mode
    plate_normal = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate_normal.update_params({"decay": 85, "mod_depth": 0, "tank_damping": 0})
    impulse = np.zeros(n, dtype=np.float32)
    impulse[0] = 1.0
    out_normal = plate_normal.process(impulse)

    # Shimmer mode
    plate_shimmer = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate_shimmer.update_params({"decay": 85, "mod_depth": 0, "tank_damping": 0,
                                  "switch1": 1})
    out_shimmer = plate_shimmer.process(impulse.copy())

    # Compare high-frequency energy (upper quarter of spectrum)
    # Use the tail portion where shimmer has had time to build up
    for ch in range(2):
        tail_normal = out_normal[ch, n // 2:]
        tail_shimmer = out_shimmer[ch, n // 2:]
        fft_normal = np.abs(np.fft.rfft(tail_normal))
        fft_shimmer = np.abs(np.fft.rfft(tail_shimmer))
        quarter = len(fft_normal) * 3 // 4
        hf_normal = np.sum(fft_normal[quarter:])
        hf_shimmer = np.sum(fft_shimmer[quarter:])
        assert hf_shimmer > hf_normal, \
            f"Shimmer should have more HF energy (ch{ch}: normal={hf_normal:.4f}, shimmer={hf_shimmer:.4f})"


# ---------------------------------------------------------------------------
# ALG-02.9  Reset deterministic
# ---------------------------------------------------------------------------

def test_reset_deterministic():
    """Reset produces identical output on re-processing."""
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    impulse = np.zeros(24000, dtype=np.float32)
    impulse[0] = 1.0

    out1 = plate.process(impulse.copy())
    plate.reset()
    out2 = plate.process(impulse.copy())

    np.testing.assert_allclose(out1, out2, atol=1e-7,
                               err_msg="Reset did not produce identical output")


# ---------------------------------------------------------------------------
# ALG-02.10  Differs from Freeverb
# ---------------------------------------------------------------------------

def test_differs_from_freeverb():
    """DattorroPlate output differs from Freeverb (distinct character)."""
    from claudeverb.algorithms.freeverb import Freeverb

    impulse = np.zeros(24000, dtype=np.float32)
    impulse[0] = 1.0

    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    fv = Freeverb()

    out_plate = plate.process(impulse.copy())
    out_fv = fv.process(impulse.copy())

    # Freeverb returns mono for mono input; plate returns stereo
    # Compare left channel of plate to freeverb mono
    assert not np.allclose(out_plate[0], out_fv, atol=1e-5), \
        "DattorroPlate should differ from Freeverb"


# ---------------------------------------------------------------------------
# ALG-02.11  Modulation varies IR
# ---------------------------------------------------------------------------

def test_modulation_varies_ir():
    """Modulated output differs from static output (time-varying IR)."""
    # With modulation
    plate_mod = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate_mod.update_params({"mod_depth": 80})
    impulse = np.zeros(48000, dtype=np.float32)
    impulse[0] = 1.0
    out_mod = plate_mod.process(impulse.copy())

    # Without modulation
    plate_static = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate_static.update_params({"mod_depth": 0})
    out_static = plate_static.process(impulse.copy())

    assert not np.allclose(out_mod, out_static, atol=1e-5), \
        "Modulated output should differ from static output"


# ---------------------------------------------------------------------------
# ALG-02.12  Stereo modes (mono/stereo/wide)
# ---------------------------------------------------------------------------

def test_stereo_modes():
    """Mono/Stereo/Wide switch modes produce expected channel relationships."""
    impulse = np.zeros(24000, dtype=np.float32)
    impulse[0] = 1.0

    # Mono mode: left == right
    plate_mono = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate_mono.update_params({"switch2": -1})
    out_mono = plate_mono.process(impulse.copy())
    np.testing.assert_allclose(out_mono[0], out_mono[1], atol=1e-7,
                               err_msg="Mono mode: L and R should be identical")

    # Stereo mode: left != right
    plate_stereo = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate_stereo.update_params({"switch2": 0})
    out_stereo = plate_stereo.process(impulse.copy())
    assert not np.allclose(out_stereo[0], out_stereo[1], atol=1e-5), \
        "Stereo mode: L and R should differ"

    # Wide mode: left != right, more separation than stereo
    plate_wide = ALGORITHM_REGISTRY["dattorro_plate"]()
    plate_wide.update_params({"switch2": 1})
    out_wide = plate_wide.process(impulse.copy())
    assert not np.allclose(out_wide[0], out_wide[1], atol=1e-5), \
        "Wide mode: L and R should differ"

    # Wide should have more L-R difference than stereo
    diff_stereo = np.sum((out_stereo[0] - out_stereo[1]) ** 2)
    diff_wide = np.sum((out_wide[0] - out_wide[1]) ** 2)
    assert diff_wide > diff_stereo, \
        f"Wide should have more separation than stereo (stereo={diff_stereo:.6f}, wide={diff_wide:.6f})"


# ---------------------------------------------------------------------------
# ALG-02.13  Output clipping
# ---------------------------------------------------------------------------

def test_output_clipped():
    """Loud input is clipped to [-1.0, 1.0]."""
    plate = ALGORITHM_REGISTRY["dattorro_plate"]()
    loud = np.full(24000, 5.0, dtype=np.float32)
    output = plate.process(loud)

    assert np.all(output >= -1.0), "Output below -1.0"
    assert np.all(output <= 1.0), "Output above 1.0"


# ---------------------------------------------------------------------------
# Preset tests (06-02)
# ---------------------------------------------------------------------------

class TestPresets:
    """Tests for Dattorro presets module."""

    def test_all_presets_have_required_keys(self):
        """Every preset has all required param keys."""
        from claudeverb.algorithms.dattorro_presets import DATTORRO_PRESETS

        required_keys = {
            "decay", "bandwidth", "tank_damping", "diffusion",
            "pre_delay", "mod_depth", "switch1", "switch2",
        }
        for name, params in DATTORRO_PRESETS.items():
            assert set(params.keys()) == required_keys, \
                f"Preset '{name}' has wrong keys: {set(params.keys())}"

    def test_knob_values_in_range(self):
        """Every preset's knob values are in 0-100 range."""
        from claudeverb.algorithms.dattorro_presets import DATTORRO_PRESETS

        knob_keys = ["decay", "bandwidth", "tank_damping", "diffusion",
                     "pre_delay", "mod_depth"]
        for name, params in DATTORRO_PRESETS.items():
            for key in knob_keys:
                assert 0 <= params[key] <= 100, \
                    f"Preset '{name}' knob '{key}' = {params[key]} out of range"

    def test_switch_values_valid(self):
        """Every preset's switch values are in [-1, 0, 1]."""
        from claudeverb.algorithms.dattorro_presets import DATTORRO_PRESETS

        for name, params in DATTORRO_PRESETS.items():
            for sw in ["switch1", "switch2"]:
                assert params[sw] in (-1, 0, 1), \
                    f"Preset '{name}' {sw} = {params[sw]} invalid"

    def test_update_params_accepts_all_presets(self):
        """DattorroPlate().update_params(preset) succeeds for all presets."""
        from claudeverb.algorithms.dattorro_presets import DATTORRO_PRESETS
        from claudeverb.algorithms.dattorro_plate import DattorroPlate

        for name, params in DATTORRO_PRESETS.items():
            plate = DattorroPlate()
            plate.update_params(params)  # should not raise

    def test_list_presets_sorted(self):
        """list_presets() returns sorted list with >= 6 entries."""
        from claudeverb.algorithms.dattorro_presets import list_presets

        names = list_presets()
        assert len(names) >= 6
        assert names == sorted(names)

    def test_all_presets_distinct(self):
        """All presets have distinct parameter combinations."""
        from claudeverb.algorithms.dattorro_presets import DATTORRO_PRESETS

        seen = []
        for name, params in DATTORRO_PRESETS.items():
            frozen = tuple(sorted(params.items()))
            assert frozen not in seen, f"Preset '{name}' is a duplicate"
            seen.append(frozen)

    def test_get_preset_returns_copy(self):
        """get_preset() returns a copy, not a reference."""
        from claudeverb.algorithms.dattorro_presets import get_preset

        p1 = get_preset("Small Plate")
        p2 = get_preset("Small Plate")
        p1["decay"] = -999
        assert p2["decay"] != -999
