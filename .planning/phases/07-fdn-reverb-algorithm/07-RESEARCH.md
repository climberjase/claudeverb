# Phase 7: FDN Reverb Algorithm - Research

**Researched:** 2026-03-11
**Domain:** Feedback Delay Network (FDN) reverb algorithm design and implementation
**Confidence:** HIGH

## Summary

Feedback Delay Networks are the gold standard for high-quality algorithmic reverb, offering dense, colorless decay that is fundamentally different from Freeverb's parallel comb topology or Dattorro's figure-eight tank. A 4-channel FDN with a Hadamard mixing matrix provides optimal inter-channel scattering with guaranteed stability (lossless when normalized by 1/sqrt(N)), and can be implemented using only additions and subtractions via the Fast Walsh-Hadamard Transform.

The key design choices are: (1) coprime delay line lengths in the 500-2500 sample range at 48 kHz for smooth modal density, (2) per-channel one-pole lowpass damping filters in the feedback loop for frequency-dependent decay, (3) input diffusion via 2-4 cascaded allpass filters to smear transients before the network, and (4) slow LFO modulation of delay times to break metallic resonances. All of these map cleanly to the existing claudeverb filter primitives (DelayLine, AllpassFilter, OnePole, DCBlocker).

**Primary recommendation:** Implement FDNCore as a composable class with a clean process_sample() API, then wrap it in an FDNReverb ReverbAlgorithm subclass. This enables Phase 8 reuse where Room/Chamber algorithms compose FDNCore with early-reflection stages.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Knob 1: Decay Time** -- maps 0-100 to decay time range (e.g., 0.2s to 20s), most intuitive control
- **Knob 2: Size** -- scales all delay line lengths independently from decay, controls perceived room dimension
- **Knob 3: Damping** -- HF rolloff in feedback loop (dark-to-bright)
- **Knob 4: Modulation** -- chorus-like delay modulation depth for lushness and metallic coloration reduction
- **Knob 5: Mix** -- wet/dry (engine forces mix=100 internally, UI handles blend)
- **Knob 6: Pre-Delay** -- delay before reverb onset
- **Switch 1: Freeze** -- Freeze/Normal/Bright (consistent with Freeverb)
- **Switch 2: Stereo Mode** -- Mono/Stereo/Wide (consistent with Freeverb)
- **Tonal Character:** smooth and dense, even colorless decay -- "transparent concert hall" sound
- **FDN Topology:** 4-channel Hadamard mixing matrix (4x4), coprime delay line lengths
- **Input diffusers:** 2-4 allpass filters before the FDN to smear input and reduce plinky attacks
- **Modulated delays:** slow LFO on delay times to break up metallic resonances
- **Stereo output:** channels 0+2 to Left, channels 1+3 to Right, width knob controls cross-feed
- **DC blockers** in feedback loop to prevent DC buildup (reuse DCBlocker from dattorro_plate.py)
- **Per-channel damping filters** (OnePole lowpass) in the feedback path
- **Phase 8 Reuse Architecture:** Composable design with FDNCore class + clean process() API
- **C Export Support:** Include to_c_struct() and to_c_process_fn() methods following Freeverb's pattern
- **Presets:** Include 3-4 presets (Small Hall, Large Hall, Cathedral, Ambient)
- **Preset pattern:** Follow dattorro_presets.py pattern (dict of param values feeding update_params())

### Claude's Discretion
- Exact coprime delay line lengths (at 48 kHz)
- Number of input diffusers (2, 3, or 4) and their delay lengths
- LFO rate and maximum modulation depth range
- Per-band decay implementation (crossover frequency, LF decay mechanism)
- Hadamard matrix normalization factor
- Exact preset parameter values (tuned by ear/metrics)
- Input distribution strategy (how mono input maps to 4 FDN channels)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ALGO-01 | User can apply FDN reverb (4-channel Hadamard, coprime delays, per-band decay) to audio | Full FDN architecture researched: Hadamard matrix construction, coprime delay selection, per-band decay via OnePole damping, composable FDNCore + FDNReverb pattern, registry integration, preset system |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | existing | float32 arrays, buffer operations | Already used throughout claudeverb |
| math | stdlib | sin/cos for LFO, pi, sqrt | C-portable math functions (maps to math.h) |

