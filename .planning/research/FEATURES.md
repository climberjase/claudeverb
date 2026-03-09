# Feature Research: v1.1 New Features

**Domain:** Reverb algorithm workbench -- new algorithms, real-time playback, EQ, C export, signal-flow diagrams
**Researched:** 2026-03-07
**Confidence:** MEDIUM-HIGH (DSP literature well-established; real-time Streamlit integration is LOW confidence)

## Feature Landscape

### Table Stakes (Users Expect These)

These are the features that make v1.1 a meaningful release over v1.0. Without them the milestone feels hollow.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Dattorro parameter variants (tank size, bandwidth, damping presets) | Users who have the Dattorro Plate already want to explore its parameter space beyond single knob positions. "Small plate", "large hall", "shimmer pad" presets using existing topology. | LOW | No new DSP code. Just curated parameter combinations stored as named presets. The existing 6-knob + 2-switch interface already covers bandwidth, damping, decay, diffusion, pre-delay, mod depth. |
| FDN reverb algorithm | The third major reverb family after Schroeder/Moorer (Freeverb) and Dattorro plate. FDN is the standard modern approach -- any reverb workbench needs one. | HIGH | 4-8 delay lines with Hadamard mixing matrix. Coprime delay lengths log-distributed. Per-band decay via biquad filters in feedback path. Significant new code but well-documented in literature. |
| Silence padding for reverb tails | Without appending silence, reverb tails get cut off abruptly at the end of the source audio. This is audibly wrong and makes analysis metrics inaccurate. | LOW | Append 2-3 seconds of zeros to input before processing. Trim output display but keep full tail for analysis. Already have the audio pipeline; just need to pad before process(). |
| Biquad EQ on reverb trails | Shaping reverb tonality is standard practice. High-cut for warmth, low-cut to remove muddiness. The Biquad class already exists in filters.py but is orphaned in the signal path. | MEDIUM | Wire existing Biquad into post-reverb signal chain. UI needs frequency, Q, gain controls per band. 3-band parametric EQ (low shelf, mid peak, high shelf) is the sweet spot for reverb shaping. |
| C code export to /daisyexport | The entire point of the C-portability constraints. Users need to actually get working .h/.c files, not just stubs. | HIGH | Must generate: struct definition, init function, process function, parameter update function. All from algorithm state. Freeverb and Dattorro have C struct comments already. Need real codegen, not just comments. |
| Real-time playback with live knob tweaking | v1.0's process-then-play forces a full re-process for every parameter change. Real-time lets users hear changes as they turn knobs -- the standard workflow for tuning reverb algorithms. | HIGH | sounddevice OutputStream callback at 48kHz/48-sample blocks. Thread-safe parameter passing to audio callback. Streamlit's rerun model conflicts with continuous audio -- this is the hardest feature. |
| Multi-file loading (4-5 files switchable) | Testing reverb across different source material (drums, guitar, vocals, speech) without re-uploading each time. | LOW | Store multiple audio arrays in session state. Radio button or tabs to switch. Already have load infrastructure. |
| Loop/single-shot toggle | Short samples need looping for sustained listening during parameter tweaking. Long samples need single-shot to hear natural decay. | LOW | Add toggle to audio player. For process-then-play: st.audio already supports loop=True. For real-time: manage loop point in callback. |

### Differentiators (Competitive Advantage)

