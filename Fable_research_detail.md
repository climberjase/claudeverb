# Fable Research Detail: Atypical & Great-Sounding Reverb Algorithms

**Date:** 2026-07-05
**Scope:** Deep research into reverb algorithm families *not yet documented in claudeverb*, with emphasis on approaches that sound like a **Bricasti M7** (dense, colorless, non-metallic hall) or a **tube-driven spring reverb** (dispersive, chirpy, drippy). Covers plate, spring, room, chamber, hall, and tank designs.

**Exclusions (already documented in this repo, or too common):** Dattorro plate and all its parameter/topology variants (single-loop, asymmetric, triple-diffuser), Freeverb, Schroeder/Moorer classics, plain Hadamard/Householder FDN with one-pole damping, and Moorer-architecture room/chamber with tapped-delay early reflections. Dattorro's figure-8 tank appears below *only* as historical context for the Griesinger designs it was derived from.

**How to use this document:** Each numbered approach (A1–A43) is self-contained: topology, math, concrete parameters, code excerpts where public source exists (with license notes), sonic character, and sources. The companion `fable_summary.md` ranks the top 20 for this project.

---

## Table of contents

- **Part 0 — Shared math primitives** (used throughout)
- **Part I — Hall / Bricasti / Lexicon school:** A1 Griesinger figure-8 loop (Lexicon 224 / Progenitor) · A2 Progenitor2 noise-dithered Random Hall · A3 Lexicon 480L spin/wander semantics · A4 Bricasti M7 analysis & replication blueprint · A5 Householder-warped serial-allpass "riser" (slow attack) · A6 zrev2 massive-diffusion + FDN hybrid · A7 CloudSeed
- **Part II — Allpass-loop school:** A8 Keith Barr FV-1 ring · A9 Spin plates & rom_rev2 · A10 Mutable Instruments Clouds loop · A11 Gardner nested-allpass rooms · A12 JPverb · A13 GreyHole · A14 Dahl/Jot absorbent allpass ring · A15 Zita-Rev1
- **Part III — Airwindows school:** A16 Galactic · A17 MatrixVerb · A18 kPlate series
- **Part IV — Spring reverb:** A19 Parametric spring via spectral delay filters · A20 Waveguide spring with dispersive allpass · A21 Modal spring · A22 FDTD helical spring · A23 Tube-drive electronics chain · A24 Practical spring cores (hexefx, BYOD)
- **Part V — Plate physical models:** A25 Finite-difference Kirchhoff plate · A26 Modal plate with physical damping · A27 Hybrid convolution head + FDN tail (EMT 140 / BX 20)
- **Part VI — Velvet-noise family:** A28 Filtered velvet noise · A29 Interleaved velvet noise · A30 Dark velvet noise & non-exponential decay · A31 Switched convolution reverberator · A32 Velvet-noise decorrelators
- **Part VII — Advanced networks & research architectures:** A33 Time-varying feedback matrices · A34 Filter/velvet feedback matrices & VFDN · A35 Allpass FDNs (uniallpass theory) · A36 Accurate T60 attenuation filters · A37 Grouped/coupled FDNs · A38 Directional FDN · A39 Modal reverberator · A40 Scattering delay networks · A41 Digital waveguide networks & meshes · A42 Erbe-Verb · A43 Dispersive-FDN hybrids & moving-tap reverbs
- **Appendices:** comparison tables, license summary, source index

---

# Part 0 — Shared math primitives

These recur in nearly every design below.

**Schroeder allpass delay** (the atom):

```
v[n] = x[n] + g·v[n−D]          (delay-line input)
y[n] = −g·v[n] + v[n−D]         → H(z) = (−g + z^−D)/(1 − g·z^−D)
```

Flat magnitude, scrambled phase; a series cascade multiplies impulse density per pass. But a *static* allpass cascade rings: each section's impulse response is an exponentially decaying pulse train at period D, so periodic excitation (vocals, snare rolls) excites audible metallic modes. Sean Costello's canonical writeup of the problem and fixes (modulate delay lengths; expose the coefficient as a Diffusion control): https://valhalladsp.com/2011/01/21/reverbs-diffusion-allpass-delays-and-metallic-artifacts/

**Leaky ("decaying") allpass** — the key Lexicon/Griesinger variant (from Freeverb3 `allpass_t.hpp::process_dc`, GPL-2.0+):

```c
input  += feedback * buffer[idx];
output  = decay * buffer[idx] - feedback * input;   /* decay < 1 => loss inside the allpass */
buffer[idx] = input;
```

The `decay` multiplier puts RT60-controlled loss *inside* the diffusor instead of only at loop level — the 224-style loop distributes decay across many elements.

