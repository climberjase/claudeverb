# Phase 2: Audio I/O + Freeverb - Research

**Researched:** 2026-03-04
**Domain:** Audio file loading/resampling, Freeverb reverb algorithm implementation
**Confidence:** HIGH

## Summary

This phase builds the first complete audio signal path: load audio files with automatic resampling to 48 kHz, process through a Freeverb implementation using the Phase 1 DSP primitives (CombFilter, AllpassFilter, DelayLine), and output processed audio. The Freeverb algorithm follows Jezar's well-documented public domain design -- 8 parallel lowpass-feedback comb filters fed into 4 series allpass filters per channel -- with delay line lengths scaled from 44.1 kHz reference values to 48 kHz.

Audio I/O uses `librosa.load()` for file loading (handles WAV, AIFF, FLAC, OGG, MP3) with built-in resampling via `sr=48000`, and `soundfile.write()` for output. Both are already project dependencies. The Freeverb implementation subclasses the existing `ReverbAlgorithm` ABC and registers in `ALGORITHM_REGISTRY`.

**Primary recommendation:** Use librosa for loading (unified format support + resampling), soundfile for writing (simpler API, no resampling needed on output), and implement Freeverb with exact Jezar topology using existing CombFilter/AllpassFilter/DelayLine primitives with 48 kHz-scaled delay lengths.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Combine wet+dry into a single **mix** knob (0=fully dry, 100=fully wet)
- 6th knob is **pre-delay** (0-100ms range), implemented with existing DelayLine primitive
- Final 6 knobs: room_size, damping, mix, width, pre-delay, + 1 TBD (or room_size, damping, mix, width, pre-delay with one spare)
- Full 0-100 range for all knobs -- no constraining to "safe" values; workbench users can explore extreme settings
- Knob values are integers 0-100, internally scaled to algorithm-appropriate float ranges
- Synthesized test samples: at minimum an impulse click; Claude's discretion on additional signals
- Freeverb follows Jezar's reference topology (8 parallel combs -> 4 series allpasses per channel)

### Claude's Discretion
- **Switch mapping**: What the 2 three-position switches (-1, 0, 1) control
- **Stereo/mono conversion**: How to handle mono vs stereo input/output routing
- **File format support**: Whether to accept only WAV/AIFF or also MP3/FLAC/OGG via librosa
- **Multi-channel handling**: How to handle >2 channel files
- **Duration limits**: Whether to warn or limit on very long files
- **Module layout**: Whether audio I/O lives in `claudeverb/audio/` subpackage or flat
- **Output destination**: Memory-only vs auto-save behavior
- **Save format**: WAV 32-bit float vs 24-bit PCM
- **Reverb tail handling**: Whether to extend output to capture full decay tail
- **Clipping strategy**: Hard clip, soft clip, or no clip on output
- **Synth signal selection**: Which generated test signals beyond impulse
- **Sample clip lengths**: Duration of bundled recording clips
- **Sample instrument focus**: Guitar-focused vs mixed instruments

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AIO-01 | User can load audio files from disk (WAV/AIFF) with automatic resampling to 48 kHz | librosa.load() with sr=48000 handles format detection and polyphase resampling; soundfile backend supports WAV/AIFF natively |
| AIO-02 | Workbench ships with bundled test samples (dry drums, guitar, vocals, impulse click) | Synthesized signals (impulse, white noise burst, sine sweep) generated via numpy; real recordings sourced as short clips |
| AIO-04 | User can generate an impulse response from any algorithm with current parameters | Process a unit impulse (1.0 at sample 0, zeros after) through algorithm.process(); extend output to capture full reverb tail |
| ALG-01 | Freeverb algorithm (8 comb + 4 allpass per channel) with 6 knobs and 2 switches | Jezar topology fully documented; existing CombFilter/AllpassFilter primitives match exactly; delay lengths and scaling constants verified |
| ALG-03 | Each algorithm exposes param_specs defining knob ranges (0-100) and switch positions | ReverbAlgorithm ABC already has abstract param_specs property; implement as dict of ParamSpec-like entries |
| ALG-04 | Algorithm registry with dropdown selection in UI | ALGORITHM_REGISTRY dict exists in algorithms/__init__.py; register Freeverb class at import time |
| ALG-05 | Algorithm reset clears all internal state between parameter changes | ReverbAlgorithm.reset() is abstract; Freeverb.reset() must call reset() on all 8+4 filters per channel plus pre-delay |
| ALG-06 | Delay line lengths scaled for 48 kHz (not 44.1 kHz reference values) | Scale factor = 48000/44100; apply to all 12 delay lengths; round to nearest int |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| librosa | >=0.10 | Audio file loading with automatic resampling | Already a project dependency; handles WAV/AIFF/FLAC/OGG/MP3; built-in polyphase resampling via `sr=48000` parameter |
| soundfile | >=0.12 | Audio file writing (WAV output) | Already a project dependency; clean write API; supports WAV float32 and int formats |
| numpy | >=1.24 | Array operations, signal generation | Already a project dependency; float32 arrays are the project audio format |
| scipy | >=1.10 | Resampling backend (used by librosa internally) | Already a project dependency; polyphase filter resampling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=7.0 | Testing | Already installed as dev dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| librosa.load() | soundfile.read() + scipy.signal.resample_poly() | Manual resampling code; librosa wraps this already |
| soundfile.write() | scipy.io.wavfile.write() | scipy wavfile has no AIFF support and less flexible dtype handling |

