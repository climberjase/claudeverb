# Phase 4: Engine + Streamlit UI - Research

**Researched:** 2026-03-05
**Domain:** Streamlit web UI, audio processing pipeline, visualization integration
**Confidence:** HIGH

## Summary

This phase integrates all existing claudeverb components (algorithms, audio I/O, samples, analysis, spectral visualization) into a Streamlit web application. The existing codebase provides strong building blocks: `ALGORITHM_REGISTRY` for dropdown population, `param_specs` for auto-generating controls, `audio.io` for loading, `analysis.metrics` and `analysis.spectral` for display. The main engineering work is the Streamlit page layout, session state management, wet/dry blending logic, and wiring everything together.

Streamlit's `st.audio` natively accepts numpy arrays with a `sample_rate` parameter and supports `loop=True`, which covers the PLAY-01 requirement without custom components. The sidebar+main layout maps directly to Streamlit's `st.sidebar` API. Matplotlib figures from spectral.py render via `st.pyplot()`. The key design challenge is wet/dry blending: store both dry and fully-wet processed signals in session state, then blend on slider change without re-processing.

**Primary recommendation:** Build a single-file Streamlit app (`claudeverb/streamlit_app.py`) using `st.sidebar` for controls and the main area for vertically stacked visualizations. Use `st.session_state` to store dry/wet audio arrays. Wet/dry slider performs real-time numpy blending of pre-computed signals.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Sidebar controls + main canvas layout
- Sidebar contains: audio source selection, algorithm dropdown, 6 knob sliders, 2 switch selectors, wet/dry slider, Process button
- Main area contains: audio player(s), waveform display, spectrograms, FFT overlay, metric readouts
- Visualizations stacked vertically in the main area (not tabbed)

### Claude's Discretion
- **Audio source widget**: Whether to use dropdown, radio buttons, or another Streamlit widget for bundled sample selection; file uploader placement
- **Knob value display**: Whether sliders show just 0-100 or also the scaled internal value (e.g., "75 -> 0.84") -- developer workbench context favors showing both but Claude decides
- **Processing engine**: In-memory pipeline vs file-based pipeline for processed audio storage
- **Audio transport**: Whether to use st.audio built-in or build custom play/stop/loop controls
- **A/B comparison**: Two audio players (input + output) side by side, or single player with toggle/wet-dry switching
- **Download button**: Whether to include a download button for processed audio after processing
- **Wet/dry mix design**: Whether the UI-level wet/dry slider replaces the algorithm's internal mix knob or operates independently as a post-processing blend
- **Wet/dry placement**: Whether the slider lives in the sidebar with other controls or in the main area near audio playback
- **Wet/dry update behavior**: Whether changing wet/dry re-processes or blends stored dry+wet signals in real-time (real-time blend recommended)
- **Wet/dry + analysis interaction**: Whether analysis displays update when wet/dry changes or only on Process click
- **Default visualizations**: Which analysis panels show by default vs. behind checkboxes/expanders
- **Metrics display format**: st.metric() cards vs table vs other layout for RT60, DRR, C80, C50, centroid delta
- **IR generation trigger**: Separate "Generate IR" button vs auto-generate behind the scenes with Process (note: RT60/DRR/C80 metrics require an IR)
- **Reset to defaults button**: Whether to include a button that restores all knobs/switches to default values

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AIO-03 | User can play, stop, and loop processed audio output | `st.audio(numpy_array, sample_rate=48000, loop=True)` handles play/stop/loop natively |
| PLAY-01 | Process-then-play workflow: tweak params, click process, listen | Sidebar controls + Process button + session_state for storing results |
| PLAY-02 | Wet/dry mix slider (0-100%) applied at output stage | Post-processing numpy blend of stored dry + wet arrays in session_state |
| PLAY-03 | Audio waveform display showing input and output amplitude envelopes | Matplotlib waveform plot rendered via `st.pyplot()` |
| UI-01 | Streamlit web interface tying all controls and displays together | Single-page Streamlit app with sidebar + main area layout |
| UI-02 | Algorithm selector dropdown populated from registry | `st.selectbox` populated from `ALGORITHM_REGISTRY.keys()` |
| UI-03 | Knob controls (6 sliders) and switch controls (2 three-position selectors) auto-generated from param_specs | `st.slider` for knobs, `st.select_slider` with `format_func` for switches |
| UI-04 | Process button triggering algorithm execution on loaded audio | `st.sidebar.button("Process")` triggers algorithm.process() |
| UI-05 | Analysis displays update after each process run | Session state flag triggers visualization section after processing |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | >=1.38 | Web UI framework | Only framework in scope; st.audio accepts numpy directly |
| matplotlib | (existing) | All visualization (waveforms, spectrograms, FFT) | Already used by analysis.spectral; renders via st.pyplot() |
| numpy | (existing) | Audio array manipulation, wet/dry blending | Already the project standard for all audio |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| io (stdlib) | - | BytesIO for in-memory WAV encoding | Only if st.audio numpy path has issues; also for download button |
| soundfile | (existing) | WAV encoding to BytesIO for download | Download button for processed audio |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| st.audio (built-in) | Custom HTML5 audio component | st.audio already has play/stop/loop -- no need for custom |
| Matplotlib waveforms | Plotly/Altair | Matplotlib already used by spectral.py; consistency wins |
| Streamlit | Gradio | Out of scope -- user chose Streamlit |

