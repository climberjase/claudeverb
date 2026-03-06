---
phase: 1
slug: dsp-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=7.0 |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | — | scaffold | `pytest tests/ -x -q` | No | ⬜ pending |
| 01-01-02 | 01 | 1 | DSP-03 | unit | `pytest tests/test_delay_line.py -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | DSP-01 | unit | `pytest tests/test_comb_filter.py -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | DSP-02 | unit | `pytest tests/test_allpass_filter.py -x` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 2 | DSP-04 | unit | `pytest tests/test_biquad.py -x` | ❌ W0 | ⬜ pending |
| 01-01-06 | 01 | 2 | DSP-05 | unit | `pytest tests/test_c_portability.py -x` | ❌ W0 | ⬜ pending |
| 01-01-07 | 01 | 2 | DSP-06 | unit | `pytest tests/test_dtype_enforcement.py -x` | ❌ W0 | ⬜ pending |
| 01-01-08 | 01 | 2 | DSP-07 | unit | `pytest tests/test_block_processing.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — project config with pytest settings
- [ ] `claudeverb/__init__.py` — package init
- [ ] `claudeverb/config.py` — SAMPLE_RATE=48000, BUFFER_SIZE=48
- [ ] `claudeverb/algorithms/__init__.py` — ALGORITHM_REGISTRY (empty)
- [ ] `tests/__init__.py` — test package init
- [ ] `tests/conftest.py` — impulse, mono_sine, stereo_sine fixtures
- [ ] `tests/test_delay_line.py` — stubs for DSP-03
- [ ] `tests/test_comb_filter.py` — stubs for DSP-01
- [ ] `tests/test_allpass_filter.py` — stubs for DSP-02
- [ ] `tests/test_biquad.py` — stubs for DSP-04
- [ ] `tests/test_c_portability.py` — stubs for DSP-05
- [ ] `tests/test_dtype_enforcement.py` — stubs for DSP-06
- [ ] `tests/test_block_processing.py` — stubs for DSP-07

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
