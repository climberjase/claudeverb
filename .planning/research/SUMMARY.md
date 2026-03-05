# Project Research Summary

**Project:** ClaudeVerb — Python DSP Reverb Algorithm Workbench
**Domain:** Algorithmic reverb development tool with C portability to STM32 Daisy Seed
**Researched:** 2026-03-04
**Confidence:** HIGH (DSP domain, architecture patterns); MEDIUM (Streamlit specifics, feature scope)

## Executive Summary

ClaudeVerb is a Python-first algorithm development workbench for building and evaluating algorithmic reverbs at 48 kHz, with a hard constraint that all DSP code must port cleanly to C on the STM32 Daisy Seed (192 KB RAM). Experts build tools like this with a strict layered architecture: core DSP primitives and algorithms are isolated from analysis and UI, all audio flows through a single orchestration engine, and every algorithm is written against C-portability rules from day one (fixed-size circular buffers, float32 everywhere, block-based processing at 48 samples). The scientific Python stack (NumPy, SciPy, librosa, matplotlib, Streamlit) is the clear choice — mature, well-integrated, and zero-ambiguity.

The recommended approach is to build from the bottom up: DSP primitives first (DelayLine, CombFilter, AllpassFilter), then Freeverb as the first complete algorithm, then analysis metrics (RT60, DRR, C80), then the Engine orchestrator, then the Streamlit UI, then Dattorro Plate as the primary target algorithm. This order avoids retrofitting problems and ensures every component is testable in isolation before the UI exists. A minimal Streamlit UI should be stood up early — after Freeverb works — to enable listening-driven iteration.