**Installation:**
```bash
pip install streamlit>=1.38
```

Add to `pyproject.toml` dependencies.

## Architecture Patterns

### Recommended Project Structure
```
claudeverb/
├── streamlit_app.py          # Main Streamlit application (single file)
├── engine.py                 # Processing engine: ties algorithm + audio + analysis
├── algorithms/               # (existing)
├── audio/                    # (existing)
├── analysis/                 # (existing)
└── config.py                 # (existing)
```

### Pattern 1: Processing Engine (Facade)
**What:** A thin engine module that orchestrates the process-then-analyze workflow, keeping the Streamlit app focused on layout/state.
**When to use:** Always -- separates DSP logic from UI concerns, making the engine independently testable.
**Example:**
```python
# claudeverb/engine.py
import numpy as np
from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.audio.impulse import generate_impulse_response
from claudeverb.analysis.metrics import (
    measure_rt60, measure_rt60_bands, compute_drr,
    compute_clarity, spectral_centroid_delta,
)
from claudeverb.analysis.spectral import plot_mel_comparison, plot_fft_comparison
from claudeverb.config import SAMPLE_RATE


def process_audio(algorithm_name: str, params: dict, audio: np.ndarray) -> dict:
    """Process audio through algorithm and return results dict.

    Returns dict with keys:
        dry: original audio
        wet: fully processed audio (algorithm mix=100)
        ir: impulse response
        metrics: dict of metric name -> value
        figures: dict of figure name -> matplotlib Figure
    """
    algo_class = ALGORITHM_REGISTRY[algorithm_name]
    algo = algo_class()

    # Force algorithm mix to 100 (full wet) -- UI handles wet/dry blend
    process_params = {**params, "mix": 100}
    algo.update_params(process_params)
    algo.reset()

    wet = algo.process(audio.copy())

    # Generate IR for metrics
    algo.update_params(process_params)
    ir = generate_impulse_response(algo, duration_seconds=3.0, mono=True)

    # Compute metrics
    metrics = {
        "RT60 (broadband)": f"{measure_rt60(ir):.2f} s",
        "RT60 (low)": f"{measure_rt60_bands(ir)['low']:.2f} s",
        "RT60 (mid)": f"{measure_rt60_bands(ir)['mid']:.2f} s",
        "RT60 (high)": f"{measure_rt60_bands(ir)['high']:.2f} s",
        "DRR": f"{compute_drr(ir):.1f} dB",
        "C80": f"{compute_clarity(ir, early_ms=80.0):.1f} dB",
        "C50": f"{compute_clarity(ir, early_ms=50.0):.1f} dB",
        "Centroid Delta": f"{spectral_centroid_delta(audio, wet):.0f} Hz",
    }

    # Generate figures
    figures = {
        "mel": plot_mel_comparison(audio, wet),
        "fft": plot_fft_comparison(audio, wet),
    }

    return {
        "dry": audio,
        "wet": wet,
        "ir": ir,
        "metrics": metrics,
        "figures": figures,
    }
```

