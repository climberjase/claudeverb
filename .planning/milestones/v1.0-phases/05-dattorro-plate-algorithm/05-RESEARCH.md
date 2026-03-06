# Phase 5: Dattorro Plate Algorithm - Research

**Researched:** 2026-03-05
**Domain:** DSP algorithm implementation (Dattorro plate reverb)
**Confidence:** HIGH

## Summary

The Dattorro plate reverb is a well-documented algorithm from Jon Dattorro's 1997 JAES paper "Effect Design Part 1: Reverberator and Other Filters." The topology consists of 4 cascaded input allpass diffusers feeding a figure-eight tank with two crossed delay paths, each containing an embedded allpass filter, a one-pole lowpass damping filter, and delay lines. The design reference sample rate is 29761 Hz; all delay lengths must be rescaled to 48 kHz via `round(length * 48000 / 29761)`.

This phase is a single-algorithm implementation following the exact patterns established by Freeverb: subclass `ReverbAlgorithm`, use `__slots__`, reuse `DelayLine` and `AllpassFilter` primitives from `filters.py`, expose `param_specs` with 6 knobs and 2 switches, register in `ALGORITHM_REGISTRY`. The existing Streamlit UI auto-generates controls from `param_specs`, so no UI changes are needed.

**Primary recommendation:** Implement the Dattorro topology faithfully from the paper using the existing `DelayLine` (with fractional read for modulation) and `AllpassFilter` primitives, adding only a simple one-pole lowpass for bandwidth/damping and an LFO sine for tank modulation. Register as `"dattorro_plate"` in the algorithm registry.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Knob 1: Decay -- tank feedback coefficient
- Knob 2: Bandwidth -- input HF rolloff before tank
- Knob 3: Tank Damping -- in-loop HF decay
- Knob 4: Diffusion -- combined input + decay diffusion (single knob scales both)
- Knob 5: Pre-delay -- 0-100ms, using existing DelayLine
- Knob 6: Mod Depth -- LFO excursion in samples
- Switch 1: Freeze (-1) / Normal (0) / Shimmer (+1)
- Switch 2: Mono (-1) / Stereo (0) / Wide (+1)
- LFO shape: Sine, fixed ~1 Hz rate
- Mod behavior: Off at depth=0, active above
- Shimmer: Half-rate sample reading in tank feedback (~10-20% blend)
- Topology: Follow Dattorro 1997 paper exactly (4 input allpass diffusers, figure-eight tank)
- Rescale all delay lengths from 29761 Hz to 48 kHz
- Mono input -> stereo tank -> stereo output

### Claude's Discretion
- Exact delay line length values after 48 kHz rescaling
- Default knob values (0-100)
- Internal parameter scaling ranges (0-100 -> algorithm coefficients)
- Output gain/scaling to match Freeverb output level
- Whether to add DC blocker in tank loop
- Tank output tap positions and mix coefficients

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ALG-02 | Dattorro Plate reverb algorithm (figure-eight tank topology) with 6 knobs and 2 switches | Full topology documented below with delay lengths, coefficients, signal flow, knob mappings, and test strategy |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | existing | float32 array processing | Already in project, used by all algorithms |
| math | stdlib | sin/cos for LFO and coefficient calculation | Maps to C math.h, no external dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| claudeverb.algorithms.filters.DelayLine | existing | All delay lines (input diffusers, tank delays, pre-delay) | Every delay element in the topology |
| claudeverb.algorithms.filters.AllpassFilter | existing | Input diffuser allpasses and tank allpasses | 4 input diffusers + 2 tank allpasses (with custom feedback coefficients) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One-pole lowpass (inline) | Biquad filter | Biquad is overkill for simple bandwidth/damping one-pole; inline one-pole is what the paper specifies and is more C-portable |
| AllpassFilter from filters.py | Custom tank allpass | AllpassFilter works but feedback coefficient must be set per-instance; verify it supports negative feedback for decay_diffusion1 |

**Installation:** No new dependencies needed.

## Architecture Patterns

### Recommended File Structure
```
claudeverb/algorithms/
    dattorro_plate.py    # DattorroPlate class (single file, ~300-400 lines)
tests/
    test_dattorro_plate.py  # Matching test file
```

### Pattern 1: Dattorro Signal Flow (Figure-Eight Tank)
**What:** The complete processing pipeline from the 1997 paper
**When to use:** Every sample processed through the algorithm

