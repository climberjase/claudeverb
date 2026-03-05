---
phase: 3
slug: analysis-metrics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=7.0 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_analysis_metrics.py tests/test_spectral.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_analysis_metrics.py tests/test_spectral.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | ANLY-02 | unit | `pytest tests/test_analysis_metrics.py::test_rt60_comb_filter -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | ANLY-02 | unit | `pytest tests/test_analysis_metrics.py::test_rt60_per_band -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 0 | ANLY-03 | unit | `pytest tests/test_analysis_metrics.py::test_drr -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 0 | ANLY-04 | unit | `pytest tests/test_analysis_metrics.py::test_c80_c50 -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 0 | ANLY-05 | unit | `pytest tests/test_analysis_metrics.py::test_spectral_centroid_delta -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 0 | ANLY-01 | unit | `pytest tests/test_spectral.py::test_mel_spectrogram_mono -x` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 0 | ANLY-06 | unit | `pytest tests/test_spectral.py::test_fft_comparison -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_analysis_metrics.py` — stubs for ANLY-02, ANLY-03, ANLY-04, ANLY-05
- [ ] `tests/test_spectral.py` — stubs for ANLY-01, ANLY-06
- [ ] `claudeverb/analysis/__init__.py` — package init with exports
- [ ] `comb_ir` fixture for RT60 validation (may extend conftest.py)

*Existing conftest.py `impulse` fixture may be reusable.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mel spectrogram visual quality | ANLY-01 | Subjective visual inspection | Run `plot_mel_comparison()` on test audio, verify axes labeled, colorbar present, both panels render |
| FFT overlay readability | ANLY-06 | Subjective visual inspection | Run `plot_fft_comparison()`, verify log-scale x-axis, both traces visible, legend present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
