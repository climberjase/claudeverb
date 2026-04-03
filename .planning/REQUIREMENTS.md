# Requirements: ClaudeVerb

**Defined:** 2026-03-07
**Core Value:** A developer can hear and visually analyze reverb algorithm output, tweak parameters, and iterate rapidly -- ears and metrics together.

## v1.1 Requirements

Requirements for v1.1 milestone. Each maps to roadmap phases.

### Algorithms

- [x] **ALGO-01**: User can apply FDN reverb (4-channel Hadamard, coprime delays, per-band decay) to audio
- [x] **ALGO-02**: User can apply Small Room reverb (tapped delay early reflections + FDN late reverb, short decay)
- [x] **ALGO-03**: User can apply Large Room reverb (tapped delay early reflections + FDN late reverb, long decay)
- [x] **ALGO-04**: User can apply Chamber reverb (dense diffusion, even decay, medium space character)
- [x] **ALGO-05**: User can select Dattorro parameter presets (Small Plate, Large Hall, Shimmer Pad, etc.) from dropdown
- [x] **ALGO-06**: User can apply Dattorro topology variant with modified tank structure (single-loop tank)
- [ ] **ALGO-07**: User can apply Dattorro topology variant with extended diffusion (triple-diffuser input)
- [ ] **ALGO-08**: User can apply Dattorro topology variant with asymmetric tank (wider stereo)

### EQ & Signal Chain

- [x] **EQ-01**: User can enable/disable post-reverb Biquad EQ on reverb trails
- [x] **EQ-02**: User can adjust 3-band EQ parameters (low shelf, mid parametric, high shelf) with frequency, Q, and gain controls

### Playback

- [x] **PLAY-01**: User can load multiple WAV files (4-5) from /samples and switch between them
- [x] **PLAY-02**: User can toggle loop or single-shot playback per clip
- [x] **PLAY-03**: User can append configurable silence to input for reverb tail preservation
- [ ] **PLAY-04**: User can play audio in real-time with live knob tweaking via sounddevice
- [ ] **PLAY-05**: User can start/stop real-time playback with transport controls

### Visualization

- [ ] **VIZ-01**: User can view signal-flow diagram for each algorithm rendered via Graphviz in the UI

### Export

- [ ] **EXP-01**: User can export algorithm as working .c and .h files to /daisyexport via UI button
- [ ] **EXP-02**: Exported C code includes current parameter settings as default values in comments
- [ ] **EXP-03**: User can see estimated RAM usage (KB) before exporting
- [ ] **EXP-04**: Exported C code includes Daisy Seed AudioCallback template for Hothouse pedal

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Algorithms

- **ALGO-09**: Additional Dattorro topology variants (nested allpass tank, Griesinger-style)
- **ALGO-10**: Schroeder classic reverb algorithm
- **ALGO-11**: Neunaber-inspired reverb algorithm

### Export

- **EXP-05**: C export for FDN/Room/Chamber algorithms (complex state structures)
- **EXP-06**: Automated compile-check of generated C code with arm-none-eabi-gcc

### UI

- **UI-01**: Side-by-side algorithm comparison view
- **UI-02**: Parameter sensitivity sweep automation

## Out of Scope

| Feature | Reason |
|---------|--------|
| AU plugin loading | Focus on own algorithms first |
| PySide6 desktop UI | Streamlit sufficient for workbench |
| Convolution reverbs | Algorithmic reverbs only -- C portability constraint |
| Live microphone/instrument input | v1.1 real-time is playback of loaded files only |
| Visual node-based algorithm designer | Enormous UI scope, beyond workbench purpose |
| Automated flashing to Daisy Seed | Platform-specific toolchain, user compiles manually |
| Arbitrary EQ chain length | Fixed 3-band matches Daisy Seed knob constraint |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ALGO-01 | Phase 7 | Complete |
| ALGO-02 | Phase 8 | Complete |
| ALGO-03 | Phase 8 | Complete |
| ALGO-04 | Phase 8 | Complete |
| ALGO-05 | Phase 6 | Complete |
| ALGO-06 | Phase 8 | Complete |
| ALGO-07 | Phase 8 | Pending |
| ALGO-08 | Phase 8 | Pending |
| EQ-01 | Phase 6 | Complete |
| EQ-02 | Phase 6 | Complete |
| PLAY-01 | Phase 6 | Complete |
| PLAY-02 | Phase 6 | Complete |
| PLAY-03 | Phase 6 | Complete |
| PLAY-04 | Phase 10 | Pending |
| PLAY-05 | Phase 10 | Pending |
| VIZ-01 | Phase 9 | Pending |
| EXP-01 | Phase 9 | Pending |
| EXP-02 | Phase 9 | Pending |
| EXP-03 | Phase 9 | Pending |
| EXP-04 | Phase 9 | Pending |

**Coverage:**
- v1.1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-08 after roadmap creation*
