# Fable Deep Research: Velvet-Noise Reverbs

**Date:** 2026-07-05

> Velvet noise definition & math · A28 filtered velvet noise (FVN) · A29 interleaved velvet noise (IVN) · A30 dark velvet noise & non-exponential decay · A31 switched convolution reverberator · A32 velvet-noise decorrelators.
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.


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
