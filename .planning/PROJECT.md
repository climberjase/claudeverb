# ClaudeVerb

## What This Is

A Python DSP workbench for developing, testing, and tuning algorithmic reverb effects at 48 kHz. Users load audio samples, apply reverb algorithms with tweakable parameters (6 knobs 0–100, 2 three-position switches), listen to results, and evaluate them with acoustic analysis (spectrograms, RT60, etc.). Algorithms are designed to be portable to C for the STM32 Daisy Seed embedded audio platform.

## Core Value

A developer can hear and visually analyze the output of a reverb algorithm applied to audio, tweak its parameters, and iterate rapidly — ears and metrics together.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Load audio files (bundled samples + custom file upload) at 48 kHz
- [ ] Apply Freeverb algorithm with 6 parametric knobs and 2 three-position switches
- [ ] Apply Dattorro Plate reverb algorithm with same parameter interface
- [ ] Process-then-play workflow: tweak params, process audio, listen to result
- [ ] Wet/dry mix control for A/B listening
- [ ] Mel spectrogram visualization of input vs. processed output
- [ ] FFT / frequency analysis display
- [ ] RT60 measurement and display
- [ ] DRR, C80/C50, spectral centroid metrics
- [ ] Impulse response generation from algorithms
- [ ] Streamlit web UI for all interaction
- [ ] Algorithm selection dropdown (registry-based)
- [ ] DSP filter primitives: comb, allpass, delay line, EQ filters (HP, LP, notch, bandpass, parametric)
- [ ] All algorithms use fixed-size delay lines (circular buffers), no dynamic allocation after init
- [ ] All algorithm state representable as C structs (portability constraint)

### Out of Scope

- AU plugin loading — deferred to future milestone, focus on own algorithms first
- C code export to Daisy Seed — v2 milestone after Python workbench is solid
- Real-time audio processing with live knob tweaking — add after process-then-play works
- PySide6 desktop UI — start with Streamlit, add native UI in later milestone
- Convolution reverbs — workbench is exclusively for algorithmic reverbs
- FDN / Schroeder / Neunaber algorithms — future additions after Freeverb and Plate are solid

## Context

- Target hardware: STM32 Daisy Seed (libDaisy/DaisySP) inside a Cleveland Audio Hothouse pedal
- Audio conventions: float32 [-1.0, 1.0], mono (N,) or stereo (2, N), always 48 kHz
- Buffer size: 48 samples (matches Daisy Seed callback block size)
- All DSP primitives must be pure Python functions that map cleanly to C
- Project is greenfield — architecture docs exist but no source code yet
- LLMs will assist in algorithm design and parameter tuning

## Constraints

- **Tech stack**: Python with numpy, scipy, librosa, soundfile, matplotlib; Streamlit for UI
- **Audio format**: float32, 48 kHz, mono/stereo only
- **C portability**: No dynamic allocation after _initialize(), circular buffer delay lines only, all state as fixed-size arrays/scalars
- **Parameters**: Max 6 knobs (0–100 int range) + 2 switches (3-position: -1, 0, 1) per algorithm
- **No convolution**: Algorithm-based reverbs only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Streamlit first, PySide6 later | Faster to prototype, good enough for process-then-play workflow | — Pending |
| Process-then-play before real-time | Simpler audio pipeline, reliable, iterate on algorithm quality first | — Pending |
| Freeverb + Dattorro Plate for v1 | Freeverb is well-understood reference; Plate is desirable for guitar pedal use | — Pending |
| C export deferred to v2 | Get the listening/analysis workbench solid before worrying about embedded target | — Pending |
| AU plugin comparison deferred | Own algorithms need to work first before comparing to commercial plugins | — Pending |

---
*Last updated: 2026-03-04 after initialization*