Features that make ClaudeVerb genuinely useful beyond a generic DSP playground.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Dattorro topology variants (modified tank structures) | Go beyond parameter presets to actually different reverb topologies: single-loop tank (simpler), triple-diffuser input stage (denser), asymmetric tank (stereo), nested allpass tank (Griesinger-style). Most reverb tools treat Dattorro as one fixed topology. | HIGH | Each variant is essentially a new algorithm class inheriting from DattorroPlate but with different _initialize() and _process_impl(). The Plateau module (VCV Rack) demonstrates that size-scaling the entire tank delay network produces dramatically different character from a single topology. |
| Room reverb algorithms (small room, large room) | Plate reverbs sound like plates, not rooms. Room algorithms use early reflection patterns (tapped delay line) feeding into late diffuse reverb (FDN or comb/allpass). Different use case from plate. | HIGH | Two separate algorithm classes. Early reflections via tapped delay line with room-geometry-derived tap positions. Late reverb via FDN or parallel comb filters. Small room = short pre-delay, dense early reflections, quick decay. Large room = longer pre-delay, sparser early reflections, longer decay. |
| Chamber reverb algorithm | Medium space between room and hall. Dense, even decay. Popular for vocals and acoustic instruments. | MEDIUM | Similar structure to room reverb but with more diffusion stages and medium-length delay lines. Can share early-reflection infrastructure with room algorithms. |
| Signal-flow diagrams in UI | Visual understanding of algorithm internals. Unique to a workbench tool -- commercial reverbs hide their topology. Shows delay lines, feedback paths, filter positions, tap points. | MEDIUM | Use Graphviz DOT notation rendered via st.graphviz_chart(). Each algorithm implements a signal_flow_dot() method returning DOT source. Static diagrams are sufficient -- no need for interactive node editing. |
| C export via UI button with current settings as defaults | One-click export that captures the exact settings the user just finished tuning. The generated C code initializes with those values as defaults, so the hardware pedal sounds the same as what they just heard. | MEDIUM | Extend C codegen to accept current param_specs values. Write to /daisyexport/[algorithm_name]/. Include main.c template for Daisy Seed AudioCallback. Depends on C export infrastructure existing first. |
| C struct memory estimation in export UI | Before exporting, show "This algorithm uses X KB of 192 KB available on Daisy Seed". Prevents surprise when code doesn't fit. | LOW | Sum all delay line lengths * sizeof(float) + filter state. Already possible from algorithm introspection. Display alongside export button. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems in this specific context.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Fully interactive real-time DSP in Streamlit | "I want to turn knobs and hear changes instantly" | Streamlit's execution model reruns the entire script on every widget interaction. This kills audio continuity. streamlit-webrtc exists but adds WebRTC complexity (ICE, STUN/TURN) for what should be local audio. sounddevice callbacks run in a separate thread that Streamlit cannot easily coordinate with. | Use sounddevice in a background thread with shared parameter state. Accept 50-100ms latency from parameter updates. Do NOT try to make Streamlit widgets directly drive the audio thread -- use a polling/queue pattern instead. |
| Arbitrary EQ chain length | "Let me add as many EQ bands as I want" | More bands = more C struct state = more RAM on Daisy Seed. Also makes the UI unwieldy and the parameter space too large for 6-knob constraint. | Fixed 3-band EQ (low shelf, mid parametric, high shelf). Matches the 6-knob constraint if dedicated (freq+gain per band). Or use 2 of the 6 knobs for EQ (tone + brightness). |
| Visual algorithm designer / node editor | "Let me wire up my own reverb topology" | Enormous UI/UX scope. DSP graph compilation. Error handling for invalid topologies. Way beyond workbench scope. | Provide multiple pre-built topologies as separate algorithm classes. Let code handle new topologies. |
| Convolution-based early reflections | "Use real room impulse responses for early reflections" | Violates algorithmic-only constraint. Convolution requires FFT-based overlap-add, very different from the circular-buffer approach required for C portability. | Algorithmic early reflections via tapped delay lines with manually-tuned tap patterns that approximate room geometry. |
| Live microphone/instrument input | "Let me play guitar through the reverb in real-time" | Requires low-latency audio I/O (< 10ms), ASIO/CoreAudio integration, and the real-time DSP pipeline must be rock-solid. Huge scope increase. | v1.1 real-time is playback of loaded files only. Live input is a future milestone explicitly. |
| Automated C code compilation and flashing | "Export and flash to Daisy Seed in one click" | Requires arm-none-eabi-gcc toolchain, libDaisy build system, USB DFU flashing. Platform-specific. Way beyond workbench scope. | Export .h/.c files. User compiles with their existing Daisy toolchain. Include a Makefile template. |

## Feature Dependencies

