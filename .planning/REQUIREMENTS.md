# Requirements: ClaudeVerb

**Defined:** 2026-03-04
**Core Value:** A developer can hear and visually analyze reverb algorithm output, tweak parameters, and iterate rapidly — ears and metrics together.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Audio I/O

- [x] **AIO-01**: User can load audio files from disk (WAV/AIFF) with automatic resampling to 48 kHz
- [x] **AIO-02**: Workbench ships with bundled test samples (dry drums, guitar, vocals, impulse click)
- [x] **AIO-03**: User can play, stop, and loop processed audio output
- [x] **AIO-04**: User can generate an impulse response from any algorithm with current parameters

### DSP Foundation

- [x] **DSP-01**: Comb filter primitive with fixed-size circular buffer delay line
- [x] **DSP-02**: Allpass filter primitive with fixed-size circular buffer delay line
- [x] **DSP-03**: Delay line primitive (circular buffer, no dynamic allocation after init)
- [x] **DSP-04**: EQ filter primitives: high-pass, low-pass, notch, bandpass, parametric boost/cut
- [x] **DSP-05**: All algorithm state representable as fixed-size C arrays and scalars (no Python objects in hot path)
- [x] **DSP-06**: All audio processed as float32 in [-1.0, 1.0], mono (N,) or stereo (2, N)
- [x] **DSP-07**: Block-based processing with BUFFER_SIZE=48 samples internally

### Algorithms

- [x] **ALG-01**: Freeverb algorithm (Jezar's Schroeder-Moorer: 8 comb + 4 allpass per channel) with 6 knobs and 2 switches
- [ ] **ALG-02**: Dattorro Plate reverb algorithm (figure-eight tank topology) with 6 knobs and 2 switches
- [x] **ALG-03**: Each algorithm exposes param_specs defining knob ranges (0-100) and switch positions (-1, 0, 1)
- [x] **ALG-04**: Algorithm registry with dropdown selection in UI
- [x] **ALG-05**: Algorithm reset clears all internal state (delay lines, filter state) between parameter changes
- [x] **ALG-06**: Delay line lengths scaled for 48 kHz (not 44.1 kHz reference values)

### Processing & Playback

- [x] **PLAY-01**: Process-then-play workflow: user tweaks parameters, clicks process, listens to result
- [x] **PLAY-02**: Wet/dry mix slider (0-100%) applied at output stage, not inside algorithm
- [x] **PLAY-03**: Audio waveform display showing input and output amplitude envelopes with reverb tail visible

### Analysis

- [x] **ANLY-01**: Mel spectrogram visualization comparing input vs. processed output (side-by-side or overlay)
- [x] **ANLY-02**: RT60 measurement via Schroeder backward integration — broadband plus per-band (low/mid/high)
- [x] **ANLY-03**: DRR (Direct-to-Reverberant Ratio) computed from impulse response
- [x] **ANLY-04**: C80 and C50 clarity metrics computed from impulse response
- [x] **ANLY-05**: Spectral centroid comparison (input vs. output delta)
- [x] **ANLY-06**: FFT magnitude comparison plot (input vs. output overlay) showing reverb coloration

### Streamlit UI

- [x] **UI-01**: Streamlit web interface tying all controls and displays together
- [x] **UI-02**: Algorithm selector dropdown populated from registry
- [x] **UI-03**: Knob controls (6 sliders 0-100) and switch controls (2 three-position selectors) auto-generated from param_specs
- [x] **UI-04**: Process button triggering algorithm execution on loaded audio
- [x] **UI-05**: Analysis displays update after each process run (spectrograms, metrics, waveforms)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Interaction

- **EINT-01**: Real-time audio processing with live knob tweaking
- **EINT-02**: PySide6 desktop UI as alternative to Streamlit
- **EINT-03**: Side-by-side algorithm comparison (two-column layout)
- **EINT-04**: Parameter preset save/load (JSON snapshots)

### Advanced Analysis

- **AADV-01**: Parameter sensitivity analysis (automated sweep + metric plot)
- **AADV-02**: Batch comparison report across all registered algorithms
- **AADV-03**: Impulse response waterfall/spectrogram
- **AADV-04**: Stereo field visualization (correlation meter)

### Export & Integration

- **EXPO-01**: C code export for Daisy Seed (to_c_struct, to_c_process_fn)
- **EXPO-02**: C struct memory estimation (RAM usage vs. 192 KB target)
- **EXPO-03**: Export parameter documentation (knob mapping markdown)
- **EXPO-04**: AU plugin loading for A/B comparison

### Additional Algorithms

- **AALG-01**: Schroeder classic reverb (1962 design)
- **AALG-02**: FDN (Feedback Delay Network) reverb
- **AALG-03**: Neunaber-inspired reverb

## Out of Scope

| Feature | Reason |
|---------|--------|
| Convolution reverb | Workbench is exclusively for algorithmic reverbs |
| DAW-style timeline/arrangement | Not needed for reverb evaluation |
| MIDI control of parameters | No use case until real-time processing exists |
| Multi-effect chains | Reverb is the focus; external chaining adds scope |
| Cloud/server deployment | Local development tool only |
| Variable sample rate support | 48 kHz is the target; supporting others complicates all coefficient math |
| Perceptual quality scoring (PESQ/ViSQOL) | Designed for speech codecs, misleading for reverb |
| Undo/redo system | Parameter presets solve this more simply |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated during roadmap creation) | | |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 0
- Unmapped: 26 ⚠️

---
*Requirements defined: 2026-03-04*
*Last updated: 2026-03-04 after initial definition*
