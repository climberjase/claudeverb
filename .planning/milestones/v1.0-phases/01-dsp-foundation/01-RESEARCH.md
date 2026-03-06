# Phase 1: DSP Foundation - Research

**Researched:** 2026-03-04
**Domain:** DSP primitives (delay lines, comb/allpass filters, biquad EQ) with C-portability constraints
**Confidence:** HIGH

## Summary

Phase 1 builds the foundational DSP primitives that all reverb algorithms depend on: DelayLine, CombFilter, AllpassFilter, and Biquad EQ filters. The user has made clear decisions on all major design points -- Direct Form II Transposed biquads with Bristow-Johnson cookbook coefficients, sample-by-sample processing with block wrappers, linear interpolation for fractional delay taps, and mono-only primitives.

This is well-trodden territory in audio DSP. The formulas are decades old, numerically stable, and have reference implementations in every language. The primary risk is not algorithmic complexity but rather ensuring C-portability constraints are enforced from the start: fixed-size buffers, no dynamic allocation after init, float32 only, and state representable as C structs.

**Primary recommendation:** Implement all primitives in a single `claudeverb/algorithms/filters.py` module with each class following the pattern: `__init__` allocates fixed numpy arrays, `process_sample(x) -> y` does per-sample work, `process(block) -> block` loops over samples, and `reset()` zeros state.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Delay Line**: Fractional tap positions via linear interpolation (two-point lerp). Single read method called multiple times for multi-tap. Max size in samples (not ms). Maps 1:1 to C array size.
- **Processing Style**: Sample-by-sample core (`process_sample(x) -> y`) with `process(block)` wrapper that loops. Stateful objects holding own state. CombFilter owns its DelayLine internally.
- **Stereo**: Primitives are mono-only. Algorithms create two instances for stereo. Stereo offset (e.g., +23 samples) applied at algorithm level.
- **EQ Filters**: Biquad topology, Direct Form II Transposed. Single `Biquad` class with factory methods (`Biquad.lowpass(freq, q)`, etc.). Smooth coefficient updates without state reset. Bristow-Johnson Audio EQ Cookbook coefficients -- no scipy dependency in DSP module.

### Claude's Discretion
- Whether to add a lightweight Protocol/ABC for DSP primitives (duck typing vs formal interface)
- Exact circular buffer implementation details
- Test fixture design beyond what conftest.py already specifies

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSP-01 | Comb filter primitive with fixed-size circular buffer delay line | Freeverb lowpass-feedback-comb-filter formula documented; delay line sizes known |
| DSP-02 | Allpass filter primitive with fixed-size circular buffer delay line | Schroeder allpass topology documented; coefficient = 0.5 per Freeverb convention |
| DSP-03 | Delay line primitive (circular buffer, no dynamic allocation after init) | Circular buffer with write pointer, linear interpolation for fractional reads |
| DSP-04 | EQ filter primitives: HP, LP, notch, bandpass, parametric | Bristow-Johnson cookbook formulas verified for all 5 types; DF2T implementation documented |
| DSP-05 | All algorithm state as fixed-size C arrays and scalars | Enforced by using pre-allocated numpy arrays in __init__, no allocation in process |
| DSP-06 | All audio float32 in [-1.0, 1.0], mono (N,) or stereo (2,N) | dtype check in process(), reject float64 with TypeError |
| DSP-07 | Block-based processing with BUFFER_SIZE=48 | process(block) loops over process_sample(); block size from config.BUFFER_SIZE |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.24 | Array operations, float32 buffers | Industry standard for numerical Python; dtype enforcement via ndarray |
| math | stdlib | sin, cos, pi for coefficient calculation | No external dependency; maps to C math.h |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=7.0 | Test framework | All unit tests for primitives |
| scipy.signal | >=1.10 | Test verification only | freqz() to verify biquad frequency response in tests -- NOT used in production DSP code |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-coded biquad coefficients | scipy.signal.iirfilter | Would add scipy dependency to DSP module; not C-portable |
| numpy circular buffer | collections.deque | deque has no fixed-size guarantee; can't map to C array |
| Linear interpolation | Allpass/sinc interpolation | Higher quality but more CPU, harder to port to C, overkill for this use case |

