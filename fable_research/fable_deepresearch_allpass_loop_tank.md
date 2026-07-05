# Fable Deep Research: Allpass-Loop & Tank Reverbs

**Date:** 2026-07-05

> A8 Keith Barr FV-1 ring · A9 Spin plates & rom_rev2 · A10 Mutable Instruments Clouds · A11 Gardner nested allpass · A12 JPverb · A13 GreyHole · A14 Dahl/Jot absorbent allpass · A15 Zita-Rev1 · plus the Airwindows tanks A16 Galactic and A17 MatrixVerb.
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.


## A8. Keith Barr's FV-1 allpass ring — `rom_rev1` (the "2AP + delay" loop)

**Context.** Keith Barr (co-founder MXR, founder Alesis — MIDIVerb — then Spin Semiconductor) documented his approach in the Spin knowledge base (http://www.spinsemi.com/knowledge_base/effects.html#Reverberation) and shipped it as the FV-1 ROM reverbs. Constraints that shaped it: **32,768 Hz** sample rate, **32,768 samples (exactly 1.0 s) delay RAM**, **128 instructions/sample**, and single-cycle `RDA`/`WRAP` ops that implement one allpass in ~2 instructions. A faithful, importable port of `rom_rev1.spn` exists in the Faust libraries as `re.kb_rom_rev1` (author Luca Spanedda, **GPL-3.0**, unlike the rest of reverbs.lib): https://github.com/grame-cncm/faustlibraries/blob/master/reverbs.lib. Sean Costello's tribute (topology description + Barr's own drawings): https://valhalladsp.com/2010/08/25/rip-keith-barr/; Barr's forum thread on ring-reverb history: http://www.spinsemi.com/forum/viewtopic.php?t=3

**The topology.** A **single feedback ring of 4 repeated blocks, each block = [delay] → [decay gain RT] → [2 series allpasses]**, damping filters in each block, input injected at two points, outputs tapped from the plain delays — never from inside an allpass ("to avoid the metallic sound that can result"). In Costello's words: Barr's building block was a **"2 allpass, 1 delay unit"**, and the design "injects input everywhere but takes output in only two places, allowing the sound to keep coming fresh as the thing decays away."

Barr's own words (Spin knowledge base, verified verbatim): *"The best resonator topology uses delays and all passes in a loop, usually two all passes, 1 delay, 2 allpasses, 1 delay, repeat as required, tied into single loop, with inputs injected at the juncture of delay outputs and the allpass pair input, and outputs taken from delays as required"* — and his modulation prescription: *"chorus generators can be placed in the delay element of a few of the all passes, which smears out any resonances that may arise in the reverb tail, with **SIN on one and COS on another from a single LFO** working well."* (The FV-1's two hardware SIN/COS LFOs with interpolated `CHO RDA` reads exist to make exactly this cheap.) Production proof that the topology scales: ValhallaVintageVerb's **Cathedral** mode is a scaled-up port of an FV-1 algorithm Costello wrote in 2014 — the original corresponds exactly to Size = 50% in the plugin (https://valhalladsp.com/2023/02/10/valhallavintageverb-the-modes/).

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


---

# Airwindows tanks (school intro)


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
