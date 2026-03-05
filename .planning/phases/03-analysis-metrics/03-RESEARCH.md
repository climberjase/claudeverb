# Phase 3: Analysis Metrics - Research

**Researched:** 2026-03-05
**Domain:** Acoustic analysis metrics, spectral visualization, DSP measurement
**Confidence:** HIGH

## Summary

Phase 3 implements quantitative acoustic analysis for reverb characterization. The core work splits into two modules: `metrics.py` for numerical measurements (RT60, DRR, C80/C50, spectral centroid) and `spectral.py` for visualization (mel spectrogram, FFT magnitude overlay). All functions are pure (no state), accept the project's standard `(N,)` mono or `(2, N)` stereo float32 arrays, and depend only on numpy, scipy, librosa, and matplotlib -- all already in the project's dependencies.

The algorithms are well-established in acoustic literature with straightforward implementations. RT60 via Schroeder backward integration is the most complex piece; DRR, C80, and C50 are simple energy ratio calculations from impulse responses. Spectral centroid uses librosa directly. Visualization wraps librosa's mel spectrogram display and numpy's FFT.

**Primary recommendation:** Implement `claudeverb/analysis/metrics.py` and `claudeverb/analysis/spectral.py` as pure-function modules. Use scipy for bandpass filtering (per-band RT60), librosa for mel spectrograms and spectral centroid, numpy for FFT and energy calculations, and matplotlib for all plotting.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLY-01 | Mel spectrogram visualization comparing input vs. processed output | librosa.feature.melspectrogram + librosa.display.specshow with matplotlib subplots |
| ANLY-02 | RT60 measurement via Schroeder backward integration -- broadband plus per-band | Schroeder backward integration (numpy cumsum), scipy.signal.butter bandpass for per-band |
| ANLY-03 | DRR computed from impulse response | Energy ratio calculation with 2.5ms direct-sound boundary |
| ANLY-04 | C80 and C50 clarity metrics from impulse response | Energy ratio at 80ms and 50ms boundaries |
| ANLY-05 | Spectral centroid comparison (input vs. output delta) | librosa.feature.spectral_centroid, report mean delta in Hz |
| ANLY-06 | FFT magnitude comparison plot (input vs. output overlay) | numpy.fft.rfft + matplotlib overlay plot |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.24 | FFT, energy calculations, array math | Already in project; standard for DSP |
| scipy | >=1.10 | Bandpass filters for per-band RT60, linear regression | Already in project; signal processing standard |
| librosa | latest | Mel spectrogram, spectral centroid, display utilities | Already in project; audio analysis standard |
| matplotlib | latest | All plotting (spectrograms, FFT overlays) | Already in project; required by librosa.display |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy.signal | (part of scipy) | Butterworth bandpass filter design | Per-band RT60 filtering |
| scipy.stats | (part of scipy) | linregress for RT60 decay slope | RT60 linear fit on Schroeder curve |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom RT60 | pyroomacoustics | External dependency for one function; our implementation is ~40 lines |
| Custom bandpass | librosa filters | scipy.signal.butter is more standard for octave-band work |

**Installation:**
```bash
# No new dependencies needed -- all already in pyproject.toml
pip install -e ".[dev]"
```

## Architecture Patterns

### Recommended Project Structure
```
claudeverb/
  analysis/
    __init__.py        # exports all public functions
    metrics.py         # RT60, DRR, C80, C50, spectral_centroid_delta
    spectral.py        # mel_spectrogram, fft_magnitude_compare
```

### Pattern 1: Pure Functions with Channel Handling
**What:** Every analysis function accepts `(N,)` or `(2, N)` float32 and handles mono/stereo internally.
**When to use:** All analysis functions.
**Example:**
```python
def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """Average stereo to mono for analysis."""
    if audio.ndim == 2 and audio.shape[0] == 2:
        return audio.mean(axis=0)
    return audio
```

### Pattern 2: Schroeder Backward Integration for RT60
**What:** Compute energy decay curve by reverse cumulative sum of squared impulse response.
**When to use:** RT60 measurement (ANLY-02).
**Example:**
```python
# Source: pyroomacoustics/experimental/rt60.py (reference algorithm)
def measure_rt60(ir: np.ndarray, sr: int = 48000, decay_db: float = 60.0) -> float:
    """Measure RT60 from impulse response via Schroeder backward integration."""
    ir = _ensure_mono(ir)
    power = ir ** 2
    # Backward integration (Schroeder method)
    energy = np.cumsum(power[::-1])[::-1]
    energy_db = 10.0 * np.log10(energy / energy[0] + 1e-12)

    # Find -5dB and -(5+decay_db) points, fit line, extrapolate to -60dB
    # Using T20 or T30 extrapolation when full 60dB decay not available
    idx_5 = np.searchsorted(-energy_db, 5.0)
    idx_end = np.searchsorted(-energy_db, 5.0 + min(decay_db, 30.0))

    if idx_end <= idx_5:
        return 0.0  # Signal too short or no decay

    t = np.arange(idx_5, idx_end) / sr
    slope, intercept, _, _, _ = scipy.stats.linregress(t, energy_db[idx_5:idx_end])

    if slope >= 0:
        return 0.0  # No decay detected

    rt60 = -60.0 / slope
    return float(rt60)
```

