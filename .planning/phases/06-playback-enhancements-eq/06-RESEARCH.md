# Phase 6: Playback Enhancements & EQ - Research

**Researched:** 2026-03-08
**Domain:** Audio playback UX, biquad shelving EQ, Dattorro preset system, Streamlit session state
**Confidence:** HIGH

## Summary

Phase 6 adds five distinct features to the existing Streamlit-based ClaudeVerb workbench: multi-file loading from `/samples`, loop/single-shot toggle, silence padding for reverb tail preservation, 3-band post-reverb EQ, and Dattorro parameter presets. All features build on well-understood existing code patterns -- the engine facade, session state management, Biquad filter primitives, and the DattorroPlate `update_params()` interface.

The main technical gap is that the Biquad class currently lacks shelving filter factory methods (`low_shelf`, `high_shelf`). The existing Biquad uses Bristow-Johnson cookbook formulas for lowpass/highpass/parametric/notch/bandpass, but shelf filters require distinct coefficient formulas that must be added. This is straightforward -- same pattern as existing factory methods, different math.

**Primary recommendation:** Add `low_shelf` and `high_shelf` classmethods to the existing Biquad class, wire a 3-band EQ chain into `engine.process_audio()` between algorithm output and return, and keep all new UI controls in the Streamlit sidebar following established patterns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Silence padding: slider 0-5 seconds, on by default at 2 seconds, appended to input before processing, padded region visually marked in output waveform
- EQ: checkbox toggle, 3-band (low shelf, mid parametric, high shelf), applies to wet signal only before wet/dry mix, dry signal untouched
- Dattorro presets: dropdown below algorithm dropdown, only visible when Dattorro Plate selected, knobs snap to preset values, label changes to "Custom" on manual tweak
- Multi-file: load from /samples, switch between them
- Loop toggle: controls Streamlit st.audio loop parameter

### Claude's Discretion
- Silence padding placement in sidebar (near audio source vs near Process button)
- Default EQ frequencies, gain range (dB), and whether mid Q is adjustable or fixed
- Number and naming of Dattorro presets (aim for distinct reverb characters)
- Multi-file switching UX pattern (selectbox vs tabs vs file manager)
- Whether to cache processed results per file or reprocess on switch
- Whether uploaded files merge into the same file list as bundled samples
- Loop toggle placement (sidebar checkbox vs per-player control)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PLAY-01 | User can load multiple WAV files (4-5) from /samples and switch between them | WAV files exist in `claudeverb/samples/` (4 files). Extend `list_samples()`/`get_sample()` or add parallel WAV discovery. Use `audio/io.py:load()` for WAV loading. |
| PLAY-02 | User can toggle loop or single-shot playback per clip | Streamlit 1.55.0 `st.audio()` supports `loop=True/False` parameter. Wire to session state checkbox. |
| PLAY-03 | User can append configurable silence to input for reverb tail preservation | `np.zeros()` append before `engine.process_audio()`. Slider 0-5s at 48kHz = 0-240000 samples. |
| EQ-01 | User can enable/disable post-reverb Biquad EQ on reverb trails | Existing `Biquad` class in `filters.py`. Add enable/disable via session state checkbox. Wire into engine. |
| EQ-02 | User can adjust 3-band EQ parameters (low shelf, mid parametric, high shelf) | **Gap:** Biquad class lacks `low_shelf`/`high_shelf` factory methods. Must add using Bristow-Johnson shelf formulas (researched below). Mid parametric already exists. |
| ALGO-05 | User can select Dattorro parameter presets from dropdown | `DattorroPlate.update_params()` accepts param dicts directly. Presets are just named dicts. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | (installed) | Silence padding array ops, float32 audio | Already used throughout |
| Biquad (internal) | N/A | 3-band EQ (low shelf, mid parametric, high shelf) | Existing class in `filters.py`, Bristow-Johnson formulas |
| streamlit | 1.55.0 | UI controls, `st.audio(loop=)`, session state | Already the app framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| soundfile | (installed) | WAV file loading for samples | Loading WAV files from `/samples` directory |
| librosa | (installed) | Resampling loaded WAVs to 48kHz | Via existing `audio/io.py:load()` |
| pathlib | stdlib | WAV file discovery in samples dir | Glob for `*.wav` files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Biquad shelving | scipy.signal IIR | Biquad class is C-portable, scipy is not |
| WAV discovery via pathlib | hardcoded list | pathlib glob is more maintainable |