**Installation:**
```bash
pip install numpy pytest scipy  # scipy for test verification only
```

## Architecture Patterns

### Recommended Project Structure
```
claudeverb/
  algorithms/
    __init__.py          # ALGORITHM_REGISTRY (empty for Phase 1)
    base.py              # ReverbAlgorithm ABC (scaffold only)
    filters.py           # ALL DSP primitives: DelayLine, CombFilter, AllpassFilter, Biquad
  config.py              # SAMPLE_RATE=48000, BUFFER_SIZE=48
tests/
  conftest.py            # impulse, mono_sine, stereo_sine fixtures
  test_delay_line.py     # DelayLine tests
  test_comb_filter.py    # CombFilter tests
  test_allpass_filter.py # AllpassFilter tests
  test_biquad.py         # Biquad EQ tests
```

### Pattern 1: Stateful DSP Primitive
**What:** Each primitive is a class that allocates state in `__init__` and processes sample-by-sample.
**When to use:** Every DSP building block in this phase.
**Example:**
```python
import numpy as np

class DelayLine:
    """Fixed-size circular buffer delay line with linear interpolation.

    C equivalent:
        typedef struct {
            float buffer[MAX_SIZE];
            int write_index;
            int max_delay;
        } DelayLine;
    """

    def __init__(self, max_delay: int):
        self._buffer = np.zeros(max_delay, dtype=np.float32)
        self._write_index = 0
        self._max_delay = max_delay

    def write(self, sample: float) -> None:
        self._buffer[self._write_index] = np.float32(sample)
        self._write_index = (self._write_index + 1) % self._max_delay

    def read(self, delay: float) -> float:
        """Read from delay line at fractional sample position (linear interpolation)."""
        read_pos = self._write_index - delay
        index = int(read_pos)
        frac = read_pos - index
        idx0 = index % self._max_delay
        idx1 = (index + 1) % self._max_delay
        return self._buffer[idx0] + frac * (self._buffer[idx1] - self._buffer[idx0])

    def process(self, block: np.ndarray) -> np.ndarray:
        if block.dtype != np.float32:
            raise TypeError(f"Expected float32, got {block.dtype}")
        output = np.empty_like(block)
        for i in range(len(block)):
            output[i] = self.read(self._max_delay)  # read at max delay
            self.write(block[i])
        return output

    def reset(self) -> None:
        self._buffer[:] = 0.0
        self._write_index = 0
```

### Pattern 2: Lowpass-Feedback-Comb Filter (Freeverb style)
**What:** Comb filter with one-pole lowpass in the feedback path for damping.
**When to use:** Freeverb and Schroeder-Moorer reverb algorithms.
**Example:**
```python
class CombFilter:
    """Lowpass-feedback comb filter (Schroeder-Moorer).

    Signal flow:
        y[n] = x[n] + feedback * lp[n]
        lp[n] = (1 - damp) * delay_out + damp * lp[n-1]
        delay writes y[n]

    C equivalent:
        typedef struct {
            DelayLine delay;
            float feedback;
            float damp1;    // 1 - damp
            float damp2;    // damp
            float filterstore;
        } CombFilter;
    """

    def __init__(self, delay_length: int, feedback: float = 0.5, damp: float = 0.5):
        self._delay = DelayLine(delay_length)
        self._feedback = np.float32(feedback)
        self._damp1 = np.float32(1.0 - damp)
        self._damp2 = np.float32(damp)
        self._filterstore = np.float32(0.0)

    def process_sample(self, x: float) -> float:
        delay_out = self._delay.read(self._delay._max_delay)
        # One-pole lowpass in feedback path
        self._filterstore = delay_out * self._damp1 + self._filterstore * self._damp2
        output = x + self._feedback * self._filterstore
        self._delay.write(output)
        return output
```

