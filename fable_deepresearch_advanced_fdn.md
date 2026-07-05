# Fable Deep Research: Advanced FDN Variants & Research Architectures

**Date:** 2026-07-05

> A33 time-varying (spinning) feedback matrices · A34 filter/velvet feedback matrices & VFDN · A35 allpass FDN theory · A36 accurate T60 attenuation filters · A37 grouped/coupled FDNs · A38 directional FDN · A42 Erbe-Verb · A43 dispersive-FDN hybrids & moving-tap reverbs · A44 converter-in-the-loop nonlinearity (EMT 250 / Sanctuary).
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.

## A33. Time-varying feedback matrices — the "spinning" unitary FDN


**Paper:** Schlecht & Habets, "Time-varying feedback matrices in feedback delay networks and their application in artificial reverberation," JASA 138(3):1389–1398, 2015 — https://pubs.aip.org/asa/jasa/article-abstract/138/3/1389/680169/; PDF via https://www.sebastianjiroschlecht.com/publication/schlecht-2015-hi/

**Idea:** modulate the **matrix**, not the delays:

```
A(n) = Q₀ · Rⁿ
Q₀ = any unitary (e.g. Householder);  R = V·blkdiag(rot(θ₁)…rot(θ_{N/2}))·Vᵀ
```

with V random orthogonal and θ_i tiny — a "Householder embedding of small rotations." Every A(n) is orthogonal, so **stability/losslessness holds at every instant**; the network experiences a dense web of slow concurrent amplitude modulations of its feedback paths with **zero pitch modulation** (no chorus/detune, unlike delay-length LFOs).

**Results:** increased "liveliness"; artifacts far less audible than delay modulation; **a smaller FDN sounds as smooth as a bigger static one.** This is the modern, mathematically safe implementation of Lexicon "spin" — and the natural way to add M7-grade micro-variance (A4 step 5) without touching delay lengths.

## A34. Filter feedback matrices (FFM), velvet feedback matrix, and the VFDN


**Paper:** Schlecht & Habets, "Scattering in Feedback Delay Networks," IEEE/ACM TASLP 28:1915–1924, 2020 — https://arxiv.org/abs/1912.08888

**Idea:** generalize the scalar matrix A to a **filter matrix A(z)**; lossless ⇔ **paraunitary**: A(z)Aᴴ(1/z*) = I. Canonical construction — unitary stages interleaved with diagonal delays:

```
A(z) = U_K D_K(z) U_{K−1} D_{K−1}(z) … U_1 D_1(z) U_0
```

Each feedback path becomes a short *diffusing FIR* instead of a scalar — modeling non-specular scattering. **Velvet feedback matrix (VFM):** choose U_k = scaled Hadamard stages and short velvet-spaced delays in D_k(z) → matrix entries are sparse velvet FIRs; **echo density explodes immediately after the first pass**; a fast-Hadamard stage costs N·log₂N adds. Scalar-delay sibling: "Dense Reverberation with Delay Feedback Matrices," WASPAA 2019 — https://www.researchgate.net/publication/336855119

