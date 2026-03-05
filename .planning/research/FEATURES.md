# Feature Landscape

**Domain:** Reverb algorithm development workbench (process-then-play, acoustic analysis, C export)
**Researched:** 2026-03-04
**Confidence:** MEDIUM (based on domain expertise from DSP literature, audio tool conventions, and reverb design practice; no live web verification available)

## Table Stakes

Features users expect from a reverb algorithm development workbench. Missing any of these and the tool fails its core purpose: hear it, see it, tweak it.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Audio file loading with bundled samples | Cannot evaluate reverb without input audio; bundled samples ensure immediate usability | Low | Include: drums, vocals, guitar, speech, impulse click. Resample to 48 kHz on load. |
| Algorithm selection and switching | Core workflow: compare algorithms on same input | Low | Registry-based dropdown. Freeverb + Dattorro Plate for v1. |
| Parameter knobs (6 knobs, 0-100) | Cannot tune algorithms without controls | Low | Map to algorithm-specific params (room size, damping, decay, diffusion, etc.) |
| 3-position switches (2 switches) | Part of the hardware constraint; algorithms need mode toggles | Low | Pre/post EQ mode, stereo width mode, etc. |
| Process-then-play workflow | The fundamental interaction loop: tweak, process, listen | Medium | Full buffer processing, then playback via sounddevice. Not real-time. |
| Wet/dry mix control | Essential for A/B evaluation; hearing dry vs. processed is how you judge reverb quality | Low | Single slider 0-100%. Apply at output stage, not inside algorithm. |
| Audio playback (play/stop/loop) | Must hear the result. Visual analysis alone is insufficient for reverb evaluation. | Medium | Use sounddevice for macOS system audio. Loop mode important for short samples. |
| Mel spectrogram visualization (input vs. output) | Standard visual analysis for reverb: shows frequency content over time, reveals resonances and coloration | Medium | Side-by-side or overlay. Use librosa + matplotlib rendered in Streamlit. |
| RT60 measurement and display | The single most important acoustic metric for reverb. Without RT60, you cannot characterize decay time. | Medium | Schroeder backward integration method. Display per-band (low/mid/high) not just broadband. |
| Impulse response generation | Feeds into every analysis metric; standard practice for characterizing any reverb | Low | Process a unit impulse through algorithm. Display as waveform. |
| Algorithm reset between runs | Algorithms have internal state (delay lines). Must clear between parameter changes to avoid artifacts from prior state. | Low | Call algorithm.reset() before each process run. |

## Differentiators

Features that set ClaudeVerb apart from generic DSP tools. Not expected, but they make the workbench genuinely useful for algorithm development and embedded deployment.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side algorithm comparison | Process same input through two algorithms simultaneously, view metrics and spectrograms together. Most DSP tools require manual A/B workflow. | Medium | Two-column layout: Algorithm A vs Algorithm B with synced playback position. |
| C struct memory estimation | Show estimated RAM usage for current algorithm config. Critical for 192 KB Daisy Seed target. | Low | Calculate from delay line lengths + filter state. Display as "X / 192 KB". |
| Parameter preset save/load | Save named parameter snapshots, reload later. Prevents losing good settings during exploration. | Low | JSON file per algorithm. Include algorithm name, param values, switch positions, notes field. |
| DRR (Direct-to-Reverberant Ratio) display | Tells you how "present" vs. "washed out" the signal is. Useful for guitar pedal tuning where you want reverb without losing attack. | Low | Compute from impulse response. Show alongside RT60. |
| C80/C50 clarity metrics | Standard room acoustics metrics. C80 for music, C50 for speech. Helps quantify "muddy" vs. "clear" reverb. | Low | Compute from impulse response energy ratios. |
| Spectral centroid tracking | Shows if reverb is darkening or brightening the signal. Important for "damping" parameter tuning. | Low | Compare input vs. output spectral centroid. Show delta. |
| FFT magnitude comparison (input vs. output) | Shows frequency-domain coloration introduced by the reverb. Reveals resonant peaks from comb filters. | Medium | Overlay plot with smoothing options. Highlight problematic resonances. |
| Impulse response waterfall/spectrogram | Shows how frequency content evolves during decay. Reveals uneven decay across frequency bands. | Medium | Time-frequency plot of IR. Standard in room acoustics but rare in simple DSP tools. |
| Parameter sensitivity analysis | Sweep one parameter while holding others fixed, plot metric changes. Reveals which params matter most. | High | Automated sweep + plot. Useful for understanding algorithm behavior and documenting knob ranges. |
| Batch comparison report | Process same input through all registered algorithms, generate comparison table of metrics. | Medium | HTML or in-app table. Good for algorithm selection decisions. |
| Export parameter documentation | When exporting C code, also export a markdown doc with parameter mappings (knob 1 = room_size, range 0-100 maps to 0.0-1.0, etc.) | Low | Crucial for hardware deployment. Auto-generated from param_specs. |
| Audio waveform display (input + output) | Time-domain view showing amplitude envelope. Useful for seeing reverb tail length visually. | Low | Basic but helpful. Highlight reverb tail region. |
| Stereo field visualization | Show stereo width of reverb output. Important for guitar pedals that may be mono or stereo. | Medium | Use correlation meter or stereo scope. Shows if algorithm produces true stereo or pseudo-stereo. |

## Anti-Features