### Pattern 3: Biquad with Factory Methods
**What:** Single Biquad class using DF2T, with classmethods for each filter type.
**When to use:** All EQ filtering needs.
**Example:**
```python
import math

class Biquad:
    """Direct Form II Transposed biquad filter.

    Difference equations (DF2T):
        y[n] = b0*x[n] + d1
        d1   = b1*x[n] - a1*y[n] + d2
        d2   = b2*x[n] - a2*y[n]

    Coefficients from Robert Bristow-Johnson's Audio EQ Cookbook.
    """

    def __init__(self, b0, b1, b2, a1, a2, sample_rate=48000):
        # Normalize by a0 during construction
        self._b0 = np.float32(b0)
        self._b1 = np.float32(b1)
        self._b2 = np.float32(b2)
        self._a1 = np.float32(a1)
        self._a2 = np.float32(a2)
        self._d1 = np.float32(0.0)
        self._d2 = np.float32(0.0)
        self._sample_rate = sample_rate

    def process_sample(self, x: float) -> float:
        y = self._b0 * x + self._d1
        self._d1 = self._b1 * x - self._a1 * y + self._d2
        self._d2 = self._b2 * x - self._a2 * y
        return float(y)

    @classmethod
    def lowpass(cls, freq: float, q: float, sample_rate: int = 48000):
        w0 = 2.0 * math.pi * freq / sample_rate
        alpha = math.sin(w0) / (2.0 * q)
        cos_w0 = math.cos(w0)

        b0 = (1.0 - cos_w0) / 2.0
        b1 = 1.0 - cos_w0
        b2 = (1.0 - cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        # Normalize by a0
        return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0, sample_rate)
```

### Pattern 4: Float32 Enforcement
**What:** Reject non-float32 input at process boundaries.
**When to use:** Every `process()` method.
**Example:**
```python
def process(self, block: np.ndarray) -> np.ndarray:
    if block.dtype != np.float32:
        raise TypeError(f"Expected float32 audio, got {block.dtype}")
    output = np.empty(len(block), dtype=np.float32)
    for i in range(len(block)):
        output[i] = self.process_sample(block[i])
    return output
```

### Discretion Recommendation: Use Protocol (not ABC)
**Recommendation:** Define a lightweight `typing.Protocol` for DSP primitives rather than a formal ABC. Rationale: primitives have slightly different interfaces (DelayLine has write/read, filters have process_sample), so a single ABC doesn't fit well. A Protocol documents the expected contract without forcing inheritance. However, this is optional -- duck typing works fine for Phase 1 since the only consumer of these primitives is the algorithm layer in Phase 2.

### Anti-Patterns to Avoid
- **Dynamic allocation in process():** Never create new numpy arrays inside `process_sample()`. All buffers allocated in `__init__`.
- **Using scipy in production DSP:** scipy is for test verification only. All coefficient math must be hand-coded for C portability.
- **Float64 default:** numpy defaults to float64. Always explicitly specify `dtype=np.float32`.
- **Modulo with negative numbers:** Python's `%` operator handles negatives correctly (always returns non-negative for positive divisor), but be explicit about this in read position calculations for clarity.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Biquad coefficient formulas | Derive from scratch | Bristow-Johnson Audio EQ Cookbook | Decades of verified math, every DSP library uses these |
| Frequency response verification | Manual FFT analysis | `scipy.signal.freqz(b, a)` in tests | Proven, handles edge cases, gives exact analytical response |
| Comb/allpass topology | Novel filter designs | Jezar's Freeverb topology | Well-tuned, extensively tested, reference implementations exist |
| Impulse response generation | Manual signal construction | `np.zeros(N, dtype=np.float32); signal[0] = 1.0` | Standard DSP test methodology |

**Key insight:** The primitives themselves are the "don't hand-roll" layer -- algorithms should never implement their own delay lines or filter math. All complexity lives in filters.py.

## Common Pitfalls

