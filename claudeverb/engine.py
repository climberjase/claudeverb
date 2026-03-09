"""Processing engine facade for claudeverb.

Orchestrates algorithm processing, metric computation, and visualization
generation. Decouples all DSP/analysis logic from the UI layer so it can
be tested with plain pytest.

Public API:
    process_audio           -- Run algorithm, compute metrics, generate figures.
    blend_wet_dry           -- Mix dry/wet signals by percentage.
    plot_waveform_comparison -- Two-panel waveform plot (input vs output).
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.algorithms.filters import Biquad
from claudeverb.analysis.metrics import (
    compute_clarity,
    compute_drr,
    measure_rt60,
    measure_rt60_bands,
    spectral_centroid_delta,
)
from claudeverb.analysis.spectral import plot_fft_comparison, plot_mel_comparison
from claudeverb.audio.impulse import generate_impulse_response
from claudeverb.config import SAMPLE_RATE


def pad_with_silence(
    audio: np.ndarray, seconds: float, sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """Append silence to audio for reverb tail preservation.

    Args:
        audio: Input audio, mono (N,) or stereo (2, N), float32.
        seconds: Duration of silence to append in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        Audio with silence appended, same dtype as input.
    """
    n_pad = int(seconds * sample_rate)
    if n_pad <= 0:
        return audio
    if audio.ndim == 1:
        padding = np.zeros(n_pad, dtype=np.float32)
        return np.concatenate([audio, padding])
    else:
        padding = np.zeros((audio.shape[0], n_pad), dtype=np.float32)
        return np.concatenate([audio, padding], axis=1)


def apply_eq(wet: np.ndarray, eq_params: dict) -> np.ndarray:
    """Apply 3-band EQ (low shelf, mid parametric, high shelf) to audio.

    Args:
        wet: Audio signal, mono (N,) or stereo (2, N), float32.
        eq_params: Dict with keys: low_freq, low_gain, mid_freq, mid_gain,
                   mid_q, high_freq, high_gain.

    Returns:
        EQ-processed audio, clipped to [-1, 1], float32.
    """
    low = Biquad.low_shelf(eq_params["low_freq"], eq_params["low_gain"],
                           sample_rate=SAMPLE_RATE)
    mid = Biquad.parametric(eq_params["mid_freq"], eq_params["mid_q"],
                            eq_params["mid_gain"], sample_rate=SAMPLE_RATE)
    high = Biquad.high_shelf(eq_params["high_freq"], eq_params["high_gain"],
                             sample_rate=SAMPLE_RATE)

    if wet.ndim == 1:
        result = high.process(mid.process(low.process(wet)))
    else:
        result = wet.copy()
        for ch in range(wet.shape[0]):
            low.reset()
            mid.reset()
            high.reset()
            channel = wet[ch].copy()
            channel = low.process(channel)
            channel = mid.process(channel)
            channel = high.process(channel)
            result[ch] = channel

    return np.clip(result, -1.0, 1.0).astype(np.float32)


def process_audio(
    algorithm_name: str,
    params: dict,
    audio: np.ndarray,
    silence_seconds: float = 0.0,
    eq_params: dict | None = None,
) -> dict:
    """Run a reverb algorithm and return results for UI consumption.

    Looks up the algorithm by name, forces mix=100 (so the UI wet/dry
    control handles the full blend range), processes audio, generates
    an impulse response, computes metrics, and creates comparison figures.

    Args:
        algorithm_name: Key in ALGORITHM_REGISTRY (e.g. "freeverb").
        params: Algorithm parameter dict (mix is overridden to 100).
        audio: Input audio, mono (N,) or stereo (2, N), float32.
        silence_seconds: Duration of silence to append to input for reverb
            tail preservation (default 0.0, no padding).
        eq_params: Optional EQ settings dict. If provided and
            ``eq_params["enabled"]`` is truthy, a 3-band EQ chain is applied
            to the wet signal. Keys: low_freq, low_gain, mid_freq, mid_gain,
            mid_q, high_freq, high_gain, enabled.

    Returns:
        Dict with keys:
            dry             -- (possibly padded) input audio (np.ndarray)
            wet             -- processed audio (np.ndarray)
            ir              -- impulse response (np.ndarray)
            metrics         -- dict of str -> str (formatted metric values)
            figures         -- dict of str -> matplotlib.figure.Figure
            original_length -- length of audio before silence padding (int)

    Raises:
        KeyError: If algorithm_name is not in ALGORITHM_REGISTRY.
    """
    # Record pre-padding length for UI waveform boundary markers
    original_length = audio.shape[-1] if audio.ndim == 2 else len(audio)

    # Silence padding stage
    if silence_seconds > 0:
        audio = pad_with_silence(audio, silence_seconds)

    # Look up and instantiate algorithm
    algo_cls = ALGORITHM_REGISTRY[algorithm_name]
    algo = algo_cls()

    # Force mix to 100 so UI wet/dry controls the full blend
    forced_params = dict(params)
    forced_params["mix"] = 100

    # Process audio
    algo.update_params(forced_params)
    algo.reset()
    wet = algo.process(audio.copy())

    # EQ stage: apply 3-band EQ to wet signal if enabled
    if eq_params and eq_params.get("enabled"):
        wet = apply_eq(wet, eq_params)

    # Generate impulse response (reset state first since process() consumed it)
    algo.update_params(forced_params)
    algo.reset()
    ir = generate_impulse_response(algo, duration_seconds=3.0, mono=True)

    # Compute metrics
    rt60 = measure_rt60(ir, sr=SAMPLE_RATE)
    rt60_bands = measure_rt60_bands(ir, sr=SAMPLE_RATE)
    drr = compute_drr(ir, sr=SAMPLE_RATE)
    c80 = compute_clarity(ir, sr=SAMPLE_RATE, early_ms=80.0)
    c50 = compute_clarity(ir, sr=SAMPLE_RATE, early_ms=50.0)
    centroid_delta = spectral_centroid_delta(audio, wet, sr=SAMPLE_RATE)

    metrics = {
        "RT60": f"{rt60:.3f} s",
        "RT60 Bands": ", ".join(
            f"{band}: {val:.3f}s" for band, val in rt60_bands.items()
        ),
        "DRR": f"{drr:.1f} dB",
        "C80": f"{c80:.1f} dB",
        "C50": f"{c50:.1f} dB",
        "Centroid Delta": f"{centroid_delta:.1f} Hz",
    }

    # Generate comparison figures
    figures = {
        "mel": plot_mel_comparison(audio, wet, sr=SAMPLE_RATE),
        "fft": plot_fft_comparison(audio, wet, sr=SAMPLE_RATE),
    }

    return {
        "dry": audio,
        "wet": wet,
        "ir": ir,
        "metrics": metrics,
        "figures": figures,
        "original_length": original_length,
    }


def blend_wet_dry(
    dry: np.ndarray, wet: np.ndarray, mix_pct: int
) -> np.ndarray:
    """Blend dry and wet signals by percentage.

    Computes (1 - alpha) * dry + alpha * wet where alpha = mix_pct / 100.
    Hard clips result to [-1.0, 1.0].

    Args:
        dry: Dry (original) audio, any shape, float32.
        wet: Wet (processed) audio, same shape as dry, float32.
        mix_pct: Wet mix percentage, 0 = fully dry, 100 = fully wet.

    Returns:
        Blended float32 array, clipped to [-1.0, 1.0].
    """
    alpha = mix_pct / 100.0
    blended = (1.0 - alpha) * dry + alpha * wet
    clipped = np.clip(blended, -1.0, 1.0)
    return clipped.astype(np.float32)


def plot_waveform_comparison(
    dry: np.ndarray,
    wet: np.ndarray,
    sr: int = SAMPLE_RATE,
    padding_start_sample: int | None = None,
) -> plt.Figure:
    """Create a two-panel waveform comparison plot.

    Top panel shows input waveform, bottom panel shows output waveform.
    Stereo inputs are averaged to mono for display.

    Args:
        dry: Input audio, mono (N,) or stereo (2, N), float32.
        wet: Output audio, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.
        padding_start_sample: If provided, shade the region from this sample
            index to the end with light gray to indicate silence padding.

    Returns:
        matplotlib Figure with two subplots. Caller is responsible for closing.
    """
    # Mono-ize stereo inputs
    dry_mono = _ensure_mono(dry)
    wet_mono = _ensure_mono(wet)

    fig, axes = plt.subplots(2, 1, figsize=(10, 3.5), sharex=True)

    t_dry = np.arange(len(dry_mono)) / sr
    t_wet = np.arange(len(wet_mono)) / sr

    axes[0].plot(t_dry, dry_mono, linewidth=0.5)
    axes[0].set_title("Input")
    axes[0].set_ylabel("Amplitude")
    axes[0].set_ylim(-1, 1)

    axes[1].plot(t_wet, wet_mono, linewidth=0.5)
    axes[1].set_title("Output")
    axes[1].set_ylabel("Amplitude")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylim(-1, 1)

    # Shade padding region if padding was applied
    if padding_start_sample is not None:
        total_samples = max(len(dry_mono), len(wet_mono))
        if padding_start_sample < total_samples:
            boundary_s = padding_start_sample / sr
            end_s = total_samples / sr
            for ax in axes:
                ax.axvspan(
                    boundary_s, end_s,
                    alpha=0.15, color="gray", label="Padding",
                )
            axes[0].legend(loc="upper right", fontsize="small")

    fig.tight_layout()
    return fig


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """Average stereo (2, N) to mono (N,). Pass mono through unchanged."""
    if audio.ndim == 2 and audio.shape[0] == 2:
        return np.mean(audio, axis=0).astype(np.float32)
    return audio
