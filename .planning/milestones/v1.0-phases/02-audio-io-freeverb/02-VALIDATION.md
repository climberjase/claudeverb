---
phase: 2
slug: audio-io-freeverb
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=7.0 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x --tb=short` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --tb=short`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | AIO-01 | unit | `pytest tests/test_audio_io.py -x` | --- W0 | pending |
| 02-01-02 | 01 | 0 | AIO-02 | unit | `pytest tests/test_samples.py -x` | --- W0 | pending |
| 02-03-01 | 03 | 0 | AIO-04 | unit | `pytest tests/test_impulse_response.py -x` | --- W0 | pending |
| 02-02-01 | 02 | 0 | ALG-01 | unit+integration | `pytest tests/test_freeverb.py -x` | --- W0 | pending |
| 02-02-02 | 02 | 0 | ALG-03 | unit | `pytest tests/test_freeverb.py::test_param_specs -x` | --- W0 | pending |
| 02-02-03 | 02 | 0 | ALG-04 | unit | `pytest tests/test_freeverb.py::test_registry -x` | --- W0 | pending |
| 02-02-04 | 02 | 0 | ALG-05 | unit | `pytest tests/test_freeverb.py::test_reset -x` | --- W0 | pending |
| 02-02-05 | 02 | 0 | ALG-06 | unit | `pytest tests/test_freeverb.py::test_delay_scaling -x` | --- W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_audio_io.py` — stubs for AIO-01 (load, resample, format support, dtype enforcement)
- [ ] `tests/test_samples.py` — stubs for AIO-02 (bundled sample availability and correctness)
- [ ] `tests/test_impulse_response.py` — stubs for AIO-04 (IR generation from algorithm)
- [ ] `tests/test_freeverb.py` — stubs for ALG-01, ALG-03, ALG-04, ALG-05, ALG-06 (Freeverb implementation, param_specs, registry, reset, scaling)
- [ ] `tests/conftest.py` — shared fixtures (already exists from Phase 1)

*Existing infrastructure covers pytest framework; only test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Freeverb sounds audibly correct | ALG-01 | Sonic quality is subjective | Load test audio, process with defaults, listen for natural-sounding reverb tail |
| Parameter changes produce meaningful audible differences | ALG-01 | Requires human listening | Adjust each knob from 0 to 100, verify reverb character changes appropriately |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