```
Input (mono) -> Pre-delay -> Bandwidth filter (one-pole LP)
    -> Input Diffuser 1 (AP, len=142@29761, coeff=+0.75)
    -> Input Diffuser 2 (AP, len=107@29761, coeff=+0.75)
    -> Input Diffuser 3 (AP, len=379@29761, coeff=+0.625)
    -> Input Diffuser 4 (AP, len=277@29761, coeff=+0.625)
    -> Tank input (feeds both sides of figure-eight)

TANK (figure-eight, two crossed paths):
  Left half:
    tank_input + decay * cross_feedback_from_right
    -> Decay Diffusion AP 1 (len=672@29761, coeff=-decay_diffusion1)
    -> Delay Line 1 (len=4453@29761, modulated by LFO)
    -> Damping Filter (one-pole LP)
    -> * decay
    -> Decay Diffusion AP 2 (len=1800@29761, coeff=+decay_diffusion2)
    -> Delay Line 2 (len=3720@29761)
    -> output feeds right half as cross_feedback

  Right half (mirror):
    tank_input + decay * cross_feedback_from_left
    -> Decay Diffusion AP 3 (len=908@29761, coeff=-decay_diffusion1)
    -> Delay Line 3 (len=4217@29761, modulated by LFO, 180-deg phase)
    -> Damping Filter (one-pole LP)
    -> * decay
    -> Decay Diffusion AP 4 (len=2656@29761, coeff=+decay_diffusion2)
    -> Delay Line 4 (len=3163@29761)
    -> output feeds left half as cross_feedback

STEREO OUTPUT: Tapped from multiple points across both tank halves
```

### Pattern 2: Delay Length Rescaling
**What:** Convert all paper delay lengths from 29761 Hz to 48 kHz
**When to use:** During `_initialize()`, compute all delay lengths once

```python
# Reference sample rate from the paper
DATTORRO_SR = 29761

# Scale factor
SCALE = SAMPLE_RATE / DATTORRO_SR  # 48000 / 29761 = 1.6129...

# Input diffuser lengths at 29761 Hz (from paper)
INPUT_DIFFUSER_LENGTHS_29761 = [142, 107, 379, 277]
INPUT_DIFFUSER_COEFFS = [0.75, 0.75, 0.625, 0.625]

# Tank element lengths at 29761 Hz (from paper)
DECAY_DIFFUSER_1_LENGTHS_29761 = [672, 908]    # Left, Right
TANK_DELAY_1_LENGTHS_29761 = [4453, 4217]      # Left, Right (modulated)
DECAY_DIFFUSER_2_LENGTHS_29761 = [1800, 2656]  # Left, Right
TANK_DELAY_2_LENGTHS_29761 = [3720, 3163]      # Left, Right

def _scale_length(length_29761: int) -> int:
    return round(length_29761 * SAMPLE_RATE / DATTORRO_SR)
```

### Pattern 3: Output Tap Positions (from paper Table 2)
**What:** Stereo output is constructed by summing/differencing taps from multiple points in the tank
**When to use:** Each sample, after tank processing

```python
# Output tap positions at 29761 Hz (from paper)
# Left output taps (positive/negative signs from paper):
#   +tap from delay_line_3 at 266
#   +tap from delay_line_3 at 2974
#   -tap from decay_ap_4 at 1913
#   +tap from delay_line_4 at 1996
#   -tap from delay_line_1 at 1990
#   -tap from decay_ap_2 at 187
#   -tap from delay_line_2 at 1066

# Right output taps (mirror from opposite tank half):
#   +tap from delay_line_1 at 353
#   +tap from delay_line_1 at 3627
#   -tap from decay_ap_2 at 1228
#   +tap from delay_line_2 at 2673
#   -tap from delay_line_3 at 2111
#   -tap from decay_ap_4 at 335
#   -tap from delay_line_4 at 121
```

### Pattern 4: Follow Freeverb's Established Patterns
**What:** Match Freeverb's code structure exactly for consistency
**When to use:** All structural decisions

```python
class DattorroPlate(ReverbAlgorithm):
    __slots__ = (
        # DSP components
        "_input_diffusers",       # list of 4 AllpassFilter
        "_decay_diffusers",       # list of 4 AllpassFilter (2 per tank half)
        "_tank_delays",           # list of 4 DelayLine
        "_damping_filters",       # 2 one-pole LP state variables
        "_pre_delay_line",        # DelayLine
        # Parameters (0-100 knobs)
        "_decay", "_bandwidth", "_tank_damping",
        "_diffusion", "_pre_delay", "_mod_depth",
        "_switch1", "_switch2",
        # Scaled internal values
        "_decay_scaled", "_bandwidth_scaled", # etc.
        # LFO state
        "_lfo_phase",
        # Tank cross-feedback state
        "_tank_left_out", "_tank_right_out",
    )
```