## Architecture Patterns

### Signal Flow for EQ Integration
```
Input Audio
  |
  +-- Silence Padding (append zeros) --> padded_input
  |
  +-- engine.process_audio(algo, params, padded_input)
        |
        +-- algo.process() --> wet_signal (100% wet)
        |
        +-- [NEW] EQ chain on wet_signal (if enabled):
        |     low_shelf.process() -> mid_parametric.process() -> high_shelf.process()
        |
        +-- return {dry: padded_input, wet: eq'd_wet, ...}
  |
  +-- UI: blend_wet_dry(dry, wet, mix_pct)
```

**Key insight:** EQ applies to the wet signal inside `engine.process_audio()`, AFTER algorithm processing but BEFORE the function returns. The dry signal is never touched by EQ. The UI-level `blend_wet_dry()` then mixes the EQ'd wet with the unprocessed dry.

### Engine Integration Pattern
```python
# In engine.process_audio(), after algo.process():
wet = algo.process(audio.copy())

# EQ stage (new)
if eq_params and eq_params.get("enabled"):
    wet = apply_eq(wet, eq_params)

# ... rest of function unchanged
```

### Preset Data Pattern
```python
# In dattorro_plate.py or a new presets module
DATTORRO_PRESETS = {
    "Small Plate": {
        "decay": 35, "bandwidth": 80, "tank_damping": 40,
        "diffusion": 90, "pre_delay": 5, "mod_depth": 20,
        "switch1": 0, "switch2": 0,
    },
    "Large Hall": {
        "decay": 85, "bandwidth": 60, "tank_damping": 20,
        "diffusion": 70, "pre_delay": 30, "mod_depth": 40,
        "switch1": 0, "switch2": 1,
    },
    # ... more presets
}
```

### Multi-file Session State Pattern
```python
# Session state keys for multi-file
st.session_state["selected_sample"]  # name of current sample/file
st.session_state["loop_playback"]    # True/False
st.session_state["silence_padding"]  # float seconds, 0.0-5.0
st.session_state["eq_enabled"]       # True/False
st.session_state["preset_name"]      # "Small Plate" or "Custom"
```

### Anti-Patterns to Avoid
- **EQ in the UI layer:** EQ is DSP, not presentation. It belongs in the engine, not in `streamlit_app.py`.
- **Rebuilding Biquad instances every process call:** Create once, use `set_coefficients()` for parameter changes to avoid state discontinuities.
- **Caching processed results per file:** Reprocessing on switch is simpler and avoids stale cache bugs. Processing is fast enough for offline (non-realtime) use.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Shelf EQ coefficients | Custom math | Bristow-Johnson shelf formulas (see below) | Battle-tested, published, matches existing Biquad pattern |
| WAV file loading | Manual soundfile calls | Existing `audio/io.py:load()` | Handles resampling, channel count, dtype conversion |
| Audio encoding for Streamlit | Manual WAV encoding | Existing `_audio_to_wav_bytes()` | Bypasses Streamlit normalization bug |
| Parameter knob UI | Custom slider code | Existing `param_specs` auto-generation pattern | Already proven for Freeverb and Dattorro |

## Common Pitfalls

