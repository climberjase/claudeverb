# Fable Summary: Top 20 Reverb Approaches

**Date:** 2026-07-05
**Companion to:** `Fable_research_detail.md` (43 approaches, full math/code/sources — the A-numbers below link there).

**Targeted per-style extracts** (same content, split for focused reading):
`fable_deepresearch_fundamentals.md` (shared math) · `fable_deepresearch_hall_bricasti_lexicon.md` (A1–A7) · `fable_deepresearch_allpass_loop_tank.md` (A8–A17) · `fable_deepresearch_plate.md` (A18, A25–A27) · `fable_deepresearch_spring.md` (A19–A24) · `fable_deepresearch_velvet_noise.md` (A28–A32) · `fable_deepresearch_advanced_fdn.md` (A33–A38, A42–A44) · `fable_deepresearch_modal.md` (A39) · `fable_deepresearch_room_acoustic_models.md` (A40–A41)

Selection criteria: sound quality first (with a bias toward Bricasti-M7-like halls and tube-spring character per the research brief), then implementability in this repo (Python prototype → tested C), then novelty relative to what claudeverb already has (Dattorro variants, Freeverb, plain FDN, Moorer rooms — all excluded).

---

## The top 20

### 1. Griesinger figure-8 loop — Lexicon 224 "Concert Hall" (A1)
The single most important undocumented-in-this-repo hall topology. A stereo cross-coupled loop of leaky modulated allpasses, nested allpasses, and delays, with output taken as sparse multi-tap mixes off the delay *middles* and a 500 Hz ×0.1 cross-feed for long bass RT. Every constant is public via Freeverb3's Progenitor (fs = 34,125 Hz). Lush, huge, the reference "expensive hall." **Effort: medium-high. Payoff: flagship.**

### 2. Bricasti M7 replication blueprint (A4)
Not one algorithm but a verified design spec: three engines (dense velvet-noise early, unmodulated 16-line FDN late with mid-delay tap-sum outputs, separate <80 Hz VLF engine), density as a bloom control, **no tail modulation** — smoothness from sheer diffusion order and incommensurate delays. Verification metric included (NED ≈ 1 within 30–80 ms, then plateau). **Effort: high. Payoff: the target sound of this whole research effort.**

### 3. Keith Barr FV-1 allpass ring — rom_rev1 (A8)
A single ring of 4 × [delay → RT gain → 2 allpasses]; no matrix at all. Complete delay/coefficient tables recovered (32,768 Hz). RT60 = 0.75·T_loop/(−log₁₀ rt); rt → 1 gives an infinite colorless tail. The best sound-per-op reverb ever shipped and the ideal first implementation from this research: tiny, C-friendly, great-sounding. **Effort: low. Payoff: high.**

### 4. Parametric spring via spectral delay filters (A19)
The Välimäki/Parker/Abel model: M ≈ 100–200 identical first-order allpasses (a₁ ≈ −0.6) form the LF chirp; a feedback loop with a randomly modulated ~30–60 ms delay produces progressively blurred echoes; separate HF band. Parker's multirate trick cuts cost to ⅓. Fully parametric (f_C, M, a₁, T_lf, g_fb). **The** spring algorithm. **Effort: medium. Payoff: the second target sound.**

### 5. Tube-drive chain around any spring core (A23)
What makes a 6G15 sound "tube": asymmetric soft saturation **before** the dispersion (harmonics get smeared into the chirps → drip), +6 dB/oct band-tilted transformer drive, ~200 Hz–4 kHz wet band, gentle recovery-stage softclip, optional tanh inside the loop so decay ducks with level. Wraps A19 or A21; trivial DSP, dominant sonic effect. **Effort: low. Payoff: converts "spring" into "tube spring."**

### 6. Progenitor2 noise-dithered Random Hall (A2)
A1 plus 10 modulated input allpasses per channel, 4 cross-feed allpasses, ~20 output taps, and noise dithering of both allpass delay *and* coefficient (sign-alternating per stage) — the public recipe for Lexicon 480L-style "random hall" alive-but-pitch-stable tails.

### 7. Zita-Rev1 (A15)
8-line FDN with a diffusing allpass *inside* each branch and an exact three-band T60 filter per line (closed-form one-pole/shelf solution included). No modulation at all; clean, neutral, mode-free hall. Also yields a free first-order ambisonic output. Excellent stepping stone from the repo's existing FDN toward #2.

### 8. CloudSeed (A7)
Seeded, fully randomized parallel network: multitap sparse-FIR early + up to 12 modulated feedback delay-line channels per side, each with internal allpass diffusers and shelving damping; per-line feedback g_i = g^(d_i/d_max) keeps equal dB/s. MIT source. The "modern 1980s studio hall" with controllable stereo decorrelation (CrossSeed).

### 9. Velvet-noise family: FVN / IVN (A28, A29)
Multiplication-free sparse-noise reverb: interleaved velvet branches (4 suffice, per listening tests) give exponentially decaying, spectrally controlled, artifact-free tails at ~100 adds/sample. Also the right generator for an M7-style dense early field and for free binaural decorrelation. Uniquely C/embedded-friendly.

### 10. Dark velvet noise + non-exponential decay (A30)
Velvet pulses with randomized widths through recursive running-sum filters (still multiplication-free) → naturally dark tails; the optimization extension matches **arbitrary decay envelopes** — coupled-room double slopes and fade-in blooms (the M7/480L "Shape" behavior) that no single-slope FDN can produce. Open JUCE/Python/MATLAB code.

