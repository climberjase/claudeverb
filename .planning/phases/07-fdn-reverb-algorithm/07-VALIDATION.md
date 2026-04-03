---
phase: 07
slug: fdn-reverb-algorithm
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pyproject.toml (existing setup) |
| **Quick run command** | `python -m pytest tests/test_fdn_reverb.py -x` |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_fdn_reverb.py -x`
- **After every plan wave:** Run `python -m pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | ALGO-01.1 | unit | `pytest tests/test_fdn_reverb.py::test_registry -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | ALGO-01.2 | unit | `pytest tests/test_fdn_reverb.py::test_param_specs -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | ALGO-01.3 | unit | `pytest tests/test_fdn_reverb.py::test_process_mono_impulse -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | ALGO-01.4 | unit | `pytest tests/test_fdn_reverb.py::test_process_stereo -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | ALGO-01.5 | unit | `pytest tests/test_fdn_reverb.py::test_extreme_knobs_stable -x` | ❌ W0 | ⬜ pending |
| 07-01-06 | 01 | 1 | ALGO-01.6 | unit | `pytest tests/test_fdn_reverb.py::test_no_dc_offset -x` | ❌ W0 | ⬜ pending |
| 07-01-07 | 01 | 1 | ALGO-01.7 | unit | `pytest tests/test_fdn_reverb.py::test_freeze_mode -x` | ❌ W0 | ⬜ pending |
| 07-01-08 | 01 | 1 | ALGO-01.8 | unit | `pytest tests/test_fdn_reverb.py::test_reset_deterministic -x` | ❌ W0 | ⬜ pending |
| 07-01-09 | 01 | 1 | ALGO-01.9 | unit | `pytest tests/test_fdn_reverb.py::test_differs_from_freeverb -x` | ❌ W0 | ⬜ pending |
| 07-01-10 | 01 | 1 | ALGO-01.10 | unit | `pytest tests/test_fdn_reverb.py::test_differs_from_dattorro -x` | ❌ W0 | ⬜ pending |
| 07-01-11 | 01 | 1 | ALGO-01.11 | unit | `pytest tests/test_fdn_reverb.py::test_modulation_varies_ir -x` | ❌ W0 | ⬜ pending |
| 07-01-12 | 01 | 1 | ALGO-01.12 | unit | `pytest tests/test_fdn_reverb.py::test_stereo_modes -x` | ❌ W0 | ⬜ pending |
| 07-01-13 | 01 | 1 | ALGO-01.13 | unit | `pytest tests/test_fdn_reverb.py::test_output_clipped -x` | ❌ W0 | ⬜ pending |
| 07-01-14 | 01 | 1 | ALGO-01.14 | unit | `pytest tests/test_fdn_reverb.py::test_hadamard_butterfly -x` | ❌ W0 | ⬜ pending |
| 07-01-15 | 01 | 1 | ALGO-01.15 | unit | `pytest tests/test_fdn_reverb.py::test_size_changes_delays -x` | ❌ W0 | ⬜ pending |
| 07-01-16 | 01 | 1 | ALGO-01.16 | unit | `pytest tests/test_fdn_reverb.py::test_all_knobs_audible -x` | ❌ W0 | ⬜ pending |
| 07-01-17 | 01 | 1 | ALGO-01.17 | unit | `pytest tests/test_fdn_reverb.py::test_fdn_core_composable -x` | ❌ W0 | ⬜ pending |
| 07-01-18 | 01 | 1 | ALGO-01.18 | unit | `pytest tests/test_fdn_reverb.py::test_presets -x` | ❌ W0 | ⬜ pending |
| 07-01-19 | 01 | 1 | ALGO-01.19 | unit | `pytest tests/test_fdn_reverb.py::test_c_export -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_fdn_reverb.py` — stubs for ALGO-01 subtests 1-19
- [ ] Framework install: None needed — pytest already configured and 186+ tests pass

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FDN sounds audibly distinct from Freeverb/Dattorro | ALGO-01 SC3 | Subjective audio quality | Process impulse through all 3 algorithms, listen for denser/smoother FDN tail |
| All knobs produce audible changes | ALGO-01 SC4 | Subjective audio perception | Sweep each knob 0-100, verify audible difference at extremes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