### Anti-Patterns to Avoid
- **Dynamic allocation in process loop:** All delay lines and filters must be allocated in `_initialize()`, never during `_process_impl()`
- **Using numpy trig in hot path:** Use `math.sin()` for LFO calculation (maps to C `sinf()`)
- **Neglecting DC offset:** The figure-eight topology can accumulate DC offset over long decays; add a simple DC blocker (single-pole highpass at ~5 Hz)
- **Processing stereo input as two independent channels:** Dattorro is mono-in, stereo-out; sum stereo input to mono before the tank

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Delay lines | Custom circular buffer | `DelayLine` from `filters.py` | Already supports fractional read via linear interpolation (essential for modulation) |
| Allpass filters | Custom allpass | `AllpassFilter` from `filters.py` | Correct topology already implemented; just set feedback per-instance |
| Pre-delay | Separate buffer management | `DelayLine` from `filters.py` | Same as Freeverb, max 4800 samples |
| Output clipping | Manual bounds checking | `np.clip(output, -1.0, 1.0)` | Consistent with Freeverb pattern |

**Key insight:** The existing `DelayLine` with fractional read is the critical enabler for tank modulation. The LFO varies the read position by a fractional amount, and `DelayLine.read()` already handles linear interpolation. No new DSP primitives are needed.

## Common Pitfalls

### Pitfall 1: DC Offset Accumulation in Tank
**What goes wrong:** The figure-eight feedback loop can slowly accumulate DC offset, especially at high decay values near 1.0, causing the output to drift away from zero and eventually clip.
**Why it happens:** Small numerical asymmetries in the allpass filters and delay lines compound over thousands of feedback iterations.
**How to avoid:** Add a DC blocker (single-pole highpass at ~5 Hz) inside the tank loop, after the damping filter. Implementation: `y = x - x_prev + 0.9995 * y_prev` (simple first-order DC blocker).
**Warning signs:** Output slowly drifts to +1 or -1 when decay is set very high and processing long signals.

### Pitfall 2: Negative Feedback Coefficient for Decay Diffusion 1
**What goes wrong:** The paper specifies a negative coefficient for decay_diffusion_1 (typically -0.7). If the AllpassFilter only accepts positive feedback, the sign gets dropped and the reverb sounds wrong.
**Why it happens:** The existing AllpassFilter may handle negative feedback correctly, but this must be verified.
**How to avoid:** Test that `AllpassFilter` with negative feedback produces the expected allpass response. If it doesn't support negative values, either modify the filter or implement inline.
**Warning signs:** Reverb sounds metallic or ringy instead of smooth and diffuse.

### Pitfall 3: LFO Modulation Range Exceeding Delay Buffer
**What goes wrong:** If the LFO excursion pushes the read position beyond the delay line's buffer bounds, you get garbage values or index errors.
**Why it happens:** The modulated delay reads at `base_delay + lfo_offset`, and if `lfo_offset` is too large, the total exceeds `max_delay`.
**How to avoid:** Allocate tank delay lines with `max_delay = base_delay + max_excursion + margin`. The Mod Depth knob (0-100) should map to 0-16 samples excursion (conservative range for ~1 Hz modulation at 48 kHz).
**Warning signs:** Clicks, pops, or sudden silence during processing.

### Pitfall 4: Shimmer Feedback Instability
**What goes wrong:** Octave-up pitch shifting in the feedback path can cause energy buildup at high frequencies, leading to runaway oscillation.
**Why it happens:** Each pass through the tank doubles frequency content; without sufficient damping, energy accumulates.
**How to avoid:** Keep shimmer blend low (10-20%), and ensure the tank damping filter aggressively rolls off high frequencies when shimmer is active. Consider increasing damping automatically in shimmer mode.
**Warning signs:** High-pitched whine or oscillation that grows over time.

