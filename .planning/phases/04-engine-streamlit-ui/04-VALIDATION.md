---
phase: 4
slug: engine-streamlit-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_streamlit_app.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_streamlit_app.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | UI-01 | unit | `pytest tests/test_streamlit_app.py::test_algorithm_dropdown -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | UI-02 | unit | `pytest tests/test_streamlit_app.py::test_param_sliders -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | UI-03 | unit | `pytest tests/test_streamlit_app.py::test_process_button -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | AIO-03, PLAY-01 | unit | `pytest tests/test_streamlit_app.py::test_audio_playback -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | PLAY-02 | unit | `pytest tests/test_streamlit_app.py::test_wetdry_mix -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | PLAY-03 | manual | N/A | N/A | ⬜ pending |
| 04-03-01 | 03 | 2 | UI-04 | unit | `pytest tests/test_streamlit_app.py::test_visualizations -x` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 2 | UI-05 | unit | `pytest tests/test_streamlit_app.py::test_impulse_response -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_streamlit_app.py` — stubs for UI-01 through UI-05, AIO-03, PLAY-01, PLAY-02
- [ ] `tests/conftest.py` — shared fixtures (already exists, may need Streamlit AppTest fixtures)

*Existing pytest infrastructure covers framework needs; Streamlit AppTest stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audio audibly plays through browser | PLAY-03 | Requires human hearing verification | 1. Load audio 2. Click Process 3. Play output 4. Verify audible reverb effect |
| Wet/dry slider audibly blends dry-to-wet | PLAY-02 | Requires subjective audio assessment | 1. Process audio 2. Move wet/dry from 0 to 100 3. Verify audible blend |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
