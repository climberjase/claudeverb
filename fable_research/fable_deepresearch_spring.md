# Fable Deep Research: Spring Reverbs (including the Tube-Driven Sound)

**Date:** 2026-07-05

> Spring physics (dispersion, f_C, bead coupling) · A19 parametric spring via spectral delay filters · A20 waveguide spring with fitted dispersive allpass · A21 modal spring · A22 FDTD helical spring · A23 tube-drive electronics chain (Fender 6G15) · A24 practical open-source spring cores.
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.


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