### Pitfall 5: Output Level Mismatch with Freeverb
**What goes wrong:** Dattorro output is much louder or quieter than Freeverb at similar settings.
**Why it happens:** Different topologies produce different gain structures. Freeverb uses `FIXED_GAIN = 0.015` at input; Dattorro output taps sum 7 values per channel.
**How to avoid:** Apply output scaling (~0.6 multiplier on summed taps, calibrate against Freeverb's impulse response peak level). The exact value is discretionary.
**Warning signs:** Users switching between algorithms get level jumps.

### Pitfall 6: Tank State Not Cross-Feeding Correctly
**What goes wrong:** The figure-eight topology requires the output of the left tank half to feed the right half's input, and vice versa. If both halves process independently, you get two parallel reverbs instead of one lush plate.
**Why it happens:** Processing both halves in the same loop iteration without properly using the previous iteration's output for cross-feedback.
**How to avoid:** Store each tank half's output from the previous sample. At each new sample, left half receives `tank_input + decay * right_prev`, and right half receives `tank_input + decay * left_prev`.
**Warning signs:** Reverb sounds like two separate mono reverbs panned L/R rather than a cohesive stereo field.

## Code Examples

### Delay Length Constants (rescaled to 48 kHz)

```python
# All values from Dattorro's 1997 paper, reference rate 29761 Hz
DATTORRO_SR = 29761

# Input allpass diffuser lengths at 29761 Hz
INPUT_AP_LENGTHS = [142, 107, 379, 277]
INPUT_AP_COEFFS = [0.75, 0.75, 0.625, 0.625]

# Tank elements at 29761 Hz [left_half, right_half]
DECAY_AP1_LENGTHS = [672, 908]       # decay diffusion allpass 1
TANK_DELAY1_LENGTHS = [4453, 4217]   # modulated delay
DECAY_AP2_LENGTHS = [1800, 2656]     # decay diffusion allpass 2
TANK_DELAY2_LENGTHS = [3720, 3163]   # final tank delay

# Rescaled to 48 kHz: round(length * 48000 / 29761)
# INPUT_AP: [229, 173, 612, 447]
# DECAY_AP1: [1084, 1465]
# TANK_DELAY1: [7188, 6805]
# DECAY_AP2: [2905, 4286]
# TANK_DELAY2: [6003, 5104]
```

### One-Pole Lowpass (Bandwidth and Damping Filters)

```python
# Inline one-pole lowpass for bandwidth filter and tank damping
# State: single float32 variable per filter instance
# Formula: y[n] = x[n] * coeff + y[n-1] * (1 - coeff)
# Where coeff is the bandwidth or (1 - damping) value

class OnePole:
    """Simple one-pole lowpass for Dattorro bandwidth/damping."""
    __slots__ = ("_coeff", "_state")

    def __init__(self, coeff: float = 0.9995) -> None:
        self._coeff = np.float32(coeff)
        self._state = np.float32(0.0)

    def process_sample(self, x: float) -> float:
        self._state = np.float32(x * self._coeff + self._state * (1.0 - self._coeff))
        return float(self._state)

    def reset(self) -> None:
        self._state = np.float32(0.0)
```

### DC Blocker

```python
# Simple first-order DC blocker (highpass at ~5 Hz)
# y[n] = x[n] - x[n-1] + R * y[n-1], where R = 1 - (2*pi*fc/fs)
# At fc=5Hz, fs=48000: R ~= 0.99935

class DCBlocker:
    """First-order DC blocking filter."""
    __slots__ = ("_r", "_x_prev", "_y_prev")

    def __init__(self, r: float = 0.99935) -> None:
        self._r = np.float32(r)
        self._x_prev = np.float32(0.0)
        self._y_prev = np.float32(0.0)

    def process_sample(self, x: float) -> float:
        y = x - self._x_prev + self._r * self._y_prev
        self._x_prev = np.float32(x)
        self._y_prev = np.float32(y)
        return float(y)

    def reset(self) -> None:
        self._x_prev = np.float32(0.0)
        self._y_prev = np.float32(0.0)
```

### LFO for Tank Modulation

```python
# Sine LFO at ~1 Hz, phase advances per sample
# LFO rate = 1.0 Hz -> phase_increment = 2 * pi * 1.0 / 48000
# Excursion controlled by mod_depth knob (0 = off, 100 = max ~16 samples)

import math

LFO_RATE_HZ = 1.0
LFO_PHASE_INC = 2.0 * math.pi * LFO_RATE_HZ / SAMPLE_RATE

# In process loop:
# lfo_val = math.sin(self._lfo_phase) * self._mod_depth_scaled
# self._lfo_phase += LFO_PHASE_INC
# if self._lfo_phase >= 2.0 * math.pi:
#     self._lfo_phase -= 2.0 * math.pi
# read_delay = base_delay + lfo_val  (fractional, handled by DelayLine.read())
```

### Shimmer (Half-Rate Read)

```python
# Octave-up via reading the delay line at half the normal delay
# This effectively doubles the pitch of the feedback signal
# Blend: shimmer_out = (1 - blend) * normal_out + blend * octave_up_out
# blend = 0.15 (15%, subtle)

SHIMMER_BLEND = 0.15

# In tank processing, when switch1 == 1 (shimmer mode):
# normal_read = delay_line.read(base_delay + lfo_offset)
# octave_read = delay_line.read((base_delay + lfo_offset) / 2.0)
# tank_sample = (1.0 - SHIMMER_BLEND) * normal_read + SHIMMER_BLEND * octave_read
```

### Recommended Parameter Scaling

```python
def _scale_params(self) -> None:
    # Decay: 0-100 -> 0.1 to 0.9999 (exponential feel)
    # Low values = short slap, high = near-infinite sustain
    self._decay_scaled = 0.1 + (self._decay / 100.0) ** 1.5 * 0.8999

    # Bandwidth: 0-100 -> 0.1 to 0.9999 (one-pole LP coefficient)
    # Low = dark input, high = bright input
    self._bandwidth_scaled = 0.1 + (self._bandwidth / 100.0) * 0.8999

    # Tank Damping: 0-100 -> 0.0 to 0.9 (damping amount, 0=no damping)
    # The one-pole in the loop uses (1 - damping) as coefficient
    self._damping_scaled = (self._tank_damping / 100.0) * 0.9

    # Diffusion: 0-100 -> scales both input and decay diffusion
    # Input diff: 0.0 to 0.75 (knob 0->0, knob 100->paper defaults)
    # Decay diff1: 0.0 to 0.7, Decay diff2: 0.0 to 0.5
    diff_scale = self._diffusion / 100.0
    self._input_diff1_scaled = diff_scale * 0.75
    self._input_diff2_scaled = diff_scale * 0.625
    self._decay_diff1_scaled = diff_scale * 0.7
    self._decay_diff2_scaled = diff_scale * 0.5

    # Pre-delay: 0-100 -> 0 to 4800 samples (0-100ms)
    self._pre_delay_samples = int((self._pre_delay / 100.0) * 0.1 * SAMPLE_RATE)

    # Mod Depth: 0-100 -> 0.0 to 16.0 samples excursion
    self._mod_depth_scaled = (self._mod_depth / 100.0) * 16.0
```

### Recommended Default Knob Values

```python
# Defaults that produce a pleasant medium plate reverb:
_decay = 60         # Moderate decay (~2s RT60)
_bandwidth = 70     # Bright but not harsh
_tank_damping = 30  # Gentle HF rolloff in tail
_diffusion = 80     # High diffusion for smooth wash
_pre_delay = 10     # Slight pre-delay (~10ms)
_mod_depth = 30     # Gentle modulation for lushness
_switch1 = 0        # Normal mode
_switch2 = 0        # Stereo mode
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static delay lines only | Modulated delay lines with interpolation | Dattorro 1997 | Essential for lush plate character; prevents metallic coloration |
| Integer delay reads | Fractional delay reads (linear interpolation) | Standard since 1990s | Already supported by project's DelayLine |

**Deprecated/outdated:**
- None applicable; the Dattorro topology is a classic design that hasn't changed. The 1997 paper remains the authoritative reference.

## Open Questions

1. **AllpassFilter negative feedback support**
   - What we know: The existing AllpassFilter accepts a `feedback` parameter. The Dattorro topology requires negative feedback (-0.7) for decay_diffusion_1.
   - What's unclear: Whether `AllpassFilter.feedback = -0.7` works correctly or if the implementation assumes positive values.
   - Recommendation: Test in first task. If negative feedback doesn't work, implement the allpass inline for tank allpasses (the formula is simple: 3 lines of code).

2. **Exact output gain calibration**
   - What we know: Freeverb uses `FIXED_GAIN = 0.015` at input. Dattorro summing 7 taps per channel needs output scaling.
   - What's unclear: The exact multiplier to match Freeverb's output level.
   - Recommendation: Start with 0.6 output multiplier (from reference implementations), calibrate by comparing impulse response peak levels between Freeverb and DattorroPlate.

3. **DelayLine read position with fractional modulation**
   - What we know: `DelayLine.read(delay)` supports fractional delay values with linear interpolation.
   - What's unclear: Whether the read position calculation works correctly when the delay value is slightly larger than the base delay (base_delay + lfo_excursion).
   - Recommendation: Allocate delay lines with `max_delay = base_delay + max_excursion + 2` to provide safety margin for interpolation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none (uses pytest defaults, existing conftest.py) |
| Quick run command | `pytest tests/test_dattorro_plate.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALG-02.1 | DattorroPlate instantiates and appears in registry | unit | `pytest tests/test_dattorro_plate.py::test_registry -x` | Wave 0 |
| ALG-02.2 | param_specs returns 6 knobs + 2 switches | unit | `pytest tests/test_dattorro_plate.py::test_param_specs -x` | Wave 0 |
| ALG-02.3 | Processes mono impulse, produces reverb tail | unit | `pytest tests/test_dattorro_plate.py::test_process_mono_impulse -x` | Wave 0 |
| ALG-02.4 | Processes stereo input, produces (2,N) output | unit | `pytest tests/test_dattorro_plate.py::test_process_stereo -x` | Wave 0 |
| ALG-02.5 | All extreme knob positions produce stable output (no NaN/inf) | unit | `pytest tests/test_dattorro_plate.py::test_extreme_knobs_stable -x` | Wave 0 |
| ALG-02.6 | No DC offset accumulation at high decay | unit | `pytest tests/test_dattorro_plate.py::test_no_dc_offset -x` | Wave 0 |
| ALG-02.7 | Freeze mode sustains reverb tail | unit | `pytest tests/test_dattorro_plate.py::test_freeze_mode -x` | Wave 0 |
| ALG-02.8 | Shimmer mode produces octave-shifted content | unit | `pytest tests/test_dattorro_plate.py::test_shimmer_mode -x` | Wave 0 |
| ALG-02.9 | Reset produces identical output | unit | `pytest tests/test_dattorro_plate.py::test_reset_deterministic -x` | Wave 0 |
| ALG-02.10 | Output differs from Freeverb (audibly distinct character) | integration | `pytest tests/test_dattorro_plate.py::test_differs_from_freeverb -x` | Wave 0 |
| ALG-02.11 | Modulation produces time-varying IR (not static comb) | unit | `pytest tests/test_dattorro_plate.py::test_modulation_varies_ir -x` | Wave 0 |
| ALG-02.12 | Mono/Stereo/Wide switch modes work correctly | unit | `pytest tests/test_dattorro_plate.py::test_stereo_modes -x` | Wave 0 |
| ALG-02.13 | Output clipped to [-1.0, 1.0] | unit | `pytest tests/test_dattorro_plate.py::test_output_clipped -x` | Wave 0 |
| ALG-02.14 | Delay lengths correctly scaled from 29761 to 48000 Hz | unit | `pytest tests/test_dattorro_plate.py::test_delay_scaling -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_dattorro_plate.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dattorro_plate.py` -- covers ALG-02 (all subtests above)

## Sources

### Primary (HIGH confidence)
- [Dattorro 1997 Paper (CCRMA Stanford)](https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf) - Original topology, delay values, coefficients, output tap structure
- Existing codebase: `claudeverb/algorithms/freeverb.py` - Pattern reference for ReverbAlgorithm subclass structure
- Existing codebase: `claudeverb/algorithms/filters.py` - DelayLine (fractional read), AllpassFilter primitives

### Secondary (MEDIUM confidence)
- [Louis Couka Python implementation](https://www.louiscouka.com/code/datorro-reverb-implementation/) - Verified delay lengths (142, 107, 379, 277 input; 672, 4453, 1800, 3720, 908, 4217, 2656, 3163 tank), output tap positions, coefficients
- [GTCMTold/plate-reverb GitHub](https://github.com/GTCMTold/plate-reverb/blob/master/reverb.py) - Python reference implementation with modulation functions
- [el-visio/dattorro-verb GitHub](https://github.com/el-visio/dattorro-verb) - C reference implementation

### Tertiary (LOW confidence)
- [Valley Plateau (VCV Rack)](https://valleyaudio.github.io/rack/plateau/) - General description of Dattorro-based reverb with LFO modulation approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses only existing project primitives, no new dependencies
- Architecture: HIGH - Dattorro topology is well-documented in the original paper and multiple reference implementations agree on delay values and signal flow
- Pitfalls: HIGH - DC offset, negative feedback, modulation bounds, and level matching are well-known issues documented across multiple implementations
- Shimmer: MEDIUM - Half-rate read approach is simple and C-portable, but exact blend level and interaction with damping needs calibration during implementation

**Research date:** 2026-03-05
**Valid until:** Indefinite (classic algorithm, stable domain)