**Installation:**
```bash
pip install -e ".[dev]"   # all needed dependencies already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
claudeverb/
├── audio/
│   ├── __init__.py      # re-exports load, save, generate_impulse_response
│   ├── io.py            # load(), save() functions
│   └── samples.py       # bundled test sample registry + generation
├── algorithms/
│   ├── __init__.py      # ALGORITHM_REGISTRY (add Freeverb import)
│   ├── base.py          # ReverbAlgorithm ABC (exists)
│   ├── filters.py       # DSP primitives (exists)
│   └── freeverb.py      # Freeverb implementation
├── config.py            # SAMPLE_RATE, BUFFER_SIZE (exists)
└── samples/             # bundled audio files (WAV)
    ├── impulse.wav
    ├── white_noise_burst.wav
    ├── sine_sweep.wav
    └── ... (real recordings)
```

### Pattern 1: Audio I/O Module
**What:** Thin wrapper around librosa/soundfile providing load/save with enforced project conventions.
**When to use:** All audio file operations.
**Example:**
```python
# claudeverb/audio/io.py
import numpy as np
import librosa
import soundfile as sf
from claudeverb.config import SAMPLE_RATE

def load(path: str) -> np.ndarray:
    """Load audio file, resample to 48 kHz, return float32 array.

    Returns:
        Mono (N,) or stereo (2, N) float32 array in [-1.0, 1.0].
    """
    # librosa.load returns (audio, sr) with mono=False for multichannel
    audio, sr = librosa.load(path, sr=SAMPLE_RATE, mono=False)
    # librosa returns float32 by default
    # Shape: (N,) for mono, (channels, N) for multi
    if audio.ndim == 1:
        return audio  # mono
    elif audio.ndim == 2 and audio.shape[0] == 2:
        return audio  # stereo
    elif audio.ndim == 2 and audio.shape[0] > 2:
        # Downmix to stereo: take first two channels
        return audio[:2].astype(np.float32)
    return audio.astype(np.float32)

def save(path: str, audio: np.ndarray,
         subtype: str = "FLOAT") -> None:
    """Save audio to WAV file.

    Args:
        path: Output file path.
        audio: float32 array, shape (N,) or (2, N).
        subtype: soundfile subtype ("FLOAT" for 32-bit float,
                 "PCM_24" for 24-bit PCM).
    """
    if audio.ndim == 2:
        # soundfile expects (N, channels), we store (channels, N)
        audio = audio.T
    sf.write(path, audio, SAMPLE_RATE, subtype=subtype)
```

### Pattern 2: Freeverb Algorithm Structure
**What:** Jezar's Schroeder-Moorer reverb as a ReverbAlgorithm subclass.
**When to use:** The primary reverb algorithm for this phase.
**Example:**
```python
# claudeverb/algorithms/freeverb.py
class Freeverb(ReverbAlgorithm):
    __slots__ = (
        "_combs_l", "_combs_r",
        "_allpasses_l", "_allpasses_r",
        "_pre_delay",
        "_room_size", "_damping", "_mix", "_width",
        "_pre_delay_ms",
        "_switch1", "_switch2",
    )

    # Jezar's reference delay lengths at 44100 Hz
    COMB_LENGTHS_44100 = [1557, 1617, 1491, 1422, 1356, 1277, 1188, 1116]
    ALLPASS_LENGTHS_44100 = [225, 556, 441, 341]
    STEREO_SPREAD = 23

    # Scaling constants from Jezar's tuning.h
    FIXED_GAIN = 0.015
    SCALE_ROOM = 0.28
    OFFSET_ROOM = 0.7
    SCALE_DAMP = 0.4

    def __init__(self):
        self._initialize()

    @staticmethod
    def _scale_length(length_44100: int) -> int:
        """Scale delay length from 44.1 kHz to 48 kHz."""
        return round(length_44100 * SAMPLE_RATE / 44100)
```