### Pattern 2: Session State for Audio Pipeline
**What:** Store dry audio, wet audio, and processing results in `st.session_state` so wet/dry blending and display persist across reruns.
**When to use:** Always -- Streamlit reruns the entire script on every interaction.
**Example:**
```python
# In streamlit_app.py
import streamlit as st
import numpy as np

# Initialize session state
if "dry_audio" not in st.session_state:
    st.session_state.dry_audio = None
    st.session_state.wet_audio = None
    st.session_state.results = None

# After processing:
st.session_state.dry_audio = audio
st.session_state.wet_audio = results["wet"]
st.session_state.results = results

# Wet/dry blend (runs on every rerun, including slider changes):
if st.session_state.dry_audio is not None:
    mix = wet_dry_slider / 100.0
    blended = (1.0 - mix) * st.session_state.dry_audio + mix * st.session_state.wet_audio
    st.audio(blended, sample_rate=48000)
```

### Pattern 3: Data-Driven Control Generation
**What:** Auto-generate sliders and switches from `param_specs` dict, so adding new algorithms requires zero UI changes.
**When to use:** Always -- this is a locked requirement (UI-03).
**Example:**
```python
def render_algorithm_controls(param_specs: dict) -> dict:
    """Generate sidebar controls from param_specs, return current values."""
    params = {}
    for name, spec in param_specs.items():
        if spec["type"] == "knob":
            params[name] = st.sidebar.slider(
                spec["label"],
                min_value=spec["min"],
                max_value=spec["max"],
                value=spec["default"],
                key=f"knob_{name}",
            )
        elif spec["type"] == "switch":
            params[name] = st.sidebar.select_slider(
                spec["label"],
                options=spec["positions"],  # [-1, 0, 1]
                value=spec["default"],
                format_func=lambda x, labels=spec["labels"], positions=spec["positions"]:
                    labels[positions.index(x)],
                key=f"switch_{name}",
            )
    return params
```

### Pattern 4: Waveform Display
**What:** Matplotlib-based amplitude envelope plot for input vs output comparison.
**When to use:** PLAY-03 requirement.
**Example:**
```python
def plot_waveform_comparison(
    dry: np.ndarray, wet: np.ndarray, sr: int = 48000
) -> plt.Figure:
    """Plot input and output waveforms overlaid or stacked."""
    import matplotlib.pyplot as plt

    # Ensure mono for display
    if dry.ndim == 2:
        dry = np.mean(dry, axis=0)
    if wet.ndim == 2:
        wet = np.mean(wet, axis=0)

    t = np.arange(len(dry)) / sr
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 4), sharex=True)
    ax1.plot(t, dry, linewidth=0.5, alpha=0.8)
    ax1.set_ylabel("Input")
    ax1.set_ylim(-1, 1)
    ax2.plot(t, wet, linewidth=0.5, alpha=0.8, color="orange")
    ax2.set_ylabel("Output")
    ax2.set_ylim(-1, 1)
    ax2.set_xlabel("Time (s)")
    fig.tight_layout()
    return fig
```

### Anti-Patterns to Avoid
- **Re-processing on wet/dry change:** Store fully dry and fully wet signals, blend with numpy. Never re-run algorithm.process() just to change mix.
- **File-based audio pipeline:** Writing WAV to disk between stages is slow and unnecessary. Keep everything as numpy arrays in session_state.
- **Importing heavy libraries at module level in streamlit_app.py:** Streamlit reruns the entire script. Use the engine module to isolate imports.
- **Not using keys on widgets:** Every slider/selectbox needs a unique `key=` parameter or Streamlit will error on rerun with duplicate widgets.
- **Forgetting algorithm.reset() before process:** Algorithms accumulate state. Always reset before processing to get deterministic results.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio playback | Custom HTML5 player | `st.audio(array, sample_rate=48000, loop=True)` | Built-in handles play/stop/loop, accepts numpy directly |
| File upload handling | Custom file reader | `st.file_uploader` + `audio.io.load()` via BytesIO | Streamlit handles multipart upload; io.load handles format |
| Spectrogram plots | New plotting code | Existing `plot_mel_comparison()`, `plot_fft_comparison()` | Already tested and working from Phase 3 |
| Metric computation | New metric code | Existing `measure_rt60()`, `compute_drr()`, `compute_clarity()` | Already tested from Phase 3 |
| IR generation | Manual impulse handling | Existing `generate_impulse_response()` | Already tested from Phase 2 |
| Algorithm instantiation | Manual class lookup | `ALGORITHM_REGISTRY[name]()` | Already working from Phase 2 |

**Key insight:** This phase is primarily integration and UI wiring. Nearly all DSP, analysis, and audio I/O code already exists and is tested. The new code should be thin glue.

## Common Pitfalls