**Modulated allpass** (chorused diffusor): read tap at `D + m[n]`, `m[n] ∈ [−E, +E]` samples, interpolated. Instantaneous pitch ratio of the recirculating signal is `1 − dm/dt`. For sinusoidal modulation of depth `A` samples at rate `f` Hz, peak pitch deviation is `2πfA/fs` — deep+fast sine LFOs sound like chorus, while **slow, lowpass-filtered random modulation spread across many elements with alternating signs stays pitch-stable** (each element's detune is tiny, uncorrelated, and averages out around the loop). Freeverb3 implements the modulated read with a **first-order allpass interpolator** (less HF loss under modulation than linear interpolation):

```c
z_1 = buffer[readidx_b] + m_frac * (buffer[readidx_a] - z_1);   /* allpass interpolation */
```

**Loop-gain ↔ RT60** (Jot & Chaigne 1991, std.): for a delay of `D` samples inside a loop,

```
g = 10^(−3·D / (fs·RT60))
|G(e^jω)| = 10^(−3·D / (fs·T60(ω)))     (frequency-dependent target per delay)
```

Freeverb3's Progenitor generalizes this: each element stores a "decay at RT60 = 1 s" constant `k` and computes `g = 10^(log10(k)/RT60)`.

**Echo density metric (NED)** — Abel & Huang, "A Simple, Robust Measure of Reverberation Echo Density," AES 121 (2006): fraction of IR samples in a sliding window beyond ±1σ, normalized to the Gaussian expectation `erfc(1/√2) ≈ 0.3173`; NED → 1 means the tail is statistically Gaussian noise. Perceptual anchors: "sputtery" ≈ 100 echoes/s; indistinguishable from Gaussian noise above ≈ 20,000 echoes/s. PDF: https://ccrma.stanford.edu/courses/318/mini-courses/rooms/mus318_Abel_Lecture/echo%20density.pdf — this is the right instrument for characterizing a Bricasti-class tail (dense from onset, NED ≈ 1 almost immediately, then plateau).

**FDN state-space form** (std., for Part VII): N delay lines of lengths M_i, feedback matrix A (N×N), input/output vectors b, c, direct gain d:

```
D(z) = diag(z^−M_1 … z^−M_N)
s_in(n) = A·s_out(n) + b·x(n);   y(n) = cᵀ·s_out(n) + d·x(n)
H(z) = cᵀ (D(z)^−1 − A)^−1 b + d
```

Poles = roots of det(D(z)^−1 − A) → exactly ΣM_i modes; ΣM_i/fs = modes/Hz (mode density). A unitary is *sufficient* for losslessness, not necessary: the full "unilossless" characterization is **A diagonally similar to unitary, A = E U E⁻¹** (Schlecht & Habets, IEEE TSP 2017 — https://arxiv.org/abs/1606.07729).

---

# Part I — Hall / Bricasti / Lexicon school

## A1. Griesinger figure-8 loop — the Lexicon 224 "Concert Hall" (Freeverb3 "Progenitor")

**What it is.** The best public reconstruction of David Griesinger's ca. 1978 hall loop (the Lexicon 224) is Freeverb3's `progenitor` ("Progenitor reverberator after Griesinger ca.1978, Copyright (C) 1977-1978 David Griesinger / 2006-2018 Teru Kamogashira", **GPL-2.0-or-later**). Its member names carry node numbers of Griesinger's original block diagram (`delayL_23`, `allpass2L_25_27`, `allpass3L_34_37`, `node37_39a`…) and the output-mix comments quote the 224 manual verbatim. Sources: https://github.com/MckAudio/freeverb3/blob/master/freeverb/progenitor.cpp and `progenitor_t.hpp`; the project's algorithm notes: https://freeverb3-vst.sourceforge.io/tips/reverb.shtml; a documented fan reconstruction of 224 v4.4 firmware: https://dannychesnut.com/Recording/Lexicon/224/index.html

**Historical/hardware context** (Gearspace "Lexicon reverbs: a brief bestiary," with ex-Lexicon staff posts — https://gearspace.com/board/high-end/362930-lexicon-reverbs-brief-bestiary.html): the 224 had a 16-bit ALU with only a **6-bit multiply coefficient**, 12-bit converters, 16 KB delay RAM, and the 224XL ran at **fs = 34,125 Hz**. The 6-bit multiplier's coarse interpolation produced the characteristic "halo" of modulation grit around the tail. Freeverb3's recreation is hard-coded to `FV3_PROGENITOR_DEFAULT_FS 34125`. Griesinger's design philosophy (SOS interview — https://www.soundonsound.com/people/david-griesinger-lexicon-creating-reverb-algorithms-surround-sound): perception-based, not room-physics-based — "patterns of reflections and reverberations that do what is optimum perceptually, whether a room could do that or not."

**Topology** (one big stereo figure-8 loop; delay lengths in samples @ 34,125 Hz):

```
            LEFT INPUT                                   RIGHT INPUT
                │ DC-cut (5 Hz)                               │ DC-cut
                │ 1-pole LPF 20 kHz (input damp)              │
                ▼                                             ▼
   (+)◄── loopdecay·[ crossR + 0.1·LPF500Hz(crossR) ]     (+)◄── loopdecay·[crossL + bass(crossL)]
    │         ▲  crossR = tail of RIGHT loop (delayR_58)      │      crossL = tail of LEFT loop (delayL_37)
    ▼         │   ← "bass boost": biquad LPF 500 Hz ×0.1 = long bass RT (the 224 split-decay)
 1-pole LPF 9 kHz (loop damping)                           LPF 9 kHz
    ▼                                                         ▼
 modAP 239 (±32, g=0.375, leak d2)                     modAP 205 (±32, g=0.375)
    ▼                                                         ▼
 delay 2                                               delay 1
    ▼                                                         ▼
 modAP 392 (±32, g=0.312, leak d3)                     modAP 329 (±32, g=0.312)
    ▼                                                         ▼
 delay 1055           (delayL_23)                      delay 1460  (delayR_40 = 625+835)
    ▼                                                         ▼
 nested AP2 {outer 1944, inner 612}                    nested AP2 {2032, 368}
   g_outer=0.406 (d3-leak), g_inner=0.25 (d1-leak)           (same coeffs)
    ▼                                                         ▼
 delay 344            (delayL_31)                      delay 500   (delayR_49)
    ▼                                                         ▼
 nested AP3 {1212 (mod ±121), 816, 1264}               nested AP3 {1452 (mod ±5), 688, 1340}
   g1=g2=0.25, g3=0.406, leaks d1/d1/d2                      (same coeffs)
    ▼                                                         ▼
 delay 1572           (delayL_37) ── crossL ──►        delay 16    (delayR_58) ── crossR ──►
        └──────────── feeds RIGHT input ┘                     └──── feeds LEFT input ┘
```

**Verbatim inner loop** (`progenitor.cpp`):

```c
/* add allpass stereo cross loop signal */
fv3_float_t crossR = delayR_58._getlast(), crossL = delayL_37._getlast();
outL += loopdecay * (crossR + bassb * lpfL_9_10(crossR));
outR += loopdecay * (crossL + bassb * lpfR_7_8(crossL));

/* LPF damping and allpass diffusion */
fv3_float_t lfomod = lfo1_lpf(lfo1()*wander);
outL = allpassmL_17_18.process_dc(delayL_16(allpassmL_15_16.process_dc(lpfLdamp_11_12(outL), lfomod)), lfomod*(-1.));
outR = allpassmR_21_22.process_dc(delayR_ts(allpassmR_19_20.process_dc(lpfRdamp_13_14(outR), lfomod*(-1.))), lfomod);
delayL_37(allpass3L_34_37._process(delayL_31(allpass2L_25_27._process(delayL_23(outL))), lfomod));
delayR_58(allpass3R_52_55._process(delayR_49(allpass2R_43_45._process(delayR_40(outR))), lfomod*(-1.)));
```

Note the **alternating modulation polarity** (`lfomod` vs `−lfomod`) between successive allpasses and between channels — detunes cancel to first order (pitch-stable tail) while modal frequencies still smear.

**Output taps** — the wet signal is a **sparse multi-tap mix off the middles of the loop delays**, weights ±0.938/0.438/0.125 — this yields the enveloping quad/stereo image and dense early buildup with no separate early-reflection engine:

```c
// Aout = node27_31[276]*0.938;
// Bout = node45_49[468]*0.438 + node40_42[625]*0.938 - node27_31[312]*0.438 + node55_58[8]*0.125
// Cout = node45_49[24]*0.938  + node37_39a[36]*0.469
// Dout = node27_31[40]*0.438  + node23*0.938 - node45_49[192]*0.438 + node37_39a[1572]*0.125
Dout = delayL_23._get_z(1)*0.938 + (delayL_31._get_z(40) - delayR_49._get_z(192))*0.438 + delayL_37._get_z(1572)*0.125;
Bout = delayR_40._get_z(625)*0.938 + (delayR_49._get_z(468) - delayL_31._get_z(312))*0.438 + delayR_58._get_z(8)*0.125;
```

("The Lexicon 224 manual says that A or C is the mono output, A and C are the stereo L and R outputs, B, D, A and C are the front left, front right, rear left and rear right outputs." — source comment.)

**Spin / Wander — the exact mechanism.** Two independent LFO systems:

1. **Loop modulation** (`spin`, `spinlimit`, `wander`): a sinusoidal LFO (default **0.5 Hz**) passed through a **1-pole LPF at 20 Hz** (slew limiter — you can drive the LFO into noise-like territory without clicks), scaled by wander ∈ [0,1] to a max excursion of **±32 samples ≈ ±0.94 ms**, applied with alternating signs to the four modulated allpasses plus the two nested-AP3 first stages.
2. **Output chorus** (`spin2 = 2.4 Hz`, `spinlimit2 = 12 Hz`, `wander2 = 0.3`, delay 22 ms): each output passes through a **feed-forward comb whose GAIN (not delay!) is LFO-modulated**, anti-phase L/R:

```c
lfomod = lfo2_lpf(lfo2()*wander2);
outL = outCombL._process_ff(Dout, lfomod);       /* y = x + g·x[n−D], g = ±LPF(sin(2π·2.4t))·0.3 */
outR = outCombR._process_ff(Bout, lfomod*(-1.));
```

This amplitude-wobbling comb slowly sweeps a ±2 dB ripple across the spectrum — **spectral motion with zero pitch modulation**. A beautifully cheap "wander."

**Decay distribution** (`resetdecay()`): normalized attenuations for RT60 = 1 s are `decay0 = 0.237` (main loop gain), `decay1 = 0.938`, `decay2 = 0.844`, `decay3 = 0.906` (leaks inside the nested/modulated allpasses); each is exponentiated as `g = 10^(log10(k)/RT60)`. Tone stack: input LPF 20 kHz, loop damping 9 kHz, output biquad LPF 10 kHz, bass-boost biquad LPF 500 Hz × 0.1 in the cross-feed (→ longer bass RT, the 224 "split decay"; cf. UAD 224 manual Bass/Mid RT + crossover — https://help.uaudio.com/hc/en-us/articles/4419497193492-Lexicon-224-Digital-Reverb-Manual).

**Sonic character.** Huge spatial image, lush slow modulation, long bass bloom, dense-but-open tail. The single most important non-Dattorro hall topology in the literature, and directly implementable from the constants above.

**Why it sounds good:** decay distributed across leaky allpasses (no single lossy point → smoother EDC); mid-delay multi-tap outputs (early energy without a separate ER engine); alternating-sign slew-limited modulation (mode smearing without chorus); LF cross-feed boost (bass reverb lasts longer, like big halls).

**License caution:** GPL-2.0+, and the header asserts Griesinger's 1977-78 design copyright. Reimplement from the topology/constants; don't paste code into a non-GPL repo.

---

## A2. Progenitor2 — the noise-dithered "Random Hall" modernization

**What it is.** Kamogashira's modernized 224 (`progenitor2.cpp`, same repo/license): everything in A1 **plus** heavy input diffusion, cross-channel allpasses, ~20 output taps per channel, and — critically — **noise-dithered modulation** of both allpass delay *and* allpass coefficient. This is the closest open-source artifact to what the Lexicon 480L "Random Hall" is described as doing.

**Additions over A1:**
- **10 series modulated input allpasses per channel** — L: 617, 535, 434, 347, 218, 162, 144, 122, 109, 74; R: 603, 547, 416, 364, 236, 162, 140, 131, 111, 79 samples; feedback −0.78; excursion ±10 samples.
- **4 cross-feed allpasses** (430/341/264/174 and 447/324/247/191, g = 0.78, crossfeed 0.4 into the opposite channel).
- A **150 Hz biquad allpass in the bass-boost path** (decorrelates the long-RT bass from the mid tail).
- **~20 output taps** per channel at weights 0.469/0.219/0.064/0.045.
- **Noise-dithered modulation**:

```c
fv3_float_t mnoise = noise1();                        /* pink-ish noise generator */
fv3_float_t lfo = (lfo1() + modnoise1*mnoise)*wander; /* modnoise1 = 0.09: noise into the LFO path */
lfo = lfo1_lpf(lfo);                                  /* slew-limited by spinlimit */
mnoise *= modnoise2;                                  /* modnoise2 = 0.06: noise applied to the
                                                         ALLPASS FEEDBACK COEFFICIENT itself */
outL = iAllpassL[i]._process(outL, lfo*i_sign, mnoise);  /* sign alternates per stage */
```

So both the delay **and the coefficient** of each input allpass are randomly perturbed, sign-alternating per stage — a faithful digital restatement of Griesinger's "randomized wandering."

**Why random modulation beats sine modulation:** a sine LFO concentrates detune energy at one rate → audible chorus on piano/strings; slow randomized tap motion spreads energy, decorrelates recirculations (raising *effective* modal density the way LARES decorrelates feedback paths), and keeps instantaneous `dm/dt` small → no perceived pitch instability. Theory: Griesinger, "Improving Room Acoustics Through Time-Variant Synthetic Reverberation," AES 90th Conv. preprint 3014, 1991 (LoC PDF: https://tile.loc.gov/storage-services/master/mbrs/recording_preservation/manuals/REPORT--Improving%20Room%20Acoustics%20Through%20Time-Variant%20Synthetic%20Reverb%20(AES,%201991)%20(Griesinger).pdf).

**Sonic character:** the "expensive rack hall" — dense onset from the 10-AP input chain, wide from cross-feed APs, alive-but-stable tail from the noise dithering.

---

## A3. Lexicon 480L "Random Hall" — spin & wander semantics (design spec)

Not an implementation but the precise *semantics* to implement, from licensed-emulator documentation:

- **Definitions** (Relab Random Hall page — https://relabdevelopment.com/learning-center/random-hall-algorithm/): "**Spin** modulates the entire reverberation field at a low rate, while **Wander** modulates the starting point of each reflection, as well as the time delay between reflections." I.e. spin = global slow LFO rate; wander = maximum random time-offset (ms) applied per tap.
- The Lexicon 480L manual describes SPN as affecting "the movement of many of the delay taps in the program" (https://www2.spsc.tugraz.at/add_material/audiotechnik/manuals/10_RP1/Lexicon/lexicon_480l_manual.pdf). On the 224 the precursor was **Mode Enhancement** — "continuously modulating certain delay lines (taps) within the program algorithms, which increases the effective density without thickening the reverb" (UAD 224 manual). Relab LX480 docs add: spin/wander "keep the resonances from building up, which means less metallic sound."
- The 480L (1986–88) also added **Shape/Spread** — energy-envelope controls shaping a **non-exponential onset** (important precedent for the Bricasti M7's bloom, A4). Michael Carnes later ported the Griesinger 224XL/480L algorithms to PCM96 with "higher fidelity wander and spin."

**Implementation recipe:** attach to every output tap (and optionally every ring delay read) an independent random offset process: `offset_i(t) = slewlimit(uniform(−W, +W), f_slew ≈ 1–5 Hz)` with W = wander (ms); plus one global LFO at spin rate modulating a subset of taps coherently. Randomize per-tap phases; alternate signs to cancel net pitch drift.

---

## A4. Bricasti M7 — analysis and replication blueprint

**Provenance/hardware.** Bricasti was founded by **Brian Zolner** (ex-Lexicon VP) and **Casey Dowdell** (ex-Lexicon DSP engineer); M7 shipped 2007. Hardware: **six dual-core ADSP-BF561 @ 600 MHz ≈ 14,400 MMACs** — roughly two orders of magnitude more MAC budget than a 480L; Dowdell has said he uses 32×16-bit multiplies where appropriate (KVR thread: https://www.kvraudio.com/forum/viewtopic.php?t=393688). The M7's smoothness is partly brute force: very many taps/delay lines. Sources: https://www.audiophilia.co.uk/bricasti-history, https://www.soundonsound.com/reviews/bricasti-design-model-7

**What Bricasti has said** (SOS review interview): the algorithms use **three separately adjustable engines**: (1) **early reverberation** — not sparse discrete reflections but "very dense and complex" from the first milliseconds; (2) **late tail**; (3) **a dedicated engine for early reverberation below 80 Hz** ("necessary to convey the depth and power of large spaces"). LiquidSonics corroborates the split by capturing early/late/LF streams separately for Fusion-IR (https://www.liquidsonics.com/software/seventh-heaven-professional/).

**Does the M7 modulate?** Evidence in order of directness:
1. **Tail: essentially no pitch/delay modulation.** Community/developer consensus (Samplicity's Number Seven notes — https://samplicity.com/number-seven/): "Bricasti uses less modulation within their algorithms, because their approach doesn't suffer from the inherent coloration of reverb algorithms based on all-pass and comb recirculating filters." The fact that **static IRs of the M7 get uncannily close** (Samplicity v1.1 became a de-facto standard — https://samplicity.com/bricasti-m7-impulse-response-files/) is itself evidence of quasi-LTI behavior.
2. **But not perfectly LTI.** LiquidSonics built **Fusion-IR** specifically because "no amount of modulation applied to a single impulse response could reproduce the same depth and subtlety of the Bricasti M7" — they capture multiple true-stereo convolution streams with modulated inputs, fused at the output. Honest reading: the M7 has **some slow/dynamic variation** (possibly time-varying tap gains or gentle randomization far below chorus depth), audible as extra "life" on sustained material — nothing like Lexicon spin/wander.
3. **V2 firmware (2010)** added Delay + Delay Modulation parameters — "higher settings are more random and deeper," and **only the (pre)delay is modulated, not the reverb tail** (https://www.bricasti.com/images/M7_V2_Manual_Addendum_Upgrade.pdf).
4. **Front panel:** Reverb Time, Size, Density, Diffusion, Pre-Delay, Rolloff, HF/LF RT multipliers + crossovers, VLF Mix, Early/Late levels — **no spin/wander-style tail-modulation controls** in V1 (https://www.bricasti.com/images/M7.pdf).

**Observed IR behavior (the replication targets):**
- **Density/onset:** the M7's Density parameter "affects echo density and also changes the rate of reverb build-up over the entire length of the tail — high = instantly dense, low = slower build-up for a **late bloom**" (manual). Hall programs show a **non-exponential onset** (energy ramps in over tens/hundreds of ms).
- **Echo-density profile:** "the Bricasti **increases density up to a point and then stops**, unlike real rooms where density always increases" (KVR reverb-design thread — https://www.kvraudio.com/forum/viewtopic.php?t=418769). NED ramps quickly to ~1 and plateaus — a Gaussian, noise-like late field.
- **Early field:** dense/specular from the first samples, selectable independently of the tail ("Early Select").
- **Tail statistics:** extremely smooth, colorless, Gaussian; long RTs stay noise-like **without** audible chorusing — the defining M7 trait, achieved through sheer density and incommensurate delay distribution rather than modulation.

**Replication blueprint** (assembled from all the evidence; cross-references other entries):

1. **Input diffusion:** 8–12 series allpasses per channel, 74→617 samples (progenitor2/zrev2 table, A2/A6), g ≈ 0.6–0.78, **no modulation** (or noise-dither at inaudible depth); plus 4 cross-channel APs (g = 0.78, crossfeed 0.4).
2. **Early engine:** filtered velvet-noise FIR (A28/A32), ~2000–4000 pulses/s over 80–150 ms, segment-lowpassed; independent level ("Early Select").
3. **Late engine:** 16-line FDN, mutually prime delays spanning ~90–260 ms, Hadamard mixing (or the Householder-warped serial-AP hybrid of A5 for an Attack/Shape control); **per-line entry allpass** (13–32 ms, g 0.6); per-line damping = 1-pole LP (Rolloff) + low/high shelf pairs implementing HF/LF RT multipliers with crossovers; **outputs = long weighted tap-sums off delay middles (not line ends)** for instant Gaussian density (the 224/Dattorro trick, scaled up); **Density** = crossfade between injecting input at all line entries (instant) vs. only via the diffusion chain (bloom).
4. **VLF engine:** parallel band (< 80–100 Hz, LR4 split) with its own small FDN, longer RT, independent mix ("VLF Mix").
5. **Modulation:** none in the tail; optionally ±1–2 samples of heavily slew-limited noise on a minority of lines (below detectability) to kill the last flutter — respects "real spaces don't modulate" while matching Fusion-IR's observed micro-variance.
6. **Verification:** NED should hit ≈1 within ~30–80 ms and plateau; no comb ridges in a 4096-pt spectrogram of the tail; EDC linear (or deliberately two-sloped when testing bloom).

**Alternative strategies people use:** multi-stream convolution morphing (LiquidSonics Fusion-IR); Wave Alchemy Magic7 rebuilds M7 programs from large IR sets with added motion (https://www.wavealchemy.co.uk/product/magic7/); velvet-noise early + FDN tail (A28–A30 — directly on point for the bloom: "Non-Exponential Reverberation Modeling Using Dark Velvet Noise," https://arxiv.org/html/2403.20090v1).

---

## A5. Householder-warped serial-allpass "riser" — slow attack / Shape control

**What it is.** A working open-source technique for the non-exponential onset (M7 bloom, 480L Shape): **8 serial allpass delays "time-warped" into a Householder 4×4 (or 8×8) feedback matrix** — a rotation/warp parameter morphs continuously between serial-allpass behavior (slow build) and FDN behavior (instant tail), controlling attack shape without envelopes.

- Discussion: KVR "FDN Reverb with a slow attack" — https://www.kvraudio.com/forum/viewtopic.php?t=547140
- Source: https://github.com/shabtronic/FDN-Reverb-Riser

**Classic alternatives for the same goal:** subtract a fast-attack short reverb from a slow long one; feed the late FDN from the *output* of the early diffusion chain so the tail inherits the build-up; Costello's productized version is the attack-controlled Ambience mode in ValhallaVintageVerb (https://valhalladsp.com/2023/02/10/valhallavintageverb-the-modes/).

**Why it matters:** attack/Shape is the single most audible difference between "algorithmic hall" and "Bricasti/480L hall" on program material; this is the cheapest structural way to get it as a continuous knob.

---

## A6. zrev2 — massive input diffusion + Hadamard FDN (the open-source "M7-shaped" hybrid)

**What it is.** Freeverb3's `zrev2` (GPL-2.0+) combines the **same 10-stage-per-channel modulated input allpass cascade as progenitor2** (617…74 samples; noise-dithered modulation — set depth ≈ 0 for M7-style) with an **8-line FDN of zita-rev1 lineage** (A15): delays `{0.153129, 0.210389, 0.127837, 0.256891, 0.174713, 0.192303, 0.125000, 0.219991}` s, each line = **allpass diffuser (20.3–31.6 ms, g = 0.6) + delay + damping filter (+ low/high shelves)**, mixed by a **Hadamard butterfly** (unitary → lossless), with two ultra-slow LFOs (0.9/1.3 Hz, excursion ±1 ms, slew-limited) that can be zeroed. Source: https://github.com/MckAudio/freeverb3/blob/master/freeverb/zrev2.cpp (and zrev.cpp).

**Verbatim core:**

```c
x0 = _diff1[0]._process(_delay[0]._getlast() + t, lfo1q);   /* per-line AP diffuser at loop entry */
...
t = x0 - x1; x0 += x1; x1 = t;   /* 8x8 Hadamard via 12 butterflies */
...
_delay[0]._process(_filt1[0](x0), lfo2q);                    /* damped, re-written */
outL = 0.3*(x1 + x2);  outR = 0.3*(x1 - x2);
```

**Scaling this to "M7-like":** 16–32 lines, per-line input injection at staggered taps, output as weighted sums of *many* mid-delay taps (224/Dattorro-style tap mixes); decay via `g_i = 10^(−3·D_i/(fs·RT60))` with separate HF/LF shelves per line; separate VLF branch; onset-shaping per A5. The consensus recipe: **instant Gaussian density from diffusion order, not modulation.**

---

## A7. CloudSeed — seeded parallel modulated delay-line network (MIT)

**What it is.** Valdemar Erlingsson's CloudSeed (https://github.com/ValdemarOrn/CloudSeed, **MIT**; continued at https://github.com/GhostNoteAudio/CloudSeedCore; JUCE port https://github.com/xunil-cloud/CloudReverb). "Based on the same principles as many classic studio reverb units from the 1980's" (README). Note: "Bricasti-adjacent" is community characterization, not vendor documentation — state as inference.

**Topology (per channel; two seeded channels = stereo, `CrossSeed` decorrelates):**

```
in ─ HP/LP (opt) ─► PreDelay (0..500 ms) ─► MultitapDiffuser ─► AllpassDiffuser (early) ─┬─► early out
                                            (1..50 taps in       (1..8 series Schroeder  │
                                             0..500 ms window,    APs, each modulated)   │
                                             random gains)                               ▼
                              ┌──────────── up to 12 parallel delay-line channels ───────────────┐
                              │  ┌─►(+)─► ModDelay(len_i) ─► LowShelf ─► HighShelf ─► LP1 ─► AP-diffuser(≤8) ─┐
                              │  │                                                    feedback·g_i            │
                              │  └────────────────────────────◄──────────────────────────────────────────────┘
                              └── Σ / √N ──► line out
out = dryOut·in + predelayOut·predelay + earlyOut·earlyStage + lineOut·Σlines
```

**Everything is randomized from seeds — the signature move** (verbatim, legacy-v1):

```csharp
// per delay line (UpdateLines):
var delay      = (0.1 + 0.9 * delayLineSeeds[i]) * lineDelay;        // 10–100% of LineDelay (≤500 ms)
var adjustedFeedback = Math.Pow(lineFeedback, delay / lineDelay);    // equal dB/s across lines
var modAmount  = lineModAmount * (0.8 + 0.2 * seeds[i + count]);
var modRate    = lineModRate   * (0.8 + 0.2 * seeds[i + 2*count]) / samplerate;

// AllpassDiffuser: stage delays and modulation are randomized too
filters[i].SampleDelay = (int)(delay * (0.5 + 1.0 * Seeds[i]));      // 50–150% of DiffusionDelay (≤50 ms)
filters[i].ModAmount   = amount * (0.8 + 0.2 * Seeds[MaxStageCount + i]);   // ≤2.5 ms
filters[i].ModRate     = rate * (0.5 + 0.5 * Seeds[MaxStageCount*2 + i]) / samplerate; // ≤5 Hz
```

`Pow(lineFeedback, ratio)` is the RT60-correct scaling: line i of length `d_i = ratio·d_max` gets `g_i = g^(d_i/d_max)`, so all lines decay at the same dB/second and `RT60 = −3·d_max/log10(g)`. T60→feedback in dB form:

```csharp
auto dbAfter1Iteration = delaySamples / lineDecaySamples * (-60);  // T60 → per-pass dB
line->SetFeedback(pow(10, dbAfter1Iteration/20));
```

The `MultitapDiffuser` builds 1–50 taps with spacings `0.1+rand()` (normalized) and gains `±rand·(1 − decay·i/N)` — a seeded sparse-FIR early block, velvet-noise-like (A32). The `ModulatedAllpass` is a direct-form Schroeder AP with a sine-modulated interpolated read head updated every 8 samples.

**Distinctive tricks:** SHA256-seeded reproducible randomization with a **Cross Seed** control (0 = L/R identical → mono-compatible; 1 = fully decorrelated → wide); optional **non-interpolated modulated reads** ("skips between samples… results in a white-noise component, which can be very pleasant on very long decays, giving an airy feeling" — deliberately re-introducing the 224's interpolation noise!); the early AP chain makes the response "non-exponentially decaying" (bloom).

**Sonic character / why Bricasti-adjacent:** no unitary matrix, no allpass ring — instead up to 24 mutually random, individually chorused feedback comb channels whose combined density and slow random modulation produce a huge grain-free "cloud" tail; the AP diffusers inside each feedback path densify every recursion. With few lines it's audibly comb-y (a feature for special effects); with 8–12 lines + modulation it approaches hardware-hall smoothness.

---

# Part II — Allpass-loop school

## A8. Keith Barr's FV-1 allpass ring — `rom_rev1` (the "2AP + delay" loop)

**Context.** Keith Barr (co-founder MXR, founder Alesis — MIDIVerb — then Spin Semiconductor) documented his approach in the Spin knowledge base (http://www.spinsemi.com/knowledge_base/effects.html#Reverberation) and shipped it as the FV-1 ROM reverbs. Constraints that shaped it: **32,768 Hz** sample rate, **32,768 samples (exactly 1.0 s) delay RAM**, **128 instructions/sample**, and single-cycle `RDA`/`WRAP` ops that implement one allpass in ~2 instructions. A faithful, importable port of `rom_rev1.spn` exists in the Faust libraries as `re.kb_rom_rev1` (author Luca Spanedda, **GPL-3.0**, unlike the rest of reverbs.lib): https://github.com/grame-cncm/faustlibraries/blob/master/reverbs.lib. Sean Costello's tribute (topology description + Barr's own drawings): https://valhalladsp.com/2010/08/25/rip-keith-barr/; Barr's forum thread on ring-reverb history: http://www.spinsemi.com/forum/viewtopic.php?t=3

**The topology.** A **single feedback ring of 4 repeated blocks, each block = [delay] → [decay gain RT] → [2 series allpasses]**, damping filters in each block, input injected at two points, outputs tapped from the plain delays — never from inside an allpass ("to avoid the metallic sound that can result"). In Costello's words: Barr's building block was a **"2 allpass, 1 delay unit"**, and the design "injects input everywhere but takes output in only two places, allowing the sound to keep coming fresh as the thing decays away."

ASCII of `rom_rev1` (delay lengths in samples @ 32,768 Hz, from the Faust port):

```
            L in ──► AP156(.5)─AP223(.5)─AP332(.5)─AP548(.5) ──┐   (input diffusers, kap=0.5)
            R in ──► AP186(.5)─AP253(.5)─AP302(.5)─AP498(.5) ──┼─────────┐
                                                               ▼         │
   ┌─► [del 4568] ─×RT─(+Lin)─ modAP1251(.6,±20@0.5Hz) ─ AP1751(.6) ─ LP ─ dc ─┐
   │                                                                           ▼
   │   ┌◄─ [del 5859] ─×RT─ AP1443(.6) ─ AP1343(.6) ─ LP ─ dc ◄────────────────┘
   │   ▼
   │  [del 4145] ─×RT─(+Rin)─ modAP1582(.6,±20@0.5Hz) ─ AP1981(.6) ─ LP ─ dc ─┐
   │                                                                          ▼
   └── [del 3476] ─×RT─ AP1274(.6) ─ AP1382(.6) ─ LP ─ dc ◄───────────────────┘

   L out = 1.5·tap@2630 + 1.2·tap@1943 + 1.0·tap@3200 + 0.8·tap@4016
   R out = 1.0·tap@2420 + 0.8·tap@2631 + 1.5·tap@1163 + 1.2·tap@3330
```

**Concrete parameters:**

| element | value |
|---|---|
| input allpasses | 4 per channel, kap = 0.5; L: 156/223/332/548, R: 186/253/302/498 |
| ring delays | 4568, 5859, 4145, 3476 samples |
| ring allpasses | 1251 & 1751, 1443 & 1343, 1582 & 1981, 1274 & 1382 samples, kap = 0.6 |
| modulation | first AP of sections 0 and 2 modulated ±20 samples by a 0.5 Hz sine (`CHO RDA`, SIN0) |
| damping | one-pole lowpass per section + leaky one-pole (coeff −0.05) as DC-blocker/shelf trim |
| input injection | L after section-0 delay, R after section-2 delay ("figure-8": two half-loops sharing one ring) |
| total ring length | 30,055 samples ≈ **917 ms** |

**Faust excerpt (GPL-3.0):**

```faust
loopSec(0) = _ @ (adaptSR(32768, 4568) - 1) : _ * rt : _ + (l : apSec(0))
           : apfMod(os.osc(0.5), adaptSR(32768, 1251), adaptSR(32768, 20), 0.6)
           : apf(adaptSR(32768, 1751), 0.6) : op(damp) : op(- 0.05);
loopSec(1) = _ @ adaptSR(32768, 5859) : _ * rt
           : apf(adaptSR(32768, 1443), 0.6) : apf(adaptSR(32768, 1343), 0.6) : op(damp) : op(- 0.05);
```

**Math: the lossless prototype and RT60.** Every diffusing element is unit-magnitude (lossless), so the undamped ring with RT gain = 1 is a *lossless prototype*: energy circulates forever while echo density grows on every pass. Decay is introduced **only** by the four explicit ×RT multipliers (and damping), so with total ring delay `T_loop` and `rt` applied 4× per lap:

```
RT60 = 3·T_loop / (−log10(rt⁴)) = 0.75·T_loop / (−log10 rt)
```

e.g. rt = 0.7 → RT60 ≈ 4.4 s from a 0.917 s ring; rt → 1 → infinite, still colorless.

**Why efficient:** one AP = 2 instructions; there is **no feedback matrix at all** — the "matrix" is the ring's cyclic permutation, the sparsest possible lossless matrix. **Why smooth:** density is multiplicative per lap; four mutually inharmonic section lengths kill periodicity; output taps sum 4 decorrelated points per channel; two slow chorused APs (±20 @ 0.5 Hz) break residual modes without pitch wobble. Character per Costello: "quite open, with somewhat less initial echo density than the various Lexicon algorithms, but with a wonderful build over time… ideal for ambient music."

**Implementation trick** for any AP ring: share one buffer with a single write pointer across the whole ring (exactly how MIDIVerb/FV-1 hardware worked) — mmalex's gist with code: https://gist.github.com/mmalex/3a538aaba60f0ca21eac868269525452

---

## A9. Spin plates (`rev_pl_*`) and `rom_rev2` — early-reflection taps inside the ring

From the PedalPCB structural analysis of the Spin programs (https://forum.pedalpcb.com/threads/high-level-analysis-of-some-common-fv-1-reverb-programs.28802/):

- **`rev_pl_1/2/3.spn` ("plates")** — ~995 ms RAM, **8 input APs (stereo input), 8 loop APs, 16 CHO modulation ops**, input AP coefficient 0.60; L/R DAC taps at different delay offsets for decorrelation; POT0 = reverb time, POT1/POT2 = LF/HF filters.
- **`rom_rev2.spn`** — the densest: 22 delay blocks, ~942 ms RAM; **each loop stage uses two back-to-back APs with deliberately different coefficients (0.6 and 0.5)** to double loop diffusion without lengthening ring delays; plus **dedicated early-reflection delays `ldel`/`rdel` (3000 samples ≈ 91 ms each) written mid-loop and tapped at four offsets each** for the output mix — room-geometry cues the plates lack; only SIN0 LFO, amplitude 160 samples (vs 33–37 in the plates), applied to two APs only.
- **`min_rev1.spn`** — the knowledge-base teaching sketch (~799 ms RAM, 4 input APs, mono in / stereo out from one loop).

**Takeaway patterns:** mixed AP coefficients within a stage (0.6/0.5) for extra diffusion; mid-loop ER delay writes tapped multiply for output; interleaved output taps (L/R from different offsets of the same ring delays) for free decorrelation.

---

## A10. Mutable Instruments Clouds / Elements / Rings reverb (Émilie Gillet, MIT)

**What it is.** The reverb in Clouds/Elements/Rings (https://github.com/pichenettes/eurorack/blob/master/clouds/dsp/fx/reverb.h, **MIT**) is an FV-1-style ring executed on an FV-1-style register machine (`fx_engine.h`: shared 16,384-sample buffer, 12-bit storage, `Read/WriteAllPass/Interpolate` ≈ `RDA/WRAP/CHO RDA`). Header comment: *"This is the Griesinger topology described in the Dattorro paper (4 AP diffusers on the input, then a loop of 2x 2AP+1Delay). Modulation is applied in the loop of the first diffuser AP for additional smearing; and to the two long delays for a slow shimmer/chorus effect."*

**Topology (Clouds; 32 kHz):**

```
in = (L+R)·gain ─► AP113 ─ AP162 ─ AP241 ─ AP399 ──► apout          kap = 0.625
                    ▲ AP113 smeared: read interpolated @ 10±60·LFO1(0.5 Hz)

  ┌────────────────────────────────────────────────────────────────────┐
  │  apout + krt·del2[4680±100·LFO2(0.3 Hz)] ─ LP(0.7) ─ AP1653 ─ AP2038 ─► del1 (3411) ─► wet L
  │  apout + krt·del1[tail]                  ─ LP(0.7) ─ AP1913 ─ AP1663 ─► del2 (4782) ─► wet R
  └────────────────────────────────────────────────────────────────────┘
```

**Verbatim core (MIT):**

```cpp
engine_.SetLFOFrequency(LFO_1, 0.5f / 32000.0f);
engine_.SetLFOFrequency(LFO_2, 0.3f / 32000.0f);
lp_ = 0.7f;  diffusion_ = 0.625f;
...
// Smear AP1 inside the loop.
c.Interpolate(ap1, 10.0f, LFO_1, 60.0f, 1.0f);
c.Write(ap1, 100, 0.0f);
c.Read(in_out->l + in_out->r, gain);
// Diffuse through 4 allpasses.
c.Read(ap1 TAIL, kap);  c.WriteAllPass(ap1, -kap);
c.Read(ap2 TAIL, kap);  c.WriteAllPass(ap2, -kap);
c.Read(ap3 TAIL, kap);  c.WriteAllPass(ap3, -kap);
c.Read(ap4 TAIL, kap);  c.WriteAllPass(ap4, -kap);
c.Write(apout);
// Main reverb loop, left half.
c.Load(apout);
c.Interpolate(del2, 4680.0f, LFO_2, 100.0f, krt);   // read del2 chorused, × reverb time
c.Lp(lp_1, klp);
c.Read(dap1a TAIL, -kap); c.WriteAllPass(dap1a, kap);
c.Read(dap1b TAIL,  kap); c.WriteAllPass(dap1b, -kap);
c.Write(del1, 2.0f);
c.Write(wet, 0.0f);
in_out->l += (wet - in_out->l) * amount;
// right half symmetric: reads del1 TAIL with krt, APs 1913/1663, writes del2
```

**Loop math:** circulation length = 1653+2038+3411+1913+1663+4782 = **15,460 samples @ 32 kHz = 483 ms**, `krt` applied twice per lap:

```
RT60 = 3·0.483 / (−2·log10 krt)     krt = 0.7 → ≈ 4.7 s;  krt = 0.9 → ≈ 15.8 s
```

(Clouds drives krt up to ≈1.2 for "frozen" tails; > 1 is tolerable in practice because 12-bit storage + LP soft-limit the blowup.)

**Family variants:**

| | Clouds (32 kHz) | Elements (32 kHz) | Rings (48 kHz) |
|---|---|---|---|
| input APs | 113/162/241/399 | 150/214/319/527 | 150/214/319/527 |
| loop APs | 1653/2038, 1913/1663 | 2182/2690, 2525/2197 | same counts |
| loop delays | 3411, 4782 | 4501, 6312 | same counts |
| loop time | 483 ms | 638 ms | 425 ms |
| AP1 smear | ±60 @ 0.5 Hz | ±80 @ 0.5 Hz | disabled |
| del mod | del2 ±100 @ 0.3 Hz | del2 ±100 @ 0.3 Hz | del2 ±50 @ 0.3 Hz and del1 ±40 @ 0.5 Hz |

**Sonic character:** extremely cheap (~2 multiplies per AP on a shared buffer), lush, slightly chorused; the 12-bit delay storage adds faint "vintage rack" grit (MIDIVerb lineage). Sign-alternated kap between the two APs of each branch (Dattorro's decorrelation trick).

---

## A11. Gardner nested-allpass rooms (1992 MIT thesis)

**Sources:** W. G. Gardner, *The Virtual Acoustic Room*, MIT MS thesis, 1992 — PDF: https://www.ee.columbia.edu/~dpwe/papers/Gardner92-virtroom.pdf; Csound implementation chapter (Hans Mikelson): https://www.eumus.edu.uy/eme/ensenanza/electivas/csound/materiales/book_chapters/24mikelson/24mikelson.html; structures reproduced in Beltrán et al., DAFx-99: https://www.dafx.de/paper-archive/1999/beltran.pdf

**The idea and math.** Vercoe & Puckette (1985) proposed replacing the delay inside a Schroeder allpass with *another* allpass (or delay + allpass chain). If the inner network A(z) is allpass, the outer structure

```
H(z) = (−g + z^(−d)·A(z)) / (1 − g·z^(−d)·A(z))
```

is still exactly allpass (|A| = 1 on the unit circle ⇒ |H| = 1) — a lossless prototype again. The payoff: echoes passing through the inner AP are multiplied, and the outer feedback *re-multiplies* them each pass, so **density compounds over time** (unlike a series cascade, whose density is fixed). Gardner puts the nested cascade inside **one global feedback loop with gain g and a lowpass/bandpass filter**, tapping outputs from points along the internal delays. (He called the designs "purely empirical.")

```
in ──►(+)──[nested-allpass chain with internal output taps]──┬──► out (weighted tap sum)
       ▲                                                     │
       └── g · LP/BP filter ◄────────────────────────────────┘
RT60 ≈ 3·T_loop / (−log10 g·|LP|)
```

**The three rooms:**

| room | chain (in order) | loop feedback | decay range |
|---|---|---|---|
| Small | double-nested AP → single-nested AP | bandpassed (~1.6 kHz center, 800 Hz BW), input pre-LP at 6 kHz "to reduce metallic ringing" | 0.38–0.57 s |
| Medium | double-nested AP → plain AP → single-nested AP | bandpass 1 kHz, 500 Hz BW | 0.58–1.29 s |
| Large | AP → AP → single-nested AP → double-nested AP | lowpassed, gain ≈ 0.3 | ≥ 1.30 s |

Recoverable values (Mikelson's Csound listing): small room — inner APs **22 ms** and **8.3 ms** inside a ~35 ms outer AP, initial ~24 ms delay, ~4.7 ms element; gains {0.25, 0.35, 0.45} (double-nested) and {0.15, 0.30, 0.08} (single-nested/output). Medium room delays {4.7, 8.3, 22, 5, 30, 67} ms, gains {0.35, 0.45, 0.25, 0.45, 0.4}. Full tables per figure are in the thesis PDF — verify there before implementation.

**Why it matters here:** Gardner is the missing link between Schroeder cascades and Barr's ring — one global filtered feedback loop around lossless diffusion, decay from one filtered gain, taps from interior delays. Known weakness (Costello): limited mode density at long RT60s — the ring topologies (A8) fix that by distributing delays/APs around the loop. Modern theory: Gardner's nested APs drop out as a special case of Schlecht's uniallpass FDNs (A35).

---

## A12. JPverb — rotation-lattice diffusers in feedback (Julian Parker, MIT)

**Sources:** `re.jpverb` in the Faust libraries (https://github.com/grame-cncm/faustlibraries/blob/master/reverbs.lib — "author Julian Parker, bug fixes and minor interface changes by Till Bovermann; license MIT"); originally in the SuperCollider **DEIND** plugins (https://doc.sccode.org/Overviews/DEIND.html). Doc: *"inspired by the lush chorused sound of certain vintage Lexicon and Alesis reverberation units. Designed to sound great with synthetic sound sources."*

**The shared building block — `diffuser` (2-in/2-out rotation lattice):** a stereo allpass-like lattice built from a **2×2 rotation** plus two prime-length delays, wrapped in feedforward `sin(g)` / feedback `−sin(g)` / through `cos(g)`:

```faust
diffuser_aux(angle, g, scale1, scale2, size, block) = si.bus(2) <: ((si.bus(2):par(i,2,*(c_norm))
    : ((si.bus(4) :> si.bus(2) : block
        : rotator(angle)                                    // 2×2 rotation: [cos −sin; sin cos]
        : (de.fdelay1a(8192, ma.primes(size*scale1) ... -1),
           de.fdelay1a(8192, ma.primes(size*scale2) ... -1)))
      ~ par(i,2,*(-s_norm))) : par(i,2,mem:*(c_norm))), par(i,2,*(s_norm)))
    :> si.bus(2)
with { c_norm = cos(g);  s_norm = sin(g); ... };
```

Rotation and lattice are both energy-preserving → each diffuser is **lossless for any g** — a 2-D generalization of the Schroeder allpass ("orthogonal-matrix allpass"). Delay lengths are literally **prime numbers indexed by the size control** (`ma.primes(size·scale)`), guaranteeing incommensurate loop lengths at every size.

**Topology:** stereo in → chorused pre-delay → damping → **4 series lattice diffusers** (early) → feedback loop containing **5 diffusers → modulated prime delays → 5 more diffusers → modulated prime delays → 3-band decay filterbank → feedback gain**:

```faust
jpverb(...) = ((... : diffuser(π/4, early_diff, 55,240,size) : diffuser(π/4,early_diff,215,85,size)
        : diffuser(π/4, early_diff,115,190,size) : diffuser(π/4,early_diff,175,145,size))
   ~ ( seq(i,5, diffuser(π/4, 1/√2, 10+30i, 110+30i, size))
     : par(i,2, fdelay4(512, depth ± depth·osc(freq)+5)
             : fdelay1a(8192, primes(size·(54+150i)) −1))
     : seq(i,5, diffuser(π/4, 1/√2, 125+30i, 25+30i, size))
     : par(i,2, fdelay4(8192, depth ± depth·osc'(freq)+5)
             : fdelay1a(8192, primes(size·(134−100i)) −1))
     : par(i,2, fi.filterbank(5,(low_cutoff,high_cutoff)) : (_*high,_*mid,_*low) :> _)
     : par(i,2, *(fb))))
with {
    depth = 50*mod_depth;                       // up to ~50 samples of chorus
    calib = 1.7;                                // t60 calibration constant (fb = 0.5 ref)
    total_length = calib*0.1*(size*5/4 - 1/4);  // effective loop length in seconds
    fb = 10^(-3/((t60)/(total_length)));        // exact RT60 law: fb = 10^(−3·T_loop/t60)
};
```

Parameters: t60 0.1–60 s; size 0.5–5 (scales all primes); mod depth/freq 0–1 / 0–10 Hz; 3-band decay via `low/mid/high` multipliers with crossovers `low_cutoff` (100–6000 Hz), `high_cutoff` (1000–10,000 Hz).

**Sonic character:** ten lossless diffusers per lap → enormous instant density; sine-chorused delays at 4 points per lap → the Lexicon/Alesis "lush chorused" wash. This is Barr's philosophy (all diffusion inside one loop, decay from one coefficient) rebuilt from 2×2 rotation lattices instead of scalar APs.

---

## A13. GreyHole — nested-lattice diffusion inside a long modulated echo loop

**Sources:** `re.greyhole` in Faust libraries (MIT, same declaration as A12); doc: *"A complex echo-like effect (stereo in/out), inspired by the classic Eventide effect of a similar name [Blackhole]. The effect consists of a diffuser (like a mini-reverb) connected in a feedback system with a long, modulated delay-line. Excels at producing spacey washes of sound."*

```faust
greyhole(dt, damp, size, early_diff, feedback, mod_depth, mod_freq)
    = (si.bus(4) :> seq(i,3, diffuser_nested(4, π/2, (−1)^i·diff, 10+19i, size))
        : par(i,2, si.smooth(damp)))
   ~ ((fdelay4(512, 10 + depth·(1±osc(freq))) x2)              // modulated short delay (chorus)
      : (de.sdelay(65536, 44100/2, floor(dt_constrained)) x2)  // long delay: up to 65,533 samples
      : par(i,2, *(fb)))
with { depth = (SR/44100)·50·mod_depth; dt_constrained = min(65533, SR·dt); ... };
```

**Topology in words:** input → **three series *nested* diffusers, each 4 levels deep** (rotation angle π/2, alternating-sign diffusion gains, prime lengths scaled by size) + damping — all inside a feedback loop whose other arm is a **modulated short delay + a very long crossfading delay (up to ~1.49 s @ 44.1 kHz) + feedback gain**. The "reverb" is a 12-lattice-deep diffusion cloud recirculating around an echo. At feedback = 1.0 it sustains forever (lossless diffusers + unity loop). `early_diff` low → diffusers collapse to plain delays (dub echo); ≈ 0.707 → smooth exponential wash. The modulated delay pitch-bends every recirculation — the "grey hole" drift.

**Eventide Blackhole context:** Blackhole began as a DSP4000 preset (mid-90s), later Space pedal/plugin; defining control **Gravity** = inverse decay (right of center: forward dense→long tails; left: reverse-envelope reverb). No block diagram has ever been published; GreyHole is the best public *functional* documentation of the concept ("gravity/feedback > diffusion time" yields the anti-physical bloom). Sources: https://www.eventideaudio.com/plug-ins/blackhole/, https://vi-control.net/community/threads/eventide-blackhole-algorithm.95231/ — treat any internal description as inference.

---

## A14. Dahl/Jot absorbent allpass ring

**Source:** L. Dahl & J.-M. Jot, "A Reverberator Based on Absorbent All-Pass Filters," DAFx-2000 (standard reference; Jot at E-mu/Creative — ancestor of many game/hardware reverbs).

**The primitive — absorbent allpass:** a Schroeder allpass whose internal delay is cascaded with a lowpass-attenuation filter:

```
          ┌──────────────[ −g ]──────────────┐
x ──►(+)──┤ z^−D · G(z)  (delay + LP·gain)   ├──►(+)──► y
      ▲   └──────────────────────────────────┘    ▲
      └──────────────[ +g ]───────────────────────┘
```

With G(z) = 1 it is exactly allpass; with G(z) = g_rt·LP(z) it provides **diffusion and frequency-dependent decay in one primitive**. A ring of these (à la Barr, A8) gives a reverberator where every element contributes both density and correctly distributed loss — the EDC has no stair-steps because loss is spread evenly around the loop.

**Design rules from the paper:** choose ring-delay lengths mutually prime spanning the desired T_loop; set per-element gain from the element's *total* delay: `g_i = 10^(−3·D_i/(fs·RT60))`; LP cutoffs set HF RT ratio. This is the formal version of what A8/A10 do empirically and the direct precursor of the "absorbent" loop in game middleware (EAX/OpenAL reverbs).

---

## A15. Zita-Rev1 — 8×8 FDN with allpasses *inside* the delay lines (Fons Adriaensen)

**Sources:** original C++ (GPL-2+), mirrored at https://github.com/PelleJuul/zita-rev1 (`source/reverb.cpp`); Faust port `re.zita_rev1_stereo` / `re.zita_rev_fdn` (STK-4.3/MIT-style) in reverbs.lib; JOS chapter: https://ccrma.stanford.edu/~jos/pasp/Zita_Rev1.html. Faust doc: *"This is an FDN reverb with allpass comb filters in each feedback delay in addition to the damping filters."*

**Structure** (from `reverb.cpp`):

```
L ──► vdelay0 (20–100 ms predelay) ──×0.3──┬(+)──► branches 0,1   (sign +)
                                           └(−)──► branches 2,3   (sign −)
R ──► vdelay1 ─────────────────────×0.3──┬(+)──► branches 4,5
                                         └(−)──► branches 6,7
branch i:  x_i = AP_i( delay_i.read() ± 0.3·in )      AP coeff c_i = ±0.6 alternating
           [x0..x7] → unnormalized 8×8 Hadamard butterfly (3 add/sub stages)
           delay_i.write( Filt1_i( x_i · √(1/8) ) )
outputs:   stereo  L = g1·(x1 + x2),  R = g1·(x1 − x2)
           ambisonic B-format: W = g0·x0, X = g1·x1, Y = g1·x4, Z = g1·x2
           → 2 parametric EQ sections (defaults 160 Hz, 2.5 kHz) on the wet buss
```

**Verbatim tables** (seconds; AP delay is *part of* the branch total):

```cpp
float Reverb::_tdiff1 [8] = { 20346e-6f, 24421e-6f, 31604e-6f, 27333e-6f,
                              22904e-6f, 29291e-6f, 13458e-6f, 19123e-6f };
float Reverb::_tdelay [8] = { 153129e-6f, 210389e-6f, 127837e-6f, 256891e-6f,
                              174713e-6f, 192303e-6f, 125000e-6f, 219991e-6f };
...
_diff1 [i].init (k1, (i & 1) ? -0.6f : 0.6f);   // allpass, ±0.6 alternating
_delay [i].init (k2 - k1);                       // plain delay = total − AP length
```

Branch totals span **125.0–256.9 ms** (mean ≈ 182 ms, mutually inharmonic), 13.5–31.6 ms of each realized as a diffusing allpass. The one-multiplier allpass:

```cpp
float z = _line[_i];  x -= _c * z;  _line[_i] = x;  if (++_i == _size) _i = 0;  return z + _c * x;
```

**Damping/EQ math (`Filt1`) — three-band T60 control, exact:**

```cpp
_gmf = powf (0.001f, del / tmf);               // mid gain: 10^(−3·del/T60mid)  (exact RT60)
_glo = powf (0.001f, del / tlo) / _gmf - 1.0f;  // low-shelf extra gain so LF decays at T60low
g    = powf (0.001f, del / thi) / _gmf;         // target HF gain at fdamp (thi = rtmid/2)
t = (1 - g*g) / (2*g*g*chi);  _whi = (sqrtf(1+4*t)-1)/(2*t);   // 1-pole LP coeff; chi = 1−cos(2π·fdamp/fs)
...
float process (float x) {
    _slo += _wlo * (x - _slo) + 1e-10f;   // one-pole LP at xover (~50–1000 Hz)
    x += _glo * _slo;                      // low shelf (LF decay boost/cut)
    _shi += _whi * (x - _shi);             // HF damping one-pole
    return _gmf * _shi;
}
```

`T60` is identical in every branch by construction — why zita has an unusually clean, mode-free decay. Controls: predelay 20–100 ms, xover (default 200 Hz), rtlow (3 s), rtmid (2 s), fdamp (T60 = rtmid/2 at fdamp), + 2 output EQs.

**Ambisonic output:** the post-matrix nodes are naturally decorrelated → four map directly to B-format W/X/Y/Z (W scaled 1/√2) — a free first-order ambisonic reverb. Stereo mode = mid-side of two nodes (x1±x2).

**Character:** "hall" not "plate" — slower build, very neutral, **no modulation at all** (Adriaensen dislikes chorused reverbs); the branch-internal APs substitute for modulation by densifying each recursion. Vital's synth reverb is documented as "similar to dm.zita_rev1". A key stepping stone toward the M7 blueprint (A4/A6).

---

# Part III — Airwindows school (Chris Johnson, MIT)

Source root: https://github.com/airwindows/airwindows/tree/master/plugins/LinuxVST/src (**MIT**). House style: delay lengths tuned at 44.1 kHz-equivalent; at higher rates the tank runs **undersampled** (`cycle`/`cycleEnd`: process the tank every 2nd/3rd/4th sample at 88.2/96+/176.4 kHz, linearly interpolating tank output) — saves CPU *and* keeps the tank tuning constant across rates.

## A16. Galactic — cross-coupled Householder banks + input vibrato

Controls: A=Replace, B=Brightness, C=Detune, D=Bigness, E=Dry/Wet. From `GalacticProc.cpp`:

```cpp
double regen = 0.0625+((1.0-A)*0.0625);             // 0.0625..0.125
double attenuate = (1.0 - (regen / 0.125))*1.333;    // input trim complements regen
double lowpass = pow(1.00001-(1.0-B),2.0)/sqrt(overallscale);
double drift = pow(C,3)*0.001;                       // vibrato speed
double size = (D*1.77)+0.1;                          // 0.1..1.87 scales all delays
delayI=3407*size; J=1823*size; K=859*size;  L=331*size;    // block 1
delayA=4801*size; B=2909*size; C=1153*size; D=461*size;    // block 2
delayE=7607*size; F=4217*size; G=2269*size; H=1597*size;   // block 3
delayM=256;                                                 // vibrato predelay
```

**Topology:**

```
in → ×attenuate → 256-sample predelay read with sine vibrato (L/R read 90° apart, drift-rate LFO)
   → one-pole LP (iirA) → [tank, undersampled]
tank:  write 4 short delays I,J,K,L; each input = sample + feedback{A..D}_of_OPPOSITE_channel · regen
       4 outs → sign matrix → write A,B,C,D → 4 outs → sign matrix → write E,F,G,H
       feedback{A..D} = sign matrix of E..H outputs;   wet = (outE+outF+outG+outH)/8
   → one-pole LP (iirB) → wet/dry
```

The "sign matrix" rows are `x_i − Σ x_j (j≠i)`, i.e. **M = 2I − J** (J = all-ones): eigenvalues {+2, +2, +2, −2} — an unnormalized Householder-family reflection with uniform gain 2. Three matrix stages ⇒ ×8, cancelled by the /8 output sum; `regen ≤ 0.125 = 1/8` means **loop gain ≤ 1 exactly at A=0** — a lossless prototype: minimum Replace = infinite stable tail, and `attenuate` simultaneously → 0 so the frozen tank stops accepting input. Decay math: `g_loop = 8·regen ∈ [0.5, 1.0]` per lap of three 4-delay banks (12 series delays per channel path).

**Signature details:** feedback is **cross-channel** (L regenerates from R's taps and vice versa — a literal figure-8 through the stereo field → wide decorrelated tails); the only modulation is the **input vibrato predelay** (detune applied *before* the tank, so the tail shimmers by accumulated re-pitching per regeneration — Doppler-style detune, not in-loop chorus). **No allpasses whatsoever**: 12 plain delays × 3 Householder banks per channel supply all diffusion. Note: the widely repeated "pitch-shift regen" description is not literal — regeneration is plain; pitch movement comes from the modulated predelay.

**Siblings:** Verbity = same 3×(4-delay + 2I−J) tank with same-channel feedback, regen max 0.09375 (< 1/8, never infinite), no vibrato. Chamber = similar tank with **golden-ratio delays** (`delayF = E·0.618…` etc., 12 delays each φ× shorter) — "turns from a chunky slapback into a smoother reverb tail that can sustain infinitely."

**Character:** giant, slow-blooming, slightly pitch-drifting pad verb. Proof that plain delays + sign-flip Householder banks + undersampling can replace allpasses entirely.

## A17. MatrixVerb — block-Householder modulated FDN with sin/asin companding

Controls: A=Filter, B=Damping, C=Speed, D=Vibrato, E=RmSize, F=Flavor, G=Dry/Wet. From `MatrixVerbProc.cpp`:

```cpp
double vibSpeed = 0.06+C;   double vibDepth = (0.027+pow(D,3))*100.0;   // up to ~103 samples(!)
double size = (pow(E,2)*90.0)+10.0;                                      // 10..100
double regen = depthFactor * (0.5 - (fabs(crossmod)*0.031));             // ≤ 0.5
delayA..H = {79,73,71,67,61,59,53,47}·size;      // 8 FDN lines (primes × size)
delayI..L = {43,41,37,31}·size;                  // 4 input allpasses, coeff 0.5
delayM = (29*size)-(56*size*fabs(crossmod));     // predelay, shrinks with "Flavor"
```

**Per-sample flow:** input → biquad LP (1–10 kHz, Q = 1.618) → **`sin(x)` waveshaper** (soft clip into the tank) → 4 series Schroeder APs (0.5; 43/41/37/31·size) → distributed (reversed/mirrored order per line) into **8 modulated FDN delays** (primes 47–79 × size). Each line is read with an independent-phase sine vibrato (shared depth/speed, random start phases), then:

```cpp
interpolX = ((1.0-blend)*interpolX) + (aX[working]*blend);   // blend = 0.955−size·0.007:
    // mostly the *unmodulated* tap, a few % chorused tap — subtle detune, not obvious chorus
feedbackA..D = Householder(2I−J) of lines A–D · regen;        // two 4×4 groups
feedbackE..H = Householder(2I−J) of lines E–H · regen;
wet = Σ(all 8)/8 → biquad LP (Q .618) → clamp → asin(x) → biquad LP (Q .5) → dry/wet
```

**Key ideas to steal:** the **95%-dry/5%-chorused tap blend** (deep vibrato depth with barely audible chorus — mode smearing without pitch wobble); **`sin()` in / `asin()` out complementary waveshaping** bracketing the tank (level-dependent "glue" in the tail that undoes itself at low level); block-diagonal feedback (two independent 4×4 Householder groups) cross-linked only by the "Flavor" bleed.

## A18. kPlate series — brute-force-searched Householder "plate" (kPlateA/B/C/D, kPlate140/240)

**What it is.** Chris Johnson's plate substitutes target "the sound of a famous EMT plate reverb on top of a famous recording studio" (Abbey Road's plates A–D), **matched by ear from released audio** — not physics, not measured IRs. Docs mirrored at https://github.com/baconpaul/airwin2rack/tree/main/res/awpdoc; product pages https://www.airwindows.com/kplatea/ etc. Per his docs: "my studio computer grinds away for hours or days to generate a 3x3 Householder matrix for allpasses … and a 5x5 Householder matrix that does the delays of the actual reverb … L and R see completely different combinations in the same matrix."

**Verified structure of `kPlateAProc.cpp`:**

1. **Undersampling:** core runs at ≤ 48 kHz regardless of host rate.
2. **Input conditioning:** 10 kHz averaging LP → 600 Hz HP → peak-tracking gain cell (`gainIn += sin(min(|x·4|,4))·x⁴`) → **"BigFastSin" overdrive** (`x>0: (x/2)·(2.827−x)`, clip ±1.4137) → HP/LP again. **kPlateD (the "all-tube" plate)** instead uses a **pure sine waveshaper** (`x = sin(clamp(x, ±π/2))`) and different regen (0.425 vs 0.415) — "its internal saturation algorithms being a whole different type."
3. **Early reflections:** 9 allpasses per channel (primes, kPlateA: 61…607 ≈ "37 ms, 170-seat club"), arranged 3×3: three parallel Schroeder APs (g = 0.5), then cross-combinations `((oeB+oeC)−oeA)` feed the next rank — a 3×3 Householder-style **feedforward** allpass matrix, different L/R wiring.
4. **Predelay** up to 0.5 s.
5. **Tank:** **25 prime-length delays per channel** (kPlateA: 5–829 samples; header: "86 ms, 882-seat hall. Scarcity, 1 in 41582" — the delay set was the best of a 41,582-candidate random search), organized as **five ranks of five**; each rank scatters through an explicit 5×5 Householder row (`aF = 3·outA − 2·(outB+outC+outD+outE)` etc.); L and R traverse the same 25 delays in different orders; rank-5 outputs form the feedback (`feedback·regen`, regen ≈ 2.4e-4–7e-4 — in-matrix gains ≫ 1 compensated by tiny regen; output sum × 0.0016 "corrected for Householder gain").
6. **In-matrix damping ("mulch"):** between ranks, one of five paths gets a fixed biquad bandpass and another a 2-sample averager; different corner sets per letter give A/B/C/D their voicings without touching topology.
7. **Output:** second sin-tracking gain cell, ×2 makeup, averaging LP, then **"BigFastArcSin" expander** `x = 2x/(2.827−x)` (undoes the input sine — soft companding around the whole reverb), submix dry/wet, 32-bit dither.

kPlate140/kPlate240 are the newer generation (new 5×5 set + "Pear" filters + "SubTight" subharmonic control); Chris notes the real plate's damping pad is a *nonlinear* acoustic coupler — "it'll be distorting low frequencies preferentially, nonlinearly" — and voices the gold-foil 240 "cloudier, murkier."

**Character:** extremely dense, non-metallic, "deep" tail with plate-like instant bloom; A = long/deep, B = shorter/brighter, C = shortest/widest, D = tube-saturated bloom. **Engineering takeaways:** offline brute-force search of delay sets against a smoothness metric; Householder feedforward ranks for L/R decorrelation from shared state; sine/arcsine companding; per-path in-loop damping.

---

# Part IV — Spring reverb (including the tube-driven sound)

## Spring physics (foundation for A19–A24)

**The mechanical system.** A reverb tank (Accutronics/O.C. type, descended from the Hammond Type 4) is 2–3 helical steel springs (~15–18 cm long, coil Ø ~4–6 mm, wire Ø ~0.3–0.4 mm) between transducers whose coils act on a **small cylindrical magnet ("bead")** crimped to each spring end; the bead rotates, so drive/pickup are **torsional**, not axial. Because the wire is a helix, curvature κ ≈ cos²α/R couples transverse (flexural), longitudinal and torsional polarizations into hybrid branches — this coupling *is* the spring sound. Canonical continuum model: **Wittrick (1966) thin helical rod equations** — 12th-order coupled PDE system, 6 DOF per cross-section, parameterized by coil radius R, wire radius r, helix angle α. Sources: Parker & Bilbao, "Spring Reverberation: A Physical Perspective," DAFx-09 — https://www.dafx.de/paper-archive/2009/papers/paper_84.pdf; https://www.amplifiedparts.com/tech-articles/spring-reverb-tanks-explained-and-compared; https://sound-au.com/articles/reverb.htm

**The impulse response.** Two regimes split at a **transition frequency f_C ≈ 2.5–4.5 kHz** (calibrated example: 4216 Hz — Gamper/Parker/Välimäki DAFx-11, https://www.dafx.de/paper-archive/2011/Papers/39_e.pdf):

- **Below f_C:** a slow echo train, period T_lf ≈ 30–60 ms, each echo a *chirp* (highs travel slower). Spectrogram arcs curve up toward f_C and flatten: **group velocity → minimum at f_C** — energy piles up there, producing the persistent "boing" band.
- **Above f_C:** a much faster, less dispersive pulse train (longitudinal branch; period ~10× shorter) — metallic sheen, not discrete boings.
- **Pre-echoes / multi-chirp structure** between main chirps (polarization conversion + second dispersion branch); the full Wittrick system has **multiple cutoffs**.

**f_C design intuition** (order-of-magnitude reconstruction — verify against Parker & Bilbao): the transition is where flexural wavelength ≈ coil circumference, β ≈ 1/R; with Euler–Bernoulli bar dispersion ω = (c·r/2)β², c = √(E/ρ) ≈ 5000 m/s (steel):

```
f_C ≈ c·r / (4π R²)      e.g. r = 0.15 mm, R = 4 mm → f_C ≈ 3.7 kHz
```

— matches the observed range and explains why smaller-coil, thicker-wire springs sound brighter.

**Magnetic bead effects:** the bead adds a mass–compliance resonance (LF bump + rolloff) at each end plus rotational→flexural conversion. State of the art: McQuillan, van Walstijn, Parker & Ortiz, "Physical Modeling of a Spring Reverb Tank Incorporating Helix Angle, Damping, and Magnetic Bead Coupling," JAES June 2025 — open PDF: https://pureadmin.qub.ac.uk/ws/portalfiles/portal/642714838/BZZZZZZ.pdf. DSP consequence: put a 2nd-order resonant band-shaping filter at model input and output; usable band ≈ 100 Hz–5 kHz.

## A19. Parametric spring via spectral delay filters (Välimäki/Parker/Abel) — the default choice

**The primitive — spectral delay filter** (Välimäki, Abel & Smith, "Spectral Delay Filters," JAES 57(7/8), 2009 — https://www.aes.org/e-lib/download.cfm?ID=14832): a cascade of **M identical first-order allpasses** + equalizer:

```
A(z) = (a₁ + z⁻¹)/(1 + a₁ z⁻¹),      H(z) = A(z)^M · E(z)

group delay:  τ(ω) = (1 − a₁²) / (1 + 2 a₁ cos ω + a₁²)   [samples]
              τ(0) = (1−a₁)/(1+a₁),   τ(π) = (1+a₁)/(1−a₁)
```

Cascading M sections multiplies group delay by M → the impulse response becomes a chirp sweeping over M·[τ_min, τ_max] samples. **a₁ < 0 → lows maximally delayed** (spring LF chirp); a₁ > 0 → highs delayed. For a₁ = −0.6: τ(0) = 4, τ(π) = 0.25 samples; **M = 100–200 gives a 400–800-sample LF chirp per pass** — the classic recipe. "Stretched" allpasses (z⁻¹ → z⁻ᴷ) move the dispersion peak to arbitrary frequencies; time-varying a₁ modulates chirp rate ("Dispersion Modulation using Allpass Filters," DAFx-08 — https://dafx.de/paper-archive/2008/papers/dafx08_36.pdf).

**The full model** (Välimäki, Parker & Abel, "Parametric Spring Reverberation Effect," JAES 58(7/8), 2010 — https://www.aes.org/e-lib/download.cfm?ID=15511): "a spectral delay filter implements the chirp-like initial response; a feedback loop containing a randomly modulated delay line produces multiple echoes, progressively blurred over time to produce the reverberant tail."

```
              ┌──────────────────────────────────────────────────────┐
              │  LOW-FREQUENCY CHIRP STRUCTURE  C_lf  (band 0..f_C)   │
 x ──►(+)──►[ A(z)^M_lf cascade, ~100–200 stages, a₁ ≈ −0.6 ]──┬──► Σ ──► y
       ▲      (intermediate taps ⇒ pre-echo / multi-chirp set)  │
       │                                                        │
       └──[ −g_fb ]◄──[ LP(f_C) ]◄──[ DC-blocker ]◄──[ z^(−L±mod) ]◄┘
                          L ≈ T_lf·fs (30–60 ms), randomly modulated
 x ──►[ C_hf : shorter stretched-allpass cascade + its own loop ]──► Σ
```

Key behaviors: every loop traversal re-disperses the signal, so the n-th echo has n× dispersion — exactly the increasing curvature of measured spring arcs; random delay modulation converts late echoes into a diffuse tail; the DC blocker stops the a₁ < 0 chain (huge DC group delay, DC gain 1) accumulating LF junk; pre-echoes come from summing intermediate cascade taps. **Automated calibration** from a measured IR (f_C from spectrogram maximum, T_lf from autocorrelation, decay from EDC, EQ from long-term spectrum): Gamper/Parker/Välimäki DAFx-11 (open PDF above).

**Efficiency** (Parker, "Efficient Dispersion Generation Structures for Spring Reverb Emulation," EURASIP JASP 2011:646134 — https://asp-eurasipjournals.springeropen.com/articles/10.1155/2011/646134): ≈ ⅓ cost via (1) **multirate** — C_lf only has energy below f_C, so decimate by D ≈ fs/(2·f_C) ≈ 4–5, run cascade+loop at fs/D, interpolate back; (2) **multiband** — only feed each chirp structure its own band. Parker's dissertation collects everything: https://aaltodoc.aalto.fi/items/5b1ff7ca-c56a-4073-9471-06846271625f

**Sonic character:** the reference parametric spring; with the tube stage of A23 in front, it *is* the tube-spring sound. Parameter API for a claudeverb implementation: `f_C, M, a₁, T_lf, g_fb, mod_depth, drive`.

## A20. Waveguide spring with fitted dispersive allpass (Abel, Berners, Costello, Smith 2006)

**Source:** "Spring Reverb Emulation Using Dispersive Allpass Filters in a Waveguide Structure," AES Convention 121, paper 6954 — https://aes2.org/publications/elibrary-page/?id=13788 (Costello = ValhallaDSP; Berners = Universal Audio).

**The idea:** a bidirectional **digital waveguide** — two propagation lines terminated by transducer reflection filters — where each line is not a pure delay but a **dispersive allpass fitted to the measured spring's group delay** τ(ω) for one transit. The closed loop then generates the entire echo/chirp cascade automatically, including per-echo re-dispersion.

**Fitting method:** measure IR → unwrap group delay of the first arrival → design a high-order allpass (cascade of low-order sections) matching it → set loop gain/EQ from measured decay.

**Why it matters:** conceptual bridge between physics and the Parker cascade models; presumed ancestor of the UAD AKG BX 20 plugin, which UA describes as a **"hybrid delay network/convolution design"** modeling the BX 20's two-spring torsional line including its **two-stage decay** (https://www.uaudio.com/products/akg-bx-20-reverb). Best choice for cloning one specific tank.

## A21. Modal spring (van Walstijn / McQuillan) — the physical state of the art

**Architecture:** diagonalize the discretized helical-spring eigenproblem once offline → run N independent 2nd-order resonators online (trivially parallel/SIMD, exact per-mode damping):

```
y_k[n] = 2 e^{−σ_k T} cos(ω_k T) y_k[n−1] − e^{−2σ_k T} y_k[n−2] + b_k x[n]
y[n]   = Σ_k c_k y_k[n]
```

with b_k, c_k sampled from mode shapes at the drive/pickup bead positions. A few hundred to ~2000 modes cover a spring's band.

**Papers:** van Walstijn, "Numerical Calculation of Modal Spring Reverb Parameters," DAFx-20 — https://www.dafx.de/paper-archive/2020/proceedings/papers/DAFx2020_paper_18.pdf (validated against a measured Accutronics/Belton 9EB2C1B); van Walstijn & McQuillan, "Modal Spring Reverb Based on Discretisation of the Thin Helical Spring Model," DAFx-20in21 — https://ieeexplore.ieee.org/document/9768284 ("numerical dispersion errors can be kept extremely small across the hearing range for a relatively low number of system nodes"); McQuillan et al. JAES 2025 (bead coupling; PDF above) — currently the best physical match to measured tanks.

**Bonus:** modal *dispersive* filters can also be designed directly from measured group-delay trajectories — K. J. Werner, "Extensions and Applications of Modal Dispersive Filters," DAFx-19 — https://ccrma.stanford.edu/~kermit/website/papers/modalDispersiveExtensions_DAFx2019.pdf

## A22. FDTD helical spring (Bilbao & Parker)

**Papers:** Bilbao & Parker, "A Virtual Model of Spring Reverberation," IEEE TASLP 18(4):799–808, 2010 — https://www.research.ed.ac.uk/en/publications/a-virtual-model-of-spring-reverberation; Bilbao, "Numerical Simulation of Spring Reverberation," DAFx-13 — https://www.researchgate.net/publication/262731418 (full R/r/α parameterization, e.g. R = 5 mm, r = 1 mm, α = 5°, with free-parameter FD stencils ε₁ = 0.084, ε₂ = −0.291, ε₃ = −0.364 tuned to minimize numerical dispersion).

**Model:** reduced (low-helix-angle) helical rod equations — two coupled fields (transverse + longitudinal) coupled through curvature κ ≈ 1/R — discretized on an interleaved grid; stencil free parameters are tuned so *numerical* dispersion matches *model* dispersion near f_C (the hard part: FD schemes disperse numerically exactly where the spring's audible signature lives). Implicit scheme (θ-schemes/linear solves); near real time for one spring. Use: reference/research, offline rendering, ground truth for cheaper models.

## A23. The tube-drive chain (Fender 6G15 archetype) — what makes "tube spring" a distinct sound

**The circuit** (https://en.wikipedia.org/wiki/Fender_Reverb_Unit): **12AT7 preamp → Dwell pot → 6K6GT power tube driving the tank through a step-down transformer → spring tank → 12AX7 recovery stage → Mixer & Tone**. An RC high-pass before the driver rolls off below ~300 Hz.

**Why it sounds different from an op-amp-driven tank:**
1. **Drive-side nonlinearity scales with Dwell.** The 6K6 + transformer into the tank's inductive coil is a soft-saturating asymmetric source. Crucially the distortion happens **before dispersion**, so harmonics generated on transients get smeared into the chirps → the "drip."
2. **Transformer + coil = bandpass drive.** Coil impedance ∝ ωL with a pentode ≈ current source → +6 dB/oct tilt until losses take over; transformer magnetizing inductance imposes LF rolloff (plus level-dependent LF transformer saturation). Combined with the RC HP and bead resonance → the classic ~200 Hz–4 kHz wet band.
3. **Recovery-side color:** 12AX7 grid-conduction softclip on spring flutter peaks, Miller HF rolloff, Tone stack.

**Recommended emulation topology:**

```
x ─►[12AT7: mild asym waveshaper + HP]─►(Dwell g)─►[6K6+xfmr model:
     HP 120–300 Hz · +6 dB/oct tilt to ~2–3 kHz · asym soft sat (level-dependent)]
  ─►[ SPRING CORE (A19/A21) ]─►[bead/pickup bandpass ~150 Hz–4.5 kHz]
  ─►[12AX7 recovery: gentle softclip + Tone LP]─► wet   (+ dry path)
optional: tanh inside the spring feedback loop (per-echo compression →
          apparent decay shortens when slammed: Dwell interacts with decay)
```

**Practitioner evidence:** BYOD puts `tanh` exactly at the loop summing node (A24); Arturia's REV SPRING-636 models the germanium preamp separately with a "grit" control and swaps 8 tank models (https://www.arturia.com/products/software-effects/rev-spring636/overview); neural-modeling papers treat spring units as nonlinear systems specifically because of the electronics (Martínez Ramírez et al., ICASSP 2020 — https://arxiv.org/pdf/1910.10105). **Model Dwell as pre-dispersion gain into a fixed-knee saturator, not as wet gain.** A waveshaper *before* the dispersion chain makes attacks "spit"; a weaker saturator *in* the loop makes drip bloom and duck with level.

## A24. Practical open-source spring cores (verbatim code)

**(a) hexefx_audiolib_F32** (Piotr Zapart, Teensy 4.x; MIT-style PJRC license) — https://github.com/hexeguitar/hexefx_audiolib_F32, `src/effect_springreverb_F32.cpp`. The cleanest small-footprint Parker-style spring:

```
in L+R ──► shelving band-limit ──► mono tank drive
   ┌───────────────────────────────────────────────────────────┐
   │  REVERB LOOP (two halves = two transducer↔transducer trips)│
   │  dly1(1945) ─►·g_t─►shelfLP─► AP(224)AP(420)AP(856)AP(1089)│  a=+0.6
   │        ▲                                        │          │
   │  in ──►+                                        ▼          │
   │        │                     dly2(1363) ◄───────+ ◄── in   │
   │  AP(1289)AP(956)AP(478)AP(156) ◄─shelfLP◄─·g_t──┘          │  a=+0.6
   │   (last AP of each half LFO-modulated, 1.35 Hz, ±10 smp)   │
   └───────────────────────────────────────────────────────────┘
 tap (lp_out1+lp_out2) ──► CHIRP CHAINS per channel:
   32 first-order allpasses = 4 groups × 8, stretched lengths
   K = {3,5,6,7} samples, coefficients {−0.7, −0.65, −0.6, −0.5}
 ──► wet
```

```c
#define INP_ALLP_COEFF      (0.6f)
#define CHIRP_ALLP_COEFF    (-0.6f)
float32_t chrp_allp_k[4] = {-0.7f, -0.65f, -0.6f, -0.5f};
...
acc = lp_dly1.getTap(0) * rv_time;          // feedback gain = decay
lp_out1 = flt_lp1.process(acc);             // damping shelf in loop
acc = sp_lp_allp1a.process(lp_out1);        // 4 long allpasses (diffusion)
acc = lp_dly2.process(acc + mono_in) * rv_time;
...
inL = inR = (lp_out1 + lp_out2);            // tap both "transducer" points
// 4×8 stretched 1st-order allpasses per channel:
allp_idx = j*SPRVB_CHIRP1_LEN + chrp_alp1_idx[j];
acc = sp_chrp_alp1_buf[allp_idx] + inL * chrp_allp_k[0];
sp_chrp_alp1_buf[allp_idx] = inL - chrp_allp_k[0] * acc;
inL = acc;
```

Engineering choices: dispersion chain **outside** the loop (cheap; per-echo re-dispersion approximated by the in-loop long APs); stereo decorrelation by reversing coefficient order L vs R; LFO tap-rotation inside two allpasses for tail blur. **Most directly translatable reference for a C spring core.**

**(b) Chowdhury-DSP BYOD SpringReverb** (GPLv3 — study only, don't copy) — https://github.com/Chowdhury-DSP/BYOD/blob/main/src/processors/other/spring_reverb/SpringReverb.cpp. Runs 2× downsampled (Parker multirate):

```
x ──►(tanh)──►DC-block(40 Hz HP)──►[16 × nested 2nd-order Schroeder APs]──┬─► LP(damp) ─► y
      ▲                                                                   │
      └── −g_fb · z^(−L, Lagrange3, chaos-modulated) ◄────────────────────┤
             y ──►(− 4×parallel-delay Householder "reflection network")◄──┘
```

```c++
auto apfG = 0.5f - 0.4f * params.spin;
float apfGVec alignas (16)[4] = { apfG, -apfG, apfG, -apfG };
for (auto& apf : vecAPFs)
    apf.setParams (msToSamples (0.35f + 3.0f * params.size), xsimd::load_aligned (apfGVec));
```

16 nested 2nd-order APs (= 32 inner APs) with sign-alternating vector coefficients ±(0.5 − 0.4·spin), SIMD 4-wide; loop delay `1000 + 0.099·size·fs` samples with `feedbackGain = pow(0.001, delaySamples/(t60·fs))`, T60 ∈ [0.5, 4.5] s; **tanh at the loop summing node** (feedback saturation à la overdriven tank); `chaos` randomly modulates loop delay up to 7%; a "shake" feature injects a half-sine burst (physically rattling the tank); a 4-delay Householder "reflection network" (0.07/0.17/0.23/0.29 s × size) with 800 Hz damping shelf is *subtracted* from the main path.

**(c) Folklore check:** multiple independent implementations converge on first-order allpass chains with a ≈ −0.5…−0.7 (e.g. a Faust "extreme dispersive spring with nonlinear feedback" using `fi.allpass_fcomb(1024, delay, −0.7)` per stage — https://github.com/timini/wiggleroom/blob/main/src/modules/TetanusCoil/tetanus_coil.dsp).

---

# Part V — Plate physical models

## Plate physics (foundation for A25–A27)

**Kirchhoff–Love thin plate:**

```
ρh ∂²u/∂t² = −D ∇⁴u + loss terms + f(x,y,t),      D = E h³ / 12(1−ν²)
```

Flexural waves are dispersive with v_ph ∝ √ω — **highs travel faster**, giving the "whip-crack" IR onset (a *downward* chirp, opposite of the spring's LF behavior). Simply supported rectangular plate L_x × L_y modes:

```
ω_mn = √(D/ρh) · [ (mπ/L_x)² + (nπ/L_y)² ]
```

Modal density is **frequency-independent**: n(f) ≈ (A/2)·√(ρh/D); for an EMT 140 (steel ≈ 2 m × 1 m, h = 0.5 mm) roughly 1–1.5 modes/Hz — flat mode density across the band is exactly why plates sound "instantly dense and colorless," and why >20,000 modes are needed to cover 20 kHz.

**Damping** (Arcas & Chaigne, "On the quality of plate reverberation," Applied Acoustics 71(3), 2010 — https://www.sciencedirect.com/science/article/abs/pii/S0003682X09001716): four measured loss mechanisms — thermoelastic damping, free-field radiation, radiation into the porous damping plate, edge/support losses. The movable damping plate works by *acoustic coupling* through a thin air gap (that's the T60 control). Thermoelastic loss peaks mid-band, radiation loss near coincidence — so plate T60(f) is **bathtub-shaped**, not the exponential-lowpass of a standard FDN. Any convincing plate model must reproduce this.

## A25. Finite-difference Kirchhoff plate (Bilbao)

- Bilbao, Arcas & Chaigne, "A Physical Model for Plate Reverberation," ICASSP 2006 — https://ieeexplore.ieee.org/document/1661238 (Kirchhoff plate + measured EMT-140-style damping).
- Bilbao, "A Digital Plate Reverberation Algorithm," JAES 55(3):135–144, 2007 — https://www.aes.org/e-lib/download.cfm?ID=14153: direct numerical simulation of the thin-plate equations of motion via explicit FD, with **physical controls: stiffness, aspect ratio, tension, and a two-parameter loss model**; stability via the standard 2-D FD condition (grid spacing tied to stiffness and sample rate; cost scales with plate area × fs).

**Unique advantage over any filter network:** input/output positions are literal (x, y) coordinates on the plate — moving the "pickups" pans the reverb *physically*; extendable to nonlinear (von Kármán) plates for high-drive "crunch."

## A26. Modal plate with physical damping (Ducceschi & Webb)

**Papers:** Ducceschi & Webb, "Plate reverberation: Towards the development of a real-time physical model for the working musician," ICA 2016 — https://www.researchgate.net/publication/306936091; Willemsen, Ducceschi et al., "Virtual Analog Simulation and Extensions of Plate Reverberation," 2017 — https://www.researchgate.net/publication/323342218 (adds time-varying/pitch-warped plates).

**Method:** closed-form modes of the simply supported plate (formula above) + Arcas/Chaigne-style per-mode damping → a bank of 10⁴–10⁵ independent 2nd-order resonators (same update as A21). Real time achieved by **psychoacoustic mode-culling** (drop masked modes) + vectorization. Same resonator math as the modal spring (A21) and the modal reverberator (A39) — one engine, three products.

**Character:** exact plate whip + bathtub T60; per-mode control enables physically impossible tricks (detune the plate over time, morph plate size while ringing).

## A27. Hybrid convolution head + FDN tail — the EMT 140 / BX 20 product architecture

**Paper:** Abel, Berners & Greenblatt, "An Emulation of the EMT 140 Plate Reverberator Using a Hybrid Reverberator Structure," AES Convention 127, paper 7928 (2009) — https://aes.org/publications/elibrary-page/?id=15123. ("The EMT 140 is approximately linear and time invariant, and its impulse response is characterized by a whip-like onset and high echo density.")

```
x ──► [ short FIR convolution with measured IR onset (~tens of ms):
        captures the dispersive whip + early density EXACTLY ] ──► Σ ─► y
  └──► [ FDN fitted to the measured tail's T60(f) and echo density ] ─► Σ
```

**Key measured insight:** the IR onset is only **weakly dependent on the damping-plate setting**, so one convolution head serves all damping positions while only the cheap FDN tail is re-fit per setting — that's how the product gets a continuous "damper" knob. UA's AKG BX 20 spring plugin reuses the same "hybrid delay network/convolution" idea (https://www.uaudio.com/products/akg-bx-20-reverb), and it is the generic recipe for cloning *any* hardware unit whose onset is signature but whose tail is statistical (including a Bricasti-style early engine, A4).

---

# Part VI — Velvet-noise family (Aalto school: Välimäki, Fagerström, Schlecht, Alary, Prawda)

## Velvet noise: definition and math (foundation for A28–A32)

**Velvet noise (VN)** is a sparse ternary sequence {−1, 0, +1}; at pulse density **Nd ≈ 1500–2000 pulses/s it is perceptually indistinguishable from — and rated smoother than — Gaussian noise**, despite ~99.8% zeros. Origin: Karjalainen & Järveläinen, "Reverberation Modeling Using Velvet Noise," AES 30th Int. Conf., 2007 — https://www.aes.org/e-lib/download.cfm?ID=13941

**Original Velvet Noise (OVN):** grid Td = fs/Nd samples; one pulse per slot, jittered:

```
k(m) = round( m·Td + r1(m)·(Td − 1) ),   m = 0,1,2,...
s(m) = 2·round( r2(m) ) − 1
v[n] = Σ_m  s(m) · δ[n − k(m)]
```

Variants (DAFx-13 perceptual study — ARN renewal-process spacing, TRN Poisson, etc.): OVN is the smoothest at a given density. **Multiplication-free convolution**: an L-second VN of density Nd costs **Nd·L additions and 0 multiplications** per output sample:

```
y(n) = Σ_{m: s=+1} x(n − k(m))  −  Σ_{m: s=−1} x(n − k(m))
```

(2-s tail @ 2000 p/s → 4000 adds vs 88,200 MACs for dense FIR — the basis of ">100× cheaper than convolution": http://research.spa.aalto.fi/publications/papers/dafx13-vscreverb/)

Generation (Python; trivially C-portable):

```python
def ovn(fs, Nd, dur, rng):
    Td = fs / Nd
    M  = int(dur * Nd)
    k  = np.round(np.arange(M)*Td + rng.random(M)*(Td-1)).astype(int)
    s  = 2*np.round(rng.random(M)) - 1
    v  = np.zeros(int(dur*fs)); v[k] = s
    return v, k, s        # keep (k, s): convolution uses only the sparse form
```

## A28. Filtered Velvet Noise (FVN) late reverb

**Paper:** Välimäki, Holm-Rasmussen, Alary, Lehtonen, "Late Reverberation Synthesis Using Filtered Velvet Noise," *Applied Sciences* 7(5), 2017 (open access) — https://www.researchgate.net/publication/316802594

**Structure:** split the tail into segments hung off a tapped delay line; each segment = short VN convolver + **low-order coloration/attenuation IIR** whose gain matches the target frequency-dependent decay at that time offset. Sparse FIR does the diffusion; tiny IIRs do T60(f). Fully parametric, extremely cheap, zero recursion artifacts.

## A29. Interleaved Velvet Noise (IVN) — the cleanest recursive velvet late reverb

**Paper:** Välimäki & Prawda, "Late-Reverberation Synthesis Using Interleaved Velvet-Noise Sequences," IEEE/ACM TASLP 29:1149–1160, 2021 — https://ieeexplore.ieee.org/document/9360485/

**Structure:** B parallel recursive branches; branch b holds a VN sequence of length equal to its feedback-delay, with feedback filter G_b(z) for frequency-dependent decay. The B velvet sequences are **interleaved so their pulses never collide** → summed output has density B·Nd with zero overlap → exponentially decaying, spectrally controlled, artifact-free noise tail:

```
        ┌──────────────────────────────┐
x ──►(+)┤  z^-L_b   G_b(z) (LP decay)  ├──► VN_b (sparse FIR, offset grid b) ──┐
        └──────────────────────────────┘                                      (+)──► y
                     (b = 1..4, interleaved pulse grids)                       ┘
```

**Listening test: 4 interleaved branches suffice for a smooth high-quality response.** Different branch output combinations give mutually decorrelated channels for multichannel/binaural output. Directly relevant to the M7 blueprint's early engine and to ultra-cheap embedded late reverbs. Multichannel extension: https://research.aalto.fi/en/publications/multichannel-interleaved-velvet-noise/

## A30. Dark Velvet Noise (DVN) + non-exponential decay

**Papers:** Fagerström, Meyer-Kahlen, Schlecht, Välimäki, "Dark Velvet Noise," DAFx-22 — https://dafx2020.mdw.ac.at/proceedings/papers/DAFx20in22_paper_31.pdf; non-exponential extension: arXiv:2403.20090 — https://arxiv.org/abs/2403.20090; binaural: DAFx-24 — https://www.dafx.de/paper-archive/2024/papers/DAFx24_paper_63.pdf. **Code (MATLAB/Python/JUCE):** https://github.com/Ion3rik/dark-velvet-noise-reverb

**DVN:** each pulse gets a randomized width w(m):

```
v_DVN[n] = Σ_m s(m) · p_{w(m)}[n − k(m)],   p_w = rect of width w (sinc-lowpass spectrum)
```

Wider pulses → lowpass ("dark") spectrum. **Efficient realization:** a small bank of recursive running-sum filters `H_w(z) = (1 − z^{−w})/(1 − z^{−1})` (2 adds each, no multiplies), one per distinct width — essentially multiplication-free.

**Non-exponential decay:** draw each pulse from a **dictionary of dissipative (lowpassed) pulse filters**; convex optimization selects per-pulse filter probabilities/gains so the tail matches an **arbitrary temporal energy decay** — two-stage coupled-room decays, fade-in "bloom" tails (the M7/480L Shape behavior!), which single-slope FDNs cannot do.

**Binaural trick worth stealing:** the right-ear sequence reuses left-ear pulses with randomized timing offsets; jitter-distribution width parametrically sets **frequency-dependent interaural coherence at zero added cost**.

**Character:** smooth, colorless, naturally darkening tails; nothing rings (FIR); "spring-ish" lumpy non-exponential decays are also reachable — an atypical route to the spring LF echo train.

## A31. Switched Convolution Reverberator

**Paper:** Lee, Abel, Välimäki, Stilson, Berners, JAES 60(4):227–236, 2012 — https://www.aes.org/e-lib/online/browse.cfm?elib=16216

**Structure:** tail partitioned into variable-length segments of **sparse velvet FIRs + lowpass filters, cascaded with Schroeder allpasses**; the sparse filter is *switched* (re-randomized) over time to avoid static-pattern artifacts. Parametric, very cheap, smooth — the missing link between convolution and algorithmic reverbs, and the academic ancestor of A27's product architecture.

## A32. Velvet-noise decorrelators (VND) — early reflections & stereo width

**Papers:** Alary, Politis, Välimäki, "Velvet-Noise Decorrelator," DAFx-17 — http://www.dafx17.eca.ed.ac.uk/papers/DAFx17_paper_96.pdf; optimized version (pulse signs/gains numerically optimized for flat response + max decorrelation): Schlecht, Alary, Välimäki, Habets, DAFx-18 — MATLAB code: https://github.com/SebastianJiroSchlecht/OptimizedVelvetDecorrelators

**Structure:** short (~30 ms) VN FIR per channel, density ~1000 p/s, segment-wise decaying gains approximating an exponential envelope → phase randomization with minimal coloration, **zero latency**, dozens of additions per sample. Use for: dense specular M7-style early fields (A4 step 2), stereo widening of mono tails, CloudSeed-style multitap pre-diffusion (A7).

---

# Part VII — Advanced networks & research architectures

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

## A40. Scattering Delay Networks (SDN) + Room Acoustic Rendering Networks

**Paper:** De Sena, Hacıhabiboğlu, Cvetković, Smith, "Efficient Synthesis of Room Acoustics via Scattering Delay Networks," IEEE/ACM TASLP 23(9):1478–1492, 2015 — https://arxiv.org/abs/1502.05751; MATLAB reference: https://github.com/enzodesena/sdn-matlab; JOS chapter: https://ccrma.stanford.edu/~jos/lumped/Scattering_Delay_Networks.html

**Topology:** one scattering node per wall (cuboid → 6 nodes), placed at the first-order reflection point for the current source/listener geometry; every node pair joined by a bidirectional delay line; source/mic connect via unidirectional lines (+direct path):

```
            S (source)
          / | \  (1/d_Sk gains, delay d_Sk·fs/c)
        N1──N2          node scattering: S = (2/(N−1))·11ᵀ − I,  wall filter H_i(z)
        │╲ ╱│
        │ ╳ │           bidirectional lines, length d_ij·fs/c
        N3──N4 … N6
          \ | /  (output gains, delay d_kM·fs/c)
            M (mic)   + direct path S→M, gain 1/d_SM
```

**Math:** the isotropic scattering matrix `S = (2/(N−1))·11ᵀ − I` is a Householder-type reflection — orthogonal ⇒ lossless — and rank-1-plus-identity: apply as `p⁺_j = 2·mean(p⁻) − p⁻_j` (one mean + K adds, no matrix multiply). Wall absorption = scalar β_i = √(1−α_i) or wall filter H_i(z). Delays are physical propagation times; branch gains enforce the 1/r law so **first-order reflections are rendered exactly in time, amplitude and direction**; higher orders are progressively approximate but energy statistics match Sabine/Eyring.

**Extensions:** RARN (Scerbo, Savioja, De Sena, TASLP 2024 — https://arxiv.org/abs/2312.14658): surface patches instead of one node per wall, stability-preserving scattering, arbitrary numbers of exact early reflections — a tunable dial between cost and accuracy; differentiable SDN (DAFx-25 — https://www.dafx.de/paper-archive/2025/DAFx25_paper_51.pdf).

**Character:** the only delay-network reverb whose early field *moves correctly* when source/listener move — the physically-parameterized room/chamber option (a genuinely different "room" algorithm than Moorer-style tapped ERs).

## A41. Digital waveguide networks (DWN) & 3-D meshes

**Papers:** Smith & Rocchesso, "Connections between Feedback Delay Networks and Waveguide Networks for Digital Reverberation," ICMC 1994 — https://quod.lib.umich.edu/i/icmc/bbp2372.1994.098; Van Duyne & Smith, "The 2-D Digital Waveguide Mesh," ICMC 1993 — https://ccrma.stanford.edu/~jos/pdf/mesh.pdf; JOS PASP book — https://ccrma.stanford.edu/~jos/pasp/

**Lossless junction:** N waveguides with admittances Γ_i:

```
p_J  = ( 2·Σ_i Γ_i p_i⁺ ) / ( Σ_i Γ_i );      p_i⁻ = p_J − p_i⁺
```

**Key theoretical result:** an FDN with a Householder matrix **is exactly a single N-branch equal-impedance scattering junction**; multi-junction DWNs generate a much larger class of lossless FDN topologies (arbitrary graphs of unequal-impedance waveguides, lossless by construction). 2-D/3-D rectilinear meshes coincide with FDTD of the wave equation; dispersion error is direction-dependent (remedies: triangular/tetrahedral meshes, frequency warping); 3-D cost O(V·fs³/c³) → practical use is LF-only room modes + hybridization. **Use here:** the theory quarry for inventing new lossless topologies (it is where ring, FDN, and SDN meet), not a production reverb.

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

---

# Appendix 1 — Cross-family comparison

| # | design | loop element | decay control | modulation | matrix | license |
|---|---|---|---|---|---|---|
| A1 | Progenitor (224) | figure-8: modAPs + nested APs + delays | distributed leaky APs, g=10^(log10 k/RT) | ±32 smp sine→LPF, alternating signs + output gain-comb | none (cross-coupled loop) | GPL-2+ (reimplement) |
| A2 | Progenitor2 | A1 + 10 input APs/ch | same | noise-dithered delay AND coefficient | none | GPL-2+ |
| A4 | M7 blueprint | 16-line FDN + AP entries + velvet early | per-line shelves (A36) | none (or inaudible dither) | Hadamard | n/a (recipe) |
| A7 | CloudSeed | ≤12 parallel combs w/ AP diffusers inside | g_i = g^(d_i/d_max) | randomized sine on everything | none (parallel) | MIT |
| A8 | FV-1 rom_rev1 | ring of 4×(delay + 2AP(0.6)) | rt ×4/lap: RT60=0.75T/−log₁₀rt | 2 APs ±20 @ 0.5 Hz | none (ring) | Faust port GPL-3.0 |
| A10 | Clouds | ring of 2×(2AP + delay) | krt ×2/lap | AP1 ±60 @0.5; del2 ±100 @0.3 | none (ring) | MIT |
| A11 | Gardner | nested APs in one filtered loop | filtered loop gain | none | none | thesis |
| A12 | jpverb | 10 rotation-lattices + 4 delays per lap | fb = 10^(−3T/t60), 3-band | 4 chorused delays/lap | 2×2 rotations | MIT |
| A13 | greyhole | 3×4-nested lattices + long delay | raw feedback 0–1 | loop-delay chorus | 2×2 rotations | MIT |
| A15 | zita-rev1 | 8 branches: AP(±0.6)+delay+3-band filter | exact 10^(−3d/T60(ω)) per branch | none | Hadamard 8×8 | GPL-2+ / Faust STK-MIT |
| A16 | Galactic | 3×(4 delays + (2I−J)) cross-coupled | regen ∈ [1/16,1/8] ×8 matrix | input vibrato predelay | 2I−J ×3 | MIT |
| A17 | MatrixVerb | 4 AP + 8 modulated FDN lines | regen ≤ 0.5 × matrix 2 | per-line vibrato, 95/5 blend | 2×(4×4 Householder) | MIT |
| A18 | kPlate | 25 delays in 5×5 Householder ranks ×5 | tiny regen vs matrix gain | none (static, searched) | 5×5 + 3×3 Householder | MIT |
| A29 | IVN | 4 recursive interleaved VN branches | G_b(z) per branch | none | none | paper |
| A34 | VFDN | small FDN + velvet I/O FIRs | std FDN law | optional | Hadamard + VN | paper |

# Appendix 2 — Spring/plate model comparison

| approach | cost | params | chirp accuracy | nonlinearity | best use |
|---|---|---|---|---|---|
| A19 SDF parametric (+A24 code) | low (×D decimated) | f_C, M, a₁, T_lf, g_fb, mod | very good below f_C | waveshaper pre-chain + tanh in loop | product-grade spring; default choice |
| A20 waveguide + fitted dispersive AP | low–mid | measured τ(ω) fit | excellent (per unit) | terminations can be NL | cloning one tank |
| A21 modal spring (bead-coupled) | mid (N osc, parallel) | eigendata + σ_k, bead | best physical match | per-mode or I/O | high-end plugin |
| A22 FDTD spring | high (implicit) | R, r, α, damping | physical incl. HF branch | hard | reference/offline |
| A23 tube chain | trivial | dwell, tilt, knees | n/a (wrapper) | the whole point | wrap any spring core |
| A25 FD plate | high | plate physical params | plate whip exact | von Kármán ext. | movable pickups |
| A26 modal plate | mid–high (10⁴ modes, cullable) | L_x, L_y, h, D, T60(f) | n/a | per-mode tricks | real-time physical plate |
| A27 hybrid conv + FDN | mid | measured IR + FDN fit | exact onset | add sat stages | faithful product emulations |
| A18 kPlate | low | searched delay sets | n/a (flavor) | sine companding, tube variant | dense musical plate substitute |

# Appendix 3 — Cost sheet (order-of-magnitude, per output sample)

| architecture | ops/sample | multiplies? | notes |
|---|---|---|---|
| VN convolution, 2 s @ 2 kp/s | ~4000 adds | none | FIR, nothing rings |
| IVN (4 branches) | ~10² adds + 4 small IIRs | few | recursive, T60(f) |
| DVN | VN + a few RRS (2 adds ea.) | none | lowpass tail |
| VFDN (N=4 + VN I/O) | >50% less than N=16 FDN | some | DAFx-20 Table 1 |
| modal, 1600 modes | ~10⁴ MAC (~500 MIPS @48k) | all | small room; SIMD/GPU-friendly |
| SDN cuboid | 6 nodes × (K adds) + 30 lines | few | exact 1st-order reflections |
| 3-D mesh | O(V·fs³/c³) | few/junction | LF-only in practice |
| FDN + GEQ/line | N² + N·(≈10 biquads) MAC | all | ±5% T60 accuracy |
| FV-1 ring | ~30 delay/AP ops total | ~14 | 128-instruction budget proof |

# Appendix 4 — License summary for code reuse

| source | license | note |
|---|---|---|
| Airwindows (Galactic, MatrixVerb, kPlate, Verbity, Chamber) | MIT | freely minable |
| Mutable Instruments eurorack (Clouds/Elements/Rings) | MIT | freely minable |
| CloudSeed / CloudSeedCore | MIT | freely minable |
| hexefx_audiolib_F32 | MIT-style (PJRC notice) | best C spring reference |
| el-visio/dattorro-verb | MIT | context only (excluded topology) |
| Freeverb3 (progenitor, progenitor2, zrev2, allpass_t) | GPL-2.0+ (plus Griesinger design copyright header) | reimplement from constants; don't paste |
| Faust reverbs.lib (jpverb, greyhole, zita ports) | MIT/STK-4.3 **except** `kb_rom_rev1` = GPL-3.0 | quote delay tables (facts) freely; don't paste GPL code |
| Chowdhury-DSP BYOD | GPLv3 | study only |
| zita-rev1 (Adriaensen original) | GPL-2+ | Faust port is STK-MIT |
| Academic MATLAB (OptimizedVelvetDecorrelators, Two_stage_filter, dark-velvet-noise-reverb, sdn-matlab, FDN-Reverb-Riser) | varies/absent | check each repo before porting |

# Appendix 5 — Research caveats

1. Direct fetches of some primary hosts (spinsemi.com, valhalladsp.com, AES paywalled PDFs, Gardner thesis mirror) were egress-blocked during research; prose from those sites was reconstructed from search extracts and faithful open-source ports. **Verify Gardner's exact per-figure tables against the thesis PDF, and Barr's article text against spinsemi.com, before implementation.**
2. "Bricasti-adjacent" claims for CloudSeed and any Eventide Blackhole internals are community inference, not vendor documentation — labeled as such above.
3. The f_C ≈ c·r/(4πR²) formula in Part IV is an order-of-magnitude reconstruction — verify against Parker & Bilbao DAFx-09 before relying on it quantitatively.
4. All verbatim code excerpts were fetched from the linked repositories during this research session (2026-07-05); delay tables and coefficients quoted are from source, not from memory.