### Pattern 3: Param Specs for Knobs and Switches
**What:** Structured parameter specifications that the UI can consume.
**When to use:** Every algorithm must define this.
**Example:**
```python
@property
def param_specs(self) -> dict:
    return {
        "room_size": {"type": "knob", "min": 0, "max": 100, "default": 75,
                      "label": "Room Size"},
        "damping":   {"type": "knob", "min": 0, "max": 100, "default": 25,
                      "label": "Damping"},
        "mix":       {"type": "knob", "min": 0, "max": 100, "default": 75,
                      "label": "Mix"},
        "width":     {"type": "knob", "min": 0, "max": 100, "default": 100,
                      "label": "Width"},
        "pre_delay": {"type": "knob", "min": 0, "max": 100, "default": 0,
                      "label": "Pre-Delay"},
        # 6th knob TBD or spare
        "switch1":   {"type": "switch", "positions": [-1, 0, 1], "default": 0,
                      "label": "Freeze", "labels": ["Freeze", "Normal", "Bright"]},
        "switch2":   {"type": "switch", "positions": [-1, 0, 1], "default": 0,
                      "label": "Stereo Mode", "labels": ["Mono", "Stereo", "Wide"]},
    }
```

### Pattern 4: Impulse Response Generation
**What:** Process a unit impulse through an algorithm to get its IR.
**When to use:** AIO-04 requirement; also used for analysis in Phase 3.
**Example:**
```python
def generate_impulse_response(
    algorithm: ReverbAlgorithm,
    duration_seconds: float = 3.0,
    mono: bool = True,
) -> np.ndarray:
    """Generate impulse response from algorithm with current parameters.

    Args:
        algorithm: Configured reverb algorithm instance.
        duration_seconds: IR length in seconds (must capture full tail).
        mono: If True, generate mono IR; if False, stereo.
    """
    n_samples = int(duration_seconds * SAMPLE_RATE)
    impulse = np.zeros(n_samples, dtype=np.float32)
    impulse[0] = 1.0
    if not mono:
        impulse = np.stack([impulse, impulse])
    algorithm.reset()
    return algorithm.process(impulse)
```

### Anti-Patterns to Avoid
- **Processing entire file in one process() call with large files:** Process in chunks of BUFFER_SIZE=48 for consistency with Daisy Seed behavior. However, for offline batch processing, processing the entire array at once is acceptable since the sample-by-sample loop inside CombFilter/AllpassFilter handles state correctly regardless of block size.
- **Using float64 anywhere in the audio path:** ReverbAlgorithm.process() rejects non-float32. Keep all audio as float32 from load to save.
- **Dynamic allocation in Freeverb after _initialize():** All delay lines must be allocated in __init__/_initialize(). No list appends, no new array allocations during process().
- **Hardcoding 44100 Hz delay lengths:** All Jezar reference values must be scaled by 48000/44100.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio file loading | Custom WAV/AIFF parser | librosa.load() | Handles format detection, codec fallbacks, channel layout, resampling in one call |
| Audio resampling | scipy.signal.resample or manual FIR | librosa.load(sr=48000) | Polyphase resampling built-in, anti-aliasing handled correctly |
| Audio file writing | Manual WAV byte packing | soundfile.write() | Handles PCM/float encoding, header generation, channel interleaving |
| Freeverb topology | Novel reverb network | Jezar's exact 8-comb + 4-allpass structure | Decades of validation; any deviation risks subtle sonic artifacts |

**Key insight:** The audio I/O layer should be as thin as possible -- librosa and soundfile handle all the edge cases (endianness, sample format conversion, channel layout). The Freeverb implementation should faithfully reproduce Jezar's topology using existing primitives, not innovate on the structure.

## Common Pitfalls