### Supporting (Reuse from existing codebase)
| Component | Location | Purpose | How Used |
|-----------|----------|---------|----------|
| DelayLine | filters.py | Circular buffer with fractional delay | FDN delay channels + input diffuser delays |
| AllpassFilter | filters.py | Schroeder allpass | Input diffusion stage (2-4 cascaded) |
| OnePole | dattorro_plate.py | One-pole lowpass | Per-channel HF damping in feedback loop |
| DCBlocker | dattorro_plate.py | DC blocking filter | Prevents DC buildup in feedback loop |
| Biquad | filters.py | Biquad EQ filter | Low shelf for per-band LF decay control |
| ReverbAlgorithm | base.py | Abstract base class | FDNReverb inherits from this |

### No New Dependencies Required
All FDN components map to existing filter primitives. No external DSP libraries needed.

## Architecture Patterns

### Recommended Project Structure
```
claudeverb/algorithms/
├── fdn_reverb.py          # FDNCore + FDNReverb classes
├── fdn_presets.py          # FDN preset definitions
├── filters.py              # (existing) DelayLine, AllpassFilter, etc.
├── dattorro_plate.py       # (existing) OnePole, DCBlocker reused from here
└── __init__.py             # Add "fdn" -> FDNReverb to ALGORITHM_REGISTRY
```

### Pattern 1: Composable FDNCore + Algorithm Wrapper

**What:** Separate the pure FDN delay network logic (FDNCore) from the ReverbAlgorithm interface (FDNReverb). FDNCore handles the 4-channel feedback network, Hadamard mixing, damping, modulation. FDNReverb wraps FDNCore with input diffusion, pre-delay, stereo output, and the param_specs interface.

**When to use:** Always for this phase. This is a locked decision for Phase 8 reuse.

**FDNCore API:**
```python
class FDNCore:
    """4-channel Feedback Delay Network core.

    Reusable by Phase 8 Room/Chamber algorithms.
    """
    __slots__ = (
        "_delay_lines", "_damping_filters", "_dc_blockers",
        "_lfo_phase", "_lfo_rate", "_mod_depth",
        "_decay_gain", "_base_delays", "_delay_scale",
        "_channel_state",
    )

    def __init__(self, base_delays: list[int], sample_rate: int = 48000):
        """Initialize with 4 coprime delay lengths."""
        ...

    def process_sample(self, inputs: list[float]) -> list[float]:
        """Process one sample through the 4-channel FDN.

        Args:
            inputs: 4-element list, one input per channel.
        Returns:
            4-element list of channel outputs.
        """
        ...

    def set_decay(self, decay_gain: float) -> None: ...
    def set_damping(self, damping_coeff: float) -> None: ...
    def set_modulation(self, depth: float, rate: float) -> None: ...
    def set_size(self, scale: float) -> None: ...
    def reset(self) -> None: ...
```

**FDNReverb wrapper:**
```python
class FDNReverb(ReverbAlgorithm):
    """FDN Reverb algorithm -- 4-channel Hadamard with input diffusion."""

    def __init__(self):
        # Create FDNCore, input diffusers, pre-delay, etc.
        self._fdn_core = FDNCore(BASE_DELAYS)
        self._input_diffusers = [AllpassFilter(...), ...]
        self._pre_delay_line = DelayLine(...)
        self._initialize()

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        # 1. Sum to mono if stereo
        # 2. Pre-delay
        # 3. Input diffusion (cascade through allpasses)
        # 4. Distribute to 4 FDN channels
        # 5. FDNCore.process_sample() per sample
        # 6. Tap outputs: ch0+ch2 -> L, ch1+ch3 -> R
        # 7. Width crossmix
        # 8. Hard clip
        ...
```

