# Fable Deep Research: Modal Reverberators

**Date:** 2026-07-05

> A39 the Abel modal architecture (fitted resonator banks for spring tanks, EMT 140 plates and rooms, plus pitch/time-warp effects). See also A21 (modal spring) and A26 (modal plate) in the spring/plate files.
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.

## A39. Modal reverberator (Abel) — thousands of resonators, fitted to hardware


**Papers/patents:** Abel, Coffin, Spratt, "A Modal Architecture for Artificial Reverberation with Application to Room Acoustics Modeling," AES 137 (2014) — https://www.aes.org/e-lib/online/browse.cfm?elib=17531; US 9,805,704 B1 — https://patents.google.com/patent/US9805704B1/en; pitch/distortion applications: Abel & Werner, DAFx-15 — https://www.ntnu.edu/documents/1001201110/1266017954/DAFx-15_submission_72.pdf

**Math:** the IR is a sum of decaying sinusoids; synthesize with one complex one-pole per mode:

```
y_m(n) = a_m·y_m(n−1) + b_m·x(n),    a_m = e^{(−1/τ_m + jω_m/fs)}
y(n)   = Re{ Σ_m γ_m y_m(n) }
τ_m    = fs·T60(ω_m)/ln(1000)   ⇔   |a_m| = 10^(−3/(fs·T60(ω_m)))
```

(real-biquad equivalent: `y = 2R cosθ·y₁ − R²·y₂ + g·x`). Mode parameters fitted from measured IRs (STFT ridge analysis; subband ESPRIT — DAFx-18: https://www.dafx.de/paper-archive/2018/papers/DAFx2018_paper_56.pdf). **Phase randomization** of γ_m = instant new source/listener positions in the same room, and prevents onset "click."

**Why it's on this list:** it is *the* published architecture behind convincing **Fender spring-tank and EMT 140 emulations** (fit the measured poles → you own the device), and the heterodyne form exposes ω_m for legal abuse — **pitch-shifted reverb, spectral inversion, time-stretch without pitch change** (DAFx-15). Time-varying mode frequencies de-metallicize like matrix modulation (A33). **Cost:** ~4 real MACs/mode/sample; a small room ≈ 1600 modes ≈ 10⁴ MACs/sample (≈500 MIPS @ 48 kHz); embarrassingly parallel (SIMD/GPU/FPGA — benchmark study: https://www.frontiersin.org/journals/signal-processing/articles/10.3389/frsip.2025.1522604/full).