### Pitfall 1: Wrong Delay Length Scaling
**What goes wrong:** Using Jezar's 44100 Hz delay lengths directly at 48 kHz produces incorrect pitch/timing.
**Why it happens:** Many Freeverb ports copy constants verbatim without scaling.
**How to avoid:** Multiply all 12 delay lengths by `48000/44100` and round to nearest integer. The stereo spread (23 samples) should also be scaled.
**Warning signs:** Reverb sounds slightly lower-pitched than reference implementations.

### Pitfall 2: Incorrect Stereo Width Implementation
**What goes wrong:** Width parameter does nothing or causes phase cancellation.
**Why it happens:** Jezar's width formula mixes L/R channels: `out_l = wet1*l + wet2*r`, `out_r = wet1*r + wet2*l` where `wet1 = wet*(1+width)/2`, `wet2 = wet*(1-width)/2`. Getting the formula wrong breaks stereo imaging.
**How to avoid:** Implement the exact Jezar formula. At width=1.0, wet2=0 (pure stereo). At width=0.0, both channels identical (mono).
**Warning signs:** Stereo field collapses or spreads unpredictably when adjusting width knob.

### Pitfall 3: Gain Staging / Clipping
**What goes wrong:** Freeverb output clips heavily at high room_size or low damping.
**Why it happens:** 8 parallel comb filters sum together, multiplied by fixedGain=0.015. With extreme settings, accumulated energy can exceed [-1, 1].
**How to avoid:** Apply soft clipping (tanh) or hard clip at the output stage. The mix knob should blend dry and wet AFTER gain scaling. Monitor peak levels in tests.
**Warning signs:** Crackling, distortion, or inf/nan values in output.

### Pitfall 4: librosa Returns float64 in Some Edge Cases
**What goes wrong:** librosa.load() typically returns float32, but certain code paths or operations may produce float64.
**Why it happens:** numpy operations on float32 arrays sometimes promote to float64.
**How to avoid:** Always cast output of librosa.load() with `.astype(np.float32)` before returning from the load function.
**Warning signs:** TypeError from ReverbAlgorithm.process() rejecting float64 input.

### Pitfall 5: Freeze Mode Feedback Loop
**What goes wrong:** Freeze mode (feedback=1.0, damp=0.0, input gain=0.0) should hold the current reverb tail indefinitely, but numerical drift causes it to grow or decay.
**Why it happens:** float32 rounding errors accumulate over thousands of iterations at unity feedback.
**How to avoid:** When freeze is active, set feedback exactly to 1.0 (not 0.9999), set input gain to 0.0 (no new input), and set damp to 0.0. Accept minor float32 drift as inherent to the topology.
**Warning signs:** Frozen reverb tail slowly grows louder or fades to silence.

### Pitfall 6: soundfile Write Expects (N, channels) Not (channels, N)
**What goes wrong:** Output file has channels and samples swapped.
**Why it happens:** Project convention is (2, N) for stereo but soundfile.write() expects (N, 2).
**How to avoid:** Transpose stereo arrays before writing: `audio.T`.
**Warning signs:** Very short file with millions of channels, or garbled audio.

## Code Examples

### Freeverb Core Processing (Mono)
```python
# Source: Jezar's Freeverb reference + project primitives
def _process_mono(self, audio: np.ndarray) -> np.ndarray:
    """Process mono audio through Freeverb."""
    n_samples = len(audio)
    output = np.zeros(n_samples, dtype=np.float32)

    for i in range(n_samples):
        x = float(audio[i]) * self.FIXED_GAIN

        # Pre-delay
        if self._pre_delay_samples > 0:
            delayed = self._pre_delay.read(self._pre_delay_samples)
            self._pre_delay.write(x)
            x = delayed

        # Sum of 8 parallel comb filters
        comb_sum = 0.0
        for comb in self._combs_l:
            comb_sum += comb.process_sample(x)

        # Series allpass filters
        out = comb_sum
        for ap in self._allpasses_l:
            out = ap.process_sample(out)

        # Mix: blend dry and wet
        dry_gain = 1.0 - self._mix_scaled
        wet_gain = self._mix_scaled
        output[i] = np.float32(audio[i] * dry_gain + out * wet_gain)

    return output
```