### Pattern 2: 4x4 Hadamard Mixing (Fast Walsh-Hadamard Transform)

**What:** The 4x4 Hadamard matrix multiply can be done with 8 additions and no multiplications (except the final 1/2 scaling), using two butterfly stages.

**Implementation:**
```python
def hadamard_4(a: float, b: float, c: float, d: float) -> tuple[float, float, float, float]:
    """4x4 Hadamard matrix multiplication via butterfly.

    H4 = (1/2) * [[1, 1, 1, 1],
                   [1,-1, 1,-1],
                   [1, 1,-1,-1],
                   [1,-1,-1, 1]]

    Normalization: 1/sqrt(4) = 1/2 for lossless (unitary) operation.
    """
    # Stage 1: pairs
    a1 = a + b
    b1 = a - b
    c1 = c + d
    d1 = c - d
    # Stage 2: cross-pairs
    out_a = (a1 + c1) * 0.5
    out_b = (b1 + d1) * 0.5
    out_c = (a1 - c1) * 0.5
    out_d = (b1 - d1) * 0.5
    return out_a, out_b, out_c, out_d
```

**Why 1/2 normalization:** For a 4x4 Hadamard, the normalization factor is 1/sqrt(N) = 1/sqrt(4) = 1/2. This makes the matrix orthogonal (unitary), ensuring the FDN is lossless -- energy is perfectly preserved through the mixing matrix. This is the fundamental stability guarantee.

### Pattern 3: Decay Time to Feedback Gain Conversion

**What:** Convert a desired RT60 decay time to per-sample feedback gain, accounting for delay line length.

**Formula:**
```python
def rt60_to_gain(rt60_seconds: float, delay_samples: int, sample_rate: int = 48000) -> float:
    """Convert RT60 decay time to per-loop feedback gain.

    Based on: gain^(loops_to_rt60) = 0.001  (60 dB down)
    Where loops_to_rt60 = rt60_seconds * sample_rate / delay_samples
    Therefore: gain = 10^(-3 * delay_samples / (rt60_seconds * sample_rate))
    """
    if rt60_seconds <= 0:
        return 0.0
    loops = rt60_seconds * sample_rate / delay_samples
    return 10.0 ** (-3.0 / loops)
```

**Why this matters:** The decay knob (0-100) maps to RT60 (0.2s-20s), and each delay channel needs its own gain computed from this formula because channels have different delay lengths. This is how "decay" and "size" remain independent -- size changes delay lengths, then gains are recomputed to maintain the same RT60.

### Pattern 4: Per-Band Decay (Damping + LF Control)

**What:** Frequency-dependent decay using a one-pole lowpass in each feedback channel (HF damping) plus a low-shelf Biquad for independent LF decay control.

**Implementation approach:**
```python
# In each feedback channel's per-sample processing:
# 1. OnePole lowpass (HF damping, controlled by Damping knob)
sample = self._damping_filters[ch].process_sample(sample)
# 2. Optional: Biquad low-shelf for LF decay (internal, not a knob)
#    Applied subtly to make LF decay slightly faster than mid,
#    preventing low-end buildup in long decays
```