The two highest risks are both architectural and must be addressed from the first line of algorithm code: (1) enforcing float32 everywhere (not NumPy's default float64) to prevent Python-to-C numerical divergence, and (2) building process() around 48-sample _process_block() calls (not full-buffer vectorized operations) so block-based C behavior matches the Python prototype exactly. Both pitfalls require rewrites to fix retroactively. The Dattorro Plate implementation also carries significant complexity risk around modulated delay lines — this phase needs careful implementation against the 1997 paper's exact specifications.

## Key Findings

### Recommended Stack

The stack is unambiguous: NumPy + SciPy for all DSP computation, soundfile for audio I/O, librosa for analysis, matplotlib for visualization, and Streamlit for UI. Python 3.11 or 3.12 required. All are mature libraries with no real alternatives worth considering. The only gotcha is Streamlit's full-script-rerun execution model, which requires aggressive use of `st.session_state` and `st.cache_data` to avoid re-processing audio on every widget interaction.

See `.planning/research/STACK.md` for full version table and pyproject.toml template.

**Core technologies:**
- **NumPy >=1.26**: All DSP computation, float32 arrays — the foundation of every operation
- **SciPy >=1.12**: Filter design via `scipy.signal.butter` / `sosfilt`; second-order sections map directly to C biquad structs
- **librosa >=0.10.1**: Mel spectrograms, STFT, spectral analysis — always pass `sr=48000` explicitly
- **soundfile >=0.12**: Audio file I/O (WAV/FLAC) without ffmpeg dependency
- **sounddevice >=0.4.6**: Local audio playback via PortAudio; Streamlit `st.audio()` handles in-browser
- **matplotlib >=3.8**: Spectrogram and analysis plots via `st.pyplot(fig)` in Streamlit
- **Streamlit >=1.35**: Complete UI framework; process-then-play workflow fits its rerun model well
- **pytest >=8.0 + pytest-cov >=5.0**: Test runner with coverage; DSP code is highly testable with impulse/sine fixtures

**Do not use:** PySide6/Qt (already deferred per project), torchaudio/torch (massive dependency, numpy covers it), pydub (ffmpeg dependency), numba (optimizes Python but algorithms must port to C), pyaudio (use sounddevice instead).

### Expected Features

See `.planning/research/FEATURES.md` for full feature table and dependency graph.

**Must have (table stakes — v1):**
- Audio file loading with 3-5 bundled samples (drums, guitar, vocals, speech, impulse click)
- Freeverb fully implemented with 6 knobs + 2 switches
- Dattorro Plate algorithm fully implemented (primary target for guitar pedal use)
- Process-then-play workflow with play/stop controls
- Wet/dry mix slider (equal-power crossfade, not linear)
- Mel spectrogram display (input vs. output, side by side)
- RT60 measurement (broadband + per-band low/mid/high)
- Impulse response generation and waveform display
- Algorithm selector dropdown from registry
- Algorithm state reset between runs (clear delay lines before each process call)

**Should have (high-value, low-effort — v1):**
- DRR, C80, spectral centroid metrics (low complexity, directly useful for guitar pedal tuning)
- FFT magnitude comparison plot (reveals comb filter resonances)
- Parameter preset save/load (JSON per algorithm; prevents losing good settings)
- C struct memory estimation display (validates Daisy Seed 192 KB feasibility early)
- Audio waveform display (time-domain input + output)

**Defer to v2:**
- Side-by-side algorithm comparison (two-column UI layout complexity)
- Parameter sensitivity analysis (automated sweep, high complexity)
- Batch comparison report (more useful once 3+ algorithms exist)
- IR waterfall/spectrogram (medium complexity, analysis luxury)
- C code export / Daisy Seed deployment (explicitly deferred per PROJECT.md)
- AU plugin comparison (explicitly deferred per PROJECT.md)
- Real-time processing with live knob tweaking

### Architecture Approach

ClaudeVerb uses a strict 5-layer architecture with unidirectional data flow: Streamlit UI → Engine (orchestrator) → [DSP Algorithms | Analysis | Audio I/O]. The Engine is the sole integration point — UI never calls algorithms or analysis directly, which keeps the processing pipeline fully testable without Streamlit. Every algorithm holds mutable state (delay lines, filter memory) and implements `_process_block(block)` internally; analysis functions are pure (no state). The C-portability constraint shapes everything: algorithms may only use fixed-size pre-allocated buffers in `_initialize()`, process() must never allocate, and float32 must be enforced throughout.

See `.planning/research/ARCHITECTURE.md` for full data flow diagram, Streamlit caching patterns, and recommended directory structure.

**Major components:**
1. **DSP Primitives** (`algorithms/filters.py`) — DelayLine, CombFilter, AllpassFilter, ModulatedDelayLine; the foundation everything else builds on
2. **Algorithm Layer** (`algorithms/`) — ReverbAlgorithm ABC + ALGORITHM_REGISTRY + Freeverb + DattorroPlate; param_specs drives auto-generated UI controls
3. **Analysis Layer** (`analysis/`) — Pure functions: `rt60()`, `drr()`, `c80()`, `spectral_centroid()`, `mel_spectrogram()`, `fft_magnitude()`, `generate_impulse_response()`
4. **Engine** (`engine.py`) — Pipeline orchestrator: loads audio, runs algorithm, runs analysis, stores results in session state; the only class the UI calls
5. **Streamlit UI** (`ui/app.py` + `ui/components.py`) — Renders controls (auto-generated from param_specs), spectrograms, metrics, audio player; thin layer over Engine

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for full details and detection methods on 14 pitfalls.

1. **Float64 default will break C portability** — Enforce `np.float32` everywhere from the first line of algorithm code. NumPy defaults to float64; recursive filters accumulate rounding errors differently between precisions; the Python prototype sounds correct but the C port diverges. Fix in the base class: assert float32 on every process() entry.

2. **Full-buffer vs block-based processing mismatch** — Process() must loop over 48-sample `_process_block()` calls internally, even for long files. Vectorized numpy processing of full buffers hides state management bugs that appear catastrophically in block-based C. Verify with `test_block_equivalence()` that processes full file and sequential blocks and diffs the output.

3. **Wrong delay line lengths for 48 kHz** — Freeverb's canonical delay lengths are tuned for 44.1 kHz. Scale all lengths by `48000/44100 = 1.0884`, round to nearest prime to prevent modal buildup. Store as computed values from `_compute_delay_lengths(sample_rate)`, never hardcoded.

4. **Circular buffer index bugs (off-by-one, modulo)** — Implement a single `DelayLine` class used by all algorithms. Write a unit test: process an impulse, verify it appears at exactly sample N in the output. Python's `-1 % 5 == 4` but C's `-1 % 5 == -1` — use `(index + 1) if (index + 1) < length else 0` to avoid modulo entirely.

5. **Comb filter feedback instability at extreme parameters** — Hard-clamp all feedback coefficients to `abs(g) < 0.999` in `update_params()`. Test all 101 knob positions (0-100) and verify no setting produces `g >= 1.0`. Add output clamping with a warning log in process().

## Implications for Roadmap

Based on combined research, the architecture's explicit dependency graph and the pitfall severity matrix suggest the following phase structure. All phases should be gated on tests passing — the workbench is only trustworthy if its measurements are trustworthy.

### Phase 1: DSP Foundation
**Rationale:** Architecture and pitfalls research agree: the DelayLine class must be built and exhaustively tested before any algorithm code. Circular buffer bugs and float32 violations here corrupt every downstream component. Cannot parallelize with anything.
**Delivers:** `config.py`, `algorithms/base.py` (ReverbAlgorithm ABC, ReverbParams, ParamSpec), `algorithms/filters.py` (DelayLine, CombFilter, AllpassFilter with correct sign convention); all with unit tests including impulse verification.
**Addresses:** Algorithm reset, parameter specs system, audio shape conventions ((N,) mono / (2,N) stereo float32)
**Avoids:** Circular buffer index bugs (Pitfall 3), allpass sign errors (Pitfall 11), float64 default (Pitfall 2)
**Research flag:** Standard DSP patterns — no phase research needed. Dattorro 1997 and Freeverb source are sufficient references.

### Phase 2: Audio I/O + Freeverb
**Rationale:** First end-to-end audio path. Freeverb is the simpler algorithm and a well-documented reference implementation, making it the right first algorithm. Audio I/O is a prerequisite for any listening. Block-based processing must be architected into Freeverb from the start.
**Delivers:** `audio/io.py` with auto-resample to 48 kHz; bundled sample files (clap, snare, guitar, speech, impulse); `algorithms/freeverb.py` fully implemented with 6 knobs + 2 switches; ALGORITHM_REGISTRY; `test_block_equivalence()` test.
**Addresses:** Audio file loading, Freeverb algorithm, process-then-play kernel, algorithm selector
**Avoids:** Sample-rate-dependent delay lengths (Pitfall 1), full-buffer vs block mismatch (Pitfall 5), feedback instability at extreme params (Pitfall 4)
**Research flag:** Standard patterns — no phase research needed.

### Phase 3: Analysis Metrics
**Rationale:** Analysis is independent of algorithms and can be built/tested in isolation using test signals with known analytical answers. RT60 implementation errors are a common failure mode — validate against analytical formulas before the UI uses these numbers. This phase gives the workbench its quantitative backbone.
**Delivers:** `analysis/spectral.py` (mel_spectrogram, fft_magnitude, stft); `analysis/metrics.py` (rt60, drr, c80, spectral_centroid); `analysis/impulse.py` (generate_impulse_response); all validated against known analytical results.
**Addresses:** RT60 measurement, DRR, C80, spectral centroid, mel spectrogram, FFT comparison, impulse response
**Avoids:** RT60 measurement errors (Pitfall 10) — validate T20/T30 method against single comb filter with known analytical RT60
**Research flag:** Standard signal processing — Schroeder backward integration is well-documented. No phase research needed.

### Phase 4: Engine + Minimal Streamlit UI
**Rationale:** The Engine wires all prior phases together. Once Engine works, a minimal Streamlit UI can be stood up to enable listening-driven iteration — hearing the algorithm is the fastest feedback loop for reverb development. Process-then-play model with explicit "Process" button avoids Streamlit rerun performance pitfalls.
**Delivers:** `engine.py` (full pipeline: load → algorithm → wet/dry mix → analysis → ProcessResult); `ui/app.py` with algorithm selector, param knobs/switches, Process button, st.audio() player, mel spectrogram panels, RT60 display; parameter preset save/load.
**Addresses:** Process-then-play workflow, wet/dry mix control (equal-power crossfade), audio playback, spectrogram display, metric display, algorithm selection, preset save/load
**Avoids:** Streamlit audio playback limitations (Pitfall 9) — aggressive caching, explicit Process button; wet/dry mix artifacts (Pitfall 8) — equal-power crossfade
**Research flag:** Streamlit `st.audio()` numpy array support and caching behavior should be verified against current Streamlit docs at implementation time. MEDIUM confidence on these specifics.

### Phase 5: Dattorro Plate Algorithm
**Rationale:** The primary target algorithm for the guitar pedal goal. More complex than Freeverb due to the figure-8 tank topology and modulated delay lines. Infrastructure from Phases 1-4 must exist first — in particular the analysis tools to verify the reverb quality by impulse response inspection.
**Delivers:** `algorithms/dattorro_plate.py` fully implemented including ModulatedDelayLine with linear interpolation, correct tank modulation per Dattorro 1997 paper; integrated into UI via ALGORITHM_REGISTRY.
**Addresses:** Dattorro Plate algorithm, ModulatedDelayLine, stereo cross-coupling, C struct memory estimation
**Avoids:** Dattorro modulation errors (Pitfall 6) — implement ModulatedDelayLine with fractional delay, verify via impulse response spectrogram showing frequency smearing; DC offset accumulation (Pitfall 7) — add DC-blocking filter at comb filter outputs; stereo as two independent mono reverbs (Pitfall 12) — use figure-8 tank topology
**Research flag:** Dattorro 1997 paper (J. Audio Eng. Soc. 45(9)) is the canonical reference and highly detailed. Phase-level research not needed, but implementor must read the paper section on tank modulation carefully.

### Phase 6: Extended Analysis + Comparison Features
**Rationale:** After both algorithms work correctly, higher-value analysis features (waveform display, C memory estimation, audio waveform display) and comparison groundwork can be added. These are the "should have" differentiators that make the workbench genuinely useful for tuning.
**Delivers:** Audio waveform display (input + output time domain); C struct memory estimation panel (X / 192 KB); FFT magnitude comparison overlay; batch metric display for multiple runs; export parameter documentation (knob mapping docs auto-generated from param_specs).
**Addresses:** All "should have" features from FEATURES.md; export parameter documentation
**Avoids:** Testing by ear alone (Meta-Pitfall) — quantitative metrics panels reinforce metric-first workflow
**Research flag:** Standard patterns — no phase research needed.

### Phase Ordering Rationale

- **Foundation before algorithms:** The DelayLine bug class (circular buffer, allpass sign, float32) corrupts everything downstream. Fixing these in isolation is 10x easier than debugging them through a complete algorithm.
- **Freeverb before Plate:** Freeverb is well-documented and simpler; it validates the infrastructure before tackling Dattorro's more complex topology.
- **Analysis before Engine:** Pure analysis functions can be unit-tested with known signals independent of any algorithm. Validating RT60 against an analytical formula from a simple comb filter is faster and more reliable than validating it against full Freeverb output.
- **Engine before full UI:** The Engine makes the pipeline testable in pytest without Streamlit. This is the correct integration order — test the pipeline first, then add the UI surface on top.
- **Early minimal UI:** Despite the formal ordering, a minimal Streamlit app should be stood up after Phase 2 Freeverb works, even before full analysis exists, to enable listening tests. Hearing the output is the fastest way to catch wrong delay lengths, tone coloration, and instability at extreme settings.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Streamlit UI):** Streamlit `st.audio()` numpy array API and caching behavior evolves quickly; verify `st.audio(numpy_array, sample_rate=48000)` against current Streamlit docs before designing the playback component. MEDIUM confidence.
- **Phase 5 (Dattorro Plate):** Implementor must work directly from Dattorro 1997 paper for the tank topology and modulation parameters. Dense notation — allocate extra implementation time.