### Pitfall 1: Silence Padding Changes Output Length
**What goes wrong:** Padded input is longer than original. The wet output will be longer than the original dry audio. `blend_wet_dry()` requires same-length arrays.
**Why it happens:** Appending silence to input before processing means output length = input_length + padding_length.
**How to avoid:** The dry signal stored in results must also be the padded version (input + silence). Both dry and wet have the same length. The waveform display should visually mark where the original audio ends and padding begins.
**Warning signs:** Array shape mismatch errors in `blend_wet_dry()`.

### Pitfall 2: EQ Creates Samples Outside [-1, 1]
**What goes wrong:** Shelf boost (+6dB or more) can push samples beyond clipping threshold.
**Why it happens:** A +6dB shelf boost doubles signal amplitude in that band.
**How to avoid:** Hard clip after EQ chain, same as existing `blend_wet_dry()` pattern. Limit gain range to +/-12dB.
**Warning signs:** Distorted/clipping audio output.

### Pitfall 3: Preset Dropdown Fights Widget State
**What goes wrong:** Selecting a preset should snap all knobs, but Streamlit widget keys are already bound to session state. Changing session state values after widget creation has no effect in the current run.
**Why it happens:** Streamlit's execution model: widgets read their key from session state at creation time. To change values, you must update session state and then `st.rerun()`.
**How to avoid:** When preset is selected, write all param values to session state keys (`knob_decay`, `knob_bandwidth`, etc.) and call `st.rerun()`. The rerun will pick up the new values. Same pattern used by existing "Reset to Defaults" button.
**Warning signs:** Knobs don't visually update after preset selection.

### Pitfall 4: "Custom" Label Detection
**What goes wrong:** Need to detect when user tweaks a knob after selecting a preset to change label to "Custom".
**Why it happens:** No built-in Streamlit "on_change" that compares to preset values.
**How to avoid:** After preset selection, store the preset param values in session state. On each run, compare current widget values to stored preset values. If any differ, label is "Custom". This comparison happens naturally in Streamlit's top-to-bottom execution.

### Pitfall 5: WAV File Discovery vs Synthesized Samples
**What goes wrong:** `list_samples()` returns synthesized sample names. WAV files in `/samples` are a different source. Mixing them in the same selectbox could confuse users.
**Why it happens:** Two different sample sources with different loading mechanisms.
**How to avoid:** Extend `list_samples()` to also discover `*.wav` files in the samples directory, or create a separate function. Use a single selectbox with clear naming (e.g., prefix WAV files with their filename, synthesized with their type).

## Code Examples

### Shelving Filter Factory Methods (Bristow-Johnson Cookbook)

These MUST be added to the existing `Biquad` class in `claudeverb/algorithms/filters.py`:

