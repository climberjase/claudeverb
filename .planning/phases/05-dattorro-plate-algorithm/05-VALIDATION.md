---
phase: 5
slug: dattorro-plate-algorithm
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none (uses pytest defaults, existing conftest.py) |
| **Quick run command** | `pytest tests/test_dattorro_plate.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dattorro_plate.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | ALG-02.1 | unit | `pytest tests/test_dattorro_plate.py::test_registry -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 0 | ALG-02.2 | unit | `pytest tests/test_dattorro_plate.py::test_param_specs -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | ALG-02.3 | unit | `pytest tests/test_dattorro_plate.py::test_process_mono_impulse -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | ALG-02.4 | unit | `pytest tests/test_dattorro_plate.py::test_process_stereo -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | ALG-02.5 | unit | `pytest tests/test_dattorro_plate.py::test_extreme_knobs_stable -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 1 | ALG-02.6 | unit | `pytest tests/test_dattorro_plate.py::test_no_dc_offset -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 1 | ALG-02.7 | unit | `pytest tests/test_dattorro_plate.py::test_freeze_mode -x` | ❌ W0 | ⬜ pending |
| 05-01-08 | 01 | 1 | ALG-02.8 | unit | `pytest tests/test_dattorro_plate.py::test_shimmer_mode -x` | ❌ W0 | ⬜ pending |
| 05-01-09 | 01 | 1 | ALG-02.9 | unit | `pytest tests/test_dattorro_plate.py::test_reset_deterministic -x` | ❌ W0 | ⬜ pending |
| 05-01-10 | 01 | 2 | ALG-02.10 | integration | `pytest tests/test_dattorro_plate.py::test_differs_from_freeverb -x` | ❌ W0 | ⬜ pending |
| 05-01-11 | 01 | 1 | ALG-02.11 | unit | `pytest tests/test_dattorro_plate.py::test_modulation_varies_ir -x` | ❌ W0 | ⬜ pending |
| 05-01-12 | 01 | 1 | ALG-02.12 | unit | `pytest tests/test_dattorro_plate.py::test_stereo_modes -x` | ❌ W0 | ⬜ pending |
| 05-01-13 | 01 | 1 | ALG-02.13 | unit | `pytest tests/test_dattorro_plate.py::test_output_clipped -x` | ❌ W0 | ⬜ pending |
| 05-01-14 | 01 | 1 | ALG-02.14 | unit | `pytest tests/test_dattorro_plate.py::test_delay_scaling -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dattorro_plate.py` — stubs for ALG-02 (all subtests above)

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Plate sounds audibly lusher/more diffuse than Freeverb | ALG-02 SC-2 | Subjective audio quality | Process same audio through both algorithms, listen for plate character |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