### Pitfall 1: Float64 Contamination
**What goes wrong:** numpy operations silently upcast float32 to float64 (e.g., `float32_array + python_float` produces float64).
**Why it happens:** Python float literals are float64. numpy promotes to the highest precision.
**How to avoid:** Use `np.float32()` wrappers for all scalar constants. Add dtype assertions in tests. Store all coefficients as `np.float32`.
**Warning signs:** Tests pass but C-exported code produces different results due to precision differences.

### Pitfall 2: Circular Buffer Off-by-One
**What goes wrong:** Write pointer and read pointer get out of sync, causing delay to be off by one sample.
**Why it happens:** Ambiguity about whether write happens before or after read in the same sample tick.
**How to avoid:** Establish a clear convention: write AFTER read in each sample cycle. Document this in the class docstring. Verify with impulse test: write impulse at sample 0, read at delay N, expect output at exactly sample N.
**Warning signs:** Impulse response is shifted by one sample from expected position.

### Pitfall 3: Biquad Coefficient Normalization
**What goes wrong:** Forgetting to divide all coefficients by a0, or dividing b coefficients but not a coefficients.
**Why it happens:** The Bristow-Johnson cookbook gives unnormalized coefficients (a0 != 1).
**How to avoid:** Normalize in the factory method: `b0/a0, b1/a0, b2/a0, a1/a0, a2/a0`. Store only normalized coefficients. The DF2T equations assume a0 = 1.
**Warning signs:** Filter output has wildly wrong magnitude or is unstable.

### Pitfall 4: Denormal Numbers
**What goes wrong:** Very small floating-point values (denormals) cause massive CPU slowdown on x86, manifesting as reverb tails that use 10x+ CPU.
**Why it happens:** Feedback loops in comb filters produce exponentially decaying values that hit denormal range.
**How to avoid:** Add a tiny DC offset or use a denormal-killing constant (e.g., `1e-25`). Freeverb's original code includes `undenormalize()` for this reason. On the C/STM32 side, the FPU can be configured to flush denormals to zero.
**Warning signs:** CPU usage spikes during quiet reverb tails.

### Pitfall 5: Sample Rate Mismatch in Freeverb Constants
**What goes wrong:** Using Jezar's original delay lengths (tuned for 44.1 kHz) at 48 kHz produces incorrect reverb characteristics.
**Why it happens:** The delay lengths define the frequency spacing of comb resonances. Wrong sample rate = wrong frequencies.
**How to avoid:** Scale all delay lengths: `new_length = round(original * 48000 / 44100)`. This is handled in Phase 2 (algorithm layer), but primitives must accept arbitrary integer sizes.
**Warning signs:** Reverb sounds different than reference implementations at the same settings.

## Code Examples

### Allpass Filter (Schroeder topology, Freeverb-style)
```python
# Source: Jezar's Freeverb (public domain), verified against STK implementation
class AllpassFilter:
    """Schroeder allpass filter.

    Signal flow:
        v[n] = x[n] + g * delay_out
        y[n] = -v[n] + (1+g) * delay_out
             = delay_out - g * v[n]   (simplified)
        delay writes v[n]

    With g = 0.5 (Freeverb default).
    """

    def __init__(self, delay_length: int, feedback: float = 0.5):
        self._delay = DelayLine(delay_length)
        self._feedback = np.float32(feedback)

    def process_sample(self, x: float) -> float:
        delay_out = self._delay.read(self._delay._max_delay)
        v = x + self._feedback * delay_out
        y = delay_out - self._feedback * v
        self._delay.write(v)
        return float(y)

    def process(self, block: np.ndarray) -> np.ndarray:
        if block.dtype != np.float32:
            raise TypeError(f"Expected float32, got {block.dtype}")
        output = np.empty(len(block), dtype=np.float32)
        for i in range(len(block)):
            output[i] = self.process_sample(block[i])
        return output

    def reset(self) -> None:
        self._delay.reset()
```