### 11. kPlate series — brute-force-searched Householder plate (A18)
Chris Johnson's Abbey-Road-plate substitutes: 25 prime delays per channel in five ranks scattered by an explicit 5×5 Householder row form, delay sets found by offline random search ("1 in 41,582"), sine/arcsine companding around the tank, per-path in-loop damping, tube variant (kPlateD). MIT. Two ideas to steal even without porting: offline delay-set search against a smoothness metric, and Householder feedforward ranks for L/R decorrelation from shared state.

### 12. JPverb rotation-lattice reverb (A12)
Julian Parker's 2×2 rotation-lattice diffusers (lossless for any diffusion gain, prime delay lengths indexed by Size) — ten per lap plus four chorused delays → enormous instant density with the "lush vintage Lexicon/Alesis" wash. MIT Faust source with exact RT60 law.

### 13. Time-varying feedback matrices (A33)
A(n) = Q₀Rⁿ with R a tiny embedded rotation: guaranteed-lossless matrix "spin" that amplitude-modulates all feedback paths with **zero pitch modulation**. The mathematically safe modern implementation of Lexicon spin — and the way to add inaudible micro-variance to an M7-style tail. Small delta on any existing FDN.

### 14. Modal reverberator (A39)
Thousands of fitted complex one-pole resonators = the measured device's actual poles (published route to Fender spring tank and EMT 140 emulations). Exact per-mode decay/EQ; phase re-randomization = new mic position for free; heterodyne form gives pitch-shifted/time-stretched reverb. Costly (~10⁴ MACs/sample) but embarrassingly SIMD-parallel.

### 15. Hybrid convolution head + FDN tail (A27)
The UAD EMT 140/BX 20 product architecture: short measured-IR convolution for the signature onset (plate whip / spring chirp / M7 early) + fitted FDN for the tail. Onset is nearly damping-invariant, so one head serves all damper settings. The generic recipe for cloning any hardware unit.

### 16. VFDN / velvet feedback matrices (A34)
Sparse velvet FIRs on a small FDN's input/output branches (or inside a paraunitary filter feedback matrix): more echo density than a double-size conventional FDN at >50% fewer ops. Probably the best density-per-op structure known — the embedded/Daisy route to a Bricasti-ish tank.

### 17. GreyHole (A13)
Three 4-deep *nested* rotation lattices recirculating around a modulated ~1.5 s delay: the open-source functional documentation of Eventide-Blackhole-style anti-physical blooming ambience. Feedback 1.0 sustains forever; diffusion knob morphs dub-echo ↔ wash.

### 18. Airwindows Galactic (A16)
No allpasses anywhere: three banks of four delays scattered by sign-matrix (2I − J) Householder reflections, cross-channel feedback (figure-8 through the stereo field), detune via modulated input predelay only, regen ≤ 1/8 = lossless prototype with a true freeze. MIT. Distinctively huge, slow-blooming pad verb; also demonstrates the undersampled-tank technique.

### 19. Gardner nested-allpass rooms (A11)
Nested (allpass-inside-allpass) chains in one filtered global loop — density *compounds* per pass; small/medium/large room recipes with published delay/gain sets. Historical bridge between Schroeder and Barr, cheap, and a genuinely different small-room flavor from the repo's Moorer-style rooms.

### 20. Modal spring with bead coupling (A21) — with the FDTD spring (A22) as its offline ground truth
The physically accurate spring: offline eigendecomposition of the helical-spring model (incl. magnetic-bead boundary effects, JAES 2025) → a few hundred to ~2000 independent biquad resonators at runtime. Best current match to measured tanks; pairs with the tube chain (#5) for the definitive tube-spring.

---

## Honorable mentions (in the detail doc, not in the top 20)

- **A5 Householder-warped serial-allpass "riser"** — a continuous Attack/Shape knob (serial-AP bloom ↔ FDN instant) with open source; fold into #2.
- **A36 GEQ / two-stage attenuation filters** — ±5% T60 accuracy is audible; this is how #2/#7 hit exact HF/LF RT multipliers (open MATLAB code).
- **A40 Scattering delay networks** — physically parameterized room reverb with exact first-order reflections; the "real room" complement to everything above.
- **A17 MatrixVerb** — the 95%-dry/5%-chorused tap-blend and sin/asin companding tricks.
- **A26 modal plate / A25 FD plate** — the physical EMT 140 routes (bathtub T60).
- **A31 switched convolution, A32 velvet decorrelators** — cheap early-field/width tools.
- **A37 grouped FDNs** (coupled-room multi-slope decay), **A38 directional FDN** (ambisonic anisotropic decay), **A42 Erbe-Verb** (granular size-morph + audio-rate everything), **A43 dispersive FDN** (spring-flavored FDN hybrid — a sound no hardware offers).
- **A44 converter-in-the-loop nonlinearity** (EMT 250 / Valhalla Sanctuary: bit reduction + floating-point gain-ranging inside the tank — verified from the designer's documentation; the digital cousin of the tube-spring loop saturator, trivially addable to any tank here).

## Suggested implementation order for claudeverb

1. **#3 Barr ring** (small, C-exportable, immediate quality win)
2. **#4 + #5 parametric tube spring** (the second target sound; multirate optional at first)
3. **#7 Zita-Rev1** (upgrades the existing FDN with in-branch allpasses + exact 3-band T60)
4. **#1 Progenitor** (flagship hall)
5. **#2 M7 blueprint** assembled from #7 + #9 early + A36 filters + A5 attack (the destination)

Each step reuses primitives from the previous one; all delay tables and coefficients needed are in the detail document.