```
Silence padding (trivial)
    |
    v
[Existing v1.0 pipeline] -----> Multi-file loading (trivial)
    |                     \----> Loop/single-shot toggle (trivial)
    |
    +---> Biquad EQ on trails
    |         Requires: Biquad class (EXISTS in filters.py)
    |         Requires: Post-reverb signal chain insertion point in engine.py
    |         Requires: UI controls for freq/Q/gain per band
    |
    +---> FDN reverb algorithm
    |         Requires: New algorithm class extending ReverbAlgorithm
    |         Requires: Hadamard matrix implementation
    |         Requires: Coprime delay length selection utility
    |         Requires: Per-band attenuation filters (can reuse Biquad)
    |
    +---> Room reverb algorithms (small/large)
    |         Requires: Tapped delay line for early reflections (new primitive)
    |         Requires: Late reverb engine (can reuse FDN or comb/allpass)
    |         Depends on: FDN reverb (shares late-reverb infrastructure)
    |
    +---> Chamber reverb algorithm
    |         Requires: Same infrastructure as Room reverb
    |         Depends on: Room reverb (shares early reflection + late reverb split)
    |
    +---> Dattorro parameter variants (presets)
    |         Requires: Preset save/load system
    |         Depends on: Existing DattorroPlate algorithm (EXISTS)
    |
    +---> Dattorro topology variants
    |         Requires: New algorithm subclasses
    |         Depends on: DattorroPlate as reference (EXISTS)
    |
    +---> Signal-flow diagrams
    |         Requires: signal_flow_dot() method on each algorithm
    |         Requires: graphviz Python package
    |         Requires: st.graphviz_chart() in Streamlit UI
    |         Depends on: All algorithms existing (renders their topology)
    |
    +---> C code export
    |         Requires: to_c_struct() and to_c_process_fn() implementations
    |         Requires: C codegen template system
    |         Requires: Export directory management
    |         Depends on: All algorithms that will be exported
    |
    +---> C export via UI button
    |         Depends on: C code export infrastructure
    |         Depends on: Streamlit UI
    |
    +---> Real-time playback with live knobs
              Requires: sounddevice OutputStream with callback
              Requires: Thread-safe parameter queue
              Requires: Audio buffer management (read position tracking)
              Requires: Loop/single-shot logic in callback
              Conflicts with: Streamlit's rerun model (needs workaround)
```

### Dependency Notes

- **Room/Chamber reverb depends on FDN:** The late reverb portion of Room/Chamber algorithms should reuse the same FDN infrastructure rather than building parallel implementations. Build FDN first, then compose it into Room/Chamber as the "late reverb engine."
- **Signal-flow diagrams depend on all algorithms:** These are documentation features -- build them last when all algorithm topologies are finalized.
- **C export depends on all algorithms:** Export code is specific to each algorithm's internal structure. Build algorithms first, export second.
- **Real-time playback conflicts with Streamlit:** This is the riskiest feature. Streamlit widgets trigger full script reruns. Audio playback needs continuous streaming. These two models fight each other. Plan for this to take the most integration effort.
- **Biquad EQ is independent:** Already have the Biquad class. Just need to wire it into the signal chain and add UI controls. Can be done at any point.
- **Silence padding and multi-file loading are trivial:** Do these first as quick wins.

## MVP Definition

### Launch With (v1.1 core)

Features needed to make this milestone meaningful.

- [ ] Silence padding for reverb tails -- quick win, fixes audible and analytical problems
- [ ] Multi-file loading with loop/single-shot toggle -- quick win, improves workflow
- [ ] Biquad EQ on reverb trails (3-band: low shelf, mid parametric, high shelf) -- wires existing code into signal path
- [ ] FDN reverb algorithm (4-channel Hadamard, coprime delays, per-band decay) -- the flagship new algorithm
- [ ] Dattorro parameter variant presets (5-8 named presets) -- easy, high impact
- [ ] C code export for Freeverb and Dattorro Plate -- the deferred v1.0 promise, now due

### Add After Core (v1.1 extended)

Features to add once core is working.

- [ ] Room reverb (small room + large room) -- once FDN infrastructure is proven
- [ ] Chamber reverb -- once Room reverb infrastructure exists
- [ ] Signal-flow diagrams for all algorithms -- once topologies are finalized
- [ ] C export via UI button with current settings as defaults -- once C codegen works
- [ ] Real-time playback with live knobs -- riskiest feature, attempt after algorithms are stable

