# Technology Stack

**Project:** ClaudeVerb v1.1 -- Algorithms, Real-Time & C Export
**Researched:** 2026-03-07
**Scope:** NEW additions only. Existing stack (numpy, scipy, soundfile, sounddevice, librosa, matplotlib, streamlit) is validated and unchanged.

## New Stack Additions for v1.1

Only **two** new packages are needed. Everything else builds on existing dependencies.

### 1. graphviz (Python package) -- Signal-Flow Diagram Rendering

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| graphviz | >=0.20 | Render algorithm signal-flow diagrams as SVG for Streamlit display | DOT language is purpose-built for directed graph layout. Automatically handles complex feedback topologies (Dattorro tank loops, FDN matrix connections) that would require manual coordinate math in matplotlib. Renders to SVG for crisp display at any size. |

**Integration pattern:** Each `ReverbAlgorithm` subclass provides a `signal_flow_dot() -> str` method returning DOT source. The engine renders it to SVG bytes via `graphviz.Source(dot_str).pipe(format='svg')`. Streamlit displays with `st.image(svg_bytes)`.

**System dependency required:** The Python `graphviz` package is a binding that calls the Graphviz system binary. Install with `brew install graphviz` on macOS.

**Alternatives evaluated and rejected:**

| Alternative | Why Rejected |
|-------------|-------------|
| matplotlib (manual drawing) | Not a graph layout engine. Drawing boxes and arrows with manual coordinates for Dattorro's figure-eight tank topology or an 8x8 FDN matrix would be brittle and ugly. |
| schemdraw | Designed for electrical circuit schematics with specific component symbols. Wrong abstraction for DSP signal-flow graphs. |
| bdsim | Full block diagram simulation framework. We need rendering only, not simulation. Overkill dependency. |

**Confidence:** HIGH -- graphviz is the standard tool for directed graph rendering (used by Doxygen, Sphinx, etc.), actively maintained, SVG output integrates cleanly with Streamlit.

### 2. Jinja2 -- C Code Export Templates

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Jinja2 | >=3.1 | Template-based C/C++ code generation for Daisy Seed / Hothouse export | Generates readable C source files from algorithm state. Templates look like C code with `{{ variable }}` substitutions, making them reviewable and maintainable. |

**Why adding explicitly:** Jinja2 is already installed as a transitive dependency of Streamlit (Streamlit depends on it). Adding it to `dependencies` makes the dependency explicit and version-pinned.

**Integration pattern:** Each algorithm provides a `to_c_context() -> dict` method returning delay sizes, coefficient values, and parameter defaults from current knob positions. Jinja2 templates produce:

```
/daisyexport/
  algorithm_name.h       -- C struct definition, init/process declarations
  algorithm_name.c       -- C implementation (delay lines, filters, etc.)
  main.cpp               -- Hothouse boilerplate: hardware init, knob mapping, AudioCallback
  Makefile               -- libDaisy/DaisySP build integration
```

**Alternatives evaluated and rejected:**

| Alternative | Why Rejected |
|-------------|-------------|
| f-strings / string concatenation | Nested braces in C code conflict with Python format strings. Indentation is error-prone. Templates cannot be reviewed as standalone C files. |
| Full AST-based code generator | Overkill. Algorithms have known, fixed structure. Value substitution in templates covers the need. |
| Mako / Cheetah | Less popular, no advantage over Jinja2 which is already installed. |

**Confidence:** HIGH -- Jinja2 is the standard Python template engine, already a transitive dependency, well-documented.

## No New Dependencies for Algorithm Work

All new reverb algorithms (FDN, Room, Chamber, Dattorro variants) use exclusively existing primitives:

| New Algorithm | Existing Primitives Used |
|---------------|--------------------------|
| Dattorro topology variants | `AllpassFilter`, `DelayLine`, `OnePole`, `DCBlocker` -- vary delay lengths, tap positions, diffusion block count |
| FDN reverb | `DelayLine` (N parallel lines) + `scipy.linalg.hadamard` or hardcoded matrix + `OnePole` for per-line damping |
| Room reverb (small/large) | `DelayLine` (early reflection taps) + `CombFilter` bank + `AllpassFilter` cascade. Distinct delay times model room geometry. |
| Chamber reverb | Dense `AllpassFilter` cascade + `CombFilter` bank + `DelayLine`. Higher diffusion density than Room for smoother tail. |

**FDN feedback matrix:** `scipy.linalg.hadamard(N)` generates the Hadamard matrix. Normalize by `1/sqrt(N)` for energy preservation. For N=4 or N=8 FDN, the matrix is small enough to hardcode in the C export (no BLAS needed on Daisy Seed -- just 16 or 64 multiply-adds per sample).

**Confidence:** HIGH -- all primitives exist with tests. FDN is well-documented in Julius O. Smith's "Physical Audio Signal Processing." Hadamard matrix is in scipy.

## No New Dependencies for Real-Time Playback

Real-time playback uses **sounddevice**, which is already in `pyproject.toml`.

**Architecture:**

```
Streamlit UI Thread                    sounddevice Audio Thread
+-----------------------+              +---------------------------+
| Slider changes ------>| shared_state | ----> audio_callback()    |
| (knobs, switches)     | (Lock-guarded)|      read current params  |
|                       |              |      read source block     |
| Play/Stop button ---->| play_state   |      algo.process(block)  |
|                       |              |      write to outdata     |
| Loop/Single toggle -->| loop_mode    |      advance read pointer |
+-----------------------+              +---------------------------+
```

