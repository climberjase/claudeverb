# Fable Top Pick — Chamber: The Griesinger Figure-8 Loop, Chamber-Tuned

**Date:** 2026-07-05
**Status:** Recommendation for implementation (chamber slot)
**Built from:** A1 (Griesinger figure-8 / Progenitor) · A2 (Progenitor2 input diffusion + noise-dithered modulation) · A3 (spin/wander semantics) · A44 (optional converter-in-loop texture)
**Companion docs:** `fable_deepresearch_hall_bricasti_lexicon.md`, `Fable_research_detail.md`, `fable_summary.md` (#1, #6)

---

## 1. The verdict

For the chamber slot, implement the **Griesinger figure-8 cross-coupled loop** (Lexicon 224 lineage, fully documented in A1 via Freeverb3's Progenitor), augmented with **Progenitor2's input-diffusion chain and noise-dithered modulation** (A2), and *tuned small*: shorter ring, darker loop damping, higher onset density, moderate RT. This is the #1-ranked approach in `fable_summary.md` and the only topology in the research corpus where **every constant of a legendary-sounding unit is public**.

### Why this is the "known to sound incredible" chamber

The brief asks for something in the class of **LiquidSonics Cinematic Rooms (Amethyst Hall)** and the **Meris Mercury7**. Neither publishes an algorithm — Cinematic Rooms is Fusion-IR convolution of captured hardware (largely Bricasti-class sources, A4), and Mercury7 is Meris's DSP homage to the Bricasti M7's aesthetic. What both *sound* like, reduced to reproducible properties:

1. **Instantly dense, non-grainy onset** — no discrete early slaps; the reverb "inflates" around the source.
2. **A wide, enveloping, cross-coupled stereo field** — L and R tails are decorrelated but belong to one space.
3. **A tail that is alive without audible chorusing** — slow spectral motion, zero pitch instability.
4. **Longer low-frequency decay than mid** — the "bloom" that reads as expensive.

Each of these is a *structural feature* of the figure-8 loop, verified in A1/A2:

| Target property | Figure-8 mechanism (A1/A2) |
|---|---|
| Dense onset | 6–10 series modulated input APs per channel + output taken as sparse multi-tap mixes off the **middles** of the loop delays — early energy without an ER engine |
| Enveloping width | The loop itself is stereo-cross-coupled: each channel's input sums the *other* channel's tail (`crossL`/`crossR`) |
| Alive, pitch-stable tail | Alternating-sign, slew-limited (20 Hz LPF) LFO on the loop APs — detunes cancel to first order; plus the output **gain-modulated** feed-forward comb (spin2): ±2 dB spectral ripple sweep with literally zero pitch modulation; plus A2's noise dithering of AP delay *and* coefficient |
| LF bloom | The 500 Hz × 0.1 lowpassed cross-feed adds loop gain only below ~500 Hz → bass RT runs ~1.3–1.6× mid RT for free |

This is also why the figure-8, not the M7-style FDN (the hall pick), is right for *chamber*: chambers are heard close-up, where onset density and modulation character dominate; the Lexicon school is precisely the "recirculating diffusion + tasteful motion" aesthetic, and at chamber sizes its one weakness (slightly colored long tails) never shows because RT stays under ~2.5 s.

### Alternatives considered

| Candidate | Why not |
|---|---|
| A8 Barr FV-1 ring | Superb and far cheaper, but "somewhat less initial echo density than the various Lexicon algorithms" (Costello, A8) — onset density is *the* chamber requirement. Keep as the budget/embedded chamber. |
| A12 JPverb | Enormous instant density, MIT-licensed, but its character is overt "lush chorus" — Alesis/Lexicon *effect*, not a credible room. Right tool for ambient patches, not the chamber slot. |
| A16 Airwindows Galactic/Chamber | Distinctive but pad-oriented; slow bloom contradicts chamber timing. |
| Scaling down the M7 hall pick | Works, but yields a *small hall*, not a chamber: the unmodulated FDN aesthetic reads as "air", not "walls". Having the two picks embody the two great schools (Bricasti-static vs Lexicon-motion) doubles the palette for the same effort. |

**License note (important):** Freeverb3's Progenitor/Progenitor2 are GPL-2.0+, and the headers assert Griesinger's 1977–78 design copyright. **Reimplement from the topology and constants documented here and in A1/A2 — do not port or paste Freeverb3 code** into this repo.

---

## 2. Architecture

One stereo figure-8: two half-loops (L and R chains) cross-feeding each other's tails. Delay values below are **native fs = 34,125 Hz** (as recovered in A1) with **48 kHz conversions** (×48000/34125 = ×1.40659, rounded; the topology does not require primality — incommensurability comes from the structure).

```
      L INPUT                                             R INPUT
        │ DC-cut 5 Hz → 1-pole LP `rolloff`                 │ (same)
        │ [chamber add, A2] 6 series mod-APs (dither)       │ (same, R table)
        ▼                                                   ▼
   (+)◄─ decay0·[ crossR + bass·LP500(crossR) ]        (+)◄─ decay0·[ crossL + bass·LP500(crossL) ]
    │       crossR = tail of R half-loop                 │      crossL = tail of L half-loop
    ▼                                                    ▼
  1-pole LP `damp` (9 kHz hall / 7 kHz chamber)        1-pole LP `damp`
    ▼                                                    ▼
  modAP 239/336₄₈ (±exc, g=.375, leak d2)             modAP 205/288₄₈ (±exc, g=.375, leak d2)
    ▼                                                    ▼
  delay 2/3₄₈                                          delay 1/1₄₈
    ▼                                                    ▼
  modAP 392/551₄₈ (±exc, g=.312, leak d3)             modAP 329/463₄₈ (±exc, g=.312, leak d3)
    ▼                                                    ▼
  delay 1055/1484₄₈   (loop delay "23")               delay 1460/2054₄₈   ("40")
    ▼                                                    ▼
  nestAP2 {1944/2734₄₈, in 612/861₄₈}                 nestAP2 {2032/2858₄₈, in 368/518₄₈}
    g_out=.406 (leak d3), g_in=.25 (leak d1)             (same coefficients)
    ▼                                                    ▼
  delay 344/484₄₈     ("31")                          delay 500/703₄₈     ("49")
    ▼                                                    ▼
  nestAP3 {1212/1705₄₈ (mod ±121/170₄₈),              nestAP3 {1452/2042₄₈ (mod ±5/7₄₈),
           816/1148₄₈, 1264/1778₄₈}                            688/968₄₈, 1340/1885₄₈}
    g1=g2=.25, g3=.406, leaks d1/d1/d2                   (same coefficients)
    ▼                                                    ▼
  delay 1572/2211₄₈   ("37") ──── crossL ──►(R input) delay 16/23₄₈ ("58") ── crossR ──►(L input)
```

All ring delays (and the nested-AP lengths) are additionally scaled by `size` (chamber default 0.65 — see §3); modulation excursions scale with them.

### 2.1 Output taps (the 224 quad mix, stereo pair)

Wet outputs are sparse tap-sums off the loop-delay interiors (native-fs offsets; scale by 1.40659·size for 48 kHz):

```
outL (224 "D") = del23[1]·0.938 + del31[40]·0.438 − del49R[192]·0.438 + del37[1572·size]·0.125
outR (224 "B") = del40R[625]·0.938 + del49R[468]·0.438 − del31[312]·0.438 + del58R[8]·0.125
```

then each output goes through the **spin2 gain-modulated feed-forward comb** (22 ms, gain = ±LPF₁₂Hz(sin 2π·2.4t)·0.3, anti-phase L/R) and a one-pole output LP (10 kHz). Any tap offset that exceeds its scaled delay length wraps modulo that length.

### 2.2 Decay distribution — the anti-stair-step trick

Loss is spread across the loop instead of applied at one point (A1 `resetdecay()`), which is why the EDC is smooth. Normalized attenuations for RT60 = 1 s, each exponentiated by 1/RT60:

```
g_k(RT60) = 10^( log10(k) / RT60 ),   with
k = { decay0: 0.237 (main cross-feed gain),
      decay1: 0.938 (leak, inner nested APs),
      decay2: 0.844 (leak, mod-APs & nestAP3 stage 3),
      decay3: 0.906 (leak, mod-AP2 & nestAP2 outer) }
```

A "leak" means the allpass's stored (recirculating) sample is multiplied by g before reuse — each diffuser is *slightly absorbent* (the A14 Dahl/Jot idea, avant la lettre). At RT60 = 1.2 s (chamber default): decay0 = 0.301, decay1 = 0.948, decay2 = 0.868, decay3 = 0.921.

Since `size` shortens the loop, effective RT at fixed gains shrinks with size; compensate by computing gains from `RT60_eff = rt60 / size` so the user-facing `rt60` stays truthful.

### 2.3 Modulation spec (exactly two systems + dither)

1. **Loop modulation** ("spin/wander", A1/A3): one sine LFO, default 0.5 Hz, through a 1-pole LP at 20 Hz (slew limiter), scaled to max excursion ±32 samples native (±45 @ 48 kHz) × `wander`; applied with **alternating polarity** to the four mod-APs and the two nestAP3 first stages (L gets +, R gets − of the same LFO).
2. **Output chorus** ("spin2"): feed-forward comb per channel, delay 22 ms, whose **gain** (not delay) is modulated: `g(t) = ±LPF₁₂Hz(sin 2π·2.4·t) · 0.3`, anti-phase L/R. Spectral motion, zero pitch motion.
3. **Noise dither** (A2, chamber-critical for the "alive" tail): per input-AP stage i, `lfo_i = slew(lfo + 0.09·noise) · wander`, sign `(−1)^i`, plus `0.06·noise` added to the **allpass coefficient** itself. Noise = pink-ish (white through one-pole LP at ~2 Hz works).

### 2.4 Chamber additions over stock A1

- **Input diffusion:** 6 series modulated APs per channel (subset of Progenitor2's 10), native lengths L {617, 434, 218, 144, 109, 74} → 48 kHz {868, 610, 307, 203, 153, 104}; R {603, 416, 236, 140, 111, 79} → {848, 585, 332, 197, 156, 111}; g = −0.78, excursion ±10 native (±14 @ 48 kHz), noise-dithered per §2.3.3.
- **Optional texture** (A44): 14-bit mantissa gain-ranged quantization at the two main loop-delay writes — the EMT-250-style "breathing" noise floor. Off by default; expose as `vintage` (0/1).

---

## 3. Parameter API (param_specs)

| name | min | max | default | unit | maps to |
|---|---|---|---|---|---|
| `rt60` | 0.3 | 5.0 | 1.2 | s | decay0..3 via §2.2 (with size compensation) |
| `size` | 0.45 | 1.25 | 0.65 | × | all ring/nested delays & tap offsets (0.65 ≈ chamber, 1.0 = 224 hall) |
| `damp` | 3000 | 16000 | 7000 | Hz | loop 1-pole LP |
| `rolloff` | 4000 | 20000 | 16000 | Hz | input 1-pole LP |
| `bass_mult` | 0.0 | 0.25 | 0.10 | — | LP500 cross-feed gain (`bass`); 0.10 ≈ bass RT ×1.4 |
| `bass_xover` | 150 | 800 | 400 | Hz | cross-feed LP corner (chamber: 400 vs hall 500) |
| `spin` | 0.05 | 3.0 | 0.6 | Hz | loop LFO rate |
| `wander` | 0.0 | 1.0 | 0.55 | — | loop LFO excursion scale (±45 smp max @ 48 kHz) |
| `spin2` | 0.5 | 6.0 | 2.4 | Hz | output comb gain-LFO rate |
| `wander2` | 0.0 | 0.6 | 0.3 | — | output comb max gain |
| `dither` | 0.0 | 1.0 | 0.7 | — | scales A2 noise depths (0.09/0.06) |
| `pre_delay` | 0 | 120 | 8 | ms | input delay |
| `vintage` | 0 | 1 | 0 | — | A44 gain-ranged quantizer in loop |
| `mix` | 0.0 | 1.0 | 0.3 | — | dry/wet |

Chamber presets: **Vocal Chamber** (rt60 1.0, size 0.55, damp 6.5k, wander 0.45) · **Stone Chamber** (rt60 1.8, size 0.75, damp 8k, bass_mult 0.14) · **224 Hall** (rt60 2.6, size 1.0, damp 9k, bass_xover 500 — sanity check against the A1 reference).

---

## 4. Python prototype (claudeverb-compatible)

Reuses `DelayLine` (fractional reads) and `OnePole`/`DCBlocker`; float32; fixed allocation. Two new primitives are introduced — the **leaky modulated allpass** and the **leaky nested allpass** — worth adding to `filters.py` since the spring pick reuses the first. Condensed: one channel chain shown symmetric; `update_params`/`param_specs`/`to_dot` follow repo patterns.

```python
"""Chamber: Griesinger figure-8 loop (224 lineage), chamber-tuned.

Reimplemented from the published topology/constants (A1/A2) — no GPL code.
"""
import math
import numpy as np
from claudeverb.algorithms.base import ReverbAlgorithm

FS_NATIVE = 34125.0

class LeakyModAllpass:
    """Schroeder allpass with LFO-modulated read tap and leaky recirculation.

    y = -g*x + (1+ leak terms) ... implemented in the fv3-documented form:
        z = buf[read(d + m)]        (linear interp)
        y = z - g*x_in              (feedforward)
        buf[wr] = x_in + g*z*leak   (leak = distributed decay)
    """
    __slots__ = ("buf", "wr", "d", "g", "leak", "exc")

    def __init__(self, d: int, exc: int, g: float) -> None:
        self.buf = np.zeros(d + 2 * exc + 4, dtype=np.float32)
        self.wr = 0
        self.d = d
        self.exc = exc
        self.g = np.float32(g)
        self.leak = np.float32(1.0)

    def process(self, x: float, mod: float, gjit: float = 0.0) -> float:
        n = len(self.buf)
        rp = (self.wr - (self.d + mod * self.exc)) % n
        i0 = int(rp)
        fr = np.float32(rp - i0)
        z = self.buf[i0] * (1 - fr) + self.buf[(i0 + 1) % n] * fr
        g = self.g + np.float32(gjit)
        y = z - g * x
        self.buf[self.wr] = x + g * z * self.leak
        self.wr = (self.wr + 1) % n
        return y


class LeakyNestedAllpass:
    """Outer allpass whose internal delay contains inner allpasses (A1)."""
    def __init__(self, d_out, g_out, inners, exc_out=0):
        self.outer = LeakyModAllpass(d_out, exc_out, g_out)
        self.inners = inners            # list of LeakyModAllpass (exc=0)

    def process(self, x: float, mod: float = 0.0) -> float:
        # signal entering the outer recirculation path passes the inners
        n = len(self.outer.buf)
        rp = (self.outer.wr - (self.outer.d + mod * self.outer.exc)) % n
        i0 = int(rp); fr = np.float32(rp - i0)
        z = self.outer.buf[i0] * (1 - fr) + self.outer.buf[(i0 + 1) % n] * fr
        for ap in self.inners:
            z = ap.process(z, 0.0)
        g = self.outer.g
        y = z - g * x
        self.outer.buf[self.outer.wr] = x + g * z * self.outer.leak
        self.outer.wr = (self.outer.wr + 1) % n
        return y


def _scale(v: float, fs: int, size: float) -> int:
    return max(1, int(round(v * fs / FS_NATIVE * size)))


class ChamberFigure8(ReverbAlgorithm):
    # native-fs constant tables (A1/A2)
    IN_AP = {"L": [617, 434, 218, 144, 109, 74],
             "R": [603, 416, 236, 140, 111, 79]}
    CHAIN = {  # per channel: modAPs, plain delays, nested defs
        "L": dict(map1=(239, .375), d1=2, map2=(392, .312), d_main=1055,
                  n2=(1944, .406, [(612, .25)]), d_mid=344,
                  n3=(1212, 121, [(816, .25), (1264, .406)]), d_tail=1572),
        "R": dict(map1=(205, .375), d1=1, map2=(329, .312), d_main=1460,
                  n2=(2032, .406, [(368, .25)]), d_mid=500,
                  n3=(1452, 5, [(688, .25), (1340, .406)]), d_tail=16),
    }
    TAPS = {"L": [("d_main", "L", 1, .938), ("d_mid", "L", 40, .438),
                  ("d_mid", "R", 192, -.438), ("d_tail", "L", 1572, .125)],
            "R": [("d_main", "R", 625, .938), ("d_mid", "R", 468, .438),
                  ("d_mid", "L", 312, -.438), ("d_tail", "R", 8, .125)]}

    def __init__(self, sample_rate: int = 48000, **params) -> None:
        self.fs = sample_rate
        self.p = {**{"rt60": 1.2, "size": 0.65, "damp": 7000.0,
                     "rolloff": 16000.0, "bass_mult": 0.10, "bass_xover": 400.0,
                     "spin": 0.6, "wander": 0.55, "spin2": 2.4, "wander2": 0.3,
                     "dither": 0.7, "mix": 0.3}, **params}
        self._initialize()

    def _initialize(self) -> None:
        p, fs, sz = self.p, self.fs, self.p["size"]
        S = lambda v: _scale(v, fs, sz)
        exc = _scale(32, fs, sz)                     # loop mod excursion
        rt_eff = p["rt60"] / sz
        self.g = {k: np.float32(10.0 ** (math.log10(v) / rt_eff))
                  for k, v in {"d0": .237, "d1": .938,
                               "d2": .844, "d3": .906}.items()}
        self.ch = {}
        for c in ("L", "R"):
            cf = self.CHAIN[c]
            m1 = LeakyModAllpass(S(cf["map1"][0]), exc, cf["map1"][1]); m1.leak = self.g["d2"]
            m2 = LeakyModAllpass(S(cf["map2"][0]), exc, cf["map2"][1]); m2.leak = self.g["d3"]
            n2i = [LeakyModAllpass(S(d), 0, g) for d, g in cf["n2"][2]]
            for ap in n2i: ap.leak = self.g["d1"]
            n2 = LeakyNestedAllpass(S(cf["n2"][0]), cf["n2"][1], n2i)
            n2.outer.leak = self.g["d3"]
            n3i = [LeakyModAllpass(S(d), 0, g) for d, g in cf["n3"][2]]
            n3i[0].leak = self.g["d1"]; n3i[1].leak = self.g["d2"]
            n3 = LeakyNestedAllpass(S(cf["n3"][0]), .25, n3i, exc_out=S(cf["n3"][1]))
            n3.outer.leak = self.g["d1"]
            in_aps = [LeakyModAllpass(S(d), S(10), -0.78) for d in self.IN_AP[c]]
            self.ch[c] = dict(
                m1=m1, m2=m2, n2=n2, n3=n3, in_aps=in_aps,
                d1=np.zeros(S(cf["d1"]), np.float32),
                d_main=np.zeros(S(cf["d_main"]), np.float32),
                d_mid=np.zeros(S(cf["d_mid"]), np.float32),
                d_tail=np.zeros(S(cf["d_tail"]), np.float32),
                wr=dict(d1=0, d_main=0, d_mid=0, d_tail=0),
                damp_s=np.float32(0), bass_s=np.float32(0), out_lp=np.float32(0))
        self.damp_c = np.float32(1 - math.exp(-2 * math.pi * p["damp"] / fs))
        self.bass_c = np.float32(1 - math.exp(-2 * math.pi * p["bass_xover"] / fs))
        # LFOs + slew limiters + dither noise state
        self.ph1 = 0.0
        self.ph2 = 0.0
        self.lfo1_lp = np.float32(0)
        self.lfo2_lp = np.float32(0)
        self.slew1 = np.float32(1 - math.exp(-2 * math.pi * 20.0 / fs))
        self.slew2 = np.float32(1 - math.exp(-2 * math.pi * 12.0 / fs))
        self.noise_lp = np.float32(0)
        self.rng = np.random.default_rng(11)
        self.comb = {c: np.zeros(int(0.022 * fs), np.float32) for c in "LR"}
        self.comb_wr = {"L": 0, "R": 0}
        self.tap_off = {c: [(nm, ci, _scale(off, fs, sz), w)
                            for nm, ci, off, w in self.TAPS[c]] for c in "LR"}

    @staticmethod
    def _dl(buf, wr, x):
        y = buf[wr]; buf[wr] = x
        return y, (wr + 1) % len(buf)

    def _half_loop(self, c: str, x_in: float, cross: float,
                   lfo: float, sgn: float) -> float:
        ch, g = self.ch[c], self.g
        # cross-feed + bass boost (long LF decay)
        ch["bass_s"] += self.bass_c * (cross - ch["bass_s"])
        v = x_in + g["d0"] * (cross + self.p["bass_mult"] * 10 * ch["bass_s"])
        ch["damp_s"] += self.damp_c * (v - ch["damp_s"])      # loop damping LP
        v = ch["damp_s"]
        v = ch["m1"].process(v, lfo * sgn)
        v, ch["wr"]["d1"] = self._dl(ch["d1"], ch["wr"]["d1"], v)
        v = ch["m2"].process(v, -lfo * sgn)
        v, ch["wr"]["d_main"] = self._dl(ch["d_main"], ch["wr"]["d_main"], v)
        v = ch["n2"].process(v)
        v, ch["wr"]["d_mid"] = self._dl(ch["d_mid"], ch["wr"]["d_mid"], v)
        v = ch["n3"].process(v, lfo * sgn)
        v, ch["wr"]["d_tail"] = self._dl(ch["d_tail"], ch["wr"]["d_tail"], v)
        return v   # = cross-feed source for the other channel

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        stereo = audio.ndim == 2
        xl = audio[0] if stereo else audio
        xr = audio[1] if stereo else audio
        n = xl.shape[0]
        out = np.zeros((2, n), dtype=np.float32)
        p = self.p
        crossL = crossR = np.float32(0.0)
        for t in range(n):
            # LFO 1 (loop) with slew limit + dither; LFO 2 (output combs)
            self.ph1 = (self.ph1 + p["spin"] / self.fs) % 1.0
            self.ph2 = (self.ph2 + p["spin2"] / self.fs) % 1.0
            noise = np.float32(self.rng.uniform(-1, 1))
            self.noise_lp += np.float32(0.0003) * (noise - self.noise_lp)
            raw1 = (math.sin(2 * math.pi * self.ph1)
                    + 0.09 * p["dither"] * self.noise_lp) * p["wander"]
            self.lfo1_lp += self.slew1 * (np.float32(raw1) - self.lfo1_lp)
            raw2 = math.sin(2 * math.pi * self.ph2) * p["wander2"]
            self.lfo2_lp += self.slew2 * (np.float32(raw2) - self.lfo2_lp)
            gjit = 0.06 * p["dither"] * self.noise_lp
            # input diffusion (sign-alternating dithered APs)
            dl, dr = xl[t], xr[t]
            for i, ap in enumerate(self.ch["L"]["in_aps"]):
                dl = ap.process(dl, self.lfo1_lp * (-1) ** i, gjit * (-1) ** i)
            for i, ap in enumerate(self.ch["R"]["in_aps"]):
                dr = ap.process(dr, -self.lfo1_lp * (-1) ** i, gjit * (-1) ** i)
            # figure-8: each half consumes the other's previous tail sample
            newL = self._half_loop("L", dl, crossR, self.lfo1_lp, +1.0)
            newR = self._half_loop("R", dr, crossL, self.lfo1_lp, -1.0)
            crossL, crossR = newL, newR
            # output taps (224 mix) + spin2 gain-modulated FF comb
            wet = {}
            for c in "LR":
                acc = np.float32(0.0)
                for nm, ci, off, w in self.tap_off[c]:
                    buf = self.ch[ci][nm]
                    acc += np.float32(w) * buf[(self.ch[ci]["wr"][nm]
                                                - 1 - off) % len(buf)]
                cb, cw = self.comb[c], self.comb_wr[c]
                gmod = self.lfo2_lp if c == "L" else -self.lfo2_lp
                y = acc + gmod * cb[cw]
                cb[cw] = acc
                self.comb_wr[c] = (cw + 1) % len(cb)
                ch = self.ch[c]           # output 10 kHz one-pole
                ch["out_lp"] += np.float32(0.8) * (y - ch["out_lp"])
                wet[c] = ch["out_lp"]
            out[0, t] = (1 - p["mix"]) * xl[t] + p["mix"] * wet["L"]
            out[1, t] = (1 - p["mix"]) * xr[t] + p["mix"] * wet["R"]
        return out if stereo else out.mean(axis=0)
```

Fidelity caveats to resolve during implementation (all verifiable against the A1 write-up): the exact fv3 leak placement inside nested APs, tap read offsets relative to write pointers (off-by-one conventions), and the mono-in behavior. None affect the architecture; all affect unit tests, so pin them with IR regression tests once auditioned.

---

## 5. C translation

The two primitives dominate; everything else is plumbing identical to the repo's existing C exports. Note **no allocation, no `%` on hot paths** (lengths are not powers of two → use compare-and-wrap).

```c
typedef struct {
    float *buf;        /* points into one big static arena */
    int    len, wr;
    int    d, exc;
    float  g, leak;
} LeakyModAP;

static inline float lmap_process(LeakyModAP *ap, float x, float mod, float gjit)
{
    float rpos = (float)ap->wr - ((float)ap->d + mod * (float)ap->exc);
    while (rpos < 0.f) rpos += (float)ap->len;
    int   i0 = (int)rpos;
    float fr = rpos - (float)i0;
    int   i1 = i0 + 1; if (i1 >= ap->len) i1 = 0;
    float z  = ap->buf[i0] + fr * (ap->buf[i1] - ap->buf[i0]);
    float g  = ap->g + gjit;
    float y  = z - g * x;
    ap->buf[ap->wr] = x + g * z * ap->leak;
    if (++ap->wr >= ap->len) ap->wr = 0;
    return y;
}

/* nested AP: outer recirculation passes through inner APs */
static inline float lnap_process(LeakyModAP *outer, LeakyModAP *inner,
                                 int n_inner, float x, float mod)
{
    float rpos = (float)outer->wr - ((float)outer->d + mod * (float)outer->exc);
    while (rpos < 0.f) rpos += (float)outer->len;
    int   i0 = (int)rpos;
    float fr = rpos - (float)i0;
    int   i1 = i0 + 1; if (i1 >= outer->len) i1 = 0;
    float z  = outer->buf[i0] + fr * (outer->buf[i1] - outer->buf[i0]);
    for (int k = 0; k < n_inner; k++)
        z = lmap_process(&inner[k], z, 0.f, 0.f);
    float y = z - outer->g * x;
    outer->buf[outer->wr] = x + outer->g * z * outer->leak;
    if (++outer->wr >= outer->len) outer->wr = 0;
    return y;
}

typedef struct {
    /* one arena for every buffer; offsets computed at init from size/fs */
    float arena[65536];
    LeakyModAP in_ap[2][6];
    LeakyModAP m1[2], m2[2];
    LeakyModAP n2_out[2], n2_in[2][1];
    LeakyModAP n3_out[2], n3_in[2][2];
    float *d1[2], *d_main[2], *d_mid[2], *d_tail[2];
    int    d1_len[2], d_main_len[2], d_mid_len[2], d_tail_len[2];
    int    d1_wr[2], d_main_wr[2], d_mid_wr[2], d_tail_wr[2];
    float  decay0, bass_mult, damp_c, bass_c;
    float  damp_s[2], bass_s[2], out_lp[2];
    /* modulation */
    float  ph1, ph2, spin_inc, spin2_inc;
    float  lfo1_lp, lfo2_lp, slew1, slew2;
    float  noise_lp, dither;
    unsigned rng;                       /* xorshift32 */
    float  comb[2][1060];               /* 22 ms @ 48 kHz */
    int    comb_wr[2];
    /* output taps: {which buffer, offset, weight} x 4 per channel */
    int    tap_buf[2][4], tap_off[2][4];
    float  tap_w[2][4];
    float  mix;
} ChamberFig8State;

static inline float xs_noise(unsigned *s)   /* white in [-1,1] */
{
    *s ^= *s << 13; *s ^= *s >> 17; *s ^= *s << 5;
    return (float)(int)*s * (1.f / 2147483648.f);
}

void chamber_fig8_process(ChamberFig8State *s,
                          const float *in_l, const float *in_r,
                          float *out_l, float *out_r, int n)
{
    float crossL = s->d_tail[0][s->d_tail_wr[0]];   /* previous tail samples */
    float crossR = s->d_tail[1][s->d_tail_wr[1]];
    for (int t = 0; t < n; t++) {
        /* LFOs: sine + slew limit; pink-ish dither */
        s->ph1 += s->spin_inc;  if (s->ph1 >= 1.f) s->ph1 -= 1.f;
        s->ph2 += s->spin2_inc; if (s->ph2 >= 1.f) s->ph2 -= 1.f;
        s->noise_lp += 0.0003f * (xs_noise(&s->rng) - s->noise_lp);
        float raw1 = sinf(6.2831853f * s->ph1) + 0.09f * s->dither * s->noise_lp;
        s->lfo1_lp += s->slew1 * (raw1 - s->lfo1_lp);
        s->lfo2_lp += s->slew2 * (sinf(6.2831853f * s->ph2) - s->lfo2_lp);
        float gjit = 0.06f * s->dither * s->noise_lp;

        float d[2] = { in_l[t], in_r[t] };
        for (int c = 0; c < 2; c++) {
            float sgn = c ? -1.f : 1.f;
            for (int i = 0; i < 6; i++) {
                float isgn = (i & 1) ? -1.f : 1.f;
                d[c] = lmap_process(&s->in_ap[c][i], d[c],
                                    sgn * isgn * s->lfo1_lp, isgn * gjit);
            }
        }
        float cross[2] = { crossR, crossL };        /* figure-8 swap */
        float tail[2];
        for (int c = 0; c < 2; c++) {
            float sgn = c ? -1.f : 1.f;
            s->bass_s[c] += s->bass_c * (cross[c] - s->bass_s[c]);
            float v = d[c] + s->decay0 * (cross[c] + s->bass_mult * 10.f * s->bass_s[c]);
            s->damp_s[c] += s->damp_c * (v - s->damp_s[c]);
            v = s->damp_s[c];
            v = lmap_process(&s->m1[c], v,  sgn * s->lfo1_lp, 0.f);
            { float y = s->d1[c][s->d1_wr[c]]; s->d1[c][s->d1_wr[c]] = v;
              if (++s->d1_wr[c] >= s->d1_len[c]) s->d1_wr[c] = 0; v = y; }
            v = lmap_process(&s->m2[c], v, -sgn * s->lfo1_lp, 0.f);
            { float y = s->d_main[c][s->d_main_wr[c]]; s->d_main[c][s->d_main_wr[c]] = v;
              if (++s->d_main_wr[c] >= s->d_main_len[c]) s->d_main_wr[c] = 0; v = y; }
            v = lnap_process(&s->n2_out[c], s->n2_in[c], 1, v, 0.f);
            { float y = s->d_mid[c][s->d_mid_wr[c]]; s->d_mid[c][s->d_mid_wr[c]] = v;
              if (++s->d_mid_wr[c] >= s->d_mid_len[c]) s->d_mid_wr[c] = 0; v = y; }
            v = lnap_process(&s->n3_out[c], s->n3_in[c], 2, v, sgn * s->lfo1_lp);
            { float y = s->d_tail[c][s->d_tail_wr[c]]; s->d_tail[c][s->d_tail_wr[c]] = v;
              if (++s->d_tail_wr[c] >= s->d_tail_len[c]) s->d_tail_wr[c] = 0;
              tail[c] = y; }
        }
        crossL = tail[0];  crossR = tail[1];

        /* output taps + spin2 gain-mod comb + 10 kHz LP */
        float wet[2];
        for (int c = 0; c < 2; c++) {
            float acc = 0.f;
            /* tap_buf indexes a table of {buf ptr,len,wr} quadruplets (init) */
            /* ... acc += tap_w * ring_read(tap_buf, tap_off) x4 ... */
            float gmod = (c ? -1.f : 1.f) * 0.3f * s->lfo2_lp;
            float y = acc + gmod * s->comb[c][s->comb_wr[c]];
            s->comb[c][s->comb_wr[c]] = acc;
            if (++s->comb_wr[c] >= 1060) s->comb_wr[c] = 0;
            s->out_lp[c] += 0.8f * (y - s->out_lp[c]);
            wet[c] = s->out_lp[c];
        }
        out_l[t] = (1.f - s->mix) * in_l[t] + s->mix * wet[0];
        out_r[t] = (1.f - s->mix) * in_r[t] + s->mix * wet[1];
    }
}
```

RAM: total ring memory at size = 1.25, 48 kHz ≈ 45k floats ≈ **180 KB** — the cheapest of the three picks by far. Ops/sample ≈ 2×(6 + 2 mod-APs + 5 plain APs) interpolated reads + filters ≈ **~150 flops** — runs on anything, including FV-1-class budgets if the dither is dropped.

---

## 6. Verification plan

1. **RT accuracy:** `measure_rt60()` within ±8% of `rt60` across size ∈ {0.55, 0.65, 1.0} (the loop's distributed decay makes RT slightly topology-dependent; calibrate `resetdecay` constants once and pin with a test).
2. **Bass bloom:** `measure_rt60_bands()` shows RT(125 Hz)/RT(1 kHz) ≈ 1.3–1.6 at `bass_mult` = 0.10, monotonic in `bass_mult`.
3. **Pitch stability:** on a 1 kHz sine burst, tail spectrogram peak deviates < 3 cents (alternating-sign modulation must cancel; a same-sign bug shows up here immediately).
4. **Spectral motion:** long-term spectrum of a white-noise-excited tail, measured in 1 s frames, shows ±1.5–2.5 dB frame-to-frame ripple movement when `wander2` = 0.3 and none at 0 (the spin2 comb).
5. **Onset density:** NED (see hall doc §6) ≥ 0.8 by 25 ms at size 0.65 with 6 input APs — the chamber requirement.
6. **224 sanity preset:** at size 1.0 / fs 34125 configuration, the IR's tap timing pattern matches the A1 output-mix offsets (structural regression test).

## 7. Implementation order in claudeverb

1. Add `LeakyModAllpass` + `LeakyNestedAllpass` to `filters.py` (also needed by the spring pick's dispersive loop, and by future Lexicon-school work).
2. `ChamberFigure8` core loop, static (wander = dither = 0) — verify RT/EDC/taps.
3. Modulation systems (loop LFO w/ slew, spin2 gain comb), then A2 dithering.
4. Input diffusion chain + presets + `to_dot()` (this topology begs for the component-level diagram).
5. C export; `vintage` quantizer last (trivial, A44 sketch).

## 8. Sources

- Topology, constants, decay distribution, output taps, spin/wander mechanisms: A1 (Freeverb3 `progenitor.cpp`/`progenitor_t.hpp` — **study only, GPL**; fv3 algorithm notes; 224 v4.4 reconstruction at dannychesnut.com; Gearspace "Lexicon bestiary"; Griesinger SOS interview)
- Input diffusion, cross-feed APs, noise-dithered modulation: A2 (Freeverb3 `progenitor2.cpp`); Griesinger AES preprint 3014 (1991) for the theory of random vs sine modulation
- Spin/wander semantics: A3 (Relab Random Hall docs; Lexicon 480L manual; UAD 224 manual)
- Chamber-class references being matched: LiquidSonics Cinematic Rooms (Fusion-IR), Meris Mercury7 (M7-homage) — both closed; matched here by property, not by reverse engineering
- Converter-in-loop texture: A44 (Valhalla Sanctuary / EMT 250 documentation)