### Future Consideration (v1.2+)

Features to defer until v1.1 is solid.

- [ ] Dattorro topology variants (modified tank structures) -- HIGH complexity, research-heavy
- [ ] C export for FDN/Room/Chamber algorithms -- complex state structures need careful C mapping
- [ ] Side-by-side algorithm comparison view -- UI layout work
- [ ] Parameter sensitivity sweeps -- nice-to-have automation

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Depends On |
|---------|------------|---------------------|----------|------------|
| Silence padding | HIGH | LOW | P1 | Nothing |
| Multi-file loading | MEDIUM | LOW | P1 | Nothing |
| Loop/single-shot toggle | MEDIUM | LOW | P1 | Nothing |
| Biquad EQ on trails | HIGH | MEDIUM | P1 | Biquad (exists) |
| Dattorro parameter presets | HIGH | LOW | P1 | DattorroPlate (exists) |
| FDN reverb algorithm | HIGH | HIGH | P1 | New code |
| C code export (Freeverb + Dattorro) | HIGH | HIGH | P1 | Algorithms (exist) |
| Room reverb (small/large) | HIGH | HIGH | P2 | FDN infrastructure |
| Chamber reverb | MEDIUM | MEDIUM | P2 | Room reverb infrastructure |
| Signal-flow diagrams | MEDIUM | MEDIUM | P2 | All algorithms |
| C export UI button | MEDIUM | MEDIUM | P2 | C codegen |
| Real-time playback + live knobs | HIGH | HIGH | P2 | sounddevice threading |
| Dattorro topology variants | MEDIUM | HIGH | P3 | Research |
| C export for new algorithms | MEDIUM | HIGH | P3 | New algorithms stable |

**Priority key:**
- P1: Must have -- defines the milestone
- P2: Should have -- makes milestone compelling
- P3: Nice to have -- defer if time-constrained

## Competitor Feature Analysis

| Feature | Dragonfly Reverb | DaisyVerb | Plateau (VCV) | Our Approach |
|---------|------------------|-----------|---------------|--------------|
| Algorithm variety | 4 algorithms (Room, Hall, Plate, Early) | Freeverb + CloudSeed | Dattorro plate only | Freeverb + Dattorro + FDN + Room + Chamber |
| Early reflections | Tapped delay line with room model | Basic | None (plate only) | Tapped delay line in Room/Chamber algorithms |
| Real-time control | Full real-time (VST plugin) | Hardware knobs | CV-controlled knobs | sounddevice callback with Streamlit parameter sync |
| C/embedded export | No | Runs on Daisy Seed directly | No | Generate .h/.c files for Daisy Seed |
| Analysis tools | None | None | None | RT60, DRR, C80, spectrograms, FFT -- unique differentiator |
| Signal-flow viz | None | None | None | Graphviz diagrams per algorithm -- unique |
| EQ on trails | Post-EQ via DAW | None | None | Built-in 3-band EQ in signal chain |

## Implementation Details for Key Features

### FDN Reverb Design

Based on Jot/Smith FDN design methodology:
- **4 delay lines** (power-of-2 count enables Hadamard fast transform)
- **Hadamard mixing matrix** -- O(N log N) multiply, no multiplies needed in fixed-point for power-of-2 sizes. Maximum determinant = optimal mixing/scattering.
- **Coprime delay lengths:** e.g., [1087, 1283, 1543, 1823] at 48kHz (logarithmically distributed primes). Maximizes mode density, avoids periodic repetition.
- **Per-band decay:** Biquad lowpass filters in each feedback path. Decay time varies by frequency band -- high frequencies decay faster (natural room behavior).
- **6 knobs:** decay, size (scales all delay lengths), damping (LP cutoff in feedback), diffusion (Hadamard mix amount vs identity), pre-delay, mod-depth
- **2 switches:** freeze/normal/shimmer, mono/stereo/wide
- **C portability:** 4 delay lines of ~2000 samples each = ~32KB float32. Fits Daisy Seed.

