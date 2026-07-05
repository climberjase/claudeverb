# Fable Deep Research: Shared Reverb Math Fundamentals

**Date:** 2026-07-05

> Primitives used throughout the research: Schroeder/leaky/modulated allpasses, loop-gain-to-RT60 law, normalized echo density (NED), FDN state-space form and losslessness conditions.
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.


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
