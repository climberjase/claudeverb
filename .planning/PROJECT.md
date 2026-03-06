# ClaudeVerb

## What This Is

A Python DSP workbench for developing, testing, and tuning algorithmic reverb effects at 48 kHz. Users load audio samples, apply reverb algorithms (Freeverb, Dattorro Plate) with tweakable parameters (6 knobs 0–100, 2 three-position switches), listen to results via Streamlit web UI, and evaluate them with acoustic analysis (RT60, DRR, C80/C50, spectrograms, FFT). Algorithms are designed to be portable to C for the STM32 Daisy Seed embedded audio platform.

## Core Value

A developer can hear and visually analyze the output of a reverb algorithm applied to audio, tweak its parameters, and iterate rapidly — ears and metrics together.

## Requirements

### Validated

- ✓ Load audio files (bundled samples + custom file upload) at 48 kHz — v1.0
- ✓ Apply Freeverb algorithm with 6 parametric knobs and 2 three-position switches — v1.0
- ✓ Apply Dattorro Plate reverb algorithm with same parameter interface — v1.0
- ✓ Process-then-play workflow: tweak params, process audio, listen to result — v1.0
- ✓ Wet/dry mix control for A/B listening — v1.0
- ✓ Mel spectrogram visualization of input vs. processed output — v1.0
- ✓ FFT / frequency analysis display — v1.0
- ✓ RT60 measurement and display — v1.0
- ✓ DRR, C80/C50, spectral centroid metrics — v1.0
- ✓ Impulse response generation from algorithms — v1.0
- ✓ Streamlit web UI for all interaction — v1.0
- ✓ Algorithm selection dropdown (registry-based) — v1.0
- ✓ DSP filter primitives: comb, allpass, delay line, EQ filters (HP, LP, notch, bandpass, parametric) — v1.0
- ✓ All algorithms use fixed-size delay lines (circular buffers), no dynamic allocation after init — v1.0
- ✓ All algorithm state representable as C structs (portability constraint) — v1.0

### Active

(Define in next milestone)

### Out of Scope

- AU plugin loading — deferred to future milestone, focus on own algorithms first
- C code export to Daisy Seed — v2 milestone after Python workbench is solid
- Real-time audio processing with live knob tweaking — add after process-then-play works
- PySide6 desktop UI — start with Streamlit, add native UI in later milestone
- Convolution reverbs — workbench is exclusively for algorithmic reverbs
- FDN / Schroeder / Neunaber algorithms — future additions after Freeverb and Plate are solid

## Context

- Shipped v1.0 with 2,711 LOC Python + 2,387 LOC tests (152 tests passing)
- Tech stack: Python, numpy, scipy, librosa, soundfile, matplotlib, Streamlit
- Target hardware: STM32 Daisy Seed (libDaisy/DaisySP) inside a Cleveland Audio Hothouse pedal
- Audio conventions: float32 [-1.0, 1.0], mono (N,) or stereo (2, N), always 48 kHz
- Buffer size: 48 samples (matches Daisy Seed callback block size)
- All DSP primitives are pure Python functions that map cleanly to C
- Known tech debt: Biquad EQ orphaned in signal path, DRR -inf for Plate algorithm, traceability table unpopulated

## Constraints

- **Tech stack**: Python with numpy, scipy, librosa, soundfile, matplotlib; Streamlit for UI
- **Audio format**: float32, 48 kHz, mono/stereo only
- **C portability**: No dynamic allocation after _initialize(), circular buffer delay lines only, all state as fixed-size arrays/scalars
- **Parameters**: Max 6 knobs (0–100 int range) + 2 switches (3-position: -1, 0, 1) per algorithm
- **No convolution**: Algorithm-based reverbs only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Streamlit first, PySide6 later | Faster to prototype, good enough for process-then-play workflow | ✓ Good — Streamlit delivered full workbench in 2 days |
| Process-then-play before real-time | Simpler audio pipeline, reliable, iterate on algorithm quality first | ✓ Good — stable pipeline, clear separation of concerns |
| Freeverb + Dattorro Plate for v1 | Freeverb is well-understood reference; Plate is desirable for guitar pedal use | ✓ Good — both algorithms working, audibly distinct |
| C export deferred to v2 | Get the listening/analysis workbench solid before worrying about embedded target | ✓ Good — workbench solid, C portability constraints enforced |
| AU plugin comparison deferred | Own algorithms need to work first before comparing to commercial plugins | — Pending |
| Facade pattern for engine | Decouple DSP/analysis from Streamlit UI layer | ✓ Good — clean separation, testable engine |
| Pre-encode WAV bytes for Streamlit audio | Bypass Streamlit peak normalization causing loud playback | ✓ Good — volume matches external players |
| Force algorithm mix to 100 internally | UI wet/dry controls full blend range without algorithm interaction | ✓ Good — clean separation of wet/dry from algorithm params |

---
*Last updated: 2026-03-06 after v1.0 milestone*
