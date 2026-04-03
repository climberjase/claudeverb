---
phase: 9
slug: signal-flow-diagrams-c-export
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 7.0 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_signal_flow.py tests/test_c_export.py -x -q` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_signal_flow.py tests/test_c_export.py -x -q`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 0 | VIZ-01 | unit | `pytest tests/test_signal_flow.py -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 0 | EXP-01, EXP-02, EXP-03, EXP-04 | unit | `pytest tests/test_c_export.py -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | VIZ-01 | unit | `pytest tests/test_signal_flow.py -x` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 1 | EXP-01 | unit | `pytest tests/test_c_export.py::test_export_generates_files -x` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 1 | EXP-02 | unit | `pytest tests/test_c_export.py::test_param_values_in_output -x` | ❌ W0 | ⬜ pending |
| 09-03-03 | 03 | 1 | EXP-03 | unit | `pytest tests/test_c_export.py::test_ram_estimation -x` | ❌ W0 | ⬜ pending |
| 09-03-04 | 03 | 1 | EXP-04 | unit | `pytest tests/test_c_export.py::test_audio_callback_template -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_signal_flow.py` — stubs for VIZ-01 (to_dot for all algorithms, DOT validity)
- [ ] `tests/test_c_export.py` — stubs for EXP-01, EXP-02, EXP-03, EXP-04

*Existing infrastructure covers framework needs (pytest already configured).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Diagram renders clearly in Streamlit | VIZ-01 | Visual layout quality subjective | Open app, select each algorithm, verify diagram is readable |
| Export preview displays correctly | EXP-01 | UI layout verification | Click "Export to C", verify .h and .c preview renders |
| Knob mapping dropdowns work | EXP-04 | UI interaction flow | Change knob assignments, verify export reflects changes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
