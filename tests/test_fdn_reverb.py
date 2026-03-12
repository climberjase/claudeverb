"""Tests for FDN (Feedback Delay Network) reverb algorithm.

Covers all 19 ALGO-01 subtests: registry, params, processing,
stability, composability, presets, and C export.
"""

import numpy as np
import pytest

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.algorithms.fdn_reverb import FDNCore, FDNReverb, hadamard_4


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mono_impulse():
    """24000-sample mono impulse (1.0 at sample 0, rest zeros)."""
    sig = np.zeros(24000, dtype=np.float32)
    sig[0] = 1.0
    return sig


@pytest.fixture
def fdn_default():
    """FDNReverb with default parameters."""
    return FDNReverb()


# ---------------------------------------------------------------------------
# 1. Registry
# ---------------------------------------------------------------------------

def test_registry():
    """'fdn' key exists in ALGORITHM_REGISTRY, maps to FDNReverb."""
    assert "fdn" in ALGORITHM_REGISTRY
    assert ALGORITHM_REGISTRY["fdn"] is FDNReverb


# ---------------------------------------------------------------------------
# 2. Parameter specs
# ---------------------------------------------------------------------------

def test_param_specs(fdn_default):
    """param_specs returns dict with 6 knobs and 2 switches."""
    specs = fdn_default.param_specs
    knob_names = ["decay_time", "size", "damping", "modulation", "mix", "pre_delay"]
    switch_names = ["switch1", "switch2"]

    for name in knob_names:
        assert name in specs, f"Missing knob: {name}"
        assert specs[name]["type"] == "knob"
        assert specs[name]["min"] == 0
        assert specs[name]["max"] == 100

    for name in switch_names:
        assert name in specs, f"Missing switch: {name}"
        assert specs[name]["type"] == "switch"
        assert specs[name]["positions"] == [-1, 0, 1]


# ---------------------------------------------------------------------------
# 3. Mono impulse processing
# ---------------------------------------------------------------------------

def test_process_mono_impulse(fdn_default, mono_impulse):
    """Mono impulse -> stereo output with reverb tail."""
    output = fdn_default.process(mono_impulse)
    assert output.shape == (2, 24000)
    assert output.dtype == np.float32
    # Reverb tail should have energy beyond sample 100
    tail_energy = np.sum(output[:, 100:] ** 2)
    assert tail_energy > 0.0, "No reverb tail energy detected"


# ---------------------------------------------------------------------------
# 4. Stereo processing
# ---------------------------------------------------------------------------

def test_process_stereo(fdn_default):
    """Stereo input -> stereo output, correct shape and dtype."""
    stereo_in = np.random.randn(2, 24000).astype(np.float32) * 0.1
    output = fdn_default.process(stereo_in)
    assert output.shape == (2, 24000)
    assert output.dtype == np.float32


# ---------------------------------------------------------------------------
# 5. Extreme knob stability
# ---------------------------------------------------------------------------

def test_extreme_knobs_stable():
    """All extreme knob combinations produce stable output (no NaN/inf)."""
    extreme_combos = [
        # All zeros
        {"decay_time": 0, "size": 0, "damping": 0, "modulation": 0, "mix": 0, "pre_delay": 0, "switch1": -1, "switch2": -1},
        # All max
        {"decay_time": 100, "size": 100, "damping": 100, "modulation": 100, "mix": 100, "pre_delay": 100, "switch1": 1, "switch2": 1},
        # Dangerous combo: max decay + no damping
        {"decay_time": 100, "size": 50, "damping": 0, "modulation": 0, "mix": 100, "pre_delay": 0, "switch1": 0, "switch2": 0},
        # Max modulation
        {"decay_time": 50, "size": 50, "damping": 50, "modulation": 100, "mix": 100, "pre_delay": 0, "switch1": 0, "switch2": 0},
        # Min size
        {"decay_time": 80, "size": 0, "damping": 50, "modulation": 50, "mix": 50, "pre_delay": 50, "switch1": 0, "switch2": 0},
        # Max size
        {"decay_time": 80, "size": 100, "damping": 50, "modulation": 50, "mix": 50, "pre_delay": 50, "switch1": 0, "switch2": 0},
        # Freeze + max everything
        {"decay_time": 100, "size": 100, "damping": 100, "modulation": 100, "mix": 100, "pre_delay": 100, "switch1": -1, "switch2": 1},
        # Mixed extremes
        {"decay_time": 0, "size": 100, "damping": 100, "modulation": 0, "mix": 0, "pre_delay": 100, "switch1": 1, "switch2": -1},
    ]

    impulse = np.zeros(48000, dtype=np.float32)
    impulse[0] = 1.0

    for i, params in enumerate(extreme_combos):
        fdn = FDNReverb()
        fdn.update_params(params)
        output = fdn.process(impulse)
        assert not np.any(np.isnan(output)), f"NaN in combo {i}: {params}"
        assert not np.any(np.isinf(output)), f"Inf in combo {i}: {params}"
        assert np.all(np.abs(output) <= 1.0), f"Clipping in combo {i}: {params}"


# ---------------------------------------------------------------------------
# 6. No DC offset
# ---------------------------------------------------------------------------

