"""Tests for Freeverb algorithm implementation."""

import numpy as np
import pytest

from claudeverb.config import SAMPLE_RATE


def test_instantiation():
    """Freeverb instantiates without error."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()
    assert fv is not None


def test_param_specs():
    """param_specs returns dict with 6 knobs and 2 switches."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()
    specs = fv.param_specs

    knob_names = ["room_size", "damping", "mix", "width", "pre_delay", "hf_damp"]
    switch_names = ["switch1", "switch2"]

    for name in knob_names:
        assert name in specs, f"Missing knob: {name}"
        assert specs[name]["type"] == "knob"
        assert specs[name]["min"] == 0
        assert specs[name]["max"] == 100
        assert "default" in specs[name]

    for name in switch_names:
        assert name in specs, f"Missing switch: {name}"
        assert specs[name]["type"] == "switch"
        assert specs[name]["positions"] == [-1, 0, 1]
        assert specs[name]["default"] == 0


def test_delay_scaling():
    """Verify delay lengths are scaled from 44100 to 48000 Hz."""
    from claudeverb.algorithms.freeverb import Freeverb

    # Expected scaled values: round(length * 48000 / 44100)
    expected_comb = [1694, 1760, 1623, 1548, 1476, 1390, 1293, 1215]
    expected_allpass = [245, 605, 480, 371]
    expected_spread = 25

    for i, expected in enumerate(expected_comb):
        scaled = round(Freeverb.COMB_LENGTHS_44100[i] * SAMPLE_RATE / 44100)
        assert scaled == expected, f"Comb {i}: {scaled} != {expected}"

    for i, expected in enumerate(expected_allpass):
        scaled = round(Freeverb.ALLPASS_LENGTHS_44100[i] * SAMPLE_RATE / 44100)
        assert scaled == expected, f"Allpass {i}: {scaled} != {expected}"

    scaled_spread = round(Freeverb.STEREO_SPREAD_44100 * SAMPLE_RATE / 44100)
    assert scaled_spread == expected_spread


def test_process_mono_impulse(impulse):
    """Process mono impulse, verify output is float32 with reverb tail."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()
    output = fv.process(impulse)

    assert output.dtype == np.float32
    assert output.shape == impulse.shape
    # Should have nonzero values beyond sample 0 (reverb tail)
    assert np.any(output[100:] != 0.0), "Expected reverb tail beyond sample 100"


def test_process_stereo_impulse():
    """Process stereo impulse, verify shape (2, N) float32."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()

    n = SAMPLE_RATE
    stereo_impulse = np.zeros((2, n), dtype=np.float32)
    stereo_impulse[0, 0] = 1.0
    stereo_impulse[1, 0] = 1.0

    output = fv.process(stereo_impulse)
    assert output.dtype == np.float32
    assert output.shape == (2, n)


def test_output_clipped(impulse):
    """Process impulse at default settings, verify all values in [-1, 1]."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()
    output = fv.process(impulse)
    assert np.all(output >= -1.0)
    assert np.all(output <= 1.0)


def test_reset_produces_identical_output(impulse):
    """Process, reset, process again -- output must match."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()

    out1 = fv.process(impulse.copy())
    fv.reset()
    out2 = fv.process(impulse.copy())

    np.testing.assert_array_equal(out1, out2)


def test_update_params_changes_output(impulse):
    """Process with default, then update room_size, process again -- outputs differ."""
    from claudeverb.algorithms.freeverb import Freeverb

    fv = Freeverb()
    out1 = fv.process(impulse.copy())
    fv.reset()
    fv.update_params({"room_size": 50})
    out2 = fv.process(impulse.copy())

    assert not np.array_equal(out1, out2), "Output should change with different room_size"


def test_extreme_knobs_stable(impulse):
    """Set each knob to 0 and 100, process, verify no NaN/inf."""
    from claudeverb.algorithms.freeverb import Freeverb

    knobs = ["room_size", "damping", "mix", "width", "pre_delay", "hf_damp"]

    for knob in knobs:
        for value in [0, 100]:
            fv = Freeverb()
            fv.update_params({knob: value})
            output = fv.process(impulse.copy())
            assert np.all(np.isfinite(output)), (
                f"NaN/inf with {knob}={value}"
            )


def test_freeze_mode(impulse):
    """Freeze mode (switch1=-1): output sustains energy from prior input."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()

    # First, feed some signal to fill the reverb
    fv.process(impulse.copy())

    # Now engage freeze and process silence
    fv.update_params({"switch1": -1})
    silence = np.zeros(SAMPLE_RATE, dtype=np.float32)
    output = fv.process(silence)

    # Frozen reverb should have nonzero energy
    energy = np.sum(output ** 2)
    assert energy > 0.0, "Freeze mode should sustain reverb tail"


def test_stereo_mode_mono():
    """Set switch2=-1, process stereo -- L and R channels identical."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()
    fv.update_params({"switch2": -1})

    n = SAMPLE_RATE
    stereo_impulse = np.zeros((2, n), dtype=np.float32)
    stereo_impulse[0, 0] = 1.0
    stereo_impulse[1, 0] = 1.0

    output = fv.process(stereo_impulse)
    np.testing.assert_array_equal(output[0], output[1])


def test_stereo_mode_wide():
    """Set switch2=1, process stereo -- L/R differ more than default width."""
    from claudeverb.algorithms.freeverb import Freeverb

    n = SAMPLE_RATE
    stereo_impulse = np.zeros((2, n), dtype=np.float32)
    stereo_impulse[0, 0] = 1.0
    stereo_impulse[1, 0] = 1.0

    # Default stereo
    fv_default = Freeverb()
    out_default = fv_default.process(stereo_impulse.copy())
    diff_default = np.sum((out_default[0] - out_default[1]) ** 2)

    # Wide stereo
    fv_wide = Freeverb()
    fv_wide.update_params({"switch2": 1})
    out_wide = fv_wide.process(stereo_impulse.copy())
    diff_wide = np.sum((out_wide[0] - out_wide[1]) ** 2)

    assert diff_wide > diff_default, "Wide mode should have more L/R difference"


def test_mix_knob_dry(impulse):
    """Set mix=0, verify output equals input (fully dry)."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()
    fv.update_params({"mix": 0})
    output = fv.process(impulse.copy())
    np.testing.assert_allclose(output, impulse, atol=1e-6)


def test_mix_knob_wet(impulse):
    """Set mix=100, verify output differs from input (fully wet)."""
    from claudeverb.algorithms.freeverb import Freeverb
    fv = Freeverb()
    fv.update_params({"mix": 100})
    output = fv.process(impulse.copy())
    assert not np.allclose(output, impulse), "Fully wet output should differ from input"