### Biquad Highpass (Bristow-Johnson)
```python
# Source: https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html
@classmethod
def highpass(cls, freq: float, q: float, sample_rate: int = 48000):
    w0 = 2.0 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)

    b0 = (1.0 + cos_w0) / 2.0
    b1 = -(1.0 + cos_w0)
    b2 = (1.0 + cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0, sample_rate)
```

### Biquad Notch, Bandpass, Parametric
```python
# Source: https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html

@classmethod
def notch(cls, freq: float, q: float, sample_rate: int = 48000):
    w0 = 2.0 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)
    b0 = 1.0; b1 = -2.0 * cos_w0; b2 = 1.0
    a0 = 1.0 + alpha; a1 = -2.0 * cos_w0; a2 = 1.0 - alpha
    return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0, sample_rate)

@classmethod
def bandpass(cls, freq: float, q: float, sample_rate: int = 48000):
    w0 = 2.0 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)
    b0 = alpha; b1 = 0.0; b2 = -alpha
    a0 = 1.0 + alpha; a1 = -2.0 * cos_w0; a2 = 1.0 - alpha
    return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0, sample_rate)

@classmethod
def parametric(cls, freq: float, q: float, gain_db: float, sample_rate: int = 48000):
    """Peaking EQ filter. gain_db is boost/cut in decibels."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)
    b0 = 1.0 + alpha * A; b1 = -2.0 * cos_w0; b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A; a1 = -2.0 * cos_w0; a2 = 1.0 - alpha / A
    return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0, sample_rate)
```

### Smooth Coefficient Update (no state reset)
```python
def set_coefficients(self, b0, b1, b2, a1, a2):
    """Update coefficients without clearing filter state (d1, d2).
    Allows smooth parameter changes during playback."""
    self._b0 = np.float32(b0)
    self._b1 = np.float32(b1)
    self._b2 = np.float32(b2)
    self._a1 = np.float32(a1)
    self._a2 = np.float32(a2)
    # Deliberately do NOT reset self._d1, self._d2

def set_frequency(self, freq: float):
    """Recalculate coefficients for new frequency, preserving filter state."""
    # Must know filter type to recalculate -- store type and Q in __init__
    pass  # Implementation depends on storing filter type metadata
```

