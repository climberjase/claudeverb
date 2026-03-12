# Roadmap: ClaudeVerb

## Milestones

- v1.0 ClaudeVerb DSP Workbench -- Phases 1-5 (shipped 2026-03-06)
- v1.1 Algorithms, Real-Time & C Export -- Phases 6-10 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (6.1, 6.2): Urgent insertions (marked with INSERTED)

<details>
<summary>v1.0 ClaudeVerb DSP Workbench (Phases 1-5) -- SHIPPED 2026-03-06</summary>

- [x] Phase 1: DSP Foundation (3/3 plans) -- completed 2026-03-05
- [x] Phase 2: Audio I/O + Freeverb (3/3 plans) -- completed 2026-03-05
- [x] Phase 3: Analysis Metrics (2/2 plans) -- completed 2026-03-05
- [x] Phase 4: Engine + Streamlit UI (3/3 plans) -- completed 2026-03-06
- [x] Phase 5: Dattorro Plate Algorithm (3/3 plans) -- completed 2026-03-06

See: `.planning/milestones/v1.0-ROADMAP.md` for full details.

</details>

### v1.1 Algorithms, Real-Time & C Export

**Milestone Goal:** Expand the algorithm library (FDN, Room, Chamber, Dattorro variants), add real-time playback with live parameter tweaking, post-reverb EQ, signal-flow diagrams, and C code export for Daisy Seed.

- [x] **Phase 6: Playback Enhancements & EQ** - Multi-file loading, loop toggle, silence padding, post-reverb EQ, and Dattorro presets
- [x] **Phase 7: FDN Reverb Algorithm** - 4-channel Hadamard FDN with coprime delays and per-band decay (completed 2026-03-12)
- [ ] **Phase 8: Room, Chamber & Dattorro Variants** - Small/Large Room, Chamber, and three Dattorro topology variants
- [ ] **Phase 9: Signal-Flow Diagrams & C Export** - Graphviz algorithm diagrams and Jinja2-based C code generation for Daisy Seed
- [ ] **Phase 10: Real-Time Playback** - Live audio playback with sounddevice and real-time parameter tweaking

## Phase Details

### Phase 6: Playback Enhancements & EQ
**Goal**: Users can load multiple audio files, control playback looping, preserve reverb tails with silence padding, shape reverb tone with post-reverb EQ, and explore Dattorro parameter presets
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: PLAY-01, PLAY-02, PLAY-03, EQ-01, EQ-02, ALGO-05
**Success Criteria** (what must be TRUE):
  1. User can load 4-5 WAV files from /samples and switch between them without restarting the app
  2. User can toggle between loop and single-shot playback for any loaded clip
  3. User can append configurable silence to input audio and hear the full reverb tail decay naturally
  4. User can enable a 3-band EQ (low shelf, mid parametric, high shelf) on the reverb output and hear tonal changes
  5. User can select named Dattorro presets (Small Plate, Large Hall, Shimmer Pad, etc.) from a dropdown and hear distinct reverb characters
**Plans:** 4 plans (3 executed + 1 gap closure)
Plans:
- [x] 06-01-PLAN.md -- Biquad shelf filters, silence padding, and 3-band EQ engine integration
- [x] 06-02-PLAN.md -- Dattorro presets and multi-file WAV sample discovery
- [x] 06-03-PLAN.md -- Streamlit UI integration for all Phase 6 features
- [ ] 06-04-PLAN.md -- Gap closure: fix Dattorro preset KeyError on algorithm switch (UAT test 5)

### Phase 7: FDN Reverb Algorithm
**Goal**: Users can apply a Feedback Delay Network reverb that sounds fundamentally different from Freeverb and Dattorro Plate
**Depends on**: Phase 6
**Requirements**: ALGO-01
**Success Criteria** (what must be TRUE):
  1. User can select "FDN Reverb" from the algorithm dropdown and process audio through it
  2. FDN output is stable (no blowup or runaway feedback) across all parameter combinations
  3. FDN reverb sounds audibly distinct from Freeverb and Dattorro -- denser, more even decay without metallic coloration
  4. All 6 knobs and 2 switches produce audible, meaningful changes to the FDN output
