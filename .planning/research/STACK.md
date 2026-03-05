# Technology Stack

**Project:** ClaudeVerb -- Python DSP Reverb Algorithm Workbench
**Researched:** 2026-03-04
**Note:** Web search tools were unavailable during research. Versions are based on training data (through early 2025) and may be slightly behind latest releases. Verify versions with `pip install --upgrade` before committing to `pyproject.toml`.

## Recommended Stack

### Core DSP / Numerical

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| NumPy | >=1.26,<3.0 | Array operations, circular buffer math, all DSP computation | The foundation of Python DSP. Every audio sample is a float32 ndarray. NumPy 2.0+ is stable and faster. Pin floor at 1.26 for compatibility. | HIGH |
| SciPy | >=1.12 | Signal processing: `scipy.signal` for filter design (biquad coefficients via `butter`, `sosfilt`), resampling via `resample_poly` | Provides IIR/FIR filter design functions that map directly to C biquad implementations. `signal.sosfilt` processes second-order sections which are the exact structure needed for Daisy Seed EQ filters. | HIGH |

### Audio I/O

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| soundfile | >=0.12 | Read/write audio files (WAV, FLAC, OGG) | Thin wrapper around libsndfile. Fast, supports 24-bit PCM write (needed for high-quality output). No dependency on ffmpeg. | HIGH |
| sounddevice | >=0.4.6 | Audio playback to system audio output | PortAudio wrapper. Needed for local listening tests on macOS. Works with numpy arrays directly. | HIGH |

### Audio Analysis

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| librosa | >=0.10.1 | Mel spectrograms, STFT, feature extraction | Industry standard for audio analysis in Python. `librosa.feature.melspectrogram` and `librosa.display.specshow` are exactly what the analysis panel needs. Note: librosa resamples to 22050 by default -- always pass `sr=48000` explicitly. | HIGH |

### Visualization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| matplotlib | >=3.8 | Spectrograms, frequency plots, RT60 decay curves, all analysis charts | Librosa's display functions are built on matplotlib. Streamlit natively renders matplotlib figures via `st.pyplot()`. No alternative is as well-integrated with the scientific Python stack. | HIGH |

### UI Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Streamlit | >=1.35 | Web-based UI: parameter knobs, algorithm selection, audio playback, chart display | PROJECT.md specifies Streamlit. It provides `st.audio()` for in-browser playback, `st.slider()` for knob parameters, `st.selectbox()` for algorithm selection, `st.pyplot()` for charts. Process-then-play workflow fits Streamlit's rerun model well. | HIGH |

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | >=8.0 | Test runner | Standard Python test framework. Use fixtures for mono_sine, stereo_sine, impulse test signals. | HIGH |
| pytest-cov | >=5.0 | Coverage reporting | Track coverage of algorithm implementations and DSP primitives. | HIGH |

### Development

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ruff | >=0.4 | Linting and formatting | Replaces flake8+black+isort. Single tool, extremely fast, good defaults. | HIGH |
| mypy | >=1.10 | Type checking | DSP code benefits heavily from type annotations (ndarray shapes, sample rates). Catches bugs before they become audio artifacts. | MEDIUM |

### Build / Packaging

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| setuptools | >=69 | Package build | Use `pyproject.toml` with `[project.optional-dependencies]` for dev extras. `pip install -e ".[dev]"` workflow. | HIGH |

## Libraries NOT to Use

| Library | Why Not | What to Use Instead |
|---------|---------|-------------------|
| PySide6 / PyQt | PROJECT.md explicitly defers desktop UI to a later milestone. Adding Qt now creates a parallel UI surface to maintain. | Streamlit for all UI in v1. |
| pydub | Wraps ffmpeg, adds unnecessary dependency layer. Slower than soundfile for simple read/write operations. | soundfile for I/O, numpy for manipulation. |
| pedalboard (Spotify) | Tempting for AU plugin hosting, but AU loading is out of scope for v1. Adds heavy C++ dependency. | Defer to v2 milestone when AU comparison is needed. |
| torchaudio / torch | Massive dependency (2+ GB) for functionality numpy/scipy already provide. No GPU needed for offline reverb processing. | NumPy + SciPy for all DSP. |
| Gradio | Alternative to Streamlit, but Streamlit has better audio widget support and is already decided in PROJECT.md. | Streamlit. |
| pyaudio | Older PortAudio binding with painful installation (requires manual portaudio build on some systems). | sounddevice (cleaner API, pip-installable). |
| aubio | C-based audio analysis. Overlaps with librosa and harder to install. Not needed when librosa + scipy cover all analysis needs. | librosa + scipy.signal. |
| numba | JIT compilation for Python. Tempting for DSP speedup, but adds complexity and the algorithms must map to C anyway (not optimized Python). Process-then-play on short clips does not need JIT speed. | Pure numpy vectorized operations. If too slow, that is a signal to port to C sooner. |