def test_no_dc_offset(fdn_default, mono_impulse):
    """High-decay impulse response has no significant DC offset in tail."""
    fdn_default.update_params({"decay_time": 95})
    # Use a longer signal to get a proper tail
    long_impulse = np.zeros(48000, dtype=np.float32)
    long_impulse[0] = 1.0
    output = fdn_default.process(long_impulse)
    # Check last half for DC offset
    dc_offset = np.abs(np.mean(output[:, -24000:]))
    assert dc_offset < 0.01, f"DC offset too high: {dc_offset}"


# ---------------------------------------------------------------------------
# 7. Freeze mode
# ---------------------------------------------------------------------------

def test_freeze_mode():
    """Freeze mode sustains energy indefinitely."""
    fdn = FDNReverb()
    # Process impulse
    impulse = np.zeros(4800, dtype=np.float32)
    impulse[0] = 1.0
    fdn.process(impulse)

    # Measure energy right after impulse
    silence_start = np.zeros(4800, dtype=np.float32)
    out_start = fdn.process(silence_start)
    energy_start = np.sum(out_start ** 2)

    # Enable freeze
    fdn.update_params({"switch1": -1})

    # Process more silence
    silence_long = np.zeros(48000, dtype=np.float32)
    out_long = fdn.process(silence_long)

    # Measure energy at the tail end
    tail_energy = np.sum(out_long[:, -4800:] ** 2)

    assert tail_energy > 0.5 * energy_start, (
        f"Freeze mode energy decayed too much: tail={tail_energy:.6f}, "
        f"start={energy_start:.6f}"
    )


# ---------------------------------------------------------------------------
# 8. Reset determinism
# ---------------------------------------------------------------------------

def test_reset_deterministic(fdn_default, mono_impulse):
    """After reset, same input produces identical output."""
    out1 = fdn_default.process(mono_impulse.copy())
    fdn_default.reset()
    out2 = fdn_default.process(mono_impulse.copy())
    np.testing.assert_allclose(out1, out2, atol=1e-7)


# ---------------------------------------------------------------------------
# 9. Differs from Freeverb
# ---------------------------------------------------------------------------

def test_differs_from_freeverb(mono_impulse):
    """FDN output differs from Freeverb output."""
    from claudeverb.algorithms.freeverb import Freeverb

    fdn = FDNReverb()
    fv = Freeverb()

    out_fdn = fdn.process(mono_impulse.copy())
    out_fv = fv.process(mono_impulse.copy())

    # Shapes may differ; compare only overlapping region
    min_ch = min(out_fdn.shape[0], out_fv.shape[0])
    min_len = min(out_fdn.shape[-1], out_fv.shape[-1])
    assert not np.allclose(out_fdn[:min_ch, :min_len], out_fv[:min_ch, :min_len], atol=1e-5)


# ---------------------------------------------------------------------------
# 10. Differs from Dattorro
# ---------------------------------------------------------------------------

def test_differs_from_dattorro(mono_impulse):
    """FDN output differs from Dattorro Plate output."""
    from claudeverb.algorithms.dattorro_plate import DattorroPlate

    fdn = FDNReverb()
    dp = DattorroPlate()

    out_fdn = fdn.process(mono_impulse.copy())
    out_dp = dp.process(mono_impulse.copy())

    min_len = min(out_fdn.shape[-1], out_dp.shape[-1])
    assert not np.allclose(out_fdn[:, :min_len], out_dp[:, :min_len], atol=1e-5)


# ---------------------------------------------------------------------------
# 11. Modulation varies IR
# ---------------------------------------------------------------------------

def test_modulation_varies_ir(mono_impulse):
    """Modulation changes the impulse response."""
    fdn_dry = FDNReverb()
    fdn_dry.update_params({"modulation": 0})
    out_dry = fdn_dry.process(mono_impulse.copy())

    fdn_wet = FDNReverb()
    fdn_wet.update_params({"modulation": 80})
    out_wet = fdn_wet.process(mono_impulse.copy())

    assert not np.allclose(out_dry, out_wet, atol=1e-5)


# ---------------------------------------------------------------------------
# 12. Stereo modes
# ---------------------------------------------------------------------------

def test_stereo_modes(mono_impulse):
    """Mono/stereo/wide modes produce correct stereo behavior."""
    # Mono mode: L == R
    fdn_mono = FDNReverb()
    fdn_mono.update_params({"switch2": -1})
    out_mono = fdn_mono.process(mono_impulse.copy())
    np.testing.assert_allclose(out_mono[0], out_mono[1], atol=1e-7,
                               err_msg="Mono mode: L and R should be identical")

    # Stereo mode: L != R
    fdn_stereo = FDNReverb()
    fdn_stereo.update_params({"switch2": 0})
    out_stereo = fdn_stereo.process(mono_impulse.copy())
    assert not np.allclose(out_stereo[0], out_stereo[1], atol=1e-5), \
        "Stereo mode: L and R should differ"

    # Wide mode: L != R and wider spread than stereo
    fdn_wide = FDNReverb()
    fdn_wide.update_params({"switch2": 1})
    out_wide = fdn_wide.process(mono_impulse.copy())
    assert not np.allclose(out_wide[0], out_wide[1], atol=1e-5), \
        "Wide mode: L and R should differ"

    # Wide should have greater L-R difference than stereo
    diff_stereo = np.sum((out_stereo[0] - out_stereo[1]) ** 2)
    diff_wide = np.sum((out_wide[0] - out_wide[1]) ** 2)
    assert diff_wide > diff_stereo, \
        f"Wide spread ({diff_wide}) should exceed stereo spread ({diff_stereo})"


