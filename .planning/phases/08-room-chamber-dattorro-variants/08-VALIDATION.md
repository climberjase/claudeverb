---
phase: 8
slug: room-chamber-dattorro-variants
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_room_reverbs.py tests/test_dattorro_variants.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_room_reverbs.py tests/test_dattorro_variants.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 0 | ALGO-02 | unit | `pytest tests/test_room_reverbs.py::TestSmallRoom -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 0 | ALGO-03 | unit | `pytest tests/test_room_reverbs.py::TestLargeRoom -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 0 | ALGO-04 | unit | `pytest tests/test_room_reverbs.py::TestChamber -x` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 0 | ALGO-06 | unit | `pytest tests/test_dattorro_variants.py::TestSingleLoop -x` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 0 | ALGO-07 | unit | `pytest tests/test_dattorro_variants.py::TestTripleDiffuser -x` | ❌ W0 | ⬜ pending |
| 08-01-06 | 01 | 0 | ALGO-08 | unit | `pytest tests/test_dattorro_variants.py::TestAsymmetric -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | ALGO-02 | unit | `pytest tests/test_early_reflections.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_early_reflections.py` — stubs for EarlyReflections class in isolation
- [ ] `tests/test_room_reverbs.py` — stubs for ALGO-02, ALGO-03, ALGO-04 (registry, param_specs, process, stability, presets, C export)
- [ ] `tests/test_dattorro_variants.py` — stubs for ALGO-06, ALGO-07, ALGO-08 (registry, param_specs, process, stability, presets, C export)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Distinct spatial character per room type | ALGO-02, ALGO-03, ALGO-04 | Perceptual quality | Process impulse through each, listen for distinct ER patterns and tail density |
| Audible early reflections distinguishing rooms from plates | ALGO-02, ALGO-03 | Perceptual quality | A/B compare room vs plate on same input, verify discrete echoes before diffuse tail |
| Dattorro variants sound different from standard Plate | ALGO-06, ALGO-07, ALGO-08 | Perceptual quality | Process same input through standard Dattorro and each variant, listen for tonal differences |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