**Plans:** 2/2 plans complete
Plans:
- [ ] 07-01-PLAN.md -- Test scaffold and FDNCore (composable 4-channel Hadamard delay network)
- [ ] 07-02-PLAN.md -- FDNReverb wrapper, presets, registry integration, and C export

### Phase 8: Room, Chamber & Dattorro Variants
**Goal**: Users can apply room-character reverbs with early reflections and explore Dattorro topology modifications
**Depends on**: Phase 7 (Room/Chamber reuse FDN late-reverb engine)
**Requirements**: ALGO-02, ALGO-03, ALGO-04, ALGO-06, ALGO-07, ALGO-08
**Success Criteria** (what must be TRUE):
  1. User can select Small Room, Large Room, and Chamber algorithms and hear distinct spatial characters for each
  2. Room algorithms produce audible early reflections (discrete echoes before diffuse tail) that distinguish them from plate reverbs
  3. User can select three Dattorro topology variants (single-loop tank, triple-diffuser, asymmetric tank) and hear differences from the standard Plate
  4. All new algorithms appear in the dropdown, have 6 knobs + 2 switches, and produce stable output across all parameter ranges
**Plans**: TBD

### Phase 9: Signal-Flow Diagrams & C Export
**Goal**: Users can visualize algorithm topology and export working C code for the Daisy Seed Hothouse pedal
**Depends on**: Phase 8 (all algorithms finalized before export)
**Requirements**: VIZ-01, EXP-01, EXP-02, EXP-03, EXP-04
**Success Criteria** (what must be TRUE):
  1. User can view a signal-flow block diagram for every algorithm showing delay lines, filters, feedback paths, and mix points
  2. User can click an export button and receive .c and .h files in /daisyexport that contain syntactically valid C
  3. Exported C code includes the user's current parameter settings as default values in comments
  4. User can see estimated RAM usage in KB before exporting, helping decide if the algorithm fits on hardware
  5. Exported code includes an AudioCallback template matching the Hothouse pedal's knob/switch layout
**Plans**: TBD

### Phase 10: Real-Time Playback
**Goal**: Users can hear reverb changes instantly by tweaking knobs during live audio playback
**Depends on**: Phase 9 (all algorithms and features stable; real-time is highest risk)
**Requirements**: PLAY-04, PLAY-05
**Success Criteria** (what must be TRUE):
  1. User can start real-time playback of a loaded WAV file and hear audio through the selected reverb algorithm continuously
  2. User can adjust any algorithm knob or switch during playback and hear the change within 100ms (no restart required)
  3. User can stop playback cleanly with a transport control button without audio glitches or app crashes
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 6 -> 6.1 -> 6.2 -> 7 -> ... -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. DSP Foundation | v1.0 | 3/3 | Complete | 2026-03-05 |
| 2. Audio I/O + Freeverb | v1.0 | 3/3 | Complete | 2026-03-05 |
| 3. Analysis Metrics | v1.0 | 2/2 | Complete | 2026-03-05 |
| 4. Engine + Streamlit UI | v1.0 | 3/3 | Complete | 2026-03-06 |
| 5. Dattorro Plate Algorithm | v1.0 | 3/3 | Complete | 2026-03-06 |
| 6. Playback Enhancements & EQ | v1.1 | 3/4 | Gap closure in progress | 2026-03-09 |
| 7. FDN Reverb Algorithm | 2/2 | Complete   | 2026-03-12 | - |
| 8. Room, Chamber & Dattorro Variants | v1.1 | 0/? | Not started | - |
| 9. Signal-Flow Diagrams & C Export | v1.1 | 0/? | Not started | - |
| 10. Real-Time Playback | v1.1 | 0/? | Not started | - |
