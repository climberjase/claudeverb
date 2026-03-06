# Roadmap: ClaudeVerb

## Overview

ClaudeVerb delivers a Python DSP workbench for developing and evaluating algorithmic reverbs at 48 kHz. The roadmap builds from DSP primitives up through a complete listening-and-analysis workflow: foundation primitives first, then Freeverb as the reference algorithm with audio I/O, then analysis metrics validated against known signals, then the Streamlit UI tying everything into a process-then-play workflow, and finally the Dattorro Plate algorithm as the primary target for guitar pedal use.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: DSP Foundation** - Core primitives (delay lines, comb/allpass filters, EQ) with C-portability constraints enforced from the start (completed 2026-03-05)
- [x] **Phase 2: Audio I/O + Freeverb** - First complete audio path: load files, process through Freeverb, output processed audio (completed 2026-03-05)
- [x] **Phase 3: Analysis Metrics** - Quantitative analysis tools (RT60, DRR, C80, spectrograms, FFT) validated against known analytical results (completed 2026-03-05)
- [ ] **Phase 4: Engine + Streamlit UI** - Process-then-play workflow with full web interface for parameter tweaking, listening, and visual analysis (gap closure in progress)
- [ ] **Phase 5: Dattorro Plate Algorithm** - Figure-eight tank reverb with modulated delay lines, the primary target algorithm for guitar pedal deployment

## Phase Details

### Phase 1: DSP Foundation
**Goal**: All DSP building blocks exist, are tested, and enforce C-portability constraints so every algorithm built on them is portable by construction
**Depends on**: Nothing (first phase)
**Requirements**: DSP-01, DSP-02, DSP-03, DSP-04, DSP-05, DSP-06, DSP-07
**Success Criteria** (what must be TRUE):
  1. A DelayLine can be instantiated with a fixed size, written to, and read from at arbitrary tap positions -- verified by impulse test showing output at exactly sample N
  2. CombFilter and AllpassFilter produce correct output when fed an impulse signal (verified against analytical expected output)
  3. EQ filters (high-pass, low-pass, notch, bandpass, parametric) produce frequency responses matching their design specifications
  4. All primitives process float32 data exclusively and reject float64 input
  5. Block-based processing (48 samples) produces identical output to processing the same data as a single buffer
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md -- Project scaffolding + DelayLine primitive
- [x] 01-02-PLAN.md -- CombFilter + AllpassFilter primitives
- [x] 01-03-PLAN.md -- Biquad EQ filters + cross-cutting quality tests

### Phase 2: Audio I/O + Freeverb
**Goal**: A developer can load an audio file, process it through Freeverb with tweakable parameters, and get processed audio output -- the first complete signal path
**Depends on**: Phase 1
**Requirements**: AIO-01, AIO-02, AIO-04, ALG-01, ALG-03, ALG-04, ALG-05, ALG-06
**Success Criteria** (what must be TRUE):
  1. User can load a WAV or AIFF file and it is automatically resampled to 48 kHz float32
  2. Bundled test samples (dry drums, guitar, vocals, impulse click) are available without any file browsing
  3. Freeverb produces audibly correct reverb output with all 6 knobs at default positions and responds meaningfully to parameter changes
  4. Every knob position (0-100) and switch position (-1, 0, 1) produces stable output without clipping, distortion, or runaway feedback
  5. Algorithm registry returns Freeverb when queried and algorithm state fully resets between processing runs
**Plans:** 3/3 plans complete

Plans:
- [ ] 02-01-PLAN.md -- Audio I/O (load/save) + bundled test samples
- [ ] 02-02-PLAN.md -- Freeverb algorithm + registry
- [ ] 02-03-PLAN.md -- Impulse response generation + end-to-end integration

### Phase 3: Analysis Metrics
**Goal**: The workbench can quantitatively characterize any reverb output using standard acoustic metrics, giving developers numbers alongside their ears
**Depends on**: Phase 1
**Requirements**: ANLY-01, ANLY-02, ANLY-03, ANLY-04, ANLY-05, ANLY-06
**Success Criteria** (what must be TRUE):
  1. RT60 measurement of a simple comb filter impulse response matches the analytical formula within 10% tolerance
  2. DRR and C80/C50 metrics computed from a known impulse response match hand-calculated expected values
  3. Mel spectrogram visualization renders correctly for both mono and stereo audio
  4. FFT magnitude comparison plot shows input vs. output frequency content as an overlay
  5. Spectral centroid delta between input and output is computed and reported as a single number
**Plans:** 2/2 plans complete

Plans:
- [ ] 03-01-PLAN.md -- Acoustic metrics (RT60, DRR, C80/C50, spectral centroid delta)
- [ ] 03-02-PLAN.md -- Spectral visualization (mel spectrogram, FFT magnitude overlay)

### Phase 4: Engine + Streamlit UI
**Goal**: A developer can open a web browser, load audio, select an algorithm, tweak parameters, process, listen, and see analysis results -- the complete workbench workflow
**Depends on**: Phase 2, Phase 3
**Requirements**: AIO-03, PLAY-01, PLAY-02, PLAY-03, UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. User can open the Streamlit app, select an algorithm from a dropdown, and see 6 knob sliders and 2 switch selectors auto-generated from the algorithm's param_specs
  2. User can click "Process" and hear the reverb-processed audio through the browser with play/stop/loop controls
  3. Wet/dry mix slider blends between original and processed audio, audibly ranging from fully dry to fully wet
  4. After processing, spectrogram panels, waveform display, and metric readouts update automatically showing input vs. output comparison
  5. Impulse response can be generated from current algorithm settings and displayed/analyzed
**Plans:** 3 plans (2 complete + 1 gap closure)

Plans:
- [x] 04-01-PLAN.md -- Processing engine facade (process_audio, wet/dry blend, waveform plot)
- [x] 04-02-PLAN.md -- Streamlit web application + human verification
- [ ] 04-03-PLAN.md -- Gap closure: add loop=True to st.audio calls (AIO-03)

### Phase 5: Dattorro Plate Algorithm
**Goal**: The Dattorro Plate reverb is available in the workbench, producing the lush plate sound characteristic of the 1997 paper's figure-eight tank topology
**Depends on**: Phase 4
**Requirements**: ALG-02
**Success Criteria** (what must be TRUE):
  1. Dattorro Plate appears in the algorithm dropdown and is selectable with its own 6-knob/2-switch parameter set
  2. Plate reverb produces audibly distinct character from Freeverb -- lusher, more diffuse tail visible in spectrogram
  3. Impulse response shows the expected frequency smearing from tank modulation (not a static comb pattern)
  4. All parameter positions produce stable output with no DC offset accumulation, runaway feedback, or artifacts
**Plans:** 2 plans

Plans:
- [ ] 05-01-PLAN.md -- Dattorro Plate algorithm (TDD: figure-eight tank, 14 test cases)
- [ ] 05-02-PLAN.md -- Output calibration + human audio quality verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5
(Note: Phases 2 and 3 could execute in parallel since Phase 3 only depends on Phase 1)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. DSP Foundation | 3/3 | Complete | - |
| 2. Audio I/O + Freeverb | 3/3 | Complete   | 2026-03-05 |
| 3. Analysis Metrics | 2/2 | Complete   | 2026-03-05 |
| 4. Engine + Streamlit UI | 2/3 | Gap closure in progress | - |
| 5. Dattorro Plate Algorithm | 0/2 | Not started | - |