### Test Fixture: Impulse Signal
```python
# conftest.py
import pytest
import numpy as np
from claudeverb.config import SAMPLE_RATE, BUFFER_SIZE

@pytest.fixture
def impulse():
    """Unit impulse: 1.0 at sample 0, then zeros. 1 second duration."""
    signal = np.zeros(SAMPLE_RATE, dtype=np.float32)
    signal[0] = 1.0
    return signal

@pytest.fixture
def mono_sine():
    """440 Hz sine wave, 1 second, float32."""
    t = np.arange(SAMPLE_RATE, dtype=np.float32) / SAMPLE_RATE
    return (np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| scipy.signal for coefficient calc | Hand-coded Bristow-Johnson | Always (for C-portable code) | No runtime scipy dependency |
| Direct Form I biquad | Direct Form II Transposed | Standard since ~2000s | Better numerical stability, fewer state variables |
| Float64 DSP in Python | Explicit float32 enforcement | Project-specific | Matches C target, catches precision issues early |

**Deprecated/outdated:**
- Direct Form I biquad: Worse numerical properties, more state variables. Use DF2T.
- scipy.signal.lfilter for production: Fine for prototyping, but not C-portable. Use hand-coded process_sample.

## Open Questions

1. **Smooth coefficient updates need filter type storage**
   - What we know: `set_frequency()` and `set_q()` need to recalculate coefficients, which requires knowing the filter type
   - What's unclear: Whether to store enum filter type + parameters, or store a coefficient-generation callable
   - Recommendation: Store `_filter_type` enum and `_freq`, `_q`, `_gain_db` as instance variables. Recalculate on update. Simpler than callables and maps to C cleanly.

2. **DelayLine read convention for integer delays**
   - What we know: Fractional reads use linear interpolation. Integer reads are a special case where frac=0.
   - What's unclear: Whether to optimize the integer path (skip interpolation) or always interpolate
   - Recommendation: Always interpolate. The cost of one extra multiply is negligible, and it avoids branching. On C/STM32, branchless code is preferable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=7.0 |
| Config file | none -- see Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DSP-01 | CombFilter produces correct impulse response | unit | `pytest tests/test_comb_filter.py -x` | Wave 0 |
| DSP-02 | AllpassFilter produces correct impulse response | unit | `pytest tests/test_allpass_filter.py -x` | Wave 0 |
| DSP-03 | DelayLine write/read at arbitrary taps, fractional interpolation | unit | `pytest tests/test_delay_line.py -x` | Wave 0 |
| DSP-04 | Biquad HP/LP/notch/bandpass/parametric match design specs | unit | `pytest tests/test_biquad.py -x` | Wave 0 |
| DSP-05 | All state is fixed-size arrays/scalars (inspection test) | unit | `pytest tests/test_c_portability.py -x` | Wave 0 |
| DSP-06 | float32 enforced, float64 rejected with TypeError | unit | `pytest tests/test_dtype_enforcement.py -x` | Wave 0 |
| DSP-07 | Block processing (48 samples) matches single-buffer processing | unit | `pytest tests/test_block_processing.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` -- project config with pytest settings
- [ ] `claudeverb/__init__.py` -- package init
- [ ] `claudeverb/config.py` -- SAMPLE_RATE, BUFFER_SIZE constants
- [ ] `claudeverb/algorithms/__init__.py` -- ALGORITHM_REGISTRY (empty)
- [ ] `tests/__init__.py` -- test package
- [ ] `tests/conftest.py` -- impulse, mono_sine, stereo_sine fixtures
- [ ] `tests/test_delay_line.py` -- covers DSP-03
- [ ] `tests/test_comb_filter.py` -- covers DSP-01
- [ ] `tests/test_allpass_filter.py` -- covers DSP-02
- [ ] `tests/test_biquad.py` -- covers DSP-04
- [ ] `tests/test_c_portability.py` -- covers DSP-05
- [ ] `tests/test_dtype_enforcement.py` -- covers DSP-06
- [ ] `tests/test_block_processing.py` -- covers DSP-07

## Sources

### Primary (HIGH confidence)
- [Audio EQ Cookbook (Bristow-Johnson)](https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html) -- biquad coefficient formulas for all 5 filter types
- [Freeverb source (Jezar, public domain)](https://github.com/gburlet/FreeVerb/blob/master/FreeVerb.cpp) -- comb/allpass topology, signal flow
- [STK FreeVerb implementation](https://github.com/thestk/stk/blob/master/src/FreeVerb.cpp) -- reference C++ with undenormalize
- [Freeverb tuning constants](https://github.com/alexmacrae/SamplerBox/blob/master/freeverb/tuning.h) -- delay lengths, scaling constants

### Secondary (MEDIUM confidence)
- [CCRMA Freeverb documentation](https://ccrma.stanford.edu/~jos/pasp/Freeverb.html) -- academic analysis of Freeverb topology
- [Wikipedia: Digital biquad filter](https://en.wikipedia.org/wiki/Digital_biquad_filter) -- DF2T difference equations
- [ARM CMSIS DSP Biquad DF2T](https://arm-software.github.io/CMSIS_5/DSP/html/group__BiquadCascadeDF2T.html) -- C reference for STM32 target

### Tertiary (LOW confidence)
- None -- all findings verified against primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- numpy + hand-coded DSP is the only viable approach given C-portability constraints
- Architecture: HIGH -- sample-by-sample with block wrapper is a well-established pattern, locked by user decision
- Pitfalls: HIGH -- float64 contamination, denormals, off-by-one are universally documented DSP issues
- Biquad coefficients: HIGH -- verified directly from Bristow-Johnson Audio EQ Cookbook (canonical source)
- Freeverb topology: HIGH -- verified against multiple implementations (STK, Jezar original, CCRMA docs)

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable domain, formulas are decades old)