### Pattern 3: Energy Ratio Metrics (DRR, C80, C50)
**What:** Split impulse response at a time boundary, compute energy ratio in dB.
**When to use:** ANLY-03 (DRR) and ANLY-04 (C80/C50).
**Example:**
```python
def compute_drr(ir: np.ndarray, sr: int = 48000, direct_ms: float = 2.5) -> float:
    """Direct-to-Reverberant Ratio in dB."""
    ir = _ensure_mono(ir)
    boundary = int(direct_ms * sr / 1000.0)
    direct_energy = np.sum(ir[:boundary] ** 2)
    reverb_energy = np.sum(ir[boundary:] ** 2)
    if reverb_energy < 1e-12:
        return float('inf')
    return float(10.0 * np.log10(direct_energy / reverb_energy))

def compute_clarity(ir: np.ndarray, sr: int = 48000, early_ms: float = 80.0) -> float:
    """C80 or C50 clarity metric in dB. Use early_ms=80 for C80, 50 for C50."""
    ir = _ensure_mono(ir)
    boundary = int(early_ms * sr / 1000.0)
    early_energy = np.sum(ir[:boundary] ** 2)
    late_energy = np.sum(ir[boundary:] ** 2)
    if late_energy < 1e-12:
        return float('inf')
    return float(10.0 * np.log10(early_energy / late_energy))
```

### Pattern 4: Per-Band RT60 with Butterworth Bandpass
**What:** Filter IR into octave bands before Schroeder integration.
**When to use:** ANLY-02 per-band measurement (low/mid/high).
**Example:**
```python
# Three bands: low (125-500 Hz), mid (500-2000 Hz), high (2000-8000 Hz)
BANDS = {
    "low":  (125.0, 500.0),
    "mid":  (500.0, 2000.0),
    "high": (2000.0, 8000.0),
}

def bandpass_filter(signal, low_hz, high_hz, sr, order=4):
    from scipy.signal import butter, sosfilt
    nyq = sr / 2.0
    sos = butter(order, [low_hz / nyq, high_hz / nyq], btype='band', output='sos')
    return sosfilt(sos, signal).astype(np.float32)
```

### Anti-Patterns to Avoid
- **Using power spectrogram when magnitude is expected:** librosa's spectral_centroid expects magnitude spectrogram by default. Don't pass power spectrogram.
- **Not handling zero/silence gracefully:** Energy ratio functions must guard against division by zero (late_energy == 0 means infinite clarity, not a crash).
- **Forgetting to normalize Schroeder curve:** Always subtract energy_db[0] so the curve starts at 0 dB.
- **Using T60 directly when decay is short:** Use T20 or T30 extrapolation (fit over 20 or 30 dB range, then scale to 60 dB).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mel spectrogram | Custom mel filterbank | `librosa.feature.melspectrogram` | Mel scale edge cases, filterbank normalization |
| Spectrogram display | Custom heatmap | `librosa.display.specshow` | Handles time/frequency axis labeling, colorbar scaling |
| Spectral centroid | Manual weighted average | `librosa.feature.spectral_centroid` | Handles STFT windowing, hop alignment |
| Bandpass filter design | Manual IIR coefficients | `scipy.signal.butter(..., output='sos')` | Numerical stability with SOS form |
| dB conversion for display | Manual log scaling | `librosa.power_to_db` | Handles ref, amin, top_db clipping |

**Key insight:** The analysis layer is glue code around well-tested library functions. The value is in correct parameterization and consistent interfaces, not novel algorithms.

## Common Pitfalls

### Pitfall 1: RT60 on Short or Quiet Impulse Responses
**What goes wrong:** Schroeder curve doesn't reach -60 dB; linear regression gives nonsensical values.
**Why it happens:** Short duration or low feedback gain means insufficient decay range.
**How to avoid:** Use T20 or T30 extrapolation (measure over 20 or 30 dB decay, multiply by 3 or 2). Guard with minimum decay range check.
**Warning signs:** RT60 > duration of the IR, or negative RT60 values.