**Recommendation (Claude's discretion):** Use OnePole lowpass for the primary HF damping (knob-controlled). For LF control, apply a fixed low-shelf Biquad at ~200 Hz with mild attenuation (-1 to -3 dB) in the feedback loop. This prevents low-frequency buildup without requiring a dedicated knob. The damping knob controls HF rolloff (the perceptually dominant effect).

### Pattern 5: Input Distribution to 4 Channels

**What:** How mono input maps to the 4 FDN channels.

**Recommendation (Claude's discretion):** Feed the diffused mono signal equally to all 4 channels with gain 1.0 each (the Hadamard matrix will handle redistribution). This is the simplest approach and works well because the input diffusers have already smeared the signal temporally. Equal injection produces the densest initial response.

### Anti-Patterns to Avoid
- **Computing Hadamard as matrix multiply:** Use the butterfly (FWHT) pattern instead -- 8 adds vs 16 multiplies+adds. More efficient and maps cleanly to C.
- **Using the same delay length for all channels:** Defeats the purpose of FDN. Delays MUST be coprime for smooth modal density.
- **Feedback gain > 1.0:** Will cause exponential blowup. The Hadamard normalization (1/2) keeps the lossless part unitary; the per-channel decay gain must be <= 1.0.
- **Modulating delay lines without extra buffer space:** DelayLine max_delay must be larger than the nominal delay to accommodate LFO excursion. Add max_mod_excursion + margin to max_delay.
- **Applying damping outside the feedback loop:** Damping must be inside the loop (between delay output and Hadamard mixing input) to create frequency-dependent decay. Outside the loop it only affects the output spectrum, not the decay rate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circular buffer delay | Custom ring buffer | `DelayLine` from filters.py | Already handles fractional delay, write/read/reset |
| Allpass diffusion | Custom allpass | `AllpassFilter` from filters.py | Correct Schroeder topology already implemented |
| One-pole lowpass | Custom IIR filter | `OnePole` from dattorro_plate.py | Exact same use case (damping in feedback loop) |
| DC blocking | Custom highpass | `DCBlocker` from dattorro_plate.py | Tuned for 48 kHz, proven in Dattorro |
| Low-shelf filter | Custom shelf | `Biquad.low_shelf()` from filters.py | Bristow-Johnson cookbook, already tested |
| Hadamard 4x4 | Full matrix class | Inline butterfly function | 8 adds + 4 multiplies, too simple for abstraction overhead |

**Key insight:** Every DSP primitive needed for the FDN already exists in the codebase. The only new code is the FDN topology (how these primitives connect) and the parameter mapping logic.

## Common Pitfalls

### Pitfall 1: DC Buildup at High Decay
**What goes wrong:** At decay=95+, tiny DC offsets accumulate through the feedback loop, causing the output to drift toward +1 or -1 and eventually clip permanently.
**Why it happens:** OnePole and Hadamard are not DC-blocking by nature. Even floating-point rounding introduces DC bias.
**How to avoid:** Place DCBlocker in each feedback channel AFTER the damping filter but BEFORE the Hadamard mixing. Already proven in Dattorro.
**Warning signs:** `np.mean(output[-24000:])` drifts above 0.01 on long impulse responses.

### Pitfall 2: Metallic Ringing / Tonal Coloration
**What goes wrong:** The FDN output has a pitched, metallic quality instead of smooth noise-like decay.
**Why it happens:** Delay lines have rational length ratios (common factors), creating reinforced modal patterns.
**How to avoid:** Use strictly coprime delay lengths. Add LFO modulation to delay times (even 1-2 samples of excursion helps). Input diffusion (allpass cascade) smears the input energy across time.
**Warning signs:** Audible pitch in the reverb tail, especially on percussive input.

### Pitfall 3: Instability at Extreme Parameters
**What goes wrong:** Output explodes to NaN/inf when multiple knobs are at extremes (e.g., decay=100, size=100, damping=0).
**Why it happens:** Feedback gain reaches or exceeds 1.0 when damping is zero and decay is maximum, especially if the Hadamard normalization is wrong.
**How to avoid:** Clamp the per-channel gain to never exceed 0.9999. In freeze mode, set gain to exactly 1.0 but zero the input (Freeverb pattern). Test ALL extreme knob combinations.
**Warning signs:** Test `test_extreme_knobs_stable` fails with NaN or values outside [-1, 1].

### Pitfall 4: Modulation Causing Delay Line Underrun
**What goes wrong:** LFO pushes the read position past the buffer boundary, reading garbage or wrapping incorrectly.
**Why it happens:** DelayLine max_delay was set to the nominal delay length without accounting for modulation excursion.
**How to avoid:** Allocate `max_delay = nominal_delay + max_mod_excursion + 2` (safety margin). Clamp the modulated read delay to `max(1.0, delay)`.
**Warning signs:** Clicks, pops, or sudden amplitude spikes in the output.

### Pitfall 5: Size Knob Not Sounding Different
**What goes wrong:** Changing the Size knob doesn't produce an audible difference because delay lengths change but decay time also changes.
**Why it happens:** If feedback gain is fixed (not recomputed), longer delays mean more loops = longer RT60, confounding size with decay.
**How to avoid:** When size changes delay lengths, immediately recompute the per-channel feedback gains using rt60_to_gain() with the current decay time and new delay lengths. This keeps RT60 constant while changing the room character.
**Warning signs:** Size and Decay knobs sound identical.

## Code Examples

### FDN Core Processing Loop (per sample)
```python
# Source: Standard FDN design from JOS "Physical Audio Signal Processing"
# + Signalsmith Audio "Let's Write A Reverb" implementation guidance

def _process_sample_core(self, input_sample: float) -> tuple[float, float, float, float]:
    """Process one sample through the 4-channel FDN."""
    # Read from delay lines (with modulation)
    lfo_val = math.sin(self._lfo_phase) * self._mod_depth
    outputs = []
    for ch in range(4):
        mod = lfo_val if ch % 2 == 0 else -lfo_val  # alternating phase
        read_delay = max(1.0, self._current_delays[ch] + mod)
        outputs.append(self._delay_lines[ch].read(read_delay))

    # Advance LFO
    self._lfo_phase += self._lfo_phase_inc
    if self._lfo_phase >= 2.0 * math.pi:
        self._lfo_phase -= 2.0 * math.pi

    # Per-channel processing: damping -> DC block -> decay gain
    for ch in range(4):
        outputs[ch] = self._damping_filters[ch].process_sample(outputs[ch])
        outputs[ch] = self._dc_blockers[ch].process_sample(outputs[ch])
        outputs[ch] *= self._channel_gains[ch]

    # Hadamard mixing (lossless, butterfly implementation)
    a, b, c, d = outputs
    a1 = a + b; b1 = a - b; c1 = c + d; d1 = c - d
    mixed = [
        (a1 + c1) * 0.5,
        (b1 + d1) * 0.5,
        (a1 - c1) * 0.5,
        (b1 - d1) * 0.5,
    ]

    # Write back to delay lines (input + mixed feedback)
    for ch in range(4):
        self._delay_lines[ch].write(input_sample + mixed[ch])

    return tuple(outputs)  # pre-mixing outputs for tapping
```

### Coprime Delay Line Lengths (Recommended Values)
```python
# Source: Research-derived, verified coprime at 48 kHz
# Chosen for: mutual coprimality, good modal spread, ~10-50ms range
# GCD of any pair = 1
BASE_DELAYS = [601, 773, 1009, 1249]  # samples at 48 kHz
# ~12.5ms, ~16.1ms, ~21.0ms, ~26.0ms
# All prime numbers -> guaranteed coprime
# Size knob scales these by 0.5x to 2.0x
```

### Stereo Output Tapping
```python
# Source: CONTEXT.md locked decision
# Channels 0+2 -> Left, Channels 1+3 -> Right
out_l = outputs[0] + outputs[2]
out_r = outputs[1] + outputs[3]

# Width crossmix (same pattern as Freeverb/Dattorro)
width = 1.0  # stereo mode default
if wide_mode:
    width = 2.0
wet1 = (1.0 + width) / 2.0
wet2 = (1.0 - width) / 2.0
final_l = out_l * wet1 + out_r * wet2
final_r = out_r * wet1 + out_l * wet2
```

### Preset Pattern
```python
# Source: dattorro_presets.py pattern
FDN_PRESETS: dict[str, dict] = {
    "Small Hall": {
        "decay_time": 35, "size": 30, "damping": 55,
        "modulation": 20, "mix": 60, "pre_delay": 10,
        "switch1": 0, "switch2": 0,
    },
    "Large Hall": {
        "decay_time": 70, "size": 65, "damping": 35,
        "modulation": 40, "mix": 50, "pre_delay": 25,
        "switch1": 0, "switch2": 1,
    },
    # ... Cathedral, Ambient
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parallel comb filters (Freeverb) | FDN with orthogonal mixing | ~2000s onward | Dense, colorless decay vs. metallic combs |
| Fixed feedback coefficient | RT60-derived per-delay gain | Standard practice | Size and decay become independent controls |
| Static delay lines | LFO-modulated delays | Common since ~2005 | Breaks up metallic modes, adds lushness |
| Single-band decay | Per-band (multi-rate) decay | JOS/Jot standard | HF and LF decay independently for realism |

**No deprecated approaches in this domain** -- FDN reverb design is mature and stable. The 4-channel Hadamard approach has been standard since Jot (1991) and Smith (JOS PASP textbook).

## Open Questions

1. **Exact LFO rate and modulation depth range**
   - What we know: Slow LFO (0.5-2 Hz) with small excursion (1-16 samples) is standard
   - What's unclear: Optimal rate for "transparent" character vs. Dattorro's 1 Hz
   - Recommendation: Use 0.7 Hz base rate, max excursion 12 samples at knob=100. Slightly different from Dattorro's 1 Hz to create distinct character.

2. **Number of input diffusers**
   - What we know: 2-4 allpass filters are standard for input diffusion
   - What's unclear: Whether 2 is enough or 4 is needed for the "dense from the start" requirement
   - Recommendation: Use 3 input diffusers with delays [149, 233, 347] (all prime, increasing). Three provides good density without excessive smearing of transients.

3. **LF decay mechanism details**
   - What we know: Per-band decay is needed; OnePole handles HF
   - What's unclear: Whether a separate Biquad low-shelf is worth the complexity vs. just accepting slightly longer LF decay
   - Recommendation: Start with OnePole HF damping only. If LF buildup is audible in testing, add a mild Biquad.low_shelf(200, -2.0) in the feedback loop. This can be a tuning decision during implementation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml or pytest.ini (existing setup) |
| Quick run command | `python -m pytest tests/test_fdn_reverb.py -x` |
| Full suite command | `python -m pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGO-01.1 | FDN appears in ALGORITHM_REGISTRY as "fdn" | unit | `pytest tests/test_fdn_reverb.py::test_registry -x` | No - Wave 0 |
| ALGO-01.2 | param_specs returns 6 knobs + 2 switches | unit | `pytest tests/test_fdn_reverb.py::test_param_specs -x` | No - Wave 0 |
| ALGO-01.3 | Mono impulse -> stereo output with reverb tail | unit | `pytest tests/test_fdn_reverb.py::test_process_mono_impulse -x` | No - Wave 0 |
| ALGO-01.4 | Stereo input -> stereo output | unit | `pytest tests/test_fdn_reverb.py::test_process_stereo -x` | No - Wave 0 |
| ALGO-01.5 | All extreme knob combos stable (no NaN/inf) | unit | `pytest tests/test_fdn_reverb.py::test_extreme_knobs_stable -x` | No - Wave 0 |
| ALGO-01.6 | No DC offset at high decay | unit | `pytest tests/test_fdn_reverb.py::test_no_dc_offset -x` | No - Wave 0 |
| ALGO-01.7 | Freeze mode sustains energy | unit | `pytest tests/test_fdn_reverb.py::test_freeze_mode -x` | No - Wave 0 |
| ALGO-01.8 | Reset produces deterministic output | unit | `pytest tests/test_fdn_reverb.py::test_reset_deterministic -x` | No - Wave 0 |
| ALGO-01.9 | Output differs from Freeverb | unit | `pytest tests/test_fdn_reverb.py::test_differs_from_freeverb -x` | No - Wave 0 |
| ALGO-01.10 | Output differs from Dattorro | unit | `pytest tests/test_fdn_reverb.py::test_differs_from_dattorro -x` | No - Wave 0 |
| ALGO-01.11 | Modulation varies impulse response | unit | `pytest tests/test_fdn_reverb.py::test_modulation_varies_ir -x` | No - Wave 0 |
| ALGO-01.12 | Stereo modes (mono/stereo/wide) | unit | `pytest tests/test_fdn_reverb.py::test_stereo_modes -x` | No - Wave 0 |
| ALGO-01.13 | Output clipped to [-1, 1] | unit | `pytest tests/test_fdn_reverb.py::test_output_clipped -x` | No - Wave 0 |
| ALGO-01.14 | Hadamard butterfly produces correct results | unit | `pytest tests/test_fdn_reverb.py::test_hadamard_butterfly -x` | No - Wave 0 |
| ALGO-01.15 | Size knob changes delay lengths | unit | `pytest tests/test_fdn_reverb.py::test_size_changes_delays -x` | No - Wave 0 |
| ALGO-01.16 | All knobs produce audible changes | unit | `pytest tests/test_fdn_reverb.py::test_all_knobs_audible -x` | No - Wave 0 |
| ALGO-01.17 | FDNCore composable (clean API) | unit | `pytest tests/test_fdn_reverb.py::test_fdn_core_composable -x` | No - Wave 0 |
| ALGO-01.18 | Presets load and produce stable output | unit | `pytest tests/test_fdn_reverb.py::test_presets -x` | No - Wave 0 |
| ALGO-01.19 | C struct/process generation | unit | `pytest tests/test_fdn_reverb.py::test_c_export -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_fdn_reverb.py -x`
- **Per wave merge:** `python -m pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_fdn_reverb.py` -- covers ALGO-01 subtests 1-19
- [ ] Framework install: None needed -- pytest already configured and 186 tests pass

## Sources

### Primary (HIGH confidence)
- [JOS Physical Audio Signal Processing - FDN Reverberation](https://ccrma.stanford.edu/~jos/pasp/FDN_Reverberation.html) - FDN theory, delay selection, feedback matrix properties
- [JOS PASP - Choice of Lossless Feedback Matrix](https://www.dsprelated.com/freebooks/pasp/Choice_Lossless_Feedback_Matrix.html) - Hadamard matrix H4, normalization 1/sqrt(N), butterfly implementation
- [Signalsmith Audio - Let's Write A Reverb](https://signalsmith-audio.co.uk/writing/2021/lets-write-a-reverb/) - Practical FDN implementation: diffusion stages, Hadamard vs Householder, modulation strategy, stereo output
- Existing codebase (filters.py, dattorro_plate.py, freeverb.py) - All reusable DSP primitives and established patterns verified by reading source

### Secondary (MEDIUM confidence)
- [KVR Forum - Understanding Hadamard Matrices in Reverb](https://www.kvraudio.com/forum/viewtopic.php?t=423754) - Butterfly computation details, normalization explanation
- [KVR Forum - FDN Reverb Discussion](https://www.kvraudio.com/forum/viewtopic.php?t=123095) - Practical implementation notes, delay length selection strategies
- [Faust Libraries - reverbs](https://faustlibraries.grame.fr/libs/reverbs/) - fdnrev0 reference: per-band decay with crossover frequencies

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All primitives exist in codebase, no new dependencies
- Architecture: HIGH - FDN is well-documented (JOS textbook, Signalsmith tutorial), composable pattern is a locked decision
- Hadamard implementation: HIGH - Mathematical identity, verified formula (1/sqrt(N) normalization, butterfly decomposition)
- Pitfalls: HIGH - DC buildup, metallic ringing, instability are well-known FDN issues with documented solutions
- Delay lengths: MEDIUM - Specific prime values are my recommendation (Claude's discretion), but coprimality principle is HIGH confidence
- Per-band decay: MEDIUM - OnePole HF is straightforward; LF shelf may need tuning during implementation

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable domain, no fast-moving dependencies)