## Key Library Interactions and Gotchas

### Streamlit + Audio Playback

Streamlit's `st.audio()` accepts numpy arrays directly (as of ~1.30+). Pass `sample_rate=48000` explicitly. The widget renders an HTML5 audio player in the browser -- no sounddevice needed for basic playback. Use sounddevice only for lower-latency local playback or when browser audio is insufficient.

**Gotcha:** Streamlit reruns the entire script on every widget interaction. This means DSP processing re-executes on every slider change unless you use `st.session_state` to cache processed audio and `st.cache_data` / `@st.cache_resource` to avoid recomputation.

### Streamlit + Matplotlib

Use `st.pyplot(fig)` to render matplotlib figures. Always create explicit `fig, ax` objects rather than using pyplot's global state -- Streamlit's rerun model and matplotlib's global state do not mix well.

### librosa Sample Rate

librosa defaults to `sr=22050` on load and in analysis functions. Always pass `sr=48000` explicitly to every librosa function. Better yet: use soundfile to load audio (which preserves native sample rate) and only use librosa for analysis functions, not for loading.

### SciPy Filter Design for C Portability

Use `scipy.signal.butter()` or `scipy.signal.iirfilter()` to compute filter coefficients, then apply them with `scipy.signal.sosfilt()` (second-order sections). The SOS form maps directly to cascaded biquad structs in C -- each section is a single biquad with 6 coefficients (b0, b1, b2, a0, a1, a2). This is the standard approach for embedded audio EQ.

### NumPy Array Conventions

The project uses `(N,)` for mono and `(2, N)` for stereo. This is channel-first format, which is efficient for per-channel processing but differs from librosa's default `(N,)` mono convention. Be consistent: always check `audio.ndim` and handle both cases in every DSP function.

## Recommended pyproject.toml Dependencies

```toml
[project]
name = "claudeverb"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26,<3.0",
    "scipy>=1.12",
    "soundfile>=0.12",
    "sounddevice>=0.4.6",
    "librosa>=0.10.1",
    "matplotlib>=3.8",
    "streamlit>=1.35",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "mypy>=1.10",
]
```

### Python Version: 3.11+

Use Python 3.11 or 3.12. Python 3.11 added significant performance improvements (10-25% faster). Python 3.12 is stable and well-supported by all listed dependencies. Do not use 3.13 yet -- some scientific libraries (particularly those with C extensions) may lag on 3.13 support.

## Installation

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify
python -c "import streamlit; import numpy; import scipy; import librosa; print('All imports OK')"
```

## Sources

- NumPy, SciPy, librosa, soundfile, matplotlib, Streamlit: Based on established training data knowledge (all are mature, stable libraries with years of production use in audio/DSP domains)
- Streamlit audio capabilities: Training data knowledge of st.audio() API
- SciPy SOS filter design: Well-documented in scipy.signal official documentation
- **Version numbers are approximate** -- verify against PyPI before finalizing pyproject.toml

## Confidence Notes

| Area | Confidence | Reason |
|------|------------|--------|
| Core DSP stack (numpy/scipy) | HIGH | These are the undisputed standard for Python DSP, unchanged for years |
| Audio I/O (soundfile/sounddevice) | HIGH | Mature, stable, well-known libraries |
| Analysis (librosa) | HIGH | Industry standard, no real competitor for Python audio analysis |
| Visualization (matplotlib) | HIGH | Only option that integrates with both librosa and Streamlit |
| UI (Streamlit) | HIGH | Explicitly chosen in PROJECT.md; good fit for process-then-play |
| Streamlit audio gotchas | MEDIUM | Based on training data; Streamlit evolves quickly, verify st.audio() API |
| Exact version numbers | LOW | Could not verify against PyPI; use as floor versions and upgrade |
