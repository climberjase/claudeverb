# Phase 8: Room, Chamber & Dattorro Variants - Research

**Researched:** 2026-04-02
**Domain:** Reverb algorithm design (early reflections, room simulation, Dattorro topology variants)
**Confidence:** MEDIUM-HIGH

## Summary

This phase implements 6 new reverb algorithms in two families: (1) Room/Chamber reverbs using a hybrid early-reflections + FDN-late-reverb architecture, and (2) Dattorro topology variants with modified tank structures. The research covers early reflection tapped delay line design, Griesinger single-loop topology, asymmetric tank patterns, and the gain staging / spectral overlap pitfalls of composing ER with FDN.

The Room/Chamber family composes a new standalone `EarlyReflections` class with the existing `FDNCore` in serial. Early reflections use tapped delay lines with per-tap OnePole lowpass for air absorption and L/R alternating panning. The Dattorro variants are fully independent algorithms: Single-Loop Tank reimagines the figure-eight as a single feedback ring, Triple-Diffuser doubles the input diffusion stage, and Asymmetric Tank uses different L/R delay lengths and diffuser counts.

**Primary recommendation:** Build the `EarlyReflections` class first as a composable unit (following the `FDNCore` pattern), then compose it into `RoomReverbBase`. Build Dattorro variants as standalone implementations reusing existing DSP primitives (`AllpassFilter`, `DelayLine`, `OnePole`, `DCBlocker`) but with entirely independent topologies.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Hybrid ER approach: tapped delay line + allpass diffusion, serial into FDNCore
- Standalone EarlyReflections class in early_reflections.py (composable like FDNCore)
- Per-tap OnePole lowpass for air absorption on ER taps
- Alternating L/R stereo panning on taps (odd left, even right)
- Room/Chamber share RoomReverbBase in separate files (small_room.py, large_room.py, chamber.py)
- Size knob scales both ER taps + FDN delays together
- 6-8 taps: Small Room 6, Large Room and Chamber 8
- Chamber: 4 taps + 3 allpass diffusers (vs Rooms' 6-8 taps + 1-2 diffusers)
- Dattorro variants are fully independent implementations (not subclassed from DattorroPlate)
- Each Dattorro variant has its own input diffusion section
- All algorithms implement to_c_struct() and to_c_process_fn()
- Sample-by-sample processing, fixed-size buffers, no dynamic allocation
- ER Level knob replaces Mod knob (0=no ER/pure FDN, 100=ER only)
- Room/Chamber: 6 knobs (Decay, Size, Damping, ER Level, Mix, Pre-Delay) + 2 switches
- Single-Loop: Loop Length knob (30-150ms)
- Triple-Diffuser: Diffusion Density knob (2-6 active diffusers)
- Asymmetric Tank: Spread knob (symmetric to max asymmetry)
- 2-3 presets per algorithm

### Claude's Discretion
- Exact ER tap positions and gains per algorithm (tuned by metrics)
- Exact allpass diffuser delay lengths and coefficients
- Exact FDN base delay values per algorithm (coprime primes at appropriate scale)
- Exact damping coefficient defaults per algorithm
- Griesinger single-loop topology details (from research)
- ER Level default value per algorithm
- Preset parameter values (tuned by ear/metrics)
- Number of allpass diffusers in ER stage per algorithm (1-2 for Rooms, 3 for Chamber)
- RoomReverbBase file location (room_base.py or similar)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ALGO-02 | User can apply Small Room reverb (tapped delay ER + FDN late reverb, short decay) | EarlyReflections class + RoomReverbBase + FDNCore composition; ER tap patterns for small spaces (1-8ms range); coprime FDN delays scaled for small room |
| ALGO-03 | User can apply Large Room reverb (tapped delay ER + FDN late reverb, long decay) | Same architecture, wider ER tap spacing (5-50ms), longer FDN delays, more spacious character |
| ALGO-04 | User can apply Chamber reverb (dense diffusion, even decay, medium space) | Fewer taps (4) + more diffusers (3) for dense, warm character; warmer damping defaults |
| ALGO-06 | User can apply Dattorro variant with single-loop tank | Griesinger-style single feedback ring with interleaved allpass+delay sections; concrete topology from research |
| ALGO-07 | User can apply Dattorro variant with triple-diffuser input | 6 input allpass diffusers + standard figure-eight tank; Diffusion Density knob activates 2-6 diffusers |
| ALGO-08 | User can apply Dattorro variant with asymmetric tank | Different L/R delay lengths and diffuser counts; Spread knob morphs from symmetric to max asymmetry |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.24 | float32 audio buffers, array ops | Already in project, required for audio shape conventions |
| math | stdlib | sin/cos/pi for LFO, coefficient computation | C-portable math (maps to math.h) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=7.0 | Test framework | All algorithm tests |

### Internal Reuse (Critical)
| Module | Class/Function | Purpose |
|--------|---------------|---------|
| `filters.py` | `DelayLine` | ER tapped delay buffer, Dattorro tank delays |
| `filters.py` | `AllpassFilter` | ER diffusion, Dattorro input/decay diffusers |
| `dattorro_plate.py` | `OnePole` | Per-tap ER air absorption, FDN/tank damping |
| `dattorro_plate.py` | `DCBlocker` | Feedback loop DC removal in all tanks |
| `fdn_reverb.py` | `FDNCore` | Late reverb engine for Room/Chamber algorithms |
| `fdn_reverb.py` | `rt60_to_gain` | Decay time to feedback gain conversion |
| `base.py` | `ReverbAlgorithm` | Abstract base class for all algorithms |

**Installation:** No new packages needed. All DSP primitives exist in the codebase.

## Architecture Patterns

### Recommended Project Structure
```
claudeverb/algorithms/
    early_reflections.py      # EarlyReflections composable class
    room_base.py              # RoomReverbBase shared base class
    small_room.py             # SmallRoom (ReverbAlgorithm)
    large_room.py             # LargeRoom (ReverbAlgorithm)
    chamber.py                # Chamber (ReverbAlgorithm)
    small_room_presets.py     # 2-3 presets
    large_room_presets.py     # 2-3 presets
    chamber_presets.py        # 2-3 presets
    dattorro_single_loop.py   # SingleLoopTank (ReverbAlgorithm)
    dattorro_triple_diffuser.py  # TripleDiffuser (ReverbAlgorithm)
    dattorro_asymmetric.py    # AsymmetricTank (ReverbAlgorithm)
    dattorro_single_loop_presets.py
    dattorro_triple_diffuser_presets.py
    dattorro_asymmetric_presets.py
```

### Pattern 1: EarlyReflections Composable Class

**What:** A standalone class following the FDNCore composable pattern. Holds a single long DelayLine for tapped reading, per-tap OnePole filters for air absorption, and a cascade of AllpassFilter diffusers.

**When to use:** Composed by RoomReverbBase to provide ER before FDN late reverb.

**Implementation design:**
```python
class EarlyReflections:
    """Composable early reflections engine.

    Tapped delay line with per-tap lowpass + allpass diffusion.
    Output is mono or stereo (L/R alternating taps).
    """
    def __init__(
        self,
        tap_delays: list[int],      # delay in samples per tap
        tap_gains: list[float],     # gain per tap (0.0-1.0)
        tap_lpf_coeffs: list[float], # OnePole coeff per tap (1.0=bright, lower=darker)
        diffuser_delays: list[int],  # allpass diffuser delay lengths
        diffuser_feedback: float = 0.5,
        sample_rate: int = 48000,
    ) -> None:
        # Single long delay line (max tap delay + margin)
        max_delay = max(tap_delays) + 2
        self._delay_line = DelayLine(max_delay)

        # Per-tap lowpass filters (air absorption)
        self._tap_filters = [OnePole(c) for c in tap_lpf_coeffs]

        # Allpass diffusion cascade
        self._diffusers = [
            AllpassFilter(d, feedback=diffuser_feedback)
            for d in diffuser_delays
        ]

        # Store config
        self._tap_delays = tap_delays
        self._tap_gains = tap_gains

    def process_sample(self, x: float) -> tuple[float, float]:
        """Process one sample, return (left, right) ER output."""
        self._delay_line.write(x)

        left = 0.0
        right = 0.0
        for i, (delay, gain) in enumerate(zip(self._tap_delays, self._tap_gains)):
            tap_val = self._delay_line.read(delay)
            tap_val = self._tap_filters[i].process_sample(tap_val)
            tap_val *= gain

            # Alternating L/R panning (odd=left, even=right)
            if i % 2 == 0:
                right += tap_val
            else:
                left += tap_val

        # Sum L+R for diffusion input (mono diffusion)
        mono = (left + right) * 0.5
        for ap in self._diffusers:
            mono = ap.process_sample(mono)

        # Add diffused signal to both channels
        left += mono
        right += mono

        return (left, right)

    def set_size_scale(self, scale: float) -> None:
        """Scale tap positions by factor (called when Size knob changes)."""
        # Recalculate tap delays from base * scale
        ...

    def reset(self) -> None:
        """Reset all internal state."""
        ...
```

**Confidence:** HIGH -- follows established FDNCore composable pattern in codebase.

### Pattern 2: RoomReverbBase (ER -> FDN Serial Chain)

**What:** Shared base class that composes EarlyReflections + FDNCore in serial, handles the common param routing, C export boilerplate, and stereo output.

**When to use:** Subclassed by SmallRoom, LargeRoom, and Chamber.

**Signal flow:**
```
mono_input -> pre_delay -> EarlyReflections -> ER_Level_mix -> FDNCore -> stereo_output
                                                                            |
                                              ER stereo also mixed in <-----+
```

**Implementation design:**
```python
class RoomReverbBase(ReverbAlgorithm):
    """Base class for Room/Chamber reverbs.

    Subclasses override _get_config() to provide tap positions,
    FDN delays, diffuser counts, decay ranges, etc.
    """

    def __init__(self) -> None:
        config = self._get_config()
        self._er = EarlyReflections(
            tap_delays=config["tap_delays"],
            tap_gains=config["tap_gains"],
            tap_lpf_coeffs=config["tap_lpf_coeffs"],
            diffuser_delays=config["diffuser_delays"],
        )
        self._fdn = FDNCore(base_delays=config["fdn_delays"])
        self._pre_delay_line = DelayLine(int(0.1 * SAMPLE_RATE))
        # ... param state ...

    def _get_config(self) -> dict:
        """Override in subclass to provide algorithm-specific config."""
        raise NotImplementedError

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        """ER -> FDN serial processing with ER Level crossfade."""
        # ... standard mono->stereo processing loop ...
        for i in range(n_samples):
            x = mono_in[i]
            # Pre-delay
            # EarlyReflections -> (er_l, er_r)
            # ER Level crossfade: 0=pure FDN, 100=ER only
            # Feed ER mono sum into FDN
            # FDN -> stereo tap
            # Combine ER stereo + FDN stereo based on ER Level
            # Width crossmix, mix dry/wet, clip
```

**Confidence:** HIGH -- straightforward composition of existing patterns.

### Pattern 3: Griesinger Single-Loop Tank

**What:** A single feedback ring with interleaved allpass filters and delay lines, rather than Dattorro's figure-eight (two cross-fed half-loops).

**Topology (derived from research):**

The Griesinger/Lexicon 224 style uses a single continuous loop:
```
input -> [input_diffusers] -> tank_input
                                   |
    +------------------------------+
    |                              v
    |   [allpass_1] -> [delay_1] -> [damping_1] -> [allpass_2] -> [delay_2] ->
    |                                                                          |
    +---- [delay_4] <- [allpass_4] <- [damping_2] <- [delay_3] <- [allpass_3] <+

    stereo output = weighted sum of taps from various points in the loop
```

**Key differences from figure-eight:**
- Single feedback path (no cross-feeding between two halves)
- Denser echo pattern due to longer total loop length
- Less inherent stereo separation (stereo comes from output tap spacing only)
- Modulation applied to one or two delays in the loop
- Loop length = sum of all delays + allpass delays, typically 80-200ms total

**Concrete implementation values (at 48 kHz):**

For a single-loop tank with configurable Loop Length (30-150ms total):
- 4 allpass sections in the loop with delays: [AP1: ~5ms, AP2: ~8ms, AP3: ~11ms, AP4: ~7ms]
- 4 delay sections between allpasses: [D1: ~15ms, D2: ~22ms, D3: ~18ms, D4: ~25ms]
- All delay lengths scale together with Loop Length knob
- Allpass feedback coefficients: 0.5-0.7 (moderate diffusion)
- Damping filters at 2 points in loop (after D1 and D3)
- DC blocker at loop junction
- Modulation on D1 (subtle, 0.3 samples depth, ~0.8 Hz)
- Feedback gain from rt60_to_gain() based on total loop delay

**Stereo output taps** (spaced for decorrelation):
- Left: sum of taps from [D1 at 30%, D2 at 60%, D4 at 45%]
- Right: sum of taps from [D1 at 70%, D3 at 40%, D4 at 80%]

**Confidence:** MEDIUM -- Griesinger's exact topology is not publicly published with full delay values. The structure above is derived from Dattorro's description "in the style of Griesinger," the Jon Pure Data implementation, Spin Semiconductor forum discussion, and general allpass-loop reverb principles. The specific delay values are educated choices that will need tuning.

### Pattern 4: Triple-Diffuser (Extended Input Diffusion)

**What:** Standard Dattorro figure-eight tank with 6 input allpass diffusers instead of 4.

**Implementation approach:**
```python
# 6 input diffusers (double Dattorro's 4)
# First 4 use same structure as DattorroPlate
# 5th and 6th add extra smoothing
INPUT_AP_LENGTHS_6 = [142, 107, 379, 277, 191, 331]  # at 29761 Hz
INPUT_AP_COEFFS_6 = [0.75, 0.75, 0.625, 0.625, 0.6, 0.6]

# Diffusion Density knob controls how many are active (2-6)
# Inactive diffusers are bypassed (pass-through)
```

The tank itself is identical to DattorroPlate's figure-eight, but with its own independent state. The `Diffusion Density` knob at 0 activates only 2 diffusers (some attack transients audible), at 100 all 6 are active (ultra-smooth onset).

**Confidence:** HIGH -- straightforward extension of existing DattorroPlate pattern.

### Pattern 5: Asymmetric Tank

**What:** Modified figure-eight where left and right paths have different delay lengths AND different numbers of diffuser stages.

**Implementation approach:**
```python
# Spread knob (0-100) morphs from symmetric to max asymmetry
# At Spread=0: delays match standard Dattorro proportions
# At Spread=100:
#   Left path: shorter delays, 1 decay diffuser
#   Right path: longer delays, 2 decay diffusers
#   This creates both timing and tonal asymmetry

# Example: base Dattorro values scaled asymmetrically
# Left half: delays * (1.0 - spread_factor * 0.3)
# Right half: delays * (1.0 + spread_factor * 0.3)
```

**Key design constraint:** At Spread=0, behavior should closely approximate standard DattorroPlate.

**Confidence:** MEDIUM -- asymmetric tank design is well-understood in principle but the specific L/R ratio and diffuser count mapping needs experimentation to sound good without phase cancellation artifacts.

### Anti-Patterns to Avoid

- **Subclassing DattorroPlate for variants:** Each variant has fundamentally different topology. Subclassing would create fragile coupling and make independent tuning difficult. Use composition of primitives instead.
- **Shared delay buffers between ER and FDN:** The ER and FDN must have independent state for clean reset and C portability.
- **Parallel ER + FDN mixing:** Research and the CONTEXT.md decision confirm serial (ER feeds into FDN) sounds more natural than parallel mixing. ER Level controls the blend, not the routing.
- **Excessive allpass cascading for ER diffusion:** More than 3 allpass diffusers in the ER stage causes metallic ringing artifacts on transient material (per Valhalla DSP research). Chamber's 3 is the maximum.
- **Hard-switching Diffusion Density:** The Triple-Diffuser's active diffuser count should crossfade, not hard-switch, to avoid clicks when changing the knob.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Delay line with fractional read | Custom circular buffer | `DelayLine` from `filters.py` | Already handles linear interpolation, wrap, float32 |
| Allpass filter | Custom allpass | `AllpassFilter` from `filters.py` | Schroeder topology already implemented and tested |
| One-pole lowpass | Custom LP filter | `OnePole` from `dattorro_plate.py` | Used for damping throughout codebase |
| DC blocking | Custom highpass | `DCBlocker` from `dattorro_plate.py` | Standard R=0.99935 at 48kHz already correct |
| RT60 to gain conversion | Custom formula | `rt60_to_gain()` from `fdn_reverb.py` | Handles edge cases (rt60<=0, gain clamping) |
| Hadamard mixing | Custom matrix multiply | `hadamard_4()` from `fdn_reverb.py` | Normalized butterfly already verified |
| FDN late reverb | Custom FDN for each room | `FDNCore` from `fdn_reverb.py` | Composable 4-channel FDN with all features |
| Preset file pattern | Custom preset loading | Follow `fdn_presets.py` pattern | `list_presets()` + `get_preset()` returning copies |

**Key insight:** Every DSP primitive needed for Phase 8 already exists in the codebase. The work is composition and tuning, not building new filter types.

## Common Pitfalls

### Pitfall 1: ER-to-FDN Gain Staging
**What goes wrong:** The combined output of ER + FDN clips or sounds thin because the ER output amplitude was not calibrated relative to the FDN input expectations.
**Why it happens:** FDNCore expects input around [-1, 1] range. If ER taps sum to >1.0, the FDN input is too hot. If ER gain is too low, the late reverb lacks density.
**How to avoid:** Normalize ER output: divide by sqrt(num_taps) or empirically scale so that ER peak output is ~0.7 for a unit impulse input. The ER Level knob crossfades between ER and direct-to-FDN, so both paths must have matched levels.
**Warning signs:** Clipping on transients (too hot), or reverb tail sounds disconnected from ER (level mismatch).

### Pitfall 2: ER Spectral Overlap with FDN
**What goes wrong:** When ER taps are too evenly spaced, they create a comb filter effect that colors the signal before it enters the FDN, resulting in a metallic or hollow sound.
**Why it happens:** Evenly spaced taps = harmonic comb filter. The FDN then amplifies this coloration through feedback.
**How to avoid:** Use non-uniform tap spacing. Ideally, tap delays should be mutually prime or at least avoid integer ratio relationships. The allpass diffusers after the taps help smear the comb peaks, but irregular spacing is the first defense.
**Warning signs:** Audible pitch/ringing on broadband input (white noise, snare drums).

### Pitfall 3: Size Knob Scaling Discontinuities
**What goes wrong:** When the Size knob scales both ER taps and FDN delays, changing it can cause clicks or zipper noise because delay line read positions jump.
**Why it happens:** FDNCore.set_size() changes delay lengths instantly. ER tap positions are recalculated as integers, causing discontinuities.
**How to avoid:** For the FDN, the existing modulation handles smooth transitions. For ER, accept that Size changes cause a slight transient (this is standard in room reverbs -- the parameter is not meant to be swept continuously). Alternatively, reset the ER delay line on size change if artifacts are unacceptable.
**Warning signs:** Audible clicks when turning the Size knob during active audio.

### Pitfall 4: Metallic Ringing from Allpass Cascades
**What goes wrong:** Cascaded allpass filters in ER diffusion or Dattorro input stages produce audible ringing on transient material (drums, plucked strings, vocals).
**Why it happens:** Allpass filters have flat magnitude response over time, but the transient response rings at the allpass delay frequency. More cascaded stages = more ringing.
**How to avoid:** Limit ER diffusers to 1-2 for rooms, 3 for chamber. Use feedback coefficients of 0.5-0.6 (not 0.7+). For Triple-Diffuser, the Diffusion Density knob lets users back off if ringing is heard.
**Warning signs:** "Twangy" or "springy" sound on percussive input.

### Pitfall 5: Single-Loop Tank Instability
**What goes wrong:** The single feedback loop accumulates energy and self-oscillates or clips.
**Why it happens:** Unlike the figure-eight where energy distributes across two paths, a single loop concentrates all feedback energy. If the total loop gain exceeds 1.0 at any frequency, the loop is unstable.
**How to avoid:** Apply damping at multiple points in the loop (not just one). Use rt60_to_gain() with the TOTAL loop delay (sum of all delays) to compute the feedback gain. Add a DC blocker inside the loop. Clamp total loop gain to max 0.999.
**Warning signs:** Output grows without bound, DC offset accumulates, or high-frequency oscillation appears.

### Pitfall 6: Asymmetric Tank Phase Cancellation
**What goes wrong:** When L and R tank paths have very different delay lengths, summing to mono causes phase cancellation, producing a thin or hollow sound.
**Why it happens:** Different delay lengths mean different phase relationships at each frequency. When stereo is collapsed to mono, some frequencies cancel.
**How to avoid:** Limit the max asymmetry ratio to ~1.6:1 between L and R delays (not 2:1 or more). Test mono compatibility at Spread=100. The Spread knob should have diminishing returns above 80%.
**Warning signs:** Mono check reveals thin or colored sound at high Spread values.

### Pitfall 7: Missing Reset State in Composed Objects
**What goes wrong:** After reset(), the algorithm still has stale state from a previous run because a composed object (ER or FDN) was not properly reset.
**Why it happens:** RoomReverbBase.reset() might forget to reset the pre-delay line, or one of the ER's per-tap filters.
**How to avoid:** reset() must chain through ALL composed objects: pre_delay_line, EarlyReflections (which resets its delay line, all tap filters, all diffusers), FDNCore.
**Warning signs:** Processing the same input twice produces different output after reset.

## Code Examples

### Early Reflection Tap Patterns (Concrete Values)

Tap positions derived from room acoustics principles. Speed of sound = 343 m/s at 48 kHz. Tap delays represent first-order wall reflections for idealized rectangular rooms, with gains decreasing for later arrivals (inverse distance).

```python
# Small Room: ~4x3x3m chapel/studio (0.5-2.0s decay)
# First reflection at ~1.2ms (nearest wall), last at ~15ms
SMALL_ROOM_CONFIG = {
    "tap_delays": [58, 97, 134, 181, 241, 307],  # samples at 48kHz (~1.2-6.4ms)
    "tap_gains": [0.84, 0.71, 0.62, 0.53, 0.42, 0.33],
    "tap_lpf_coeffs": [0.95, 0.92, 0.88, 0.84, 0.78, 0.72],  # later = darker
    "diffuser_delays": [67, 101],  # 2 allpass diffusers (~1.4ms, 2.1ms)
    "fdn_delays": [443, 577, 751, 941],  # smaller primes for short room
}

# Large Room: ~12x8x5m live room / hall (1.0-3.5s decay)
# First reflection at ~4ms, last at ~50ms
LARGE_ROOM_CONFIG = {
    "tap_delays": [192, 311, 431, 587, 769, 953, 1201, 1487],  # ~4-31ms
    "tap_gains": [0.80, 0.72, 0.64, 0.55, 0.47, 0.40, 0.33, 0.27],
    "tap_lpf_coeffs": [0.93, 0.89, 0.85, 0.80, 0.75, 0.70, 0.64, 0.58],
    "diffuser_delays": [83, 127],  # 2 allpass diffusers
    "fdn_delays": [887, 1151, 1493, 1879],  # larger primes for bigger room
}

# Chamber: ~6x4x3m echo chamber (1.0-4.0s decay)
# Fewer taps (4) + more diffusers (3) = dense, warm
CHAMBER_CONFIG = {
    "tap_delays": [120, 223, 367, 521],  # ~2.5-10.9ms, wider spacing
    "tap_gains": [0.78, 0.65, 0.52, 0.40],
    "tap_lpf_coeffs": [0.88, 0.82, 0.75, 0.68],  # warmer than rooms
    "diffuser_delays": [79, 113, 163],  # 3 allpass diffusers for density
    "fdn_delays": [659, 853, 1103, 1381],  # medium primes, warm character
}
```

**Design rationale:**
- Tap delays are non-uniformly spaced (avoid comb filtering)
- Tap gains decrease with delay (inverse distance law approximation)
- LPF coefficients decrease with delay (air absorption increases with distance)
- All FDN delay values are prime and mutually coprime
- Small Room FDN delays sum to ~2712 samples (~56ms), Large Room to ~5410 (~113ms)

**Confidence:** MEDIUM -- tap positions are physically motivated but will need tuning by ear/metrics. FDN delays are good starting points.

### ER Level Crossfade Implementation

```python
# ER Level: 0 = no ER (pure FDN tail), 100 = ER only (no tail)
# This controls the BLEND, not the routing (ER always feeds FDN)
er_level = self._er_level / 100.0  # 0.0 to 1.0

# Process ER
er_l, er_r = self._er.process_sample(x)

# Feed ER mono sum to FDN (always, regardless of ER Level)
er_mono = (er_l + er_r) * 0.5
fdn_outputs = self._fdn.process_sample([er_mono, er_mono, er_mono, er_mono])

# Stereo tap from FDN
fdn_l = (fdn_outputs[0] + fdn_outputs[2]) * freeze_gain
fdn_r = (fdn_outputs[1] + fdn_outputs[3]) * freeze_gain

# Crossfade: er_level controls ER prominence in output
# At 0: output = FDN only (but FDN still receives ER-processed input)
# At 100: output = ER only (FDN still runs but not in output)
out_l = er_l * er_level + fdn_l * (1.0 - er_level)
out_r = er_r * er_level + fdn_r * (1.0 - er_level)
```

### Size Knob Scaling (ER + FDN Together)

```python
def _apply_size(self, size_val: int) -> None:
    """Scale both ER taps and FDN delays from Size knob (0-100)."""
    # Map 0-100 to 0.5x-2.0x scale factor
    scale = 0.5 + (size_val / 100.0) * 1.5

    # Scale ER tap positions
    self._er.set_size_scale(scale)

    # Scale FDN delay lengths
    self._fdn.set_size(scale)
```

### Single-Loop Tank Core Processing

```python
def _process_tank_sample(self, tank_input: float) -> tuple[float, float]:
    """Process one sample through the single-loop tank."""
    # Read from end of loop (feedback)
    loop_fb = self._loop_delay_4.read(self._loop_d4_len)
    loop_fb = self._dc_blocker.process_sample(loop_fb)
    loop_fb *= self._feedback_gain

    # Inject input + feedback
    x = tank_input + loop_fb

    # Section 1: allpass -> delay -> damping
    x = self._loop_ap1.process_sample(x)
    self._loop_delay_1.write(x)
    x = self._loop_delay_1.read(self._loop_d1_len + self._lfo_val)  # modulated
    x = self._loop_damp_1.process_sample(x)

    # Section 2: allpass -> delay
    x = self._loop_ap2.process_sample(x)
    self._loop_delay_2.write(x)
    x = self._loop_delay_2.read(self._loop_d2_len)

    # Section 3: allpass -> delay -> damping
    x = self._loop_ap3.process_sample(x)
    self._loop_delay_3.write(x)
    x = self._loop_delay_3.read(self._loop_d3_len)
    x = self._loop_damp_2.process_sample(x)

    # Section 4: allpass -> delay (feeds back to start)
    x = self._loop_ap4.process_sample(x)
    self._loop_delay_4.write(x)

    # Output taps for stereo (read from various points)
    out_l = (self._loop_delay_1.read(self._tap_l1) +
             self._loop_delay_2.read(self._tap_l2) +
             self._loop_delay_4.read(self._tap_l3))
    out_r = (self._loop_delay_1.read(self._tap_r1) +
             self._loop_delay_3.read(self._tap_r2) +
             self._loop_delay_4.read(self._tap_r3))

    return (out_l, out_r)
```

### Algorithm Registration Pattern

```python
# In claudeverb/algorithms/__init__.py, add:
from claudeverb.algorithms.small_room import SmallRoom
from claudeverb.algorithms.large_room import LargeRoom
from claudeverb.algorithms.chamber import Chamber
from claudeverb.algorithms.dattorro_single_loop import DattorroSingleLoop
from claudeverb.algorithms.dattorro_triple_diffuser import DattorroTripleDiffuser
from claudeverb.algorithms.dattorro_asymmetric import DattorroAsymmetric

ALGORITHM_REGISTRY = {
    "freeverb": Freeverb,
    "dattorro_plate": DattorroPlate,
    "fdn": FDNReverb,
    "small_room": SmallRoom,
    "large_room": LargeRoom,
    "chamber": Chamber,
    "dattorro_single_loop": DattorroSingleLoop,
    "dattorro_triple_diffuser": DattorroTripleDiffuser,
    "dattorro_asymmetric": DattorroAsymmetric,
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Moorer's 6 parallel combs for late reverb | FDN with Hadamard mixing | 1990s-2000s | FDNs are standard; combs sound metallic |
| Fixed early reflections from raytracing | Configurable ER with density control | 2010s (ValhallaRoom etc.) | Users prefer adjustable ER density over physical accuracy |
| Shared allpass between ER and late | Separate ER and late reverb stages | Standard practice | Cleaner separation, independent tuning |
| Single Dattorro topology | Multiple variant topologies | Ongoing | Different tanks serve different aesthetic goals |

**Deprecated/outdated:**
- Parallel comb filter late reverb (Schroeder/Moorer style): Replaced by FDN for better density and less coloration
- Ray-traced ER tap patterns: Over-engineered for musical reverb; perceptual tuning is more effective

## Open Questions

1. **Griesinger single-loop exact delay values**
   - What we know: The topology is 4 allpass sections interleaved with 4 delays in a ring, total loop ~80-200ms, with modulation on one delay.
   - What's unclear: The exact delay lengths from the original Lexicon 224 are not publicly documented. Dattorro's paper gives the figure-eight variant, not the single-loop.
   - Recommendation: Use the delay values from the Jon Pure Data implementation (scaled from 29761 Hz to 48 kHz) as a starting point, then tune by ear. The Loop Length knob provides user adjustability.

2. **Optimal ER-to-FDN transition**
   - What we know: Serial routing (ER output feeds FDN input) is the decided approach.
   - What's unclear: Whether the ER output should be slightly attenuated before feeding FDN, or if the FDN input gain handles this naturally.
   - Recommendation: Start with ER output normalized to ~0.7 peak, adjust if FDN response is too hot or too thin. Add a fixed attenuation factor (e.g., 0.6) on the ER->FDN feed if needed.

3. **Asymmetric diffuser count crossfading**
   - What we know: At Spread=0 both halves have identical diffuser counts. At Spread=100, one half has 1 diffuser and the other has 2.
   - What's unclear: How to smoothly transition between 1 and 2 diffusers (you can't have 1.5 allpass stages).
   - Recommendation: At Spread < 50, both halves use 2 decay diffusers (like standard Dattorro). At Spread >= 50, left half uses 1, right half uses 2. The coefficient of the "removed" diffuser can crossfade to 0 (passthrough) for a smoother transition.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pytest.ini` or `pyproject.toml` (existing) |
| Quick run command | `pytest tests/test_room_reverbs.py tests/test_dattorro_variants.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGO-02 | Small Room in registry, processes audio, produces stereo, stable | unit | `pytest tests/test_room_reverbs.py::TestSmallRoom -x` | No -- Wave 0 |
| ALGO-03 | Large Room in registry, processes audio, produces stereo, stable | unit | `pytest tests/test_room_reverbs.py::TestLargeRoom -x` | No -- Wave 0 |
| ALGO-04 | Chamber in registry, processes audio, produces stereo, stable | unit | `pytest tests/test_room_reverbs.py::TestChamber -x` | No -- Wave 0 |
| ALGO-06 | Single-Loop Tank in registry, processes audio, stereo, stable | unit | `pytest tests/test_dattorro_variants.py::TestSingleLoop -x` | No -- Wave 0 |
| ALGO-07 | Triple-Diffuser in registry, processes audio, stereo, stable | unit | `pytest tests/test_dattorro_variants.py::TestTripleDiffuser -x` | No -- Wave 0 |
| ALGO-08 | Asymmetric Tank in registry, processes audio, stereo, stable | unit | `pytest tests/test_dattorro_variants.py::TestAsymmetric -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_room_reverbs.py tests/test_dattorro_variants.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_early_reflections.py` -- covers EarlyReflections class in isolation
- [ ] `tests/test_room_reverbs.py` -- covers ALGO-02, ALGO-03, ALGO-04 (registry, param_specs, process, stability, presets, C export)
- [ ] `tests/test_dattorro_variants.py` -- covers ALGO-06, ALGO-07, ALGO-08 (registry, param_specs, process, stability, presets, C export)

## Sources

### Primary (HIGH confidence)
- Existing codebase: `fdn_reverb.py`, `dattorro_plate.py`, `filters.py` -- direct source for all reusable DSP primitives
- [CCRMA Stanford - Choice of Delay Lengths](https://ccrma.stanford.edu/~jos/pasp/Choice_Delay_Lengths.html) -- FDN delay selection criteria, mean free path formula
- [CCRMA Stanford - Early Reflections](https://ccrma.stanford.edu/~jos/pasp/Early_Reflections.html) -- tapped delay line ER implementation guidance

### Secondary (MEDIUM confidence)
- [Jon Pure Data Griesinger-style reverb](https://github.com/antonhornquist/jon-pd) -- concrete delay values for Dattorro's Griesinger-style topology
- [Dragonfly Room Reverb / DeepWiki](https://deepwiki.com/michaelwillis/dragonfly-reverb/4.2-room-reverb-guide) -- Moorer ER + Dattorro late reverb composition pattern
- [Signalsmith Audio - Let's Write a Reverb](https://signalsmith-audio.co.uk/writing/2021/lets-write-a-reverb/) -- diffusion stage design, feedback network patterns
- [Valhalla DSP - Reverbs: Diffusion, Allpass Delays, and Metallic Artifacts](https://valhalladsp.com/2011/01/21/reverbs-diffusion-allpass-delays-and-metallic-artifacts/) -- allpass cascade coloration prevention
- [Valhalla DSP - ValhallaRoom ER vs Early Energy](https://valhalladsp.com/2011/05/04/valhallaroom-early-reflections-versus-early-energy/) -- ER design philosophy

### Tertiary (LOW confidence)
- [KVR Audio - Dattorro reverb improvements](https://www.kvraudio.com/forum/viewtopic.php?t=564078) -- asymmetric tank stereo width discussion
- [Freeverb3 - Reverb Algorithm Tips](https://freeverb3-vst.sourceforge.io/tips/reverb.shtml) -- Griesinger/Lexicon 224 topology overview

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all primitives exist in codebase, no new libraries
- Room/Chamber architecture: HIGH -- composing EarlyReflections + FDNCore is well-understood
- ER tap patterns: MEDIUM -- physically motivated but need ear-tuning
- Griesinger single-loop: MEDIUM -- topology structure clear but exact values are educated estimates
- Triple-Diffuser: HIGH -- straightforward extension of existing Dattorro pattern
- Asymmetric Tank: MEDIUM -- concept clear, L/R ratio limits need experimentation
- Common pitfalls: HIGH -- well-documented in reverb design literature

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable domain, no fast-moving dependencies)
