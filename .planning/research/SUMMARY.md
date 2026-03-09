# Project Research Summary

**Project:** ClaudeVerb v1.1 -- Algorithms, Real-Time & C Export
**Domain:** DSP reverb workbench with embedded hardware export target
**Researched:** 2026-03-07
**Confidence:** MEDIUM-HIGH

## Executive Summary

ClaudeVerb v1.1 extends a working Python DSP reverb workbench (v1.0: Freeverb + Dattorro Plate, Streamlit UI, 152 tests) with new reverb algorithms (FDN, Room, Chamber, Dattorro variants), real-time playback with live parameter tweaking, post-reverb EQ, signal-flow diagrams, and C code export targeting the Daisy Seed / Hothouse pedal. The existing codebase is well-structured with a registry-based algorithm discovery pattern, an ABC with auto-generated UI controls, and C-portability constraints already enforced. All new algorithms build exclusively on existing DSP primitives (DelayLine, CombFilter, AllpassFilter, Biquad, OnePole, DCBlocker) with only two new pip packages needed: graphviz for diagram rendering and Jinja2 for C code templates.

The recommended approach is a six-phase build that starts with foundation primitives (silence padding, TappedDelayLine, BiquadChain), then adds algorithms in dependency order (FDN first, then Room/Chamber which reuse FDN infrastructure), then integrates engine enhancements and UI features, and defers the two highest-risk features -- real-time playback and C export -- to later phases when all algorithms are stable. This ordering is driven by the dependency graph: Room/Chamber algorithms need FDN's late-reverb engine, C export needs finalized algorithm structures, and real-time playback benefits from stable algorithms that will not change underneath the audio thread.

The key risks are: (1) FDN feedback matrix instability causing audio blowup -- mitigated by using mathematically guaranteed unitary matrices (Hadamard/Householder) with automated energy-decay tests; (2) Streamlit's rerun model fundamentally conflicting with continuous audio playback -- mitigated by running sounddevice in a background thread with lock-free parameter passing; (3) C export generating code that compiles but sounds different or crashes on hardware -- mitigated by generating test harnesses, using static arrays for delay buffers, and adding float32-precision behavioral tests. Real-time Streamlit integration is the lowest-confidence area and should be treated as experimental.

## Key Findings

### Recommended Stack

The existing stack (numpy, scipy, soundfile, sounddevice, librosa, matplotlib, Streamlit) is validated and unchanged. Only two new packages are needed.

See `.planning/research/STACK.md` for full details.

**Core technologies:**
- **graphviz** (>=0.20): Signal-flow diagram rendering -- DOT language handles complex feedback topologies (Dattorro tank loops, FDN matrix connections) that would require manual coordinate math in matplotlib. Requires `brew install graphviz` system dependency.
- **Jinja2** (>=3.1): C code template engine -- already a transitive dependency of Streamlit; adding it explicitly for template-based C/C++ code generation. Templates look like C code with variable substitutions, making them reviewable.
- **No new deps for algorithms or real-time**: All new reverb algorithms use existing primitives. Real-time playback uses existing sounddevice.

### Expected Features

See `.planning/research/FEATURES.md` for full feature table and dependency graph.

**Must have (table stakes):**
- Silence padding for reverb tails -- fixes audible cutoff and inaccurate analysis metrics
- FDN reverb algorithm -- the third major reverb family; any serious workbench needs one
- Biquad EQ on reverb trails -- 3-band parametric using existing Biquad class
- C code export for Freeverb and Dattorro -- the deferred v1.0 promise
- Dattorro parameter variant presets -- easy, high-impact exploration of existing topology
- Multi-file loading with loop/single-shot toggle -- workflow improvement

**Should have (differentiators):**
- Room reverb (small/large) -- structurally different from plate, requires early reflections
- Chamber reverb -- dense, smooth character for vocals/acoustic instruments
- Signal-flow diagrams -- unique to a workbench tool; commercial reverbs hide topology
- Real-time playback with live knobs -- transforms the workflow from process-then-play
- C export via UI button with current settings baked in as defaults

**Defer (v1.2+):**
- Dattorro topology variants (modified tank structures) -- HIGH complexity, needs independent tuning
- C export for FDN/Room/Chamber -- complex state structures need careful C mapping
- Live microphone/instrument input -- massive scope increase
- Visual algorithm designer / node editor -- far beyond workbench scope

### Architecture Approach

The architecture extends v1.0's patterns: registry-based algorithm discovery, ABC with `param_specs` driving auto-generated UI, engine facade isolating DSP from Streamlit. New components slot in cleanly: algorithms in `algorithms/`, real-time engine in `audio/realtime.py`, C export in `export/`, diagrams in `diagrams/`. The critical new pattern is thread-safe parameter passing for real-time playback via atomic dict swap or `queue.Queue`, keeping the sounddevice audio thread fully decoupled from Streamlit reruns.