### Freeverb Stereo Processing
```python
# Source: Jezar's Freeverb reference
def _process_stereo(self, audio: np.ndarray) -> np.ndarray:
    """Process stereo (2, N) audio through Freeverb."""
    left_in, right_in = audio[0], audio[1]
    n_samples = len(left_in)
    left_out = np.zeros(n_samples, dtype=np.float32)
    right_out = np.zeros(n_samples, dtype=np.float32)

    for i in range(n_samples):
        # Mono sum of input for reverb (standard Freeverb behavior)
        x = (float(left_in[i]) + float(right_in[i])) * self.FIXED_GAIN

        # Left channel: 8 combs -> 4 allpasses
        comb_l = sum(c.process_sample(x) for c in self._combs_l)
        out_l = comb_l
        for ap in self._allpasses_l:
            out_l = ap.process_sample(out_l)

        # Right channel: 8 combs -> 4 allpasses
        comb_r = sum(c.process_sample(x) for c in self._combs_r)
        out_r = comb_r
        for ap in self._allpasses_r:
            out_r = ap.process_sample(out_r)

        # Width crossmix
        wet1 = self._wet_scaled * (1.0 + self._width_scaled) / 2.0
        wet2 = self._wet_scaled * (1.0 - self._width_scaled) / 2.0
        dry_gain = 1.0 - self._mix_scaled

        left_out[i] = np.float32(
            left_in[i] * dry_gain + out_l * wet1 + out_r * wet2
        )
        right_out[i] = np.float32(
            right_in[i] * dry_gain + out_r * wet1 + out_l * wet2
        )

    return np.stack([left_out, right_out])
```

### 48 kHz Delay Length Scaling
```python
# Jezar's reference values at 44100 Hz
COMB_LENGTHS_44100 = [1557, 1617, 1491, 1422, 1356, 1277, 1188, 1116]
ALLPASS_LENGTHS_44100 = [225, 556, 441, 341]
STEREO_SPREAD_44100 = 23

# Scale to 48000 Hz
SCALE = 48000 / 44100  # ~1.0884

COMB_LENGTHS = [round(l * SCALE) for l in COMB_LENGTHS_44100]
# Result: [1694, 1760, 1623, 1548, 1476, 1390, 1293, 1215]

ALLPASS_LENGTHS = [round(l * SCALE) for l in ALLPASS_LENGTHS_44100]
# Result: [245, 605, 480, 371]

STEREO_SPREAD = round(23 * SCALE)
# Result: 25
```

### Knob-to-Parameter Scaling
```python
def _scale_params(self):
    """Convert 0-100 integer knob values to internal float ranges."""
    # Room size: 0-100 -> OFFSET_ROOM to OFFSET_ROOM + SCALE_ROOM (0.7 to 0.98)
    self._room_scaled = (self._room_size / 100.0) * self.SCALE_ROOM + self.OFFSET_ROOM

    # Damping: 0-100 -> 0.0 to SCALE_DAMP (0.0 to 0.4)
    self._damp_scaled = (self._damping / 100.0) * self.SCALE_DAMP

    # Mix: 0-100 -> 0.0 to 1.0
    self._mix_scaled = self._mix / 100.0

    # Width: 0-100 -> 0.0 to 1.0
    self._width_scaled = self._width / 100.0

    # Pre-delay: 0-100 -> 0 to 4800 samples (0 to 100ms at 48kHz)
    self._pre_delay_samples = int((self._pre_delay / 100.0) * 0.1 * SAMPLE_RATE)

    # Apply room_size as feedback to all combs
    for comb in self._combs_l + self._combs_r:
        comb.feedback = self._room_scaled
        comb.damp = self._damp_scaled
```

### Bundled Test Samples Generation
```python
def generate_impulse_click(duration_s: float = 1.0) -> np.ndarray:
    """Unit impulse for IR measurement."""
    n = int(SAMPLE_RATE * duration_s)
    sig = np.zeros(n, dtype=np.float32)
    sig[0] = 1.0
    return sig

def generate_white_noise_burst(duration_s: float = 0.5,
                                burst_s: float = 0.1) -> np.ndarray:
    """Short white noise burst followed by silence."""
    n = int(SAMPLE_RATE * duration_s)
    burst_n = int(SAMPLE_RATE * burst_s)
    sig = np.zeros(n, dtype=np.float32)
    sig[:burst_n] = np.random.default_rng(42).standard_normal(burst_n).astype(np.float32) * 0.5
    return sig

def generate_sine_sweep(duration_s: float = 2.0,
                         f_start: float = 20.0,
                         f_end: float = 20000.0) -> np.ndarray:
    """Logarithmic sine sweep for frequency response analysis."""
    from scipy.signal import chirp
    t = np.linspace(0, duration_s, int(SAMPLE_RATE * duration_s), dtype=np.float64)
    sweep = chirp(t, f_start, duration_s, f_end, method='logarithmic')
    return (sweep * 0.8).astype(np.float32)
```