### Pitfall 2: Noise Floor Corrupting RT60
**What goes wrong:** Noise energy at the tail of the IR flattens the Schroeder curve, underestimating RT60.
**Why it happens:** Digital noise or quantization artifacts in the tail.
**How to avoid:** Start the regression fit at -5 dB (skip the initial transient), end before noise floor dominates. The -5 dB to -35 dB range (T30) is standard practice.
**Warning signs:** Schroeder curve flattens instead of continuing to decay.

### Pitfall 3: Boundary Sample Off-by-One in DRR/C80/C50
**What goes wrong:** Off-by-one in the boundary index shifts which samples count as "direct" vs "reverberant."
**Why it happens:** Confusion between ms-to-sample conversion (inclusive vs exclusive boundary).
**How to avoid:** Use `int(ms * sr / 1000)` consistently. Document whether boundary sample is included in early or late.
**Warning signs:** DRR or C80 values slightly different from hand calculations.

### Pitfall 4: Stereo Handling Inconsistency
**What goes wrong:** Some functions average channels, others don't, leading to confusing results.
**Why it happens:** No consistent policy across functions.
**How to avoid:** All metrics functions call `_ensure_mono()` as first step. Visualization functions can show per-channel if desired.
**Warning signs:** Different results for mono vs stereo versions of the same signal.

### Pitfall 5: FFT Magnitude Plot Frequency Axis
**What goes wrong:** Frequency axis shows bin indices instead of Hz, or is linear when log would be more useful.
**Why it happens:** Using raw FFT output without computing frequency axis.
**How to avoid:** Use `np.fft.rfftfreq(n, 1.0/sr)` for the frequency axis. Use log scale for x-axis (standard for audio).
**Warning signs:** Plot shows frequencies up to sr instead of sr/2; low frequencies are invisible on linear scale.

## Code Examples

### Mel Spectrogram Comparison (ANLY-01)
```python
# Source: librosa docs - display.specshow
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

def plot_mel_comparison(
    input_audio: np.ndarray,
    output_audio: np.ndarray,
    sr: int = 48000,
    n_mels: int = 128,
    fmax: float = 8000.0,
) -> plt.Figure:
    """Side-by-side mel spectrogram comparison."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    for ax, audio, title in zip(axes, [input_audio, output_audio], ["Input", "Output"]):
        audio_mono = audio.mean(axis=0) if audio.ndim == 2 else audio
        S = librosa.feature.melspectrogram(y=audio_mono, sr=sr, n_mels=n_mels, fmax=fmax)
        S_db = librosa.power_to_db(S, ref=np.max)
        librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='mel',
                                  fmax=fmax, ax=ax)
        ax.set_title(title)

    fig.colorbar(axes[0].images[0], ax=axes, format='%+2.0f dB')
    fig.tight_layout()
    return fig
```

### FFT Magnitude Overlay (ANLY-06)
```python
def plot_fft_comparison(
    input_audio: np.ndarray,
    output_audio: np.ndarray,
    sr: int = 48000,
) -> plt.Figure:
    """Overlay FFT magnitude of input vs. output."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for audio, label, alpha in [(input_audio, "Input", 0.7), (output_audio, "Output", 0.9)]:
        mono = audio.mean(axis=0) if audio.ndim == 2 else audio
        n = len(mono)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        magnitude = np.abs(np.fft.rfft(mono))
        magnitude_db = 20.0 * np.log10(magnitude + 1e-12)
        ax.plot(freqs, magnitude_db, label=label, alpha=alpha)

    ax.set_xscale('log')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Magnitude (dB)')
    ax.set_title('FFT Magnitude Comparison')
    ax.legend()
    ax.set_xlim(20, sr / 2)
    fig.tight_layout()
    return fig
```

### Spectral Centroid Delta (ANLY-05)
```python
def spectral_centroid_delta(
    input_audio: np.ndarray,
    output_audio: np.ndarray,
    sr: int = 48000,
) -> float:
    """Compute spectral centroid delta between input and output in Hz."""
    in_mono = input_audio.mean(axis=0) if input_audio.ndim == 2 else input_audio
    out_mono = output_audio.mean(axis=0) if output_audio.ndim == 2 else output_audio

    in_centroid = librosa.feature.spectral_centroid(y=in_mono, sr=sr)[0]
    out_centroid = librosa.feature.spectral_centroid(y=out_mono, sr=sr)[0]

    # Return mean delta (output - input), negative means reverb darkened the signal
    return float(np.mean(out_centroid) - np.mean(in_centroid))
```