### Pitfall 1: Streamlit Rerun Model
**What goes wrong:** Developers expect stateful behavior, but Streamlit reruns the entire script top-to-bottom on every widget interaction.
**Why it happens:** Coming from traditional frameworks where state persists between events.
**How to avoid:** Use `st.session_state` for all data that must survive reruns (audio arrays, processing results, algorithm instances).
**Warning signs:** Audio disappearing after clicking a slider, results clearing unexpectedly.

### Pitfall 2: Large Audio Arrays in Session State
**What goes wrong:** Session state stores numpy arrays by reference, but rerun semantics can cause copies.
**Why it happens:** A 10-second stereo float32 clip at 48kHz is ~3.7 MB. Storing dry + wet + IR + blended = ~15 MB per session.
**How to avoid:** This is manageable for a local developer tool. Keep arrays in session_state, do not cache them with `@st.cache_data` (they change per parameter set). Limit input audio length (already warned at 60s in io.load).
**Warning signs:** Slow reruns, browser tab using excessive memory.

### Pitfall 3: Matplotlib Figure Lifecycle
**What goes wrong:** Matplotlib figures accumulate in memory if not explicitly closed.
**Why it happens:** `plt.subplots()` creates figures that persist until `plt.close(fig)`.
**How to avoid:** After calling `st.pyplot(fig)`, call `plt.close(fig)`. Or use `st.pyplot(fig, clear_figure=True)` (deprecated but still works). Better: the engine returns figures, display code closes them.
**Warning signs:** Memory growth over repeated Process clicks.

### Pitfall 4: st.audio with Stereo Arrays
**What goes wrong:** `st.audio` expects shape `(channels, samples)` for multi-channel, which matches our `(2, N)` convention.
**Why it happens:** Convention alignment is actually correct here.
**How to avoid:** Verify that our stereo convention `(2, N)` works directly with `st.audio`. It should, but test it.
**Warning signs:** Audio sounds garbled or plays at wrong speed.

### Pitfall 5: Algorithm Mix Parameter vs UI Wet/Dry
**What goes wrong:** If the algorithm's internal `mix` parameter and the UI wet/dry slider both affect wet/dry ratio, the user gets confusing double-attenuation.
**Why it happens:** Freeverb has a `mix` knob in its param_specs.
**How to avoid:** When processing, set algorithm mix to 100 (fully wet). The UI wet/dry slider then independently blends dry and fully-wet signals. Hide or disable the algorithm's mix slider in the UI, OR clearly label that algorithm mix controls reverb density while UI wet/dry controls overall blend.
**Warning signs:** User sets wet/dry to 100% but still hears dry signal, or vice versa.

### Pitfall 6: file_uploader Returns UploadedFile, Not Path
**What goes wrong:** `audio.io.load()` expects a file path string, but `st.file_uploader` returns an `UploadedFile` (BytesIO-like) object.
**Why it happens:** Streamlit uploads are in-memory, not saved to disk.
**How to avoid:** Use `librosa.load(uploaded_file, sr=48000, mono=False)` directly (librosa accepts file-like objects), or write a thin wrapper. Do NOT write to temp file.
**Warning signs:** TypeError on load, or file not found errors.

## Code Examples

### Loading Audio from file_uploader
```python
# Source: librosa docs + Streamlit file_uploader docs
import io
import librosa
import numpy as np
from claudeverb.config import SAMPLE_RATE

def load_uploaded_audio(uploaded_file) -> np.ndarray:
    """Load audio from Streamlit UploadedFile object."""
    audio, sr = librosa.load(uploaded_file, sr=SAMPLE_RATE, mono=False)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 2 and audio.shape[0] > 2:
        audio = audio[:2]
    return audio
```

### Wet/Dry Blending (numpy, no re-processing)
```python
# Real-time blending of pre-computed signals
def blend_wet_dry(dry: np.ndarray, wet: np.ndarray, mix_pct: int) -> np.ndarray:
    """Blend dry and wet audio signals.

    Args:
        dry: Original audio, float32
        wet: Fully processed audio, float32
        mix_pct: 0-100 percentage (0=fully dry, 100=fully wet)

    Returns:
        Blended audio, float32, hard-clipped to [-1, 1]
    """
    alpha = mix_pct / 100.0
    blended = (1.0 - alpha) * dry + alpha * wet
    return np.clip(blended, -1.0, 1.0).astype(np.float32)
```