Use `sd.OutputStream(samplerate=48000, blocksize=48, channels=2, callback=audio_callback)`. The 48-sample blocksize matches the Daisy Seed callback size exactly. Parameter changes from Streamlit sliders are picked up on the next callback invocation (48 samples = 1ms latency at 48 kHz).

**Why NOT streamlit-webrtc:** streamlit-webrtc routes audio through WebRTC (browser <-> server). ClaudeVerb processes audio server-side and plays to the server's local audio device. sounddevice is the correct model for a local DSP workbench. streamlit-webrtc adds PyAV dependency, TURN server complexity, and browser audio API constraints with no benefit.

**Why NOT streamlit-advanced-audio (Audix):** Immature component (released Nov 2024). Standard `st.audio()` + sounddevice callback covers all needs. Does not support DSP callback injection.

**Thread safety:** Use `threading.Lock` to guard shared parameter state between the Streamlit main thread and the sounddevice callback thread. The algorithm's `update_params()` method is called inside the callback with the lock held, reading from a shared dict that Streamlit writes to.

**Confidence:** HIGH -- sounddevice callback API is well-documented. The project's block size and sample rate were specifically chosen to match Daisy Seed.

## Hothouse C Export Target Details

The generated C code targets the Cleveland Music Co. Hothouse pedal (Daisy Seed-based):

| Hardware Feature | Spec | Mapping |
|------------------|------|---------|
| Potentiometer knobs | 6 (ADC pins, 0.0-1.0 float) | Maps to algorithm's 6 knobs (scaled from 0-100 int range) |
| Toggle switches | 3 (3-position: up/mid/down) | Project uses 2 of 3 for algorithm switches (-1, 0, 1) |
| Footswitches | 2 (momentary) | Bypass/engage, secondary function |
| Audio I/O | Stereo (AK4556 codec) | Mono-to-stereo or stereo-to-stereo |
| Sample rate | 48 kHz | Matches `SAMPLE_RATE = 48000` |
| Block size | 48 samples (typical) | Matches `BUFFER_SIZE = 48` |
| Build system | arm-none-eabi-gcc + Make | libDaisy Makefile template |

**C code constraints (matching existing project rules):**
- No dynamic allocation after init -- all delay lines are fixed-size arrays
- All state representable as C structs with fixed-size members
- Generated code is plain C (`.h` + `.c`), callable from C++ `main.cpp` via `extern "C"` linkage
- The Hothouse `main.cpp` template handles hardware init (DaisySeed, ADC, GPIO) and calls the algorithm's C `process()` inside `AudioCallback`

**Confidence:** HIGH -- Hothouse hardware specs confirmed via clevelandmusicco/HothouseExamples repository. The project's C portability constraints were designed for this target.

## Updated pyproject.toml Dependencies

```toml
[project]
dependencies = [
    "numpy>=1.24",
    "scipy>=1.10",
    "soundfile",
    "sounddevice",
    "librosa",
    "matplotlib",
    "streamlit>=1.38",
    "graphviz>=0.20",
    "Jinja2>=3.1",
]
```

## System Dependencies

```bash
# macOS -- required for the graphviz Python package to call the Graphviz layout engine
brew install graphviz
```

## Summary: What Changes, What Does Not

| Category | Change | Details |
|----------|--------|---------|
| New pip packages | 2 added | `graphviz>=0.20`, `Jinja2>=3.1` |
| System packages | 1 added | `graphviz` via Homebrew |
| Algorithm code | 0 new deps | All built from existing `DelayLine`, `AllpassFilter`, `CombFilter`, `OnePole`, `Biquad` |
| Real-time playback | 0 new deps | Uses existing `sounddevice` |
| Existing deps | 0 changed | numpy, scipy, soundfile, librosa, matplotlib, streamlit all stay as-is |

## Sources

- [sounddevice callback-based streaming docs](https://python-sounddevice.readthedocs.io/en/0.4.1/usage.html)
- [graphviz Python package user guide](https://graphviz.readthedocs.io/en/stable/manual.html)
- [Jinja2 template engine](https://jinja.palletsprojects.com/)
- [Cleveland Music Co. Hothouse Examples (C++ templates, knob/switch mapping)](https://github.com/clevelandmusicco/HothouseExamples)
- [DaisyVerb -- Reverb algorithms for Daisy Seed (FDN, Freeverb, Dattorro)](https://github.com/adion12/DaisyVerb)
- [libDaisy hardware abstraction library](https://github.com/electro-smith/libDaisy)
- [FDN Reverberation -- Julius O. Smith, Physical Audio Signal Processing](https://www.dsprelated.com/freebooks/pasp/FDN_Reverberation.html)
- [FDNTB: Feedback Delay Network Toolbox (DAFx 2020)](https://dafx2020.mdw.ac.at/proceedings/papers/DAFx2020_paper_53.pdf)
- [streamlit-webrtc (evaluated, rejected for this use case)](https://github.com/whitphx/streamlit-webrtc)
- [Hothouse pedal hardware specs](https://clevelandmusicco.com/hothouse-diy-digital-signal-processing-platform-kit/)

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| graphviz for diagrams | HIGH | Standard tool, well-maintained, SVG output confirmed |
| Jinja2 for C export | HIGH | Already a transitive dep, standard template engine |
| sounddevice for real-time | HIGH | Already installed, callback API documented, block size matches |
| No new algo deps | HIGH | All primitives exist and are tested in v1.0 |
| Hothouse C target | HIGH | Hardware specs confirmed via official examples repo |
| streamlit-webrtc rejection | HIGH | Wrong architecture for local server-side DSP playback |
