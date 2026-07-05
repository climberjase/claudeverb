# Fable Top Pick — Spring: Parametric Spectral-Delay Spring in a Tube-Drive Chain

**Date:** 2026-07-05
**Status:** Recommendation for implementation (spring slot)
**Built from:** A19 (Välimäki/Parker/Abel parametric spring) · A23 (Fender 6G15 tube-drive chain — the nonlinearity model) · A24(a) (hexefx structural reference) · A21/A22 (modal/FDTD as future ground truth) · A43(c) (chirp-rate modulation)
**Companion docs:** `fable_deepresearch_spring.md`, `Fable_research_detail.md`, `fable_summary.md` (#4 + #5)

---

## 1. The verdict

Implement the **parametric spring via spectral delay filters** (A19: a cascade of ~M = 100–200 identical first-order allpasses forms the LF chirp; a feedback loop with a randomly modulated ~30–60 ms delay produces the progressively blurred echo train; a separate short HF branch adds the metallic sheen) — and wrap it in the **complete tube-drive electronics chain** (A23), which is where the "tube spring" identity actually lives. The spring core is #4 in `fable_summary.md`; the tube chain is #5 and is explicitly described there as "trivial DSP, dominant sonic effect."

The central design commitment, from A23, dictates the whole signal flow:

> **Model Dwell as pre-dispersion gain into a fixed-knee saturator, not as wet gain.** A waveshaper *before* the dispersion chain makes attacks "spit"; a weaker saturator *inside* the loop makes drip bloom and duck with level.

Distortion **before** dispersion is the tube-spring fingerprint: harmonics generated on a transient are then *smeared into the chirp*, which is what listeners identify as "drip."

### Alternatives considered

| Candidate | Why not the pick |
|---|---|
| A21 modal spring (van Walstijn/McQuillan) | Best physical match to a *measured* tank (incl. bead coupling, JAES 2025), but needs an offline eigensolver toolchain and ~10³ biquads/spring. It is the designated **phase-3 upgrade and offline ground truth** — the tube chain built here wraps it unchanged. |
| A22 FDTD helical spring | Research-grade reference; barely real-time; wrong cost profile for a tested-C target. Use to *generate calibration IRs*. |
| A20 waveguide + fitted dispersive AP | Excellent for cloning one specific tank from a measurement; less parametric. The A19 model subsumes it for a knob-driven claudeverb algorithm. |
| A24(a) hexefx core as-is | Great C reference (dispersion outside the loop = cheap) but that shortcut loses per-echo re-dispersion — the increasing chirp curvature of real springs. We keep its engineering ideas (stretched-AP groups, coefficient-order stereo decorrelation) but put the cascade **inside** the loop per A19. |

---

## 2. The physics targets (what the DSP must reproduce)

From the spring-physics foundation in `fable_deepresearch_spring.md`:

- **Transition frequency f_C ≈ 2.5–4.5 kHz** (calibrated example 4216 Hz). Below f_C: echo train with period **T_lf ≈ 30–60 ms**, every echo a chirp (lows arrive first), curvature increasing with echo index (n-th echo has n× dispersion). Group velocity minimum at f_C → persistent "boing" band.
- **Above f_C:** a much faster (~10× shorter period), nearly non-dispersive pulse train — sheen, not boings.
- **Bead/transducer band-shaping:** usable band ≈ 100 Hz–5 kHz with a resonant LF bump — 2nd-order band filters at model input and output.
- **Tube electronics:** ~200 Hz–4 kHz effective wet band, +6 dB/oct drive tilt, level-dependent asymmetric saturation before the tank, gentle softclip after it, decay that audibly *compresses/ducks* when slammed (Dwell interacts with decay).

---

## 3. Architecture

```
                        ┌─────────────────────  TUBE DRIVE (A23)  ─────────────────────┐
 x (mono sum) ──► [12AT7: mild asym waveshaper + HP 300 Hz] ──► ×Dwell ──►
     [6K6 + transformer: HP 180 Hz → +6 dB/oct tilt (→ ~2.5 kHz) → asym soft-sat, ADAA]
                        └──────────────────────────────┬───────────────────────────────┘
                                                       ▼
   ┌──────────────────────  SPRING CORE, LF (A19), runs at fs/D  ──────────────────────┐
   │                                                                                   │
   │   ──►(+)──► [ A(z)^M : M ≈ 100 first-order APs, a₁ ≈ −0.6 ]──┬─► pre-echo taps ─┐ │
   │       ▲          (per-echo re-dispersion happens because      │                 │ │
   │       │           the cascade is INSIDE the loop)             ▼                 ▼ │
   │       └─[×(−g_fb)]◄─[tanh loop sat]◄─[LP f_C]◄─[DC-block]◄─[z^(−L ± mod)]      Σ ─┼─► ×w_lf
   │                                                  L = T_lf·fs/D − M·τ(0)          │
   └───────────────────────────────────────────────────────────────────────────────────┘
   ┌────────────────  SPRING CORE, HF (full rate)  ─────────────────┐
   │  ──►(+)──► [ stretched cascade: M_hf ≈ 24 APs, z⁻¹→z⁻ᴷ ]──┬──► ×w_hf
   │      ▲                                                     │
   │      └──[×(−g_hf)]◄──[HP f_C]◄──[z^(−L_hf ± mod)]◄─────────┘
   └────────────────────────────────────────────────────────────────┘
        Σ(LF↑D interpolated, HF) ──► [bead/pickup bandpass 150 Hz–4.5 kHz, resonant]
        ──► [12AX7 recovery: gentle softclip + Tone LP] ──► wet ──► mix with dry (stereo: 2
             detuned cores, or coefficient-order-swapped cascades L/R per A24(a))
```

### 3.1 The dispersion primitive — math

First-order allpass `A(z) = (a₁ + z⁻¹)/(1 + a₁z⁻¹)`, group delay

```
τ(ω) = (1 − a₁²) / (1 + 2a₁cos ω + a₁²)   [samples]
τ(0) = (1 − a₁)/(1 + a₁)        τ(π) = (1 + a₁)/(1 − a₁)
```

For a₁ = −0.6: τ(0) = 4, τ(π) = 0.25. A cascade of M identical sections multiplies group delay by M → an impulse becomes a chirp spanning M·[0.25, 4] samples, lows last… **but we need lows *first*** — in the spring the *low* frequencies arrive first below f_C (highs travel slower in the flexural branch). Convention check from A19: a₁ < 0 delays lows most *at DC*; the measured spring chirp sweeps **up** (lows early → highs late) *within the sub-f_C band as rendered by the decimated model*: at the reduced rate fs/D, the band 0…f_C maps to 0…π, and τ rising toward π (a₁ = −0.6 gives τ min at DC in the *stretched* sense…) — **resolve empirically**: the A19 paper and every open implementation (A24) use a₁ ≈ −0.6 at the decimated rate and produce the correct upward-curving arcs; keep a₁ sign a parameter and verify against the spectrogram test in §7. (This sign subtlety is called out so the implementer doesn't "fix" it by intuition.)

**Placing f_C:** two mechanisms, use both:
1. **Multirate (Parker, A19-efficiency):** run the LF core at fs/D with `D = floor(fs/(2·f_C_headroom))`; at fs = 48 kHz and f_C = 4.2 kHz, D = 5 (core rate 9.6 kHz, Nyquist 4.8 kHz). This alone puts the entire cascade's dispersion into 0–4.8 kHz *and* cuts cost ≈ 5× (the "⅓ cost" claim of A19 is conservative). Anti-alias with the loop's own LP(f_C) plus a short polyphase FIR for the ↓D/↑D.
2. **Stretched allpasses** (z⁻¹ → z⁻ᴷ) for the HF branch: dispersion peak lands near ω = π/K, i.e. `f_peak ≈ fs/(2K)`; K = 5–6 at 48 kHz puts it at 4–4.8 kHz — matching hexefx's empirically-chosen K = {3,5,6,7} groups (A24a).

**Echo period:** total LF loop time = delay + cascade LF group delay:

```
T_lf · fs/D = L + M·τ(0)     →     L = T_lf·fs/D − M·(1 − a₁)/(1 + a₁)
```

(M = 100, a₁ = −0.6, D = 5, T_lf = 42 ms @ 48 kHz → L = 403 − 400 = 3 … i.e. at these settings the cascade *is* most of the loop; pick M and T_lf jointly, keep L ≥ 32 for modulation headroom, e.g. M = 80 → L = 83.)

**Decay:** per-echo gain g_fb ⇒ `RT60 = −3·T_lf / log₁₀(g_fb · g_sat_avg)`; note the tanh loop saturator makes decay level-dependent **by design** (§4.4).

**Pre-echoes / multi-chirp:** tap the cascade at 2–3 intermediate points (e.g. after M/3 and 2M/3 stages), summed with small gains (±0.2) — reproduces polarization-conversion pre-echoes (A19).

**Chirp "wobble"** (optional, A43c): modulate a₁ by ±0.02 with slew-limited noise — vibrato-of-dispersion, an alive quality no static cascade has.

### 3.2 The random echo-blur modulation

The loop delay L is modulated by **slew-limited noise** (not sine): ±2–4 samples at the decimated rate, noise LPF ≈ 1–3 Hz. Each traversal re-disperses *and* slightly re-times, so echo n has n-fold accumulated blur — the measured "echoes dissolve into wash" behavior (A19). Sine modulation here sounds like chorus, wrong for spring.

---

## 4. The tube nonlinearity model (the point of this pick)

Every stage below is memoryless-nonlinear or first/second-order linear — cheap, but ordering is everything. All saturators run with **first-order ADAA** (antiderivative anti-aliasing) or 2× oversampling, because the drive stage is *meant* to be pushed (§4.6).

### 4.1 Stage 1 — 12AT7 input stage (pre-Dwell)

Mild, asymmetric, always-on. Bias-shifted tanh with the bias re-centered so silence stays at zero:

```
f₁(x) = tanh(g₁·x + b) − tanh(b),      g₁ ≈ 1.5, b ≈ 0.2
```

Asymmetry (b ≠ 0) generates even harmonics — the "warm" tube signature; keep g₁ low so this stage only grazes. Follow with a 1-pole HP at ~300 Hz (the 6G15's RC into the driver: bass never reaches the tank hard).

### 4.2 Stage 2 — Dwell → 6K6 power stage + output transformer + coil

Dwell is a *gain into a fixed knee* (0.5…8×). The electrical load (pentode ≈ current source into the coil's rising impedance) gives the **+6 dB/oct tilt**; the transformer gives LF rolloff plus level-dependent LF sag. Model:

```
u  = Dwell · f₁-output
u  = HP₁₈₀(u)                                  1-pole, transformer magnetizing L
u  = TILT(u):  H(s) = (1 + s/ω_z)/(1 + s/ω_p), f_z = 200 Hz, f_p = 2.5 kHz
               (first-order shelf ≈ +6 dB/oct across the wet band, flattening at f_p
                where coil losses take over — A23 mechanism 2)
y  = f₂(u):    asymmetric soft clip with level-dependent bias (grid-current shift):
               b₂[n] = 0.98·b₂[n−1] + 0.02·max(u,0)          (envelope → bias creep)
               f₂(u) = (u − 0.35·b₂) / (1 + |u − 0.35·b₂|^p)^(1/p),   p ≈ 2.2
```

The bias-creep term is the cheapest honest model of grid-conduction shift: sustained loud input pushes the operating point, increasing asymmetry exactly when a real 6G15 does. `p ≈ 2.2` gives a knee between tanh (p→∞ harsh) and x/(1+|x|) (p=1 soft).

### 4.3 Stage — bead/transducer bandpass (linear, but essential)

Input and output of the spring core each get a 2nd-order filter pair (per A23/McQuillan-2025 guidance): HP biquad 150 Hz Q = 0.8 + LP biquad 4.5 kHz **Q = 1.6** — the resonant LP peak just below f_C reinforces the "boing" band the way the group-velocity pileup does physically.

### 4.4 Stage — in-loop saturator (decay ducking)

Inside the LF feedback loop, before the feedback gain:

```
w → tanh(d·w)/d,     d = drive_loop ∈ [0.5, 3]
```

Passivity: |tanh(d·w)/d| ≤ |w| for all d > 0, so the loop **cannot** blow up regardless of g_fb ≤ 1 — a free stability guarantee (A42's principle). Sonic effect: loud echoes are compressed → early tail denser/louder, then decay *opens up* as level drops — the "drip blooms then relaxes" behavior; and because Dwell raises loop level, **Dwell audibly shortens/thickens apparent decay**, matching the hardware interaction (A23; BYOD puts tanh at exactly this node, A24b).

### 4.5 Stage 3 — 12AX7 recovery + Tone

```
f₃(x) = x / (1 + 0.6·x²)          gentle, symmetric-ish softclip (flutter peaks only)
Tone  = 1-pole LP, 1.5–8 kHz
```

### 4.6 Aliasing control — first-order ADAA

For each memoryless saturator f with antiderivative F:

```
y[n] = ( F(x[n]) − F(x[n−1]) ) / ( x[n] − x[n−1] )     if |x[n]−x[n−1]| > ε
     = f( (x[n]+x[n−1])/2 )                            otherwise
F_tanh(x)  = ln cosh(x)        F_{x/(1+0.6x²)}(x) = (1/1.2)·ln(1 + 0.6x²)
```

(Bilinear-form ADAA: Parker/Zavalishin/Le Bivic, DAFx-16.) The p-norm clipper of §4.2 has no closed-form antiderivative for arbitrary p — use p = 2 there (`F(x) = asinh(x)` family: with p = 2, f(u) = u/√(1+u²), F(u) = √(1+u²)) or 2× oversample just that stage. At 48 kHz with these gentle knees, ADAA alone is clean; the spring core's LP(f_C) then strips anything above the wet band anyway.

---

## 5. Parameter API (param_specs)

| name | min | max | default | unit | maps to |
|---|---|---|---|---|---|
| `dwell` | 0.5 | 8.0 | 2.0 | × | §4.2 pre-sat gain |
| `f_c` | 2200 | 4800 | 4200 | Hz | decimation D, LP/HP split, LP(f_C), bead LP corner |
| `t_lf` | 25 | 65 | 42 | ms | echo period → L |
| `rt60` | 0.8 | 5.0 | 2.2 | s | g_fb = 10^(−3·T_lf/RT60) (pre-saturator) |
| `n_stages` (M) | 40 | 160 | 100 | — | chirp length (fixed max alloc 160) |
| `a1` | −0.75 | −0.45 | −0.60 | — | chirp curvature |
| `mod_depth` | 0 | 4 | 2.0 | smp | loop-delay noise excursion (decimated rate) |
| `wobble` | 0 | 1 | 0.15 | — | a₁ noise mod ±0.02 (A43c) |
| `loop_drive` | 0.5 | 3.0 | 1.2 | × | §4.4 in-loop tanh |
| `hf_level` | 0 | 1 | 0.35 | — | HF branch mix (sheen) |
| `tension` (K) | 3 | 7 | 5 | — | HF stretched-AP factor |
| `tone` | 1500 | 8000 | 4000 | Hz | recovery LP |
| `springs` | 1 | 3 | 2 | — | parallel detuned cores (T_lf ×{1, 1.07, 0.93}) |
| `mix` | 0.0 | 1.0 | 0.35 | — | dry/wet |

---

## 6. Code

### 6.1 Python prototype (claudeverb-compatible)

Key practical trick for Python speed: the LF core runs **block-wise at the decimated rate** with block size ≤ L_min − mod_depth, so the feedback loop is exact while each cascade stage processes a whole block via `scipy.signal.lfilter` (each AP is `lfilter([a1, 1], [1, a1], x)`). The C version (§6.2) is per-sample. Nonlinear stages are vectorized numpy. Condensed to the DSP; boilerplate follows `fdn_reverb.py`.

```python
"""Tube spring: A19 parametric spectral-delay core in the A23 tube chain."""
import math
import numpy as np
from scipy.signal import lfilter, resample_poly
from claudeverb.algorithms.base import ReverbAlgorithm


def adaa_tanh(x: np.ndarray, x1: float, d: float):
    """First-order ADAA tanh(d*x)/d over a block; returns (y, new_x1)."""
    xs = np.concatenate(([x1], x)).astype(np.float64)
    dx = np.diff(xs)
    F = np.log(np.cosh(d * xs)) / (d * d)
    y = np.where(np.abs(dx) > 1e-6,
                 np.diff(F) / np.where(dx == 0, 1, dx),
                 np.tanh(d * (xs[:-1] + xs[1:]) * 0.5) / d)
    return y.astype(np.float32), float(x[-1])


def sat_p2(u: np.ndarray, bias: float):
    """Asymmetric p=2 softclip with grid-bias creep; block-wise (§4.2)."""
    out = np.empty_like(u)
    b = bias
    for i in range(len(u)):                 # short blocks: acceptable
        b = 0.98 * b + 0.02 * max(u[i], 0.0)
        v = u[i] - 0.35 * b
        out[i] = v / math.sqrt(1.0 + v * v)
    return out, b


class TubeSpring(ReverbAlgorithm):
    def __init__(self, sample_rate: int = 48000, **params) -> None:
        self.fs = sample_rate
        self.p = {**{"dwell": 2.0, "f_c": 4200.0, "t_lf": 42.0, "rt60": 2.2,
                     "n_stages": 100, "a1": -0.60, "mod_depth": 2.0,
                     "loop_drive": 1.2, "hf_level": 0.35, "tension": 5,
                     "tone": 4000.0, "mix": 0.35}, **params}
        self._initialize()

    def _initialize(self) -> None:
        p, fs = self.p, self.fs
        self.D = max(2, int(fs / (2.0 * p["f_c"] * 1.14)))     # decim factor
        fsd = fs / self.D
        self.M = int(p["n_stages"])
        self.a1 = np.float32(p["a1"])
        tau0 = (1 - p["a1"]) / (1 + p["a1"])
        self.L = max(32, int(p["t_lf"] * 1e-3 * fsd - self.M * tau0))
        self.g_fb = np.float32(10.0 ** (-3.0 * p["t_lf"] * 1e-3 / p["rt60"]))
        self.casc_state = np.zeros(self.M, dtype=np.float64)   # lfilter zi
        self.loop_buf = np.zeros(self.L + 16, dtype=np.float32)
        self.loop_wr = 0
        self.dc_x = 0.0; self.dc_y = 0.0                       # loop DC blocker
        self.lp_state = 0.0                                    # loop LP(f_C)
        self.lp_c = 1 - math.exp(-2 * math.pi * p["f_c"] / fsd)
        self.noise_lp = 0.0
        self.rng = np.random.default_rng(23)
        # HF branch (full rate): stretched cascade, K = tension
        K = int(p["tension"]); self.K = K
        self.M_hf = 24
        self.hf_state = np.zeros((self.M_hf, K), dtype=np.float64)
        self.hf_buf = np.zeros(int(0.005 * fs), dtype=np.float32)  # ~5 ms loop
        self.hf_wr = 0
        self.g_hf = np.float32(0.45)
        self.hf_hp = 0.0
        # tube chain states
        self.x1_in = 0.0; self.bias2 = 0.0; self.x1_loop = 0.0
        self.hp300 = 0.0; self.hp180 = 0.0
        self.tilt_z = 0.0                                       # 1st-ord shelf state
        self.tone_s = 0.0
        # bead bandpass biquads (HP150 Q.8, LP4500 Q1.6): design once
        from claudeverb.algorithms.filters import BiquadFilter    # repo primitive
        self.bead_in = [BiquadFilter.highpass(150, 0.8, fs),
                        BiquadFilter.lowpass(p["f_c"] * 1.07, 1.6, fs)]
        self.bead_out = [BiquadFilter.highpass(150, 0.8, fs),
                         BiquadFilter.lowpass(p["f_c"] * 1.07, 1.6, fs)]

    # ---- LF core: one decimated block through cascade + loop ----
    def _lf_core(self, blk: np.ndarray) -> np.ndarray:
        n = len(blk)
        assert n <= self.L - 8
        # read n samples of feedback from loop delay (with noise-modulated tap)
        self.noise_lp += 0.02 * (self.rng.uniform(-1, 1) - self.noise_lp)
        off = self.p["mod_depth"] * self.noise_lp
        idx = (self.loop_wr - self.L + np.arange(n) - off)
        i0 = np.floor(idx).astype(int) % len(self.loop_buf)
        fr = np.float32(idx - np.floor(idx))
        i1 = (i0 + 1) % len(self.loop_buf)
        fb = self.loop_buf[i0] * (1 - fr) + self.loop_buf[i1] * fr
        v = blk - self.g_fb * fb                     # (+) with −g_fb feedback
        # cascade of M identical APs, each a block lfilter with carried state
        b = [self.a1, 1.0]; a = [1.0, self.a1]
        for m in range(self.M):
            v, z = lfilter(b, a, v, zi=[self.casc_state[m]])
            self.casc_state[m] = z[0]
        y = v.astype(np.float32)
        # loop conditioning: tanh sat -> LP(f_C) -> DC block -> write
        w, self.x1_loop = adaa_tanh(y, self.x1_loop, self.p["loop_drive"])
        for i in range(n):                            # tiny per-sample tail
            self.lp_state += self.lp_c * (w[i] - self.lp_state)
            d_in = self.lp_state
            dc = d_in - self.dc_x + 0.995 * self.dc_y
            self.dc_x, self.dc_y = d_in, dc
            self.loop_buf[self.loop_wr] = dc
            self.loop_wr = (self.loop_wr + 1) % len(self.loop_buf)
        return y

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        stereo = audio.ndim == 2
        x = audio.mean(axis=0) if stereo else audio          # mono tank drive
        p = self.p
        # ---- tube drive (full rate, vectorized) ----
        u = np.tanh(1.5 * x + 0.2) - math.tanh(0.2)          # 12AT7
        u = self._onepole_hp(u, "hp300", 300.0)
        u = np.float32(p["dwell"]) * u
        u = self._onepole_hp(u, "hp180", 180.0)
        u = self._tilt(u, 200.0, 2500.0)                     # +6 dB/oct band tilt
        u, self.bias2 = sat_p2(u, self.bias2)                # 6K6 + xfmr
        for bq in self.bead_in:
            u = bq.process_block(u)
        # ---- LF core at fs/D ----
        lf_in = resample_poly(u, 1, self.D).astype(np.float32)
        blk = self.L - 8
        lf_out = np.concatenate([self._lf_core(lf_in[i:i + blk])
                                 for i in range(0, len(lf_in), blk)])
        lf = resample_poly(lf_out, self.D, 1)[:len(u)].astype(np.float32)
        # ---- HF branch at full rate (stretched cascade, short loop) ----
        hf = self._hf_branch(u)
        wet = lf + np.float32(p["hf_level"]) * hf
        for bq in self.bead_out:
            wet = bq.process_block(wet)
        wet = wet / (1.0 + 0.6 * wet * wet)                  # 12AX7 recovery
        wet = self._onepole_lp(wet, "tone_s", p["tone"])
        out = np.zeros((2, len(x)), dtype=np.float32)
        # stereo: L direct, R = short decorrelating allpass on wet (A24a trick)
        out[0] = (1 - p["mix"]) * x + p["mix"] * wet
        out[1] = (1 - p["mix"]) * x + p["mix"] * np.roll(wet, 7)  # placeholder
        return out if stereo else out[0]
```

(`_onepole_hp/_onepole_lp/_tilt/_hf_branch` are 5-line helpers in the same style; `BiquadFilter.highpass/lowpass` = repo biquad with RBJ coefficients; the `np.roll` decorrelator is a placeholder for a 7-sample allpass. `springs > 1` = run 2–3 `_lf_core` instances with T_lf scaled ×{1.0, 1.07, 0.93} and sum — the real reason two-spring tanks sound "wider".)

### 6.2 C translation (per-sample, export-ready)

The cascade is the hot loop: M states, 2 multiplies each, single-precision. Per-sample cost at 48 kHz ≈ M/D·2 (cascade, decimated) + 24·2 (HF) + ~40 (filters + saturators) ≈ **~150 flops/sample** at defaults — trivially real-time; ~2 KB of state.

```c
#define SPR_MAX_STAGES 160
#define SPR_MAX_LOOP   1024      /* decimated-rate loop delay */
#define SPR_HF_STAGES  24
#define SPR_HF_K       7

typedef struct {
    /* LF chirp cascade + loop (all at fs/D) */
    float casc_s[SPR_MAX_STAGES];        /* one state per 1st-order AP  */
    int   n_stages;
    float a1;
    float loop_buf[SPR_MAX_LOOP];
    int   loop_len, loop_wr;             /* loop_len = L                */
    float g_fb, loop_drive;
    float lp_c, lp_s;                    /* loop LP(f_C)                */
    float dc_x, dc_y;                    /* loop DC blocker             */
    float noise_lp, mod_depth;
    unsigned rng;
    float adaa_x1, adaa_f1;              /* loop tanh ADAA state        */
    /* decimator (D-phase averaging FIR halfband pair or simple polyphase) */
    int   D, dphase;
    float dec_acc, interp_z;
    /* HF branch (full rate) */
    float hf_s[SPR_HF_STAGES][SPR_HF_K];
    int   hf_k;
    float hf_buf[256]; int hf_len, hf_wr;
    float g_hf, hf_hp_s;
    /* tube chain */
    float dwell, hp300_s, hp180_s, hp_c300, hp_c180;
    float tilt_z, tilt_b0, tilt_b1, tilt_a1;    /* 1st-order shelf */
    float bias2;
    float bead_in_z[2][4],  bead_in_c[2][5];    /* 2 biquads TDF-II */
    float bead_out_z[2][4], bead_out_c[2][5];
    float tone_s, tone_c;
    float mix;
} TubeSpringState;

static inline float spr_ap1(float *s, float a1, float x)
{   /* H = (a1 + z^-1)/(1 + a1 z^-1), transposed DF-II: y = a1*x + s; s = x - a1*y */
    float y = a1 * x + *s;
    *s = x - a1 * y;
    return y;
}

static inline float spr_tanh_adaa(TubeSpringState *s, float x, float d)
{
    float dx = x - s->adaa_x1;
    float F  = logf(coshf(d * x)) / (d * d);
    float y  = (fabsf(dx) > 1e-6f) ? (F - s->adaa_f1) / dx
                                   : tanhf(d * 0.5f * (x + s->adaa_x1)) / d;
    s->adaa_x1 = x;  s->adaa_f1 = F;
    return y;
}

/* one sample at the DECIMATED rate through cascade + loop */
static float spr_lf_tick(TubeSpringState *s, float x)
{
    /* modulated feedback read (linear interp) */
    s->rng ^= s->rng << 13; s->rng ^= s->rng >> 17; s->rng ^= s->rng << 5;
    float n = (float)(int)s->rng * (1.f / 2147483648.f);
    s->noise_lp += 0.02f * (n - s->noise_lp);
    float rpos = (float)s->loop_wr - (float)s->loop_len
               - s->mod_depth * s->noise_lp;
    while (rpos < 0.f) rpos += (float)SPR_MAX_LOOP;
    int i0 = (int)rpos, i1 = i0 + 1;
    if (i1 >= SPR_MAX_LOOP) i1 = 0;
    float fr = rpos - (float)i0;
    float fb = s->loop_buf[i0] + fr * (s->loop_buf[i1] - s->loop_buf[i0]);

    float v = x - s->g_fb * fb;
    for (int m = 0; m < s->n_stages; m++)
        v = spr_ap1(&s->casc_s[m], s->a1, v);
    float y = v;                                   /* chirped output tap */

    float w = spr_tanh_adaa(s, y, s->loop_drive);  /* in-loop saturation */
    s->lp_s += s->lp_c * (w - s->lp_s);            /* LP(f_C)            */
    float dc = s->lp_s - s->dc_x + 0.995f * s->dc_y;
    s->dc_x = s->lp_s;  s->dc_y = dc;              /* DC blocker         */
    s->loop_buf[s->loop_wr] = dc;
    if (++s->loop_wr >= SPR_MAX_LOOP) s->loop_wr = 0;
    return y;
}

void tube_spring_process(TubeSpringState *s, const float *in,
                         float *out_l, float *out_r, int n)
{
    for (int t = 0; t < n; t++) {
        /* ---- tube drive, full rate ---- */
        float x = in[t];
        float u = tanhf(1.5f * x + 0.2f) - 0.19738f;         /* 12AT7 */
        s->hp300_s += s->hp_c300 * (u - s->hp300_s); u -= s->hp300_s;
        u *= s->dwell;
        s->hp180_s += s->hp_c180 * (u - s->hp180_s); u -= s->hp180_s;
        { float y = s->tilt_b0 * u + s->tilt_z;              /* +6dB/oct tilt */
          s->tilt_z = s->tilt_b1 * u - s->tilt_a1 * y;  u = y; }
        s->bias2 = 0.98f * s->bias2 + 0.02f * (u > 0.f ? u : 0.f);
        { float v = u - 0.35f * s->bias2;                    /* 6K6+xfmr, p=2 */
          u = v / sqrtf(1.f + v * v); }
        /* bead input bandpass: 2 x TDF-II biquad (coef in bead_in_c) */
        for (int b = 0; b < 2; b++) {
            float *c = s->bead_in_c[b], *z = s->bead_in_z[b];
            float y = c[0] * u + z[0];
            z[0] = c[1] * u - c[3] * y + z[1];
            z[1] = c[2] * u - c[4] * y;
            u = y;
        }
        /* ---- LF core at fs/D: naive polyphase (average-down, hold-interp up) */
        float lf;
        s->dec_acc += u;
        if (++s->dphase >= s->D) {
            s->dphase = 0;
            float ylf = spr_lf_tick(s, s->dec_acc / (float)s->D);
            s->interp_z = ylf;        /* zero-order hold; upgrade: halfband FIR */
            s->dec_acc = 0.f;
        }
        lf = s->interp_z;
        /* ---- HF branch: stretched cascade + short loop ---- */
        float hfb = s->hf_buf[s->hf_wr];
        s->hf_hp_s += 0.35f * (hfb - s->hf_hp_s);
        float h = u - s->g_hf * (hfb - s->hf_hp_s);          /* HP'd feedback */
        for (int m = 0; m < SPR_HF_STAGES; m++) {            /* z^-1 -> z^-K  */
            float *st = s->hf_s[m];
            float xin = h;
            float y = 0.5f * xin + st[s->hf_k ? s->hf_k - 1 : 0]; /* a=+0.5    */
            /* stretched AP: rotate K-slot state ring per stage */
            float ynew = 0.5f * xin + st[0];
            for (int k = 0; k < SPR_HF_K - 1; k++) st[k] = st[k + 1];
            st[SPR_HF_K - 1] = xin - 0.5f * ynew;
            h = ynew; (void)y;
        }
        s->hf_buf[s->hf_wr] = h;
        if (++s->hf_wr >= s->hf_len) s->hf_wr = 0;

        float wet = lf + 0.35f * h;
        for (int b = 0; b < 2; b++) {                        /* bead output BP */
            float *c = s->bead_out_c[b], *z = s->bead_out_z[b];
            float y = c[0] * wet + z[0];
            z[0] = c[1] * wet - c[3] * y + z[1];
            z[1] = c[2] * wet - c[4] * y;
            wet = y;
        }
        wet = wet / (1.f + 0.6f * wet * wet);                /* 12AX7 recovery */
        s->tone_s += s->tone_c * (wet - s->tone_s);
        wet = s->tone_s;

        out_l[t] = (1.f - s->mix) * x + s->mix * wet;
        out_r[t] = out_l[t];   /* stereo: second detuned core or 7-smp AP */
    }
}
```

(The zero-order-hold interpolator and per-stage K-slot rotation are the two places to upgrade first: a 15-tap halfband FIR for ↑D and a circular index instead of the memmove-style rotate. Both are marked; neither changes the architecture.)

---

## 7. Verification plan

1. **f_C:** spectrogram (repo `plot_mel_comparison` or raw STFT) of the wet IR shows chirp arcs curving toward and flattening at f_C ± 10%, with the energy ridge ("boing" band) at f_C — the Gamper/Parker/Välimäki DAFx-11 calibration read in reverse.
2. **Echo period:** autocorrelation of the wet IR envelope peaks at T_lf ± 5%, harmonics decaying (blur).
3. **Increasing chirp curvature:** arc n's instantaneous-frequency slope ≈ n × arc 1's (per-echo re-dispersion — this is the test that fails if the cascade is moved outside the loop).
4. **RT & ducking:** `measure_rt60()` at dwell = 0.5 within ±10% of `rt60`; at dwell = 8 the *early* EDC slope must be measurably shallower (loop compression) then converge — assert EDC slope ratio early/late > 1.15.
5. **Tube signature:** THD of stage chain on 500 Hz sine: predominantly 2nd harmonic at low dwell (asymmetry), 3rd rising with dwell; DC offset < 1e-4 after the DC blocker (bias creep must not leak DC into the tank).
6. **Aliasing:** 3 kHz sine at dwell = 8 → no inharmonic components above −60 dB (validates ADAA).
7. **C parity:** Python (per-sample reference mode, not the lfilter fast path) vs C within 1e-5 RMS.

## 8. Implementation order in claudeverb

1. `ChirpCascade` primitive (first-order AP chain with block and per-sample modes) + unit test against the τ(ω) formula (group-delay measurement via cross-correlation of sine bursts).
2. LF core (cascade + modulated loop + LP/DC) linear first (`loop_drive → 0` limit); verify §7.1–3.
3. Tube chain stages with ADAA + bead filters; verify §7.4–6.
4. HF branch, multi-spring detune, stereo decorrelation (A24a coefficient-order swap or short APs).
5. C export; per-sample Python reference mode for parity tests.
6. Phase 3 (optional): swap the core for the A21 modal spring driven through the identical tube chain; use A22 FDTD renders as calibration targets.

## 9. Sources

- Core model: A19 (Välimäki/Abel/Smith JAES 2009 spectral delay filters; Välimäki/Parker/Abel JAES 2010 parametric spring; Gamper/Parker/Välimäki DAFx-11 calibration; Parker EURASIP 2011 multirate)
- Physics: `fable_deepresearch_spring.md` foundation (Parker & Bilbao DAFx-09; McQuillan et al. JAES 2025 bead coupling)
- Tube chain: A23 (Fender 6G15 circuit; practitioner evidence: BYOD loop-tanh, Arturia 636 grit stage; Martínez Ramírez ICASSP 2020)
- Structural reference: A24(a) hexefx_audiolib_F32 (MIT-style) — stretched-AP groups K={3,5,6,7}, stereo by coefficient-order reversal
- Chirp-rate modulation: A43(c) (Pekonen et al. DAFx-09)
- ADAA: Parker, Zavalishin, Le Bivic, "Reducing the Aliasing of Nonlinear Waveshaping Using Continuous-Time Convolution," DAFx-16
- Upgrade path: A21 (van Walstijn DAFx-20; van Walstijn & McQuillan DAFx-20in21), A22 (Bilbao & Parker IEEE TASLP 2010)
