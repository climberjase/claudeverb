# Fable Deep Research: Hall Reverbs — Bricasti M7 & Lexicon/Griesinger School

**Date:** 2026-07-05

> A1 Griesinger figure-8 loop (Lexicon 224/Progenitor) · A2 Progenitor2 noise-dithered Random Hall · A3 480L spin/wander semantics · A4 Bricasti M7 analysis & replication blueprint · A5 slow-attack riser FDN · A6 zrev2 hybrid · A7 CloudSeed.
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.


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