### WAV Download via BytesIO
```python
# For download button
import io
import soundfile as sf
from claudeverb.config import SAMPLE_RATE

def audio_to_wav_bytes(audio: np.ndarray) -> bytes:
    """Convert numpy audio array to WAV bytes for download."""
    buf = io.BytesIO()
    data = audio.T if audio.ndim == 2 and audio.shape[0] == 2 else audio
    sf.write(buf, data, SAMPLE_RATE, format="WAV", subtype="FLOAT")
    buf.seek(0)
    return buf.read()
```

### Sidebar Layout Skeleton
```python
import streamlit as st
from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.audio.samples import list_samples, get_sample

st.set_page_config(page_title="ClaudeVerb", layout="wide")

with st.sidebar:
    st.title("ClaudeVerb")

    # Audio source
    source_type = st.radio("Audio Source", ["Bundled Sample", "Upload File"])
    if source_type == "Bundled Sample":
        sample_name = st.selectbox("Sample", list_samples())
        audio = get_sample(sample_name)
    else:
        uploaded = st.file_uploader("Upload Audio", type=["wav", "aiff", "flac", "ogg"])
        audio = load_uploaded_audio(uploaded) if uploaded else None

    # Algorithm selection
    algo_name = st.selectbox("Algorithm", list(ALGORITHM_REGISTRY.keys()))
    algo_class = ALGORITHM_REGISTRY[algo_name]
    specs = algo_class().param_specs

    # Auto-generate controls
    params = render_algorithm_controls(specs)

    # Wet/dry
    wet_dry = st.slider("Wet/Dry Mix", 0, 100, 75, key="wet_dry")

    # Process button
    process_clicked = st.button("Process", type="primary", use_container_width=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.audio(bytes_data)` only | `st.audio(numpy_array, sample_rate=N)` | Streamlit 1.18+ (2023) | No need for BytesIO conversion for playback |
| `@st.cache` (deprecated) | `@st.cache_data` / `@st.cache_resource` | Streamlit 1.18+ (2023) | New caching API; use `@st.cache_data` for data transforms |
| No native testing | `st.testing.v1.AppTest` | Streamlit 1.28+ (2023) | Can write pytest tests simulating app interactions |
| `st.experimental_rerun()` | `st.rerun()` | Streamlit 1.27+ (2023) | Stable API for forcing rerun |
| No loop support | `st.audio(data, loop=True)` | Streamlit 1.35+ (2024) | Native loop support, no custom component needed |

**Deprecated/outdated:**
- `@st.cache`: Replaced by `@st.cache_data` and `@st.cache_resource`
- `st.experimental_rerun()`: Now `st.rerun()`

## Discretion Recommendations

Based on research, here are recommendations for areas marked as Claude's Discretion:

| Area | Recommendation | Rationale |
|------|---------------|-----------|
| Audio source widget | `st.radio` for source type + `st.selectbox` for sample selection | Radio is clearer for binary choice; selectbox for sample list |
| Knob value display | Show 0-100 only; tooltip shows scaled value | Simpler UI; developer can see internal value on hover via `help=` param |
| Processing engine | In-memory pipeline (numpy arrays in session_state) | No disk I/O needed; faster; local-only tool |
| Audio transport | `st.audio` built-in with `loop=True` | Native play/stop/loop covers all requirements |
| A/B comparison | Two `st.audio` players (Input + Output) in side-by-side columns | Allows direct comparison; simple implementation |
| Download button | Yes, include `st.download_button` for processed audio | Minimal code, useful for developer workflow |
| Wet/dry mix design | UI wet/dry operates independently; algorithm mix knob hidden or set to 100 internally | Avoids confusing double-mix; cleaner mental model |
| Wet/dry placement | Sidebar, below algorithm controls, above Process button | Groups all controls together in sidebar |
| Wet/dry update behavior | Real-time blend of stored dry+wet (no re-processing) | Instant feedback; re-processing is slow |
| Wet/dry + analysis | Analysis displays update ONLY on Process click, not on wet/dry change | Spectrograms/metrics are expensive; wet/dry is a listening aid |
| Default visualizations | All visible by default (waveform, spectrograms, metrics) in expanders | Developer workbench should show everything; expanders allow collapse |
| Metrics display format | `st.metric()` cards in columns | Clean, native Streamlit look; each metric gets its own card |
| IR generation trigger | Auto-generate IR behind the scenes during Process | Metrics require IR; no reason to make user click separately |
| Reset to defaults | Yes, include reset button | Minimal code, useful when exploring parameter space |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_streamlit_app.py -x` |
| Full suite command | `pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AIO-03 | Audio playback with loop | manual-only | Manual: open browser, verify st.audio player works | N/A |
| PLAY-01 | Process-then-play workflow | integration | `pytest tests/test_engine.py::test_process_audio -x` | No (Wave 0) |
| PLAY-02 | Wet/dry mix blending | unit | `pytest tests/test_engine.py::test_wet_dry_blend -x` | No (Wave 0) |
| PLAY-03 | Waveform display | unit | `pytest tests/test_engine.py::test_waveform_plot -x` | No (Wave 0) |
| UI-01 | Streamlit app runs without error | integration | `pytest tests/test_streamlit_app.py::test_app_runs -x` | No (Wave 0) |
| UI-02 | Algorithm dropdown from registry | unit+AppTest | `pytest tests/test_streamlit_app.py::test_algorithm_selector -x` | No (Wave 0) |
| UI-03 | Auto-generated knob/switch controls | unit | `pytest tests/test_engine.py::test_param_specs_to_controls -x` | No (Wave 0) |
| UI-04 | Process button triggers execution | integration+AppTest | `pytest tests/test_streamlit_app.py::test_process_button -x` | No (Wave 0) |
| UI-05 | Analysis displays update after process | integration+AppTest | `pytest tests/test_streamlit_app.py::test_analysis_display -x` | No (Wave 0) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_engine.py tests/test_streamlit_app.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_engine.py` -- covers PLAY-01, PLAY-02, PLAY-03, UI-03 (engine logic without Streamlit)
- [ ] `tests/test_streamlit_app.py` -- covers UI-01, UI-02, UI-04, UI-05 (using `st.testing.v1.AppTest`)
- [ ] `streamlit` package install: `pip install streamlit>=1.38`

### Testing Strategy Notes

**Engine tests (test_engine.py):** Standard pytest. Test `process_audio()`, `blend_wet_dry()`, waveform plotting -- no Streamlit dependency needed.

**Streamlit AppTest (test_streamlit_app.py):** Use `st.testing.v1.AppTest.from_file("claudeverb/streamlit_app.py")` to simulate the app. Can verify:
- App loads without exception: `assert not at.exception`
- Sidebar widgets exist: check `at.sidebar.selectbox`, `at.sidebar.slider`, `at.sidebar.button`
- Process button interaction: `at.sidebar.button[0].click().run()` and verify output elements appear

**Manual testing required for:** Audio playback quality, visual appearance, browser interaction. These cannot be automated via AppTest.

## Open Questions

1. **librosa.load with UploadedFile**
   - What we know: librosa.load accepts file-like objects in most versions
   - What's unclear: Whether Streamlit's UploadedFile (which is a BytesIO subclass) works seamlessly with librosa without `.seek(0)`
   - Recommendation: Test during implementation; add `.seek(0)` if needed, or read bytes into BytesIO explicitly

2. **st.audio with stereo (2, N) arrays**
   - What we know: st.audio docs say it accepts `(C, S)` shape for multi-channel
   - What's unclear: Whether our `(2, N)` float32 convention maps perfectly or if normalization is needed
   - Recommendation: Test during implementation; fallback to mono averaging if stereo causes issues

## Sources

### Primary (HIGH confidence)
- [Streamlit st.audio docs](https://docs.streamlit.io/develop/api-reference/media/st.audio) -- numpy array support, loop parameter, sample_rate
- [Streamlit AppTest docs](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) -- testing framework API
- [Streamlit st.select_slider docs](https://docs.streamlit.io/develop/api-reference/widgets/st.select_slider) -- format_func for switch labels
- [Streamlit release notes 2025-2026](https://docs.streamlit.io/develop/quick-reference/release-notes/2025) -- version verification

### Secondary (MEDIUM confidence)
- [Streamlit community: numpy array audio](https://discuss.streamlit.io/t/integrate-audio-from-a-numpy-array/25890) -- confirmed numpy path works
- [Streamlit caching docs](https://docs.streamlit.io/develop/concepts/architecture/caching) -- cache_data vs session_state patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Streamlit is the only framework, well-documented, numpy audio support confirmed
- Architecture: HIGH -- Pattern is straightforward (sidebar + main, session_state); all integration points exist and are tested
- Pitfalls: HIGH -- Streamlit rerun model is well-documented; audio handling verified via official docs

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (Streamlit releases monthly but core APIs are stable)
