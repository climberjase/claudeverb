# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — ClaudeVerb DSP Workbench

**Shipped:** 2026-03-06
**Phases:** 5 | **Plans:** 14 | **Sessions:** ~10

### What Was Built
- Complete DSP primitive library (DelayLine, CombFilter, AllpassFilter, Biquad EQ) with C-portability enforced
- Two reverb algorithms: Freeverb (Schroeder-Moorer) and Dattorro Plate (figure-eight tank)
- Audio I/O with auto-resampling and 6 bundled test samples (procedurally generated)
- Acoustic analysis suite: RT60, DRR, C80/C50, spectral centroid, mel spectrogram, FFT overlay
- Streamlit web UI with process-then-play workflow, wet/dry blending, auto-generated controls
- 152 passing tests across all subsystems

### What Worked
- TDD approach for all DSP primitives caught edge cases early (float32 enforcement, block processing consistency)
- Building from primitives up (Phase 1 → algorithms → analysis → UI) gave clean dependency chain
- Facade pattern for engine.py cleanly separated DSP/analysis from UI concerns
- Phase 2 and 3 could have run in parallel (both only depend on Phase 1)
- Gap closure plans (04-03, 05-03) efficiently addressed issues found during human verification

### What Was Inefficient
- REQUIREMENTS.md traceability table was never populated — relied on PLAN frontmatter and VERIFICATION.md instead
- Roadmap plan checkboxes fell out of sync with actual completion status (some plans marked [ ] despite having SUMMARY.md)
- Nyquist validation files were created but never brought to compliant status (all partial)
- DRR metric design assumed short pre-delay; Dattorro Plate exposed this as a design limitation late

### Patterns Established
- Pre-encode WAV bytes via soundfile for Streamlit audio playback (bypasses peak normalization)
- Force algorithm mix=100 internally, use external wet/dry for clean separation
- Procedural sample generation with fixed RNG seeds for reproducible test audio
- Lazy import pattern for heavy libraries (librosa) in lightweight metric modules
- DC blocker placement: after tank output, before cross-feedback in recirculating topologies

### Key Lessons
1. C-portability constraints (fixed-size arrays, no dynamic alloc) should be enforced from the first primitive, not retrofitted — this was done right and paid off
2. Human verification items accumulate and become tech debt if not formally closed — 6 items carried to ship
3. The DRR -inf issue shows that metric parameters (direct_ms window) need to be algorithm-aware, not hard-coded
4. Streamlit's audio normalization behavior requires workarounds for accurate playback — document this for future UI work

### Cost Observations
- Model mix: primarily opus for planning/execution, sonnet for research/exploration, haiku for validation
- Timeline: 2 days from init to ship (79 commits)
- Notable: Phases 2 and 3 were sequential but could have been parallelized for faster delivery

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~10 | 5 | Initial project — established TDD, C-portability, facade patterns |

### Cumulative Quality

| Milestone | Tests | Coverage | Tech Debt Items |
|-----------|-------|----------|-----------------|
| v1.0 | 152 | — | 8 |

### Top Lessons (Verified Across Milestones)

1. (First milestone — lessons to be verified in future milestones)