## Discretion Recommendations

These are my recommendations for the areas marked as Claude's Discretion:

### Switch Mapping
- **Switch 1 (Freeze):** -1 = Freeze (feedback=1.0, damp=0.0, gain=0.0), 0 = Normal, 1 = Bright (reduced damping, slight high-frequency boost via lower damp coefficient)
- **Switch 2 (Stereo Mode):** -1 = Mono (force mono output), 0 = Stereo (standard Jezar stereo), 1 = Wide (double the stereo spread offset)

### Stereo/Mono Conversion
- Mono input processed through mono Freeverb path (left channel only, no stereo spread)
- Stereo input: sum L+R for reverb input (standard Freeverb), process through separate L/R comb+allpass chains, apply width crossmix
- Output matches input channel count (mono in = mono out, stereo in = stereo out)

### File Format Support
- Accept WAV, AIFF, FLAC, and OGG via librosa/soundfile (zero extra code)
- MP3 support via librosa's audioread fallback (may require ffmpeg installed)
- No need to restrict formats -- librosa handles it transparently

### Multi-Channel Handling
- >2 channels: take first two channels only, log a warning
- Single channel: process as mono

### Duration Limits
- No hard limit, but log a warning for files >60 seconds (memory/processing time consideration)
- Let the user decide -- this is a workbench tool

### Module Layout
- `claudeverb/audio/` subpackage with `io.py` and `samples.py`
- Matches ARCHITECTURE.md reference to `claudeverb/audio/io.py`

### Output Destination
- Memory-only by default (return numpy array)
- Provide explicit `save()` function when user wants to write to disk
- No auto-save behavior

### Save Format
- Default to WAV 32-bit float (lossless, matches internal format)
- Offer WAV 24-bit PCM as option via subtype parameter

### Reverb Tail Handling
- For impulse response generation: extend output by 3 seconds to capture full decay
- For regular file processing: extend output by `max(RT60_estimate, 2.0)` seconds, or let user control tail length
- Simple approach: pad input with zeros, then trim trailing silence

### Clipping Strategy
- Hard clip to [-1.0, 1.0] at output stage (np.clip)
- This matches standard audio convention and is C-portable
- Soft clip (tanh) is an option but adds coloration that may confuse analysis

### Synth Signals
- Impulse click (required): 1 sample at 1.0, rest zeros
- White noise burst: 100ms burst at -6dB, useful for hearing reverb tail character
- Sine sweep (20Hz-20kHz logarithmic): essential for Phase 3 frequency response analysis

### Sample Clip Lengths
- 3-5 seconds per clip (enough to hear reverb tail, short enough for fast iteration)

### Sample Instrument Focus
- Guitar-focused (matches Daisy Seed guitar pedal use case) with one vocal and one drums clip for variety

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| librosa.load(mono=True) default | librosa.load(mono=False) for stereo | librosa 0.8+ | Must explicitly pass mono=False to preserve stereo |
| scipy.signal.resample (FFT-based) | Polyphase filtering (default in librosa) | librosa 0.9+ | Better quality, no spectral leakage artifacts |
| soundfile expects (N,) or (N,ch) | Same convention maintained | Stable | Must transpose from project (ch, N) convention |

