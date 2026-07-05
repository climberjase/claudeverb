# Fable Deep Research: Plate Reverbs

**Date:** 2026-07-05

> Plate physics (Kirchhoff PDE, modes, EMT 140 damping) · A25 finite-difference plate · A26 modal plate · A27 hybrid convolution head + FDN tail (EMT 140 / BX 20) · plus A18 Airwindows kPlate (brute-force-searched Householder plate).
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.


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


---

# Airwindows kPlate (school intro)


Source root: https://github.com/airwindows/airwindows/tree/master/plugins/LinuxVST/src (**MIT**). House style: delay lengths tuned at 44.1 kHz-equivalent; at higher rates the tank runs **undersampled** (`cycle`/`cycleEnd`: process the tank every 2nd/3rd/4th sample at 88.2/96+/176.4 kHz, linearly interpolating tank output) — saves CPU *and* keeps the tank tuning constant across rates.

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
