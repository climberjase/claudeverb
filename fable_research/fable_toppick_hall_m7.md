# Fable Top Pick — Hall: The Bricasti-M7-Style Unmodulated Dense FDN

**Date:** 2026-07-05
**Status:** Recommendation for implementation (hall slot)
**Built from:** A4 (M7 blueprint) · A6 (zrev2 hybrid) · A15 (Zita-Rev1 branch design) · A28/A32 (velvet-noise early engine) · A36 (accurate T60 filters) · A5 (Shape/bloom) · A33 (optional micro-variance) · A37 (VLF as coupled group)
**Companion docs:** `fable_deepresearch_hall_bricasti_lexicon.md`, `fable_deepresearch_velvet_noise.md`, `fable_deepresearch_advanced_fdn.md`, `Fable_research_detail.md`, `fable_summary.md` (#2)

---

## 1. The verdict

For an M7-like hall, implement the **three-engine unmodulated dense FDN** described by the A4 replication blueprint:

1. **Early engine** — filtered velvet-noise FIR (dense, specular, independent level)
2. **Late engine** — 16-line FDN, mutually prime delays 90–260 ms, per-line entry allpass, Hadamard (FWHT) mixing, outputs as **weighted tap-sums off the delay middles**, **no tail modulation**
3. **VLF engine** — a separate small FDN below ~80 Hz with its own (longer) RT and independent mix

This is ranked #2 in `fable_summary.md` and is the explicit *target sound* of the whole research effort. Everything below turns the blueprint into an implementable claudeverb spec.

### Why this wins over the alternatives

| Candidate | Why not the top hall pick |
|---|---|
| A1/A2 Griesinger figure-8 (Progenitor) | The definitive *Lexicon* hall — lush, modulated, colored. Gorgeous, but it is the chamber pick (see `fable_toppick_chamber_figure8.md`); the M7 aesthetic is explicitly *not* modulated. |
| A7 CloudSeed | Great modern hall, but its smoothness relies on per-line chorusing — audible motion on piano/strings; "Bricasti-adjacent" is community folklore, not a verified match. |
| A8 Barr FV-1 ring | Best sound-per-op ever, but its density builds slowly and tops out below M7 standards at long RTs. Ideal *first* implementation, not the flagship. |
| A15 Zita-Rev1 as-is | Correct DNA (in-branch APs, exact 3-band T60, zero modulation) but 8 lines / no early engine / no VLF / no Shape. **We scale it up rather than reject it** — the late engine below is "Zita ×2 + 224-style tap outputs." |

The M7's defining trait — a tail that stays noise-like and colorless at long RTs **without chorusing** — comes from *diffusion order and incommensurate delay distribution*, not modulation (evidence chain in A4: quasi-LTI static IRs get uncannily close; V1 panel has no spin/wander; V2 modulates only the predelay). The design below is therefore quasi-LTI by construction, which also makes it the friendliest of the three picks for claudeverb's C export and unit testing (deterministic IRs).

---

## 2. Architecture

```
                                 ┌────────────────────────────────────────────┐
                                 │              EARLY ENGINE                  │
             ┌──────────────────►│  velvet-noise FIR, ~2500 p/s, 0–120 ms,    │──► early L/R ─┐
             │                   │  segment LP (darkening), L/R decorrelated  │               │
             │                   └────────────────────────────────────────────┘               │
 in L/R ─► DC-cut ─► pre-delay ─► input diffusion: 6 series APs/ch (g=0.6)                    ▼
             │                     + 2 cross-channel APs (g=0.78, xfeed 0.4)          out = dry
             │                                 │                                          + e·early
             │                                 ▼   (Density x-fade: direct vs diffused)   + l·late
             │                   ┌────────────────────────────────────────────┐          + v·vlf
             │                   │              LATE ENGINE                   │               ▲
             │                   │  16 lines, each:                           │               │
             │                   │   in_i ─►(+)─► AP_i (13–32 ms, g=0.6)      │               │
             │                   │            ▲     └─► delay D_i (90–260 ms) │               │
             │                   │            │           ├─ mid taps ──────► │──► late L/R ──┤
             │                   │            │           ▼                   │               │
             │                   │            │      shelves+LP (T60(f))      │               │
             │                   │            └── FWHT16 (Hadamard) ◄─┘       │               │
             │                   │  NO modulation anywhere in the loop        │               │
             │                   └────────────────────────────────────────────┘               │
             │                   ┌────────────────────────────────────────────┐               │
             └── LR4 LP 80 Hz ──►│  VLF ENGINE: 4-line FDN, RT×vlf_mult,      │──► vlf (mono)─┘
                                 │  delays 80–150 ms, output LP 100 Hz        │
                                 └────────────────────────────────────────────┘
```

### 2.1 Late engine — delay set

16 mutually prime lengths, log-spaced across 90–260 ms @ 48 kHz (ratio ≈ 1.073 per step), snapped to primes. Verify primality with `sympy.isprime` at implementation time; regenerate for other sample rates with the same rule (log-space, snap to prime).

```python
LATE_DELAYS_48K = [
    4327, 4639, 4973, 5347, 5737, 6151, 6607, 7103,
    7607, 8167, 8761, 9403, 10099, 10837, 11633, 12487,
]  # samples @ 48 kHz  (90.1 .. 260.1 ms)
```

Rationale (A4/A6): the delay *span* sets the mean free path of a big hall; the log spacing plus primality prevents any two lines sharing periodicity, which is where FDN "metal" comes from. 16 lines is the knee of the quality curve given tap-sum outputs (below); 8 needs modulation to hide flutter, 32 buys little audible improvement (A34's density math).

### 2.2 Per-line entry allpass (Zita branch design, A15)

Each line's input passes through one Schroeder allpass **inside the branch** before the plain delay — this substitutes for modulation by re-densifying the signal on *every* recursion:

```python
ENTRY_AP_DELAYS_48K = [
    977, 1153, 1327, 1523, 641, 743, 829, 919,
    1051, 1229, 1409, 1597, 683, 787, 887, 997,
]  # 13.3–33.3 ms, primes, g = 0.6, sign of g alternates per line (Zita's ±0.6)
```

The AP delay counts toward the branch total `D_i^tot = D_i + D_i^ap` for the decay computation.

### 2.3 Feedback matrix — FWHT16

Unnormalized 16×16 Hadamard applied as a fast Walsh–Hadamard transform (4 butterfly stages, 64 adds, zero multiplies), then scaled by 1/4 (= 1/√16) to make it orthogonal. **The repo already has the C recipe: `docs/FWHT_to_c.md`** — reuse it, extended from 8 to 16.

### 2.4 Decay — exact per-line gains + frequency-dependent T60

Scalar decay per line (exact RT60 law):

```
g_i = 10^(−3 · D_i^tot / (fs · T60))
```

Frequency dependence via Zita's closed-form three-band filter per line (verbatim math in A15), giving independent `rt_low` (below `xover_lo` ≈ 200 Hz) and HF damping (T60 = rt_mid/2 at `f_damp`):

```
g_mid = 0.001^(D/ (fs·T60_mid))
g_lo  = 0.001^(D/(fs·T60_low)) / g_mid − 1          (low-shelf extra gain)
g_hi  = 0.001^(D/(fs·T60_hi))  / g_mid              (target at f_damp)
t = (1 − g_hi²)/(2 g_hi² χ),  w_hi = (√(1+4t) − 1)/(2t),  χ = 1 − cos(2π f_damp/fs)
y: s_lo += w_lo(x − s_lo);  x += g_lo·s_lo;  s_hi += w_hi(x − s_hi);  out = g_mid·s_hi
```

**Upgrade path (A36):** when ±5% octave-band T60 accuracy is wanted (it is audible), replace the per-line one-pole/shelf pair with the two-stage attenuation filter (low-order trend filter + GEQ on the residual; open MATLAB at github.com/KPrawda/Two_stage_filter). Phase 2 work — the Zita filter is good enough to ship phase 1.

### 2.5 Outputs — mid-delay tap-sums (the single most important trick)

Do **not** take outputs from line ends. Each stereo output is a weighted sum of ~10 taps read from the *middles* of the delay lines (the 224/Dattorro trick, A1/A4, scaled up). This is what makes density Gaussian from the first 30 ms without an LFO.

Deterministic tap rule (golden-ratio placement — incommensurate with everything by construction):

```
L taps: lines i ∈ {0,2,4,6,8,10,12,14},  position p_i = frac((i+1)·φ) · D_i,  φ = 0.618033…
R taps: lines i ∈ {1,3,5,7,9,11,13,15},  position p_i = frac((i+2)·φ) · D_i
weights: cycle ±{0.938, 0.438, 0.312, 0.125}  (224 output-mix weights, alternating sign)
normalize each side by 1/√(Σw²)
```

L and R read *disjoint line sets* → decorrelated by construction (free width, mono-safe because all taps are from one diffuse field).

### 2.6 Density / Shape (the M7 "bloom")

M7's Density parameter = rate of density build-up (A4). Implement as an **input-injection crossfade**:

- `density = 1`: input (post input-diffusion) injected equally into all 16 line entries → instant density.
- `density = 0`: input injected into only 4 lines, *and* the wet output is taken only from the tap-sums (which need several recirculations to fill) → slow bloom, non-exponential onset.
- Intermediate: crossfade injection gains `b_i = lerp(mask4_i, 1/√16, density)`.

**Upgrade path (A5):** the Householder-warped serial-allpass "riser" gives Shape as a continuous structural knob (serial-AP behavior ↔ FDN behavior). Fold in when a true 480L-style Shape control is wanted.

### 2.7 Early engine — filtered velvet noise (A28/A32)

Per channel: sparse FIR of velvet-noise pulses, density ~2500 pulses/s over 0–120 ms (≈300 taps), signs random ±1, amplitude envelope `exp(−t/60 ms)`, and **segment lowpassing**: split into 4 × 30 ms segments, each convolved-equivalent by running its taps through progressively darker one-pole LPs (implemented as 4 tap-groups each summed into its own one-pole). R channel = same pulse set with timing re-jittered ±2 ms (the DAFx-24 binaural trick, A30) → decorrelated but spectrally matched.

Cost: ~300 adds + 4 one-poles per channel — multiplication-free except the envelope gains, which can be quantized to ±2^-k shifts in C if needed.

### 2.8 VLF engine (A4 step 4, A37)

- Input branch: 4th-order Linkwitz–Riley lowpass at 80 Hz (two cascaded Butterworth biquads).
- Core: 4-line FDN (Hadamard 4), delays `{3833, 4783, 5827, 7127}` samples @ 48 kHz (80–148 ms), decay `g_i = 10^(−3·D_i/(fs·T60·vlf_mult))`, `vlf_mult` ∈ [1.0, 2.0].
- Output: one-pole LP at 100 Hz (keeps it purely "power and depth", never audible as a separate reverb), summed to both channels (mono is correct below 80 Hz).

This is the cheapest correct realization of "a dedicated engine for early reverberation below 80 Hz … necessary to convey the depth and power of large spaces" (Bricasti, via SOS — A4).

### 2.9 Modulation policy

**None in the tail.** If (and only if) a final listening pass finds residual flutter at RT > 5 s, add ±1–2 samples of heavily slew-limited noise (LPF at 1 Hz) to at most 3 of the 16 delay read positions — below detectability (A4 step 5). The mathematically cleaner alternative is A33's spinning matrix `A(n) = Q₀Rⁿ` with θ ≈ 1e-4 rad/sample — zero pitch modulation, guaranteed lossless — but start static; the M7 evidence says static is already right.

---

## 3. Parameter API (param_specs)

| name | min | max | default | unit | maps to |
|---|---|---|---|---|---|
| `rt60` | 0.4 | 20.0 | 2.8 | s | per-line `g_i` |
| `rt_low_mult` | 0.25 | 2.5 | 1.2 | × | low-shelf extra gain, per line |
| `xover_lo` | 50 | 1000 | 200 | Hz | `w_lo` |
| `f_damp` | 1500 | 16000 | 5500 | Hz | HF one-pole target (T60=rt60/2 at f_damp) |
| `rolloff` | 2000 | 20000 | 14000 | Hz | input one-pole LP |
| `pre_delay` | 0 | 250 | 12 | ms | input delay |
| `density` | 0.0 | 1.0 | 0.85 | — | injection crossfade (§2.6) |
| `early_level` | 0.0 | 1.0 | 0.5 | — | early engine mix |
| `late_level` | 0.0 | 1.0 | 0.8 | — | late engine mix |
| `vlf_mix` | 0.0 | 1.0 | 0.35 | — | VLF engine mix |
| `vlf_mult` | 1.0 | 2.0 | 1.35 | × | VLF RT multiplier |
| `size` | 0.5 | 1.5 | 1.0 | × | scales all late/VLF delays (re-snap to prime) |
| `mix` | 0.0 | 1.0 | 0.3 | — | dry/wet |

---

## 4. Python prototype (claudeverb-compatible)

Reuses `DelayLine`, `AllpassFilter`, `OnePole`, `DCBlocker` from `claudeverb.algorithms.filters` / `dattorro_plate`; subclass of `ReverbAlgorithm`; float32 throughout; fixed allocation in `_initialize()` (C-portable). Condensed to the load-bearing DSP — parameter plumbing (`update_params`, `param_specs`, `to_dot`) follows the `fdn_reverb.py` pattern.

```python
"""M7-style hall: 16-line unmodulated FDN + velvet early + VLF engine."""
import numpy as np
from claudeverb.algorithms.base import ReverbAlgorithm

PHI = 0.6180339887498949

LATE_DELAYS = [4327, 4639, 4973, 5347, 5737, 6151, 6607, 7103,
               7607, 8167, 8761, 9403, 10099, 10837, 11633, 12487]
ENTRY_AP    = [977, 1153, 1327, 1523, 641, 743, 829, 919,
               1051, 1229, 1409, 1597, 683, 787, 887, 997]
INPUT_AP_L  = [853, 613, 431, 307, 227, 149]        # ~3–18 ms input diffusion
INPUT_AP_R  = [859, 601, 439, 311, 223, 151]
VLF_DELAYS  = [3833, 4783, 5827, 7127]
TAP_WEIGHTS = [0.938, -0.438, 0.312, -0.125]


def fwht16(x: np.ndarray) -> np.ndarray:
    """In-place 16-point fast Walsh-Hadamard, scaled orthogonal (1/4)."""
    h = 1
    while h < 16:
        for i in range(0, 16, h * 2):
            for j in range(i, i + h):
                a, b = x[j], x[j + h]
                x[j], x[j + h] = a + b, a - b
        h *= 2
    x *= np.float32(0.25)
    return x


class ZitaBranchFilter:
    """Per-line 3-band T60: low shelf + HF one-pole + mid gain (A15 math)."""
    __slots__ = ("g_mid", "g_lo", "w_lo", "w_hi", "s_lo", "s_hi")

    def __init__(self, d_total: int, fs: int, t60: float,
                 rt_low_mult: float, xover_lo: float, f_damp: float) -> None:
        self.g_mid = 0.001 ** (d_total / (fs * t60))
        self.g_lo = 0.001 ** (d_total / (fs * t60 * rt_low_mult)) / self.g_mid - 1.0
        self.w_lo = 2.0 * np.pi * xover_lo / fs
        g_hi = 0.001 ** (d_total / (fs * t60 * 0.5)) / self.g_mid   # T60/2 @ f_damp
        chi = 1.0 - np.cos(2.0 * np.pi * f_damp / fs)
        t = (1.0 - g_hi * g_hi) / (2.0 * g_hi * g_hi * chi)
        self.w_hi = (np.sqrt(1.0 + 4.0 * t) - 1.0) / (2.0 * t)
        self.s_lo = np.float32(0.0)
        self.s_hi = np.float32(0.0)

    def process(self, x: float) -> float:
        self.s_lo += self.w_lo * (x - self.s_lo)
        x += self.g_lo * self.s_lo
        self.s_hi += self.w_hi * (x - self.s_hi)
        return self.g_mid * self.s_hi


class M7Hall(ReverbAlgorithm):
    def __init__(self, sample_rate: int = 48000, **params) -> None:
        self.fs = sample_rate
        self.p = {**{"rt60": 2.8, "rt_low_mult": 1.2, "xover_lo": 200.0,
                     "f_damp": 5500.0, "density": 0.85, "early_level": 0.5,
                     "late_level": 0.8, "vlf_mix": 0.35, "vlf_mult": 1.35,
                     "mix": 0.3, "pre_delay": 12.0}, **params}
        self._initialize()

    def _initialize(self) -> None:
        p = self.p
        # --- late engine ---
        self.lines = [np.zeros(d, dtype=np.float32) for d in LATE_DELAYS]
        self.wr = [0] * 16
        self.ap_buf = [np.zeros(d, dtype=np.float32) for d in ENTRY_AP]
        self.ap_wr = [0] * 16
        self.ap_g = np.float32(0.6)
        self.branch_filt = [
            ZitaBranchFilter(LATE_DELAYS[i] + ENTRY_AP[i], self.fs, p["rt60"],
                             p["rt_low_mult"], p["xover_lo"], p["f_damp"])
            for i in range(16)]
        # injection gains: density crossfade (4 lines <-> all 16)
        mask4 = np.array([1.0 if i % 4 == 0 else 0.0 for i in range(16)],
                         dtype=np.float32) * 0.5
        full = np.full(16, 0.25, dtype=np.float32)
        self.inj = mask4 + (full - mask4) * np.float32(p["density"])
        # output taps: golden-ratio positions on disjoint line sets
        self.tapL = [(i, int(((i + 1) * PHI % 1.0) * LATE_DELAYS[i]),
                      TAP_WEIGHTS[(i // 2) % 4]) for i in range(0, 16, 2)]
        self.tapR = [(i, int(((i + 2) * PHI % 1.0) * LATE_DELAYS[i]),
                      TAP_WEIGHTS[(i // 2) % 4]) for i in range(1, 16, 2)]
        norm = 1.0 / np.sqrt(sum(w * w for _, _, w in self.tapL))
        self.tap_norm = np.float32(norm)
        # --- input diffusion (6 APs/ch, g=0.6, signs alternate) ---
        self.in_ap_l = [np.zeros(d, dtype=np.float32) for d in INPUT_AP_L]
        self.in_ap_r = [np.zeros(d, dtype=np.float32) for d in INPUT_AP_R]
        self.in_ap_wr_l = [0] * 6
        self.in_ap_wr_r = [0] * 6
        # --- early engine: velvet FIR (precomputed sparse taps) ---
        rng = np.random.default_rng(7)          # fixed seed = deterministic IR
        n_pulse = int(2500 * 0.120)
        grid = self.fs / 2500.0
        k = np.round(np.arange(n_pulse) * grid
                     + rng.random(n_pulse) * (grid - 1)).astype(int)
        s = (2 * np.round(rng.random(n_pulse)) - 1)
        env = np.exp(-k / (0.060 * self.fs))
        self.velvet_l = list(zip(k.tolist(), (s * env).astype(np.float32)))
        jit = np.clip(k + rng.integers(-96, 96, n_pulse), 0, None)
        self.velvet_r = list(zip(jit.tolist(), (s * env).astype(np.float32)))
        self.early_buf = np.zeros(1 << 13, dtype=np.float32)  # 170 ms ring
        self.early_wr = 0
        # --- VLF engine ---
        self.vlf_lines = [np.zeros(d, dtype=np.float32) for d in VLF_DELAYS]
        self.vlf_wr = [0] * 4
        t60v = p["rt60"] * p["vlf_mult"]
        self.vlf_g = np.array(
            [0.001 ** (d / (self.fs * t60v)) for d in VLF_DELAYS],
            dtype=np.float32)
        # LR4 @ 80 Hz + 100 Hz output one-pole: states
        self.lr4 = np.zeros(4, dtype=np.float32)   # 2 cascaded TDF-II biquads
        self.vlf_lp = np.float32(0.0)

    def _ap(self, buf, wr_list, idx, x, g):
        """One-multiplier Schroeder allpass (Zita form)."""
        i = wr_list[idx]
        z = buf[i]
        x = x - g * z
        buf[i] = x
        wr_list[idx] = (i + 1) % len(buf)
        return z + g * x

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        stereo = audio.ndim == 2
        xl = audio[0] if stereo else audio
        xr = audio[1] if stereo else audio
        n = xl.shape[0]
        out = np.zeros((2, n), dtype=np.float32)
        p = self.p
        wet_l = np.float32(p["late_level"])
        el = np.float32(p["early_level"])
        v = np.float32(p["vlf_mix"])
        mix = np.float32(p["mix"])
        fb = np.zeros(16, dtype=np.float32)
        for t in range(n):
            # input diffusion
            dl, dr = xl[t], xr[t]
            for j in range(6):
                g = self.ap_g if j % 2 == 0 else -self.ap_g
                dl = self._ap(self.in_ap_l[j], self.in_ap_wr_l, j, dl, g)
                dr = self._ap(self.in_ap_r[j], self.in_ap_wr_r, j, dr, g)
            diffused = np.float32(0.5) * (dl + dr)
            # --- late: read line ends -> FWHT -> entry AP -> damp -> write
            for i in range(16):
                fb[i] = self.lines[i][self.wr[i]]        # read = end of line
            fwht16(fb)
            yl = np.float32(0.0)
            yr = np.float32(0.0)
            for i, pos, w in self.tapL:
                yl += w * self.lines[i][(self.wr[i] + pos) % LATE_DELAYS[i]]
            for i, pos, w in self.tapR:
                yr += w * self.lines[i][(self.wr[i] + pos) % LATE_DELAYS[i]]
            yl *= self.tap_norm
            yr *= self.tap_norm
            for i in range(16):
                g = self.ap_g if i % 2 == 0 else -self.ap_g
                s = self._ap(self.ap_buf[i], self.ap_wr, i,
                             fb[i] + self.inj[i] * diffused, g)
                self.lines[i][self.wr[i]] = self.branch_filt[i].process(s)
                self.wr[i] = (self.wr[i] + 1) % LATE_DELAYS[i]
            # --- early: velvet FIR via ring buffer (write mono in, read taps)
            self.early_buf[self.early_wr] = diffused
            e_l = np.float32(0.0)
            e_r = np.float32(0.0)
            m = len(self.early_buf)
            for k, w in self.velvet_l:
                e_l += w * self.early_buf[(self.early_wr - k) % m]
            for k, w in self.velvet_r:
                e_r += w * self.early_buf[(self.early_wr - k) % m]
            self.early_wr = (self.early_wr + 1) % m
            # --- VLF: LR4 split -> 4-line Hadamard FDN -> 100 Hz LP
            lo = self._lr4_80(diffused)
            a = [self.vlf_lines[i][self.vlf_wr[i]] for i in range(4)]
            h0, h1 = a[0] + a[1], a[0] - a[1]
            h2, h3 = a[2] + a[3], a[2] - a[3]
            mixv = [(h0 + h2), (h1 + h3), (h0 - h2), (h1 - h3)]
            vlf_out = np.float32(0.0)
            for i in range(4):
                self.vlf_lines[i][self.vlf_wr[i]] = (
                    self.vlf_g[i] * np.float32(0.5) * mixv[i] + lo)
                self.vlf_wr[i] = (self.vlf_wr[i] + 1) % VLF_DELAYS[i]
                vlf_out += a[i]
            self.vlf_lp += np.float32(0.0131) * (vlf_out - self.vlf_lp)  # ~100 Hz
            # --- sum
            wl = wet_l * yl + el * e_l + v * self.vlf_lp
            wr_ = wet_l * yr + el * e_r + v * self.vlf_lp
            out[0, t] = (1 - mix) * xl[t] + mix * wl
            out[1, t] = (1 - mix) * xr[t] + mix * wr_
        return out if stereo else out.mean(axis=0)
```

(`_lr4_80` = two cascaded 2nd-order Butterworth LP biquads at 80 Hz using the repo's biquad; `reset`, `update_params`, `param_specs` follow `fdn_reverb.py`. The velvet FIR inner loop is the slow part in pure Python — vectorize with `np.add.at` over block boundaries, or accept it; the C version is trivially fast.)

---

## 5. C translation

State struct and process function in the shape `c_export.py` expects from `to_c_struct()` / `to_c_process_fn()`. Static allocation only; all delay lengths are compile-time constants at 48 kHz.

```c
#define M7_NLINES 16
#define M7_NVEL   300           /* velvet pulses per channel */
#define M7_EARLY_LEN 8192

typedef struct {
    /* late engine */
    float line_buf[M7_NLINES][12487];   /* sized to max; index with line_len */
    int   line_len[M7_NLINES];
    int   line_wr[M7_NLINES];
    float ap_buf[M7_NLINES][1597];
    int   ap_len[M7_NLINES];
    int   ap_wr[M7_NLINES];
    float ap_g;                          /* 0.6, sign applied per line parity */
    /* per-line 3-band T60 filter */
    float g_mid[M7_NLINES], g_lo[M7_NLINES];
    float w_lo, w_hi[M7_NLINES];
    float s_lo[M7_NLINES], s_hi[M7_NLINES];
    /* injection + taps */
    float inj[M7_NLINES];
    int   tap_line_l[8], tap_pos_l[8];
    int   tap_line_r[8], tap_pos_r[8];
    float tap_w[8], tap_norm;
    /* input diffusion */
    float in_ap_buf[2][6][859];
    int   in_ap_len[2][6], in_ap_wr[2][6];
    /* early engine (sparse velvet FIR) */
    float early_buf[M7_EARLY_LEN];
    int   early_wr;
    int   vel_k[2][M7_NVEL];
    float vel_w[2][M7_NVEL];
    /* VLF engine */
    float vlf_buf[4][7127];
    int   vlf_len[4], vlf_wr[4];
    float vlf_g[4];
    float lr4_state[8];                 /* 2 biquads x 4 states */
    float lr4_coef[10];                 /* 2 x (b0 b1 b2 a1 a2) */
    float vlf_lp_state, vlf_lp_coef;
    /* mix */
    float early_level, late_level, vlf_mix, mix;
    int   sample_rate;
} M7HallState;

static inline float m7_allpass(float *buf, int len, int *wr, float x, float g)
{
    float z = buf[*wr];
    x -= g * z;
    buf[*wr] = x;
    if (++*wr >= len) *wr = 0;
    return z + g * x;
}

static inline void m7_fwht16(float *x)  /* see docs/FWHT_to_c.md */
{
    for (int h = 1; h < 16; h <<= 1)
        for (int i = 0; i < 16; i += h << 1)
            for (int j = i; j < i + h; j++) {
                float a = x[j], b = x[j + h];
                x[j] = a + b;  x[j + h] = a - b;
            }
    for (int j = 0; j < 16; j++) x[j] *= 0.25f;
}

void m7_hall_process(M7HallState *s, const float *in_l, const float *in_r,
                     float *out_l, float *out_r, int n)
{
    for (int t = 0; t < n; t++) {
        /* ---- input diffusion ---- */
        float dl = in_l[t], dr = in_r[t];
        for (int j = 0; j < 6; j++) {
            float g = (j & 1) ? -s->ap_g : s->ap_g;
            dl = m7_allpass(s->in_ap_buf[0][j], s->in_ap_len[0][j],
                            &s->in_ap_wr[0][j], dl, g);
            dr = m7_allpass(s->in_ap_buf[1][j], s->in_ap_len[1][j],
                            &s->in_ap_wr[1][j], dr, g);
        }
        float diffused = 0.5f * (dl + dr);

        /* ---- late engine ---- */
        float fb[M7_NLINES];
        for (int i = 0; i < M7_NLINES; i++)
            fb[i] = s->line_buf[i][s->line_wr[i]];
        m7_fwht16(fb);

        float yl = 0.f, yr = 0.f;
        for (int k = 0; k < 8; k++) {
            int il = s->tap_line_l[k], ir = s->tap_line_r[k];
            int pl = s->line_wr[il] + s->tap_pos_l[k];
            int pr = s->line_wr[ir] + s->tap_pos_r[k];
            if (pl >= s->line_len[il]) pl -= s->line_len[il];
            if (pr >= s->line_len[ir]) pr -= s->line_len[ir];
            yl += s->tap_w[k] * s->line_buf[il][pl];
            yr += s->tap_w[k] * s->line_buf[ir][pr];
        }
        yl *= s->tap_norm;  yr *= s->tap_norm;

        for (int i = 0; i < M7_NLINES; i++) {
            float g = (i & 1) ? -s->ap_g : s->ap_g;
            float v = m7_allpass(s->ap_buf[i], s->ap_len[i], &s->ap_wr[i],
                                 fb[i] + s->inj[i] * diffused, g);
            /* 3-band T60 filter */
            s->s_lo[i] += s->w_lo * (v - s->s_lo[i]);
            v += s->g_lo[i] * s->s_lo[i];
            s->s_hi[i] += s->w_hi[i] * (v - s->s_hi[i]);
            v = s->g_mid[i] * s->s_hi[i];
            s->line_buf[i][s->line_wr[i]] = v;
            if (++s->line_wr[i] >= s->line_len[i]) s->line_wr[i] = 0;
        }

        /* ---- early engine: sparse velvet FIR ---- */
        s->early_buf[s->early_wr] = diffused;
        float el = 0.f, er = 0.f;
        for (int m = 0; m < M7_NVEL; m++) {
            int kl = s->early_wr - s->vel_k[0][m];
            int kr = s->early_wr - s->vel_k[1][m];
            el += s->vel_w[0][m] * s->early_buf[kl & (M7_EARLY_LEN - 1)];
            er += s->vel_w[1][m] * s->early_buf[kr & (M7_EARLY_LEN - 1)];
        }
        if (++s->early_wr >= M7_EARLY_LEN) s->early_wr = 0;

        /* ---- VLF engine ---- */
        float lo = diffused;
        for (int b = 0; b < 2; b++) {           /* LR4 = 2 biquads, TDF-II */
            float *c = &s->lr4_coef[b * 5], *z = &s->lr4_state[b * 4];
            float y = c[0] * lo + z[0];
            z[0] = c[1] * lo - c[3] * y + z[1];
            z[1] = c[2] * lo - c[4] * y;
            lo = y;
        }
        float a0 = s->vlf_buf[0][s->vlf_wr[0]], a1 = s->vlf_buf[1][s->vlf_wr[1]];
        float a2 = s->vlf_buf[2][s->vlf_wr[2]], a3 = s->vlf_buf[3][s->vlf_wr[3]];
        float h0 = a0 + a1, h1 = a0 - a1, h2 = a2 + a3, h3 = a2 - a3;
        float mv[4] = { h0 + h2, h1 + h3, h0 - h2, h1 - h3 };
        float vlf = a0 + a1 + a2 + a3;
        for (int i = 0; i < 4; i++) {
            s->vlf_buf[i][s->vlf_wr[i]] = s->vlf_g[i] * 0.5f * mv[i] + lo;
            if (++s->vlf_wr[i] >= s->vlf_len[i]) s->vlf_wr[i] = 0;
        }
        s->vlf_lp_state += s->vlf_lp_coef * (vlf - s->vlf_lp_state);

        /* ---- output ---- */
        float wl = s->late_level * yl + s->early_level * el
                 + s->vlf_mix * s->vlf_lp_state;
        float wr = s->late_level * yr + s->early_level * er
                 + s->vlf_mix * s->vlf_lp_state;
        out_l[t] = (1.f - s->mix) * in_l[t] + s->mix * wl;
        out_r[t] = (1.f - s->mix) * in_r[t] + s->mix * wr;
    }
}
```

RAM estimate: 16 late lines (Σ≈124k) + 16 entry APs (Σ≈17k) + VLF (Σ≈21.6k) + early ring (8k) ≈ **175k floats ≈ 700 KB** — fine on desktop; for Hothouse/Daisy (64 MB SDRAM) place `line_buf` in SDRAM. Per-sample cost ≈ 16 APs + 64 adds (FWHT) + 16 lines + ~600 velvet adds + small — ~1.5k ops/sample, comfortably real-time in C.

---

## 6. Verification plan (the M7 acceptance test)

From A4, extended with the repo's existing metrics:

1. **RT accuracy** — `measure_rt60()` on the wet IR within ±5% of `rt60`; `measure_rt60_bands()` confirms `rt_low_mult` and the T60/2 @ `f_damp` law per octave band.
2. **NED profile** — add `normalized_echo_density()` to `claudeverb/analysis/metrics.py` (Abel & Huang 2006): sliding 25 ms Hann window, `NED(t) = (1/erfc(1/√2)) · Σ w[k]·1{|h[t+k]| > σ_w(t)}`. Acceptance: NED reaches ≈1 within 30–80 ms and **plateaus** (the M7 signature — density stops increasing).

```python
from scipy.special import erfc
def normalized_echo_density(ir, fs, win_ms=25.0, hop_ms=5.0):
    w = np.hanning(int(win_ms * 1e-3 * fs)); w /= w.sum()
    hop = int(hop_ms * 1e-3 * fs); c = 1.0 / erfc(1.0 / np.sqrt(2.0))
    out = []
    for i in range(0, len(ir) - len(w), hop):
        seg = ir[i:i + len(w)]
        sigma = np.sqrt(np.sum(w * seg * seg))
        out.append(c * np.sum(w * (np.abs(seg) > sigma)))
    return np.asarray(out)
```

3. **No comb ridges** — 4096-pt spectrogram of the 1–3 s tail region shows no stable horizontal ridges (compare against `plot_mel_comparison`).
4. **EDC linearity** — Schroeder integral is a straight line in dB (single slope), except when `density < 0.5`, where a fade-in bloom must appear.
5. **Determinism** — fixed velvet seed ⇒ bit-identical IRs across runs (unit-testable; a genuine advantage of the no-modulation design).
6. **C parity** — Python vs exported C output within 1e-6 RMS on a 1 s noise burst (existing `test_c_portability.py` pattern).

---

## 7. Implementation order in claudeverb

1. `M7Late` (16-line core + Zita branch filters + tap-sum outputs) — reuses `DelayLine`/`AllpassFilter`; extend `docs/FWHT_to_c.md` to 16.
2. NED metric in `analysis/metrics.py` (needed to tune the delay/tap sets).
3. `VelvetEarly` (sparse FIR, seeded) + `VLFEngine` (LR4 + FDN4).
4. `M7Hall` wrapper: three engines + density crossfade + param_specs + `to_dot()`.
5. C export (`to_c_struct`/`to_c_process_fn`), Hothouse template.
6. Phase 2: A36 two-stage T60 filters; A5 Shape riser; A33 matrix spin (only if flutter is audible at RT > 5 s).

## 8. Sources

- Bricasti provenance, engine split, modulation evidence: A4 in `Fable_research_detail.md` (SOS review, KVR threads, Samplicity notes, M7 manual + V2 addendum, LiquidSonics Fusion-IR rationale)
- Zita branch/filter math: A15 (Adriaensen `reverb.cpp`, JOS PASP chapter)
- zrev2 scaling recipe: A6 (Freeverb3)
- Velvet noise: A28/A30/A32 (Karjalainen & Järveläinen 2007; Välimäki et al. 2017/2021; Alary et al. DAFx-17)
- T60 filter accuracy: A36 (Prawda et al. DAFx-19; Välimäki et al. IEEE SPL 2024)
- NED: Abel & Huang, "A simple, robust measure of reverberation echo density," AES 121st Conv., 2006