```python
# Source: https://webaudio.github.io/Audio-EQ-Cookbook/Audio-EQ-Cookbook.txt

@classmethod
def low_shelf(cls, freq: float, gain_db: float, q: float = 0.707,
              sample_rate: int = 48000) -> Biquad:
    """Create a low shelf biquad filter.

    Args:
        freq: Shelf transition frequency in Hz.
        gain_db: Boost/cut in dB below the shelf frequency.
        q: Quality factor (0.707 = Butterworth slope).
        sample_rate: Sample rate in Hz.
    """
    a_lin = 10.0 ** (gain_db / 40.0)  # = sqrt(10^(dBgain/20))
    w0 = 2.0 * math.pi * freq / sample_rate
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * q)
    two_sqrt_a_alpha = 2.0 * math.sqrt(a_lin) * alpha

    b0 = a_lin * ((a_lin + 1) - (a_lin - 1) * cos_w0 + two_sqrt_a_alpha)
    b1 = 2.0 * a_lin * ((a_lin - 1) - (a_lin + 1) * cos_w0)
    b2 = a_lin * ((a_lin + 1) - (a_lin - 1) * cos_w0 - two_sqrt_a_alpha)
    a0 = (a_lin + 1) + (a_lin - 1) * cos_w0 + two_sqrt_a_alpha
    a1 = -2.0 * ((a_lin - 1) + (a_lin + 1) * cos_w0)
    a2 = (a_lin + 1) + (a_lin - 1) * cos_w0 - two_sqrt_a_alpha

    return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, sample_rate)

@classmethod
def high_shelf(cls, freq: float, gain_db: float, q: float = 0.707,
               sample_rate: int = 48000) -> Biquad:
    """Create a high shelf biquad filter.

    Args:
        freq: Shelf transition frequency in Hz.
        gain_db: Boost/cut in dB above the shelf frequency.
        q: Quality factor (0.707 = Butterworth slope).
        sample_rate: Sample rate in Hz.
    """
    a_lin = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sample_rate
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * q)
    two_sqrt_a_alpha = 2.0 * math.sqrt(a_lin) * alpha

    b0 = a_lin * ((a_lin + 1) + (a_lin - 1) * cos_w0 + two_sqrt_a_alpha)
    b1 = -2.0 * a_lin * ((a_lin - 1) + (a_lin + 1) * cos_w0)
    b2 = a_lin * ((a_lin + 1) + (a_lin - 1) * cos_w0 - two_sqrt_a_alpha)
    a0 = (a_lin + 1) - (a_lin - 1) * cos_w0 + two_sqrt_a_alpha
    a1 = 2.0 * ((a_lin - 1) - (a_lin + 1) * cos_w0)
    a2 = (a_lin + 1) - (a_lin - 1) * cos_w0 - two_sqrt_a_alpha

    return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, sample_rate)
```

### 3-Band EQ Chain

```python
def apply_eq(wet: np.ndarray, eq_params: dict) -> np.ndarray:
    """Apply 3-band EQ to wet signal.

    Args:
        wet: Wet audio, mono (N,) or stereo (2, N), float32.
        eq_params: Dict with keys: low_freq, low_gain, mid_freq, mid_gain,
                   mid_q, high_freq, high_gain.
    """
    from claudeverb.algorithms.filters import Biquad
    from claudeverb.config import SAMPLE_RATE

    low = Biquad.low_shelf(eq_params["low_freq"], eq_params["low_gain"],
                           sample_rate=SAMPLE_RATE)
    mid = Biquad.parametric(eq_params["mid_freq"], eq_params["mid_q"],
                            eq_params["mid_gain"], sample_rate=SAMPLE_RATE)
    high = Biquad.high_shelf(eq_params["high_freq"], eq_params["high_gain"],
                             sample_rate=SAMPLE_RATE)

    if wet.ndim == 1:
        result = low.process(wet)
        result = mid.process(result)
        result = high.process(result)
    else:
        # Stereo: process each channel independently
        for ch in range(wet.shape[0]):
            low.reset(); mid.reset(); high.reset()
            channel = wet[ch].copy()
            channel = low.process(channel)
            channel = mid.process(channel)
            channel = high.process(channel)
            wet[ch] = channel
        result = wet

    return np.clip(result, -1.0, 1.0).astype(np.float32)
```

### Silence Padding

```python
def pad_with_silence(audio: np.ndarray, seconds: float,
                     sample_rate: int = 48000) -> np.ndarray:
    """Append silence to audio for reverb tail preservation."""
    n_pad = int(seconds * sample_rate)
    if n_pad <= 0:
        return audio
    if audio.ndim == 1:
        padding = np.zeros(n_pad, dtype=np.float32)
        return np.concatenate([audio, padding])
    else:
        padding = np.zeros((audio.shape[0], n_pad), dtype=np.float32)
        return np.concatenate([audio, padding], axis=1)
```

### Dattorro Presets