Features to explicitly NOT build. These either conflict with project constraints, add complexity without value, or are premature.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time audio processing with live knob tweaking | Adds massive complexity (audio thread, lock-free queues, latency management). Process-then-play is simpler and sufficient for algorithm development. | Process full buffer on parameter change. Add real-time later as separate milestone. |
| Convolution reverb support | Explicitly out of scope. Workbench is for algorithmic reverbs only. Convolution is a fundamentally different approach. | Use impulse response analysis to characterize algorithmic reverbs, but don't implement convolution processing. |
| AU plugin loading/hosting | Requires CoreAudio framework integration, AU validation, parameter bridging. Enormous scope for v1. | Defer to future milestone. Compare algorithms against reference recordings instead. |
| DAW-style timeline/arrangement | Not needed for reverb evaluation. Adds UI complexity for zero benefit. | Simple file load + process + play is sufficient. |
| MIDI control of parameters | Premature. No use case until real-time processing exists. | Use Streamlit sliders. Add MIDI later with real-time milestone. |
| Multi-effect chains | Reverb is the focus. Chaining EQ, compression, etc. before/after adds scope. | Keep EQ filters as internal algorithm components only. External chaining is out of scope. |
| Cloud/server deployment | This is a local development tool. No need for multi-user, authentication, or cloud hosting. | Run Streamlit locally. `streamlit run app.py` is the deployment. |
| Undo/redo system | Over-engineering for a development workbench. Parameter presets solve the same need more simply. | Use parameter preset save/load instead. |
| Custom sample rate support | 48 kHz is the target (Daisy Seed). Supporting variable sample rates adds complexity to every filter coefficient calculation. | Hardcode 48 kHz. Resample on load. |
| Automated perceptual quality scoring (PESQ, ViSQOL) | These metrics are designed for speech codecs, not reverb evaluation. They would give misleading results. | Use RT60, DRR, C80, spectral centroid -- metrics that actually characterize reverb quality. |

## Feature Dependencies

```
Audio I/O (load/save) --> Everything else
  |
  +--> Algorithm base + filters --> Algorithm implementations (Freeverb, Plate)
  |                                    |
  |                                    +--> Process-then-play workflow
  |                                    |       |
  |                                    |       +--> Audio playback (sounddevice)
  |                                    |       +--> Wet/dry mix control
  |                                    |
  |                                    +--> Impulse response generation
  |                                           |
  |                                           +--> RT60 measurement
  |                                           +--> DRR, C80/C50 metrics
  |                                           +--> IR waterfall plot
  |
  +--> Spectral analysis (librosa) --> Mel spectrogram display
  |                                +--> FFT magnitude comparison
  |                                +--> Spectral centroid
  |
  +--> Algorithm registry --> Algorithm selector UI
  |                       +--> Side-by-side comparison
  |                       +--> Batch comparison report
  |
  +--> Parameter system (ParamSpec) --> Knob/switch UI controls
                                    +--> Preset save/load
                                    +--> Parameter sensitivity analysis
                                    +--> Export parameter documentation
```

Critical path: Audio I/O --> Filters --> Algorithm base --> Freeverb --> Process + Play --> Analysis metrics --> Streamlit UI

## MVP Recommendation

### Must have for v1 (table stakes that make the tool usable):

1. **Audio file loading** with 3-5 bundled samples (dry drums, guitar, vocals, speech, click/impulse)
2. **Freeverb algorithm** fully implemented with 6 knobs + 2 switches
3. **Dattorro Plate algorithm** fully implemented (the desired target for guitar pedal)
4. **Process-then-play** with play/stop controls
5. **Wet/dry mix** slider
6. **Mel spectrogram** (input vs. output, side by side)
7. **RT60 measurement** (broadband + per-band)
8. **Impulse response** generation and waveform display
9. **Algorithm selector** dropdown from registry
10. **Streamlit UI** tying it all together

### Should have for v1 (differentiators worth the low effort):

11. **DRR, C80, spectral centroid** metrics (low complexity, high value for tuning)
12. **FFT magnitude comparison** plot
13. **Parameter preset save/load** (prevents losing good settings)
14. **C struct memory estimation** (validates Daisy Seed feasibility early)
15. **Audio waveform display** (input + output time domain)

### Defer to v2:

- **Side-by-side algorithm comparison** (needs two-column UI layout work)
- **Parameter sensitivity analysis** (high complexity, nice-to-have)
- **Batch comparison report** (useful after 3+ algorithms exist)
- **Stereo field visualization** (secondary concern for v1)
- **IR waterfall/spectrogram** (medium complexity, analysis luxury)
- **C code export** (explicitly deferred per PROJECT.md)
- **AU plugin comparison** (explicitly deferred per PROJECT.md)

## Sources

- DSP domain knowledge: Schroeder (1962), Moorer (1979), Dattorro (1997) reverb design papers
- Acoustic metrics: ISO 3382 (RT60, C80, C50, DRR definitions)
- Reverb evaluation practice: standard approaches from audio engineering (impulse response analysis, spectral comparison, listening tests)
- Project constraints: PROJECT.md, ARCHITECTURE.md, CLAUDE.md specifications
- Confidence level: MEDIUM -- based on established DSP/audio engineering practice rather than live competitive analysis of current tools

---

*Feature landscape analysis: 2026-03-04*