See `.planning/research/ARCHITECTURE.md` for full component map and data flow diagrams.

**Major components:**
1. **New algorithm files** (fdn_reverb.py, room_reverb.py, chamber_reverb.py, dattorro_variants.py) -- subclass ReverbAlgorithm, register in ALGORITHM_REGISTRY, zero UI code changes needed
2. **audio/realtime.py** -- RealtimePlayer class wrapping sounddevice.OutputStream with persistent algorithm instance stored in st.session_state
3. **export/c_codegen.py + templates/** -- Jinja2-based C code generation producing .h/.c files, main.cpp, and Makefile for Hothouse pedal
4. **filters.py additions** -- TappedDelayLine (early reflections) and BiquadChain (post-reverb EQ), both C-portable
5. **diagrams/signal_flow.py** -- renders algorithm topology as block diagrams via graphviz

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for all 14 pitfalls with detection methods.

1. **FDN feedback matrix instability** -- use Hadamard or Householder matrices (mathematically guaranteed unitary). Never construct from user parameters. Add automated energy-decay stability test.
2. **Real-time audio in Streamlit** -- Streamlit cannot do streaming audio. Use sounddevice.OutputStream in a background thread with lock-free parameter passing. Accept that UI and audio are decoupled.
3. **C export producing non-functional code** -- Python float64 intermediates vs C float32, uninitialized delay lines, stack overflow from large buffers, negative modulo. Use static arrays, memset, positive-modulo indexing, and generate a test harness.
4. **Room/Chamber sounding like plate** -- without explicit early reflections (tapped delay line), all algorithmic reverbs collapse to "diffuse tail with different decay." Use Moorer architecture, not Dattorro derivative.
5. **Dattorro topology modifications breaking stability** -- parameter variants are safe; topology variants are effectively new algorithms requiring independent tuning. Keep them separate.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation Primitives
**Rationale:** All subsequent phases depend on these building blocks. No modifications to existing code -- zero risk of breakage.
**Delivers:** Silence padding utility, TappedDelayLine filter primitive, BiquadChain filter primitive, all with tests.
**Addresses:** Silence padding (P1), EQ infrastructure (P1)
**Avoids:** Pitfall 9 (wrong padding length -- implement RT60-adaptive padding from the start)

### Phase 2: New Algorithms
**Rationale:** Algorithms are the core deliverable and must stabilize before C export or real-time playback depend on them. FDN must come first because Room/Chamber reuse its late-reverb infrastructure.
**Delivers:** FDN reverb, Room reverb (small/large), Chamber reverb, Dattorro parameter presets. All registered in ALGORITHM_REGISTRY with auto-generated UI.
**Addresses:** FDN (P1), Room/Chamber (P2), Dattorro presets (P1)
**Avoids:** Pitfall 1 (FDN matrix instability), Pitfall 5 (Room sounding like plate), Pitfall 10 (metallic FDN resonances), Pitfall 14 (exceeding 6-knob constraint)

### Phase 3: Engine Enhancements
**Rationale:** Integrates Phase 1 primitives into the processing pipeline. Modifies engine.py but changes are additive (new optional parameters).
**Delivers:** Silence padding in process pipeline, EQ post-processing on wet signal, base class methods for signal flow and C export (concrete with None defaults).
**Addresses:** EQ on trails (P1), silence padding integration
**Avoids:** Pitfall 6 (DC offset from EQ -- place after reverb, add DCBlocker)

### Phase 4: UI Features and Visualization
**Rationale:** Builds on Phase 3 engine changes. UI-only work with no DSP risk.
**Delivers:** EQ controls in sidebar, multi-file loading, loop/single-shot toggle, signal-flow diagram display, algorithm signal_flow_description() implementations.
**Addresses:** Multi-file loading (P1), loop toggle (P1), signal-flow diagrams (P2)
**Avoids:** Pitfall 11 (diagram rendering blocking UI -- pre-render as static per algorithm class), Pitfall 12 (memory from multi-file -- cap duration, lazy processing)

### Phase 5: Real-Time Playback
**Rationale:** The riskiest feature, isolated to its own phase. Benefits from all algorithms being stable. Requires careful Streamlit lifecycle management.
**Delivers:** RealtimePlayer with sounddevice callback, live parameter tweaking, transport controls (play/stop/loop).
**Addresses:** Real-time playback (P2)
**Avoids:** Pitfall 2 (Streamlit limitations), Pitfall 7 (parameter glitches), Pitfall 8 (thread safety), Pitfall 13 (loop resetting state)

### Phase 6: C Export
**Rationale:** Needs finalized algorithm structures. Template-based generation using Jinja2 targeting Hothouse pedal hardware.
**Delivers:** C struct/process code generation for Freeverb + Dattorro (minimum), export UI button, memory estimation, Makefile template.
**Uses:** Jinja2 templates, algorithm c_state_fields() methods
**Avoids:** Pitfall 4 (non-functional C code -- generate test harness, use static arrays, positive modulo, float32 behavioral test)

### Phase Ordering Rationale

- **Dependency-driven:** Room/Chamber depend on FDN infrastructure; C export depends on finalized algorithms; real-time playback benefits from stable algorithms.
- **Risk isolation:** Real-time (Phase 5) and C export (Phase 6) are the highest-risk, highest-complexity features. Deferring them means the milestone delivers value even if they slip.
- **Incremental testability:** Each phase produces independently testable outputs. Phases 1-2 are pure additions with zero risk of breaking v1.0.
- **Pitfall avoidance:** Building algorithms before export means C codegen can be tested against known-good Python outputs. Building algorithms before real-time means the audio thread processes stable code.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Algorithms):** FDN delay length selection, Room reverb early reflection tap patterns, and Moorer architecture specifics need phase-level research. The DSP literature is well-established but implementation choices (N=4 vs N=8 FDN, specific tap positions for room geometry) require targeted investigation.
- **Phase 5 (Real-Time):** Streamlit + sounddevice integration is poorly documented. The hybrid architecture (sounddevice thread + Streamlit UI) has sparse examples. Expect prototyping.
- **Phase 6 (C Export):** Daisy Seed memory layout (SDRAM vs SRAM placement), libDaisy AudioCallback signature, and Hothouse knob/switch mapping need verification against current hardware SDK.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Primitives):** Well-documented DSP building blocks. TappedDelayLine and BiquadChain are textbook.
- **Phase 3 (Engine):** Additive changes to existing facade pattern. Straightforward.
- **Phase 4 (UI):** Standard Streamlit widget patterns. No novel integration.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Only 2 new packages, both well-established. All algorithm work uses existing deps. |
| Features | MEDIUM-HIGH | Feature set well-defined. Real-time Streamlit integration is LOW confidence. |
| Architecture | HIGH | Extends proven v1.0 patterns. Component boundaries clear. Build order logical. |
| Pitfalls | HIGH | DSP pitfalls well-documented in academic literature. Threading pitfalls standard. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Real-time Streamlit integration:** No established pattern for continuous audio playback alongside Streamlit's rerun model. Will require prototyping and possibly architectural compromise. Plan for this phase to take longer than estimated.
- **C behavioral equivalence:** Python float64 intermediates vs C float32 will produce audible differences. Need to decide on acceptable tolerance and build verification tooling. No existing framework for this in the codebase.
- **Room reverb early reflection patterns:** Specific tap positions for convincing room geometry simulation need targeted research. The Moorer (1979) paper provides the framework but actual tap values for "small room" vs "large room" need tuning by ear.
- **Graphviz vs matplotlib for diagrams:** STACK.md recommends graphviz; ARCHITECTURE.md suggests matplotlib to avoid the dependency. Recommendation: use graphviz -- it is purpose-built for directed graphs and already added to deps.

## Sources

### Primary (HIGH confidence)
- [CCRMA FDN Reverberation -- Julius O. Smith](https://ccrma.stanford.edu/~jos/pasp/FDN_Reverberation.html) -- FDN theory, mixing matrices, stability
- [Dattorro "Effect Design Part 1" (1997)](https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf) -- plate reverb topology, tap positions, tuning
- [sounddevice callback docs](https://python-sounddevice.readthedocs.io/) -- real-time audio threading
- [Cleveland Music Co. Hothouse Examples](https://github.com/clevelandmusicco/HothouseExamples) -- C export target hardware specs
- [libDaisy hardware abstraction](https://github.com/electro-smith/libDaisy) -- Daisy Seed API

### Secondary (MEDIUM confidence)
- [KVR Forum: Dattorro improvements](https://www.kvraudio.com/forum/viewtopic.php?t=564078) -- topology modification risks
- [Signalsmith Audio: Let's Write A Reverb](https://signalsmith-audio.co.uk/writing/2021/lets-write-a-reverb/) -- practical FDN implementation
- [FDNTB: Feedback Delay Network Toolbox (DAFx 2020)](https://dafx2020.mdw.ac.at/proceedings/papers/DAFx2020_paper_53.pdf) -- FDN optimization
- [Streamlit community: real-time audio](https://discuss.streamlit.io/t/experience-report-working-with-realtime-audio-in-streamlit/86637) -- integration challenges
- [Dragonfly Room Reverb Manual](https://michaelwillis.github.io/dragonfly-reverb/dragonfly-room-manual.html) -- early reflection + late reverb architecture

### Tertiary (LOW confidence)
- [Efficient Optimization of FDN (2024)](https://arxiv.org/html/2402.11216v2) -- advanced FDN techniques, may not be needed for v1.1

---
*Research completed: 2026-03-07*
*Ready for roadmap: yes*