```python
DATTORRO_PRESETS = {
    "Small Plate": {
        "decay": 30, "bandwidth": 85, "tank_damping": 45,
        "diffusion": 90, "pre_delay": 3, "mod_depth": 15,
        "switch1": 0, "switch2": 0,
    },
    "Large Hall": {
        "decay": 80, "bandwidth": 55, "tank_damping": 15,
        "diffusion": 65, "pre_delay": 35, "mod_depth": 45,
        "switch1": 0, "switch2": 1,  # Wide stereo
    },
    "Bright Room": {
        "decay": 40, "bandwidth": 95, "tank_damping": 10,
        "diffusion": 80, "pre_delay": 8, "mod_depth": 25,
        "switch1": 0, "switch2": 0,
    },
    "Dark Chamber": {
        "decay": 65, "bandwidth": 40, "tank_damping": 60,
        "diffusion": 75, "pre_delay": 15, "mod_depth": 30,
        "switch1": 0, "switch2": 0,
    },
    "Shimmer Pad": {
        "decay": 90, "bandwidth": 70, "tank_damping": 25,
        "diffusion": 85, "pre_delay": 20, "mod_depth": 50,
        "switch1": 1, "switch2": 1,  # Shimmer + Wide
    },
    "Frozen Space": {
        "decay": 95, "bandwidth": 60, "tank_damping": 20,
        "diffusion": 80, "pre_delay": 0, "mod_depth": 60,
        "switch1": -1, "switch2": 1,  # Freeze + Wide
    },
}
```

### WAV File Discovery

```python
from pathlib import Path

def list_wav_samples() -> list[str]:
    """Discover WAV files in the bundled samples directory."""
    samples_dir = Path(__file__).parent.parent / "samples"
    if not samples_dir.exists():
        return []
    return sorted(p.stem for p in samples_dir.glob("*.wav"))

def load_wav_sample(name: str) -> np.ndarray:
    """Load a WAV sample by stem name."""
    samples_dir = Path(__file__).parent.parent / "samples"
    path = samples_dir / f"{name}.wav"
    return load(str(path))  # uses existing audio/io.py:load()
```

## Recommended Defaults (Claude's Discretion)

### EQ Defaults
| Band | Frequency | Gain Range | Default Gain | Q |
|------|-----------|------------|--------------|---|
| Low Shelf | 200 Hz | -12 to +12 dB | 0 dB | 0.707 (fixed) |
| Mid Parametric | 1000 Hz | -12 to +12 dB | 0 dB | 1.5 (adjustable, 0.5-5.0) |
| High Shelf | 6000 Hz | -12 to +12 dB | 0 dB | 0.707 (fixed) |

**Rationale:** 200 Hz captures the warmth/muddiness range for reverb. 1 kHz is the clarity region. 6 kHz handles air/presence. Q fixed for shelves (shelf Q mainly affects transition steepness, not a knob users typically adjust). Mid Q adjustable for precision control. +/-12 dB is standard for studio EQ.

### Silence Padding Placement
Place the silence padding slider near the audio source section in the sidebar, right after the sample selection. This is where it logically belongs -- it modifies the input signal, not the algorithm.

### Multi-file UX
Use `st.selectbox` for the file selector. Merge WAV files and synthesized samples into a single list with clear labeling (e.g., "audio1-acoustic [WAV]" vs "guitar [synth]"). This is the simplest pattern that matches the existing single-sample selectbox.

### Loop Toggle Placement
Sidebar checkbox, persistent across files. Simple and discoverable.

### Caching Decision
Do NOT cache processed results per file. Reprocess on switch. Reasons:
1. Processing is ~1-3 seconds for typical audio lengths
2. Avoids complex cache invalidation when algorithm params change
3. Simpler session state management
4. Consistent with existing "Process" button pattern

### Dattorro Preset Count
6 presets (shown in code example above): Small Plate, Large Hall, Bright Room, Dark Chamber, Shimmer Pad, Frozen Space. These cover distinct characters across the parameter space and demonstrate all three switch1 modes (Normal, Shimmer, Freeze).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single sample selectbox | Multi-file + WAV discovery | Phase 6 | Users test with real recordings |
| No reverb tail visibility | Silence padding + visual marker | Phase 6 | Full decay audible and visible |
| Raw reverb output | 3-band EQ shaping | Phase 6 | Tonal control without algorithm changes |
| Manual param exploration | Named presets | Phase 6 | Starting points for Dattorro |