**VFDN** (Fagerström, Alary, Schlecht, Välimäki, "Velvet-Noise Feedback Delay Network," DAFx-20 — https://research.aalto.fi/files/52251303/DAFx2020_paper_23.pdf): sparse velvet FIRs on the **input and output branches** of a small FDN — **exceeds the echo density of a conventional FDN using half the delay lines and >50% fewer operations**, with minimized coloration. Probably the best density-per-op structure known — highly relevant to an embedded (Daisy/Hothouse) Bricasti-style tank.

## A35. Allpass FDNs — the unifying theory (uniallpass)


**Paper:** Schlecht, "Allpass Feedback Delay Networks," IEEE TSP 69:1028–1038, 2021 — https://arxiv.org/abs/2007.07337

**Result:** characterizes **uniallpass FDNs** — allpass for *arbitrary* delay lengths: A diagonally similar to unitary (A = E U E⁻¹) **plus** a completion procedure solving for b, c, d so H(z) is allpass. Schroeder's series allpass, **Gardner's nested allpass (A11)**, and Poletti's unitary MIMO reverberator all drop out as special cases. Practical payoff: colorless recursive diffusers with guaranteed stability for any delay set — principled building blocks for rings (A8), loops (A13), and dispersive hybrids (A43). Also the theoretical justification for the Dahl/Jot absorbent allpass (A14).

## A36. Accurate T60 control — graphic-EQ and two-stage attenuation filters


**Papers:** Prawda, Schlecht, Välimäki, "Improved Reverberation Time Control for Feedback Delay Networks," DAFx-19 — https://www.sebastianjiroschlecht.com/publication/prawda-2019-tq/; Välimäki, Prawda, Schlecht, "Two-Stage Attenuation Filter for Artificial Reverberation," IEEE SPL 2024 — **code:** https://github.com/KPrawda/Two_stage_filter

**Problem:** ≈5% T60 error is already audible, and the error propagation from filter magnitude to T60 is brutally nonlinear (T60 error ∝ 1/log g — tiny dB errors near unity gain blow up RT accuracy). One-pole Jot dampers are nowhere near accurate octave-band control.

**Solution:** end each delay line with an **octave graphic EQ cascade + high shelf**, command gains per band `−60·M_i/(fs·T60(band))` dB, optimized with the nonlinear error weighting; or (2024) a **two-stage design** — low-order filter capturing the overall T60 trend + GEQ on the residual (better accuracy, lower order). This is how you hit the M7's independent HF/LF RT multipliers and the plate's bathtub T60 *exactly*.

## A37. Grouped / coupled FDNs — multi-slope decay


**Paper:** Das & Abel line, "Grouped Feedback Delay Networks with Frequency-Dependent Coupling," IEEE/ACM TASLP 2023 — https://www.researchgate.net/publication/370863090

**Idea:** blocks of delay lines per room volume; block-diagonal unitary feedback plus small coupling blocks → **multi-slope decays of coupled spaces** (cathedral + side chapel; stage + hall). Complements the DVN non-exponential approach (A30) with a recursive structure. Also the right frame for the M7's separate VLF engine: a coupled LF group with its own longer RT.

## A38. Directional / ambisonic FDN


**Paper:** Alary, Politis, Schlecht, Välimäki, "Directional Feedback Delay Network," JAES 67(10):752–762, 2019 — https://www.aes.org/e-lib/browse.cfm?elib=20693; frequency-dependent extension: https://research.aalto.fi/en/publications/frequency-dependent-directional-feedback-delay-network

**Idea:** each delay line carries a **multichannel spherical-harmonic (ambisonic) signal**; a direction-dependent transform in the SH domain applies **anisotropic decay** (different T60 per direction) → directional reverberant fields for arrays/binaural. Zita-Rev1's free B-format output (A15) is the degenerate ancestor.

## A42. Erbe-Verb — the performance FDN (Make Noise / Tom Erbe)


**Paper:** Tom Erbe, "Building the Erbe-Verb: Extending the Feedback Delay Network Reverb for Modular Synthesizer Use," ICMC 2015 — https://quod.lib.umich.edu/cgi/p/pod/dod-idx/building-the-erbe-verb-extending-the-feedback-delay-network.pdf?c=icmc%3Bidno%3Dbbp2372.2015.054%3Bformat%3Dpdf

**Documented design:** core = 4-delay FDN (Stautner–Puckette/Gerzon unitary matrix — chosen over Schroeder chains, Moore's Space Station, and Griesinger's figure-8 after evaluation); per-branch allpass diffusion + first-order lowpass in every branch; absorption/decay uniform across branches. Unitary ⇒ sustains indefinitely at feedback 1.0.

**The atypical parts:**
- **Everything is a knob/CV at audio rate** ("modeless morphing"): all delay lengths scale continuously with Size; **granular envelopes on the delay lines crossfade grains during size changes** → artifact-free dynamically changing rooms (the trick to steal for any "size morph" control).
- **Both periodic and random modulation** in the tank, tuned to break resonances while avoiding chorusing.
- Audio-rate predelay modulation → FM sidebands ("gorgeously metallic," intentional).
- **Reverse mode**: windowed backwards-read taps on the tank.
- With decay ≥ 1 the loop sustains/blooms; the paper does not publish a saturation curve, but the general principle stands: a memoryless nonlinearity with |f(v)| ≤ |v| inside a lossless loop keeps state bounded (passivity) while regenerating harmonics each pass — **the basis of "saturated tank" reverbs** and the tube-spring loop saturator (A23).

## A43. Dispersive-FDN hybrids & moving-tap reverbs (atypical loop citizens)


**(a) Dispersive FDN ("spring-plate hybrid"):** take any 4–8-line FDN; replace each delay z^−L with `z^−(L−δ)·A(z)^m` (m ≈ 4–16 first-order allpasses, a ≈ −0.5…−0.7, group-delay-compensated so loop time stays L) → chirped, "sproingy" echoes with FDN density — a sound unavailable from hardware. Theory support: high-order dispersive delays as cascaded low-order allpass sections or modal group-delay approximations (Werner DAFx-19, A21-bonus; Schlecht allpass-FDN theory, A35). Cost: m extra 1-mult allpasses per line.

**(b) Ursa Major Space Station (Christopher Moore):** multitap delay with **time-varying (moving) taps** feeding back — the third historical school besides Lexicon and Barr (documented in Erbe's ICMC paper as one of the studied topologies). Moving output taps = per-tap Doppler → the "swirly" 70s broadcast reverb; modern restatement: randomize tap positions with slew-limited noise (cf. A3 wander).

**(c) Chirp-modulated loops:** time-varying allpass coefficients inside a loop modulate chirp rate directly (Pekonen et al., "Spectral Delay Filters with Feedback and Time-Varying Coefficients," DAFx-09 — slides: http://research.spa.aalto.fi/publications/papers/dafx09-sdf/Pekonen2009DAFxslides.pdf) — vibrato-of-dispersion, a uniquely "alive" spring wobble.

## A44. Converter-in-the-loop nonlinearity (EMT 250 / Valhalla Sanctuary style)


**What it is.** Deliberately embedding the **nonlinearities of early digital converters inside the reverb signal path** as part of the sound. Verified from the designer's own documentation: ValhallaVintageVerb's **Sanctuary** mode (modeled on the EMT 250, the 1970s German digital reverberator) "incorporates the **bit reduction and floating-point gain control** used in the A/D and D/A convertors of the early digital hardware" — i.e. a gain-ranging (floating-point-style companding) converter model plus mantissa truncation applied to the recirculating signal (https://valhalladsp.com/2023/02/10/valhallavintageverb-the-modes/; background: https://valhalladsp.wordpress.com/tag/emt250/; Costello's AES 2015 talk: https://www.aes-media.org/sections/pnw/ppt/costello/AES2015ReverbPresentation.pdf).

**Why this is a distinct approach.** It is the digital cousin of the tube-spring saturator (A23): a **level-dependent nonlinearity inside the loop** that regenerates texture on every pass. Gain-ranging converters compress-then-expand around the tank, so quantization noise is loudest exactly when the signal masks it and the tail gains a faint animated "breathing" noise floor — the same mechanism as the 224's 6-bit-coefficient "halo" (A1) and CloudSeed's deliberate non-interpolated reads (A7). Related production strategy verified from the same source: **Random Space** mode uses Griesinger-style *internal delay-length randomization* (not chorused LFOs) to suppress metallic ringing without audible pitch shift.

**Implementation sketch:**

```
inside the loop, per delay-line write:
  g_range = 2^ceil(log2(max(|x|, floor)))        # gain-ranging stage (slew-limited)
  x_q     = quantize(x / g_range, B bits) · g_range   # B ≈ 12–16; optional error feedback
optionally: mild sample-rate/bandwidth truncation to taste (EMT 250 ran ~24 kHz-class rates)
```

Guard the loop with a DC blocker; keep quantization *after* damping so hiss doesn't accumulate at HF. Trivial to add to any tank in this document; the payoff is "vintage rack" life without any pitch modulation.

---