### Comb Filter RT60 Analytical Formula (for testing)
```python
# For test validation: analytical RT60 of a comb filter
# RT60 = -60 * delay_seconds / (20 * log10(feedback_gain))
# Simplified: RT60 = -3 * delay_seconds / log10(feedback_gain)
def comb_rt60_analytical(delay_samples: int, feedback: float, sr: int = 48000) -> float:
    """Analytical RT60 for a comb filter."""
    import math
    delay_s = delay_samples / sr
    if feedback <= 0 or feedback >= 1:
        return float('inf')
    return -3.0 * delay_s / math.log10(feedback)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| T60 direct measurement | T20/T30 extrapolation | Standard since ISO 3382 | More reliable with noise floors |
| scipy.signal.lfilter | scipy.signal.sosfilt | scipy 0.16+ | Better numerical stability for high-order filters |
| Manual mel filterbank | librosa.feature.melspectrogram | librosa 0.6+ | Consistent, tested filterbank |
| Power spectrogram display | librosa.power_to_db + specshow | librosa 0.8+ | Proper dB scaling with ref/amin |

**Deprecated/outdated:**
- `scipy.signal.butter` with `output='ba'`: Use `output='sos'` for numerical stability
- Manual STFT for spectral centroid: `librosa.feature.spectral_centroid` handles this correctly

## Open Questions

1. **DRR direct-sound boundary (2.5ms vs other values)**
   - What we know: 2.5ms is commonly used for close-mic/synthetic IRs. Literature varies from 1ms to 5ms.
   - What's unclear: Whether 2.5ms is appropriate for all our synthetic reverb IRs.
   - Recommendation: Default to 2.5ms, accept as parameter. Test validates with this default.

2. **Per-band frequency boundaries**
   - What we know: ISO standard uses octave bands (125, 250, 500, 1k, 2k, 4k Hz centers). Requirements say "low/mid/high."
   - What's unclear: Exact boundary frequencies for the three bands.
   - Recommendation: Use low=125-500 Hz, mid=500-2000 Hz, high=2000-8000 Hz. Three bands aligns with typical audio terminology.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=7.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_analysis_metrics.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLY-01 | Mel spectrogram renders for mono and stereo | unit | `pytest tests/test_spectral.py::test_mel_spectrogram_mono -x` | No - Wave 0 |
| ANLY-02 | RT60 of comb filter matches analytical formula within 10% | unit | `pytest tests/test_analysis_metrics.py::test_rt60_comb_filter -x` | No - Wave 0 |
| ANLY-02 | Per-band RT60 returns dict with low/mid/high keys | unit | `pytest tests/test_analysis_metrics.py::test_rt60_per_band -x` | No - Wave 0 |
| ANLY-03 | DRR of known IR matches hand-calculated value | unit | `pytest tests/test_analysis_metrics.py::test_drr -x` | No - Wave 0 |
| ANLY-04 | C80 and C50 of known IR match hand-calculated values | unit | `pytest tests/test_analysis_metrics.py::test_c80_c50 -x` | No - Wave 0 |
| ANLY-05 | Spectral centroid delta computed and returned as float | unit | `pytest tests/test_analysis_metrics.py::test_spectral_centroid_delta -x` | No - Wave 0 |
| ANLY-06 | FFT magnitude overlay renders with two traces | unit | `pytest tests/test_spectral.py::test_fft_comparison -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_analysis_metrics.py tests/test_spectral.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_analysis_metrics.py` -- covers ANLY-02, ANLY-03, ANLY-04, ANLY-05
- [ ] `tests/test_spectral.py` -- covers ANLY-01, ANLY-06
- [ ] `claudeverb/analysis/__init__.py` -- package init with exports
- [ ] Existing conftest.py `impulse` fixture sufficient; may need `comb_ir` fixture for RT60 validation

## Sources

### Primary (HIGH confidence)
- pyroomacoustics RT60 implementation (https://github.com/LCAV/pyroomacoustics/blob/master/pyroomacoustics/experimental/rt60.py) - Schroeder backward integration reference
- librosa 0.11.0 docs (https://librosa.org/doc/main/generated/librosa.feature.melspectrogram.html) - mel spectrogram API
- librosa spectral_centroid docs (https://librosa.org/doc/main/generated/librosa.feature.spectral_centroid.html) - spectral centroid API
- scipy.signal.butter docs (https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.iirfilter.html) - bandpass filter design

### Secondary (MEDIUM confidence)
- Vocal.com RT60 band practice (https://vocal.com/dereverberation/practice-of-rt60-estimation-in-bands/) - per-band RT60 methodology
- Acoustic measurement literature - DRR 2.5ms boundary convention

### Tertiary (LOW confidence)
- DRR boundary time selection - varies by application, 2.5ms is reasonable default

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, well-documented APIs
- Architecture: HIGH - pure functions, no state, straightforward module structure
- Pitfalls: HIGH - well-known issues in acoustic measurement literature
- Metrics formulas: HIGH - ISO 3382 standard, verified against pyroomacoustics implementation
- Per-band boundaries: MEDIUM - using common low/mid/high split, not ISO octave bands

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, no fast-moving dependencies)