**Deprecated/outdated:**
- librosa's `audioread` backend is being deprecated in favor of `soundfile` for all formats -- but still works for MP3

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=7.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x --tb=short` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AIO-01 | Load WAV/AIFF, resample to 48kHz float32 | unit | `pytest tests/test_audio_io.py -x` | No -- Wave 0 |
| AIO-02 | Bundled test samples accessible | unit | `pytest tests/test_samples.py -x` | No -- Wave 0 |
| AIO-04 | Impulse response generation | unit | `pytest tests/test_impulse_response.py -x` | No -- Wave 0 |
| ALG-01 | Freeverb produces reverb output | unit+integration | `pytest tests/test_freeverb.py -x` | No -- Wave 0 |
| ALG-03 | param_specs defines knobs/switches | unit | `pytest tests/test_freeverb.py::test_param_specs -x` | No -- Wave 0 |
| ALG-04 | ALGORITHM_REGISTRY contains Freeverb | unit | `pytest tests/test_freeverb.py::test_registry -x` | No -- Wave 0 |
| ALG-05 | reset() clears all state | unit | `pytest tests/test_freeverb.py::test_reset -x` | No -- Wave 0 |
| ALG-06 | Delay lengths scaled for 48kHz | unit | `pytest tests/test_freeverb.py::test_delay_scaling -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --tb=short`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_audio_io.py` -- covers AIO-01 (load, resample, format support, dtype enforcement)
- [ ] `tests/test_samples.py` -- covers AIO-02 (bundled sample availability and correctness)
- [ ] `tests/test_impulse_response.py` -- covers AIO-04 (IR generation from algorithm)
- [ ] `tests/test_freeverb.py` -- covers ALG-01, ALG-03, ALG-04, ALG-05, ALG-06 (Freeverb implementation, param_specs, registry, reset, scaling)

## Open Questions

1. **6th Knob**
   - What we know: User decided on room_size, damping, mix, width, pre-delay as 5 knobs. 6th is TBD.
   - What's unclear: Whether to use the 6th knob or leave it spare.
   - Recommendation: Implement 5 knobs now, leave 6th as a placeholder (e.g., "output_level" or "hf_damp" for independent high-frequency damping control). Can be decided during implementation.

2. **Real Recording Samples**
   - What we know: User wants bundled dry drums, guitar, vocals clips.
   - What's unclear: Where to source royalty-free short clips.
   - Recommendation: Generate all test samples programmatically for Phase 2 (impulse, noise burst, sine sweep, synthesized guitar-like pluck). Defer real recordings to a later task or let user provide their own. This avoids licensing concerns and keeps the repo lightweight.

3. **Freeverb Performance**
   - What we know: Sample-by-sample Python processing will be slow for long files.
   - What's unclear: Whether performance is acceptable for the workbench use case.
   - Recommendation: Accept Python performance for now (workbench is not real-time). A 5-second stereo file at 48kHz = 480,000 samples; with 8 combs + 4 allpasses = ~5.7M filter operations. Expect 2-10 seconds processing time. Acceptable for workbench.

## Sources

### Primary (HIGH confidence)
- [Jezar Freeverb reference (CCRMA/JOS)](https://ccrma.stanford.edu/~jos/pasp/Freeverb.html) - Algorithm topology, stereo spread, allpass coefficient
- [FreeVerb.h (gburlet/GitHub)](https://github.com/gburlet/FreeVerb/blob/master/FreeVerb.h) - Tuning constants: fixedGain, scaleRoom, offsetRoom, scaleDamp, defaults
- [FreeVerb.cpp (gburlet/GitHub)](https://github.com/gburlet/FreeVerb/blob/master/FreeVerb.cpp) - Exact delay line lengths, freeze mode behavior
- [STK FreeVerb.cpp (thestk/GitHub)](https://github.com/thestk/stk/blob/master/src/FreeVerb.cpp) - Reference implementation with sample rate scaling
- [librosa.load documentation](https://librosa.org/doc/main/generated/librosa.load.html) - Audio loading API, resampling, format support
- [librosa.resample documentation](https://librosa.org/doc/main/generated/librosa.resample.html) - Resampling methods (polyphase, fft, scipy)
- [python-soundfile documentation](https://python-soundfile.readthedocs.io/) - Audio file writing API
- Existing codebase: `filters.py`, `base.py`, `config.py`, `conftest.py` - Project conventions and existing primitives

### Secondary (MEDIUM confidence)
- [librosa I/O format support](https://librosa.org/doc/main/ioformats.html) - WAV/AIFF/FLAC/OGG via soundfile, MP3 via audioread
- [DSPRelated Freeverb analysis](https://www.dsprelated.com/freebooks/pasp/Freeverb.html) - Algorithm description and analysis

### Tertiary (LOW confidence)
- None -- all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in pyproject.toml, APIs verified with official docs
- Architecture: HIGH - follows existing project patterns (base.py ABC, filters.py primitives, __slots__, float32)
- Freeverb algorithm: HIGH - Jezar's design is public domain, extensively documented, exact constants verified from source code
- Audio I/O: HIGH - librosa and soundfile are mature, well-documented libraries already in project deps
- Pitfalls: HIGH - based on known issues with Freeverb ports and audio processing in Python

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable domain, mature libraries)