# ---------------------------------------------------------------------------
# 13. Output clipped
# ---------------------------------------------------------------------------

def test_output_clipped():
    """Hot signal output stays within [-1, 1]."""
    fdn = FDNReverb()
    hot = np.ones(24000, dtype=np.float32) * 0.9
    output = fdn.process(hot)
    assert np.all(output >= -1.0) and np.all(output <= 1.0), \
        "Output exceeds [-1, 1] range"


# ---------------------------------------------------------------------------
# 14. Hadamard butterfly
# ---------------------------------------------------------------------------

def test_hadamard_butterfly():
    """Hadamard H4 butterfly produces correct results."""
    # Unit vector -> equal distribution
    result = hadamard_4(1.0, 0.0, 0.0, 0.0)
    np.testing.assert_allclose(result, (0.5, 0.5, 0.5, 0.5), atol=1e-7)

    # All ones -> energy concentrated in channel 0
    result = hadamard_4(1.0, 1.0, 1.0, 1.0)
    np.testing.assert_allclose(result, (2.0, 0.0, 0.0, 0.0), atol=1e-7)

    # Zero input -> zero output
    result = hadamard_4(0.0, 0.0, 0.0, 0.0)
    np.testing.assert_allclose(result, (0.0, 0.0, 0.0, 0.0), atol=1e-7)

    # Self-inverse: hadamard_4(hadamard_4(a,b,c,d)) == (a,b,c,d)
    a, b, c, d = 0.3, -0.7, 0.5, 1.2
    intermediate = hadamard_4(a, b, c, d)
    roundtrip = hadamard_4(*intermediate)
    np.testing.assert_allclose(roundtrip, (a, b, c, d), atol=1e-6)


# ---------------------------------------------------------------------------
# 15. Size changes delays
# ---------------------------------------------------------------------------

def test_size_changes_delays(mono_impulse):
    """Different size values produce different outputs."""
    fdn_small = FDNReverb()
    fdn_small.update_params({"size": 20})
    out_small = fdn_small.process(mono_impulse.copy())

    fdn_large = FDNReverb()
    fdn_large.update_params({"size": 80})
    out_large = fdn_large.process(mono_impulse.copy())

    assert not np.allclose(out_small, out_large, atol=1e-5)


# ---------------------------------------------------------------------------
# 16. All knobs audible
# ---------------------------------------------------------------------------

def test_all_knobs_audible(mono_impulse):
    """Each knob produces audible difference between low and high settings."""
    knobs = ["decay_time", "size", "damping", "modulation", "mix", "pre_delay"]

    for knob in knobs:
        fdn_low = FDNReverb()
        fdn_low.update_params({knob: 10})
        out_low = fdn_low.process(mono_impulse.copy())

        fdn_high = FDNReverb()
        fdn_high.update_params({knob: 90})
        out_high = fdn_high.process(mono_impulse.copy())

        rms_diff = np.sqrt(np.mean((out_low - out_high) ** 2))
        assert rms_diff > 0.001, f"Knob '{knob}' not audible: RMS diff = {rms_diff}"


# ---------------------------------------------------------------------------
# 17. FDNCore composable
# ---------------------------------------------------------------------------

def test_fdn_core_composable():
    """FDNCore can be used independently of FDNReverb."""
    core = FDNCore()
    result = core.process_sample([0.5, 0.5, 0.5, 0.5])
    assert isinstance(result, list)
    assert len(result) == 4
    assert all(isinstance(v, float) for v in result)


# ---------------------------------------------------------------------------
# 18. Presets
# ---------------------------------------------------------------------------

def test_presets():
    """Each FDN preset loads and produces stable output."""
    from claudeverb.algorithms.fdn_presets import FDN_PRESETS, get_preset

    for name in FDN_PRESETS:
        preset = get_preset(name)
        fdn = FDNReverb()
        fdn.update_params(preset)
        impulse = np.zeros(4800, dtype=np.float32)
        impulse[0] = 1.0
        output = fdn.process(impulse)
        assert not np.any(np.isnan(output)), f"Preset '{name}' produced NaN"
        assert not np.any(np.isinf(output)), f"Preset '{name}' produced Inf"


# ---------------------------------------------------------------------------
# 19. C export
# ---------------------------------------------------------------------------

def test_c_export(fdn_default):
    """to_c_struct() and to_c_process_fn() return valid C code strings."""
    c_struct = fdn_default.to_c_struct()
    assert isinstance(c_struct, str)
    assert "typedef struct" in c_struct

    c_process = fdn_default.to_c_process_fn()
    assert isinstance(c_process, str)
    assert "void" in c_process