Phases with standard patterns (skip research-phase):
- **Phase 1 (DSP Foundation):** Circular buffers, biquad filters, and allpass topology are textbook DSP. No external research needed.
- **Phase 2 (Freeverb):** Jezar's original implementation is public domain and widely documented. Scale delay lengths to 48 kHz, enforce float32.
- **Phase 3 (Analysis):** Schroeder backward integration for RT60, ISO 3382 metrics — established signal processing literature.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Mature, stable libraries; no ambiguity in choices. Version numbers are approximate — verify against PyPI at implementation time. |
| Features | MEDIUM | Based on DSP domain expertise and reverb engineering practice, not live competitive analysis. Feature set is well-reasoned for the stated purpose. |
| Architecture | HIGH | Layered architecture and C-portability patterns are established in embedded audio engineering. Streamlit-specific details (caching, st.audio) are MEDIUM — evolves quickly. |
| Pitfalls | HIGH | All pitfalls drawn from 25+ year old, well-documented algorithms (Freeverb, Dattorro). Core DSP engineering principles are stable. |

**Overall confidence:** HIGH for DSP/architecture decisions; MEDIUM for UI tooling specifics.

### Gaps to Address

- **Streamlit st.audio() numpy support:** Research noted MEDIUM confidence. Verify `st.audio(array, sample_rate=48000)` syntax against current Streamlit 1.35+ docs before Phase 4 implementation. Fallback: write float32 numpy array to a BytesIO buffer as WAV using soundfile.
- **Exact pyproject.toml versions:** Version floor numbers in STACK.md are based on training data, not live PyPI. Run `pip install --upgrade` and record actual resolved versions before finalizing pyproject.toml.
- **Dattorro modulation specifics:** The paper's notation for excursion values and LFO frequencies should be treated as the ground truth. No inference needed — just requires careful reading.
- **Schroeder algorithm (stub):** The existing codebase has a Schroeder stub in `algorithms/`. This is neither Freeverb nor Dattorro Plate — its role in the roadmap is undefined by research. Treat as a future v2 algorithm; don't block on it.
- **PySide6 migration:** The existing codebase uses PySide6 (pre-research). Research recommends migrating to Streamlit as the UI framework for v1. This represents a rewrite of the UI layer — the migration cost should be acknowledged in roadmap planning.

## Sources

### Primary (HIGH confidence)
- Dattorro, J. (1997). "Effect Design Part 1: Reverberator and Other Filters." JAES 45(9), 660-684 — Plate reverb topology, tank modulation, allpass filter design
- Jezar's Freeverb source code (public domain, ~2000) — Freeverb delay line lengths, comb/allpass topology
- Smith, J.O. "Physical Audio Signal Processing" — CCRMA Stanford — RT60 formula, comb filter stability theory
- ISO 3382 — RT60, C80, C50, DRR definitions

### Secondary (MEDIUM confidence)
- NumPy, SciPy, librosa, soundfile, matplotlib, Streamlit documentation — Stack recommendations based on training data knowledge of established library capabilities
- Streamlit execution model and st.audio() API — training data, verify against current docs

### Tertiary (LOW confidence)
- Exact version numbers in STACK.md — approximate, based on training data; verify against PyPI before committing to pyproject.toml
- Streamlit numpy audio playback specifics — version-dependent, needs verification at implementation time

---
*Research completed: 2026-03-04*
*Ready for roadmap: yes*
