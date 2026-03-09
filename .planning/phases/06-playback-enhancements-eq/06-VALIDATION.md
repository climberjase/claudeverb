---
phase: 6
slug: playback-enhancements-eq
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed) |
| **Config file** | none (uses defaults) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | PLAY-01 | unit | `pytest tests/test_samples.py -x` | Exists (extend) | ⬜ pending |
| 06-01-02 | 01 | 1 | PLAY-02 | manual-only | N/A (Streamlit UI) | N/A | ⬜ pending |
| 06-01-03 | 01 | 1 | PLAY-03 | unit | `pytest tests/test_engine.py::TestSilencePadding -x` | Wave 0 | ⬜ pending |
| 06-02-01 | 02 | 1 | EQ-02 | unit | `pytest tests/test_biquad.py::TestBiquadLowShelf -x` | Wave 0 | ⬜ pending |
| 06-02-02 | 02 | 1 | EQ-01 | unit | `pytest tests/test_engine.py::TestEQ -x` | Wave 0 | ⬜ pending |
| 06-03-01 | 03 | 1 | ALGO-05 | unit | `pytest tests/test_dattorro_plate.py::TestPresets -x` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_biquad.py` — add `TestBiquadLowShelf` and `TestBiquadHighShelf` classes (shelf frequency response)
- [ ] `tests/test_engine.py` — add `TestSilencePadding` (pad length, dtype, mono/stereo)
- [ ] `tests/test_engine.py` — add `TestEQ` (EQ enable/disable, output shape, bypass)
- [ ] `tests/test_dattorro_plate.py` — add `TestPresets` (all presets produce valid params, update_params succeeds)
- [ ] `tests/test_samples.py` — add WAV file discovery tests

*Existing infrastructure covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Loop toggle controls st.audio loop param | PLAY-02 | Streamlit UI widget behavior, no headless test | 1. Load a sample 2. Toggle loop on/off 3. Verify playback behavior changes |
| Preset dropdown snaps knobs to values | ALGO-05 | Streamlit session state + visual knob sync | 1. Select preset from dropdown 2. Verify knob positions match preset values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