## Open Questions

1. **Stereo EQ: shared or per-channel controls?**
   - What we know: EQ should process stereo channels independently (different filter state per channel) but with the same frequency/gain/Q settings
   - What's unclear: Whether to expose per-channel controls
   - Recommendation: Single set of EQ controls, applied identically to both channels. Per-channel EQ is advanced and beyond scope.

2. **Waveform padding visualization**
   - What we know: User decided padded region should be visually marked
   - What's unclear: Exact visual treatment (shaded background, dashed line, annotation)
   - Recommendation: Use `axvspan()` with light gray fill + alpha to shade the padding region. Return the original audio length alongside padded audio so the UI knows where to draw the boundary.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed) |
| Config file | none (uses defaults) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAY-01 | Load WAV files from /samples, switch between them | unit | `pytest tests/test_samples.py -x` | Exists (extend) |
| PLAY-02 | Loop toggle controls st.audio loop param | manual-only | N/A (Streamlit UI behavior) | N/A |
| PLAY-03 | Silence padding appends zeros, correct length | unit | `pytest tests/test_engine.py::TestSilencePadding -x` | Wave 0 |
| EQ-01 | EQ enable/disable, bypasses when off | unit | `pytest tests/test_engine.py::TestEQ -x` | Wave 0 |
| EQ-02 | 3-band EQ: shelf frequency response correct | unit | `pytest tests/test_biquad.py::TestBiquadLowShelf -x` | Wave 0 |
| ALGO-05 | Preset dicts produce valid params, knobs snap | unit | `pytest tests/test_dattorro_plate.py::TestPresets -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_biquad.py` -- add `TestBiquadLowShelf` and `TestBiquadHighShelf` classes (shelf frequency response)
- [ ] `tests/test_engine.py` -- add `TestSilencePadding` (pad length, dtype, mono/stereo)
- [ ] `tests/test_engine.py` -- add `TestEQ` (EQ enable/disable, output shape, bypass)
- [ ] `tests/test_dattorro_plate.py` -- add `TestPresets` (all presets produce valid params, update_params succeeds)
- [ ] `tests/test_samples.py` -- add WAV file discovery tests

## Sources

### Primary (HIGH confidence)
- Bristow-Johnson Audio EQ Cookbook (https://webaudio.github.io/Audio-EQ-Cookbook/Audio-EQ-Cookbook.txt) - shelf filter coefficient formulas
- Codebase inspection: `claudeverb/algorithms/filters.py` - existing Biquad class, confirmed no shelf methods
- Codebase inspection: `claudeverb/engine.py` - current signal flow, integration point for EQ
- Codebase inspection: `claudeverb/algorithms/dattorro_plate.py` - param_specs, update_params() interface
- Codebase inspection: `claudeverb/streamlit_app.py` - session state patterns, widget key conventions
- Codebase inspection: `claudeverb/audio/samples.py` - sample registry, get_sample/list_samples
- Codebase inspection: `claudeverb/samples/` - 4 WAV files present (acoustic, bass, faith-bridge, faith-verse)

### Secondary (MEDIUM confidence)
- Streamlit docs (https://docs.streamlit.io/develop/api-reference/media/st.audio) - st.audio loop parameter confirmed
- Streamlit version 1.55.0 confirmed installed

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and used in codebase
- Architecture: HIGH - follows established engine facade and session state patterns
- Shelving EQ formulas: HIGH - Bristow-Johnson cookbook is the canonical reference, verified against official source
- Pitfalls: HIGH - based on direct Streamlit session state observation and existing codebase patterns
- Dattorro presets: MEDIUM - preset parameter values are reasonable starting points but will need ear-testing

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain, no fast-moving dependencies)