### Room Reverb Design

Two-stage architecture following Moorer (1979):
1. **Early reflections:** Tapped delay line with 6-12 taps. Tap positions derived from rectangular room model (image-source method). Small room: taps within 20ms. Large room: taps within 80ms.
2. **Late reverb:** FDN engine (reuse FDN algorithm's core). Crossfade from early to late at ~80ms.
- **Small Room knobs:** size (scales tap positions + FDN delays), damping, diffusion, ER/late balance, pre-delay, brightness
- **Large Room knobs:** same parameter set, different default values and delay length ranges

### Real-Time Playback Architecture

This is the riskiest feature. Streamlit's model and real-time audio are fundamentally at odds.

**Recommended approach:** Run sounddevice.OutputStream in a persistent background thread. Use a shared `threading.Event` + `queue.Queue` for parameter updates. The audio callback reads from a pre-loaded numpy array (the current source file) and applies the reverb algorithm sample-by-sample (or block-by-block at 48 samples). Streamlit widgets write parameter changes to the queue. The callback polls the queue on each block.

**Key constraint:** The algorithm's `_process_impl` currently processes the entire buffer at once. For real-time, we need per-block processing (48 samples at a time). The `process_sample` methods already exist on all filter primitives. The Dattorro algorithm already loops sample-by-sample internally. This is compatible.

**Streamlit integration challenge:** `st.audio()` is static -- it renders a fixed audio element. For real-time, we need sounddevice to bypass Streamlit's audio entirely and play directly through the system audio output. The UI shows transport controls (play/stop/loop) and parameter sliders, but audio does not flow through Streamlit.

### C Code Export Design

Each algorithm needs to generate:
1. **`[algo]_reverb.h`** -- struct typedef, function prototypes
2. **`[algo]_reverb.c`** -- init(), process(), update_params() implementations
3. **`daisy_main.c`** -- Template AudioCallback using libDaisy, with algorithm instance and knob/switch reading from Hothouse pedal hardware

The existing C struct comments in freeverb.py and dattorro_plate.py provide the struct layout. The codegen must:
- Convert numpy float32 operations to C float operations
- Convert Python loops to C for-loops
- Map delay line read/write to circular buffer pointer arithmetic
- Generate correct buffer sizes from algorithm's current delay line allocations
- Embed current parameter values as `#define` defaults

## Sources

- [FDN Reverberation -- Julius O. Smith, CCRMA Stanford](https://ccrma.stanford.edu/~jos/pasp/FDN_Reverberation.html)
- [FDN Reverberation -- DSPRelated](https://www.dsprelated.com/freebooks/pasp/FDN_Reverberation.html)
- [Dattorro (1997) Effect Design Part 1](https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf)
- [Plateau VCV Rack -- Dattorro-based reverb with size/modulation variants](https://valleyaudio.github.io/rack/plateau/)
- [Dragonfly Room Reverb Manual -- early reflection + late reverb architecture](https://michaelwillis.github.io/dragonfly-reverb/dragonfly-room-manual.html)
- [Signalsmith Audio -- Let's Write A Reverb](https://signalsmith-audio.co.uk/writing/2021/lets-write-a-reverb/)
- [DaisyVerb -- reverb algorithms for Daisy Seed](https://github.com/adion12/DaisyVerb)
- [streamlit-webrtc -- real-time audio in Streamlit](https://github.com/whitphx/streamlit-webrtc)
- [sounddevice Python documentation](https://python-sounddevice.readthedocs.io/)
- [st.graphviz_chart -- Streamlit Docs](https://docs.streamlit.io/develop/api-reference/charts/st.graphviz_chart)
- [Efficient Optimization of FDN -- arxiv 2024](https://arxiv.org/html/2402.11216v2)
- [Algorithmic Reverbs: The Moorer Design](https://christianfloisand.wordpress.com/2012/10/18/algorithmic-reverbs-the-moorer-design/)
- [Dattorro reverb improvements -- KVR Audio forum](https://www.kvraudio.com/forum/viewtopic.php?t=564078)

---
*Feature research for: ClaudeVerb v1.1 milestone*
*Researched: 2026-03-07*
