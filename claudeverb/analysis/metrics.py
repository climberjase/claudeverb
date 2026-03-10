"""Numerical acoustic metrics for reverb analysis.

All functions accept mono (N,) or stereo (2, N) float32 arrays.
Stereo inputs are averaged to mono before analysis.

Functions:
    measure_rt60        -- Broadband RT60 via Schroeder backward integration (T30 extrapolation).
    measure_rt60_bands  -- Per-band RT60 for low, mid, high frequency ranges.
    compute_drr         -- Direct-to-Reverberant Ratio in dB.
    compute_clarity     -- Clarity index (C80 or C50) in dB.
    spectral_centroid_delta -- Spectral centroid difference between input/output in Hz.
"""

from __future__ import annotations

import numpy as np
import scipy.signal
import scipy.stats


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """Average stereo (2, N) to mono (N,). Pass mono through unchanged."""
    if audio.ndim == 2 and audio.shape[0] == 2:
        return np.mean(audio, axis=0).astype(np.float32)
    return audio


def measure_rt60(ir: np.ndarray, sr: int = 48000, decay_db: float = 60.0) -> float:
    """Measure RT60 using Schroeder backward integration with T30 extrapolation.

    Computes the energy decay curve (EDC) via backward integration of the
    squared impulse response. Fits a line to the -5 dB to -35 dB range
    (T30 region) and extrapolates to the full 60 dB decay time.

    Args:
        ir: Impulse response, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.
        decay_db: Target decay in dB (default 60).

    Returns:
        RT60 in seconds. Returns 0.0 if signal is too short or no
        measurable decay is found.
    """
    ir = _ensure_mono(ir)

    # Need at least a few hundred samples to measure any decay
    if len(ir) < 256:
        return 0.0

    # Schroeder backward integration: EDC(t) = integral from t to inf of h^2(tau) dtau
    energy = ir.astype(np.float64) ** 2
    edc = np.cumsum(energy[::-1])[::-1]

    # Avoid log of zero
    if edc[0] <= 0:
        return 0.0

    # Normalize and convert to dB
    edc_db = 10.0 * np.log10(edc / edc[0] + 1e-20)

    # Find the -5 dB and -35 dB points for T30 extrapolation
    idx_5 = np.searchsorted(-edc_db, 5.0)
    idx_35 = np.searchsorted(-edc_db, 35.0)

    # Need enough samples between the two points
    if idx_35 <= idx_5 + 10 or idx_35 >= len(edc_db):
        return 0.0

    # Linear regression on the T30 region
    t = np.arange(idx_5, idx_35, dtype=np.float64) / sr
    db_values = edc_db[idx_5:idx_35]

    slope, _intercept, _r, _p, _se = scipy.stats.linregress(t, db_values)

    if slope >= 0:
        return 0.0

    # Extrapolate to full 60 dB decay
    rt60 = -decay_db / slope
    return float(max(rt60, 0.0))


def measure_rt60_bands(
    ir: np.ndarray, sr: int = 48000
) -> dict[str, float]:
    """Measure RT60 in low, mid, and high frequency bands.

    Filters the IR into three bands using 4th-order Butterworth bandpass
    filters, then measures RT60 in each band.

    Bands:
        low:  125 - 500 Hz
        mid:  500 - 2000 Hz
        high: 2000 - 8000 Hz

    Args:
        ir: Impulse response, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.

    Returns:
        Dict with keys "low", "mid", "high", each mapping to RT60 in seconds.
    """
    ir = _ensure_mono(ir)
    nyquist = sr / 2.0

    bands = {
        "low": (125.0, 500.0),
        "mid": (500.0, 2000.0),
        "high": (2000.0, 8000.0),
    }

    result: dict[str, float] = {}
    for name, (lo, hi) in bands.items():
        # Clamp to just below Nyquist
        lo_norm = lo / nyquist
        hi_norm = min(hi / nyquist, 0.99)
        sos = scipy.signal.butter(4, [lo_norm, hi_norm], btype="band", output="sos")
        filtered = scipy.signal.sosfilt(sos, ir.astype(np.float64)).astype(np.float32)
        result[name] = measure_rt60(filtered, sr=sr)

    return result


def compute_drr(
    ir: np.ndarray, sr: int = 48000, direct_ms: float = 2.5
) -> float:
    """Compute Direct-to-Reverberant Ratio in dB.

    DRR = 10 * log10(E_direct / E_reverb)

    where E_direct is energy in the first `direct_ms` milliseconds and
    E_reverb is the remaining energy.

    Args:
        ir: Impulse response, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.
        direct_ms: Duration of direct sound window in milliseconds.

    Returns:
        DRR in dB. Returns +inf if reverberant energy is near zero.
    """
    ir = _ensure_mono(ir)
    boundary = int(sr * direct_ms / 1000.0)
    boundary = min(boundary, len(ir))

    direct_energy = float(np.sum(ir[:boundary].astype(np.float64) ** 2))
    reverb_energy = float(np.sum(ir[boundary:].astype(np.float64) ** 2))

    if reverb_energy < 1e-20:
        return float("inf")
    if direct_energy < 1e-20:
        return float("-inf")

    return float(10.0 * np.log10(direct_energy / reverb_energy))


def compute_clarity(
    ir: np.ndarray, sr: int = 48000, early_ms: float = 80.0
) -> float:
    """Compute clarity index (C80 or C50) in dB.

    Clarity = 10 * log10(E_early / E_late)

    where E_early is energy in the first `early_ms` milliseconds and
    E_late is the remaining energy.

    Args:
        ir: Impulse response, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.
        early_ms: Early reflection window in milliseconds (80 for C80, 50 for C50).

    Returns:
        Clarity in dB. Returns +inf if late energy is near zero.
    """
    ir = _ensure_mono(ir)
    boundary = int(sr * early_ms / 1000.0)
    boundary = min(boundary, len(ir))

    early_energy = float(np.sum(ir[:boundary].astype(np.float64) ** 2))
    late_energy = float(np.sum(ir[boundary:].astype(np.float64) ** 2))

    if late_energy < 1e-20:
        return float("inf")
    if early_energy < 1e-20:
        return float("-inf")

    return float(10.0 * np.log10(early_energy / late_energy))


def spectral_centroid_delta(
    input_audio: np.ndarray, output_audio: np.ndarray, sr: int = 48000
) -> float:
    """Compute spectral centroid difference between input and output.

    Uses librosa.feature.spectral_centroid to compute the mean spectral
    centroid of each signal, then returns the difference in Hz.

    Args:
        input_audio: Input signal, mono (N,) or stereo (2, N), float32.
        output_audio: Output signal, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.

    Returns:
        Delta in Hz (output centroid - input centroid). Positive means
        output is brighter, negative means darker.
    """
    import librosa

    inp = _ensure_mono(input_audio).astype(np.float32)
    out = _ensure_mono(output_audio).astype(np.float32)

    centroid_in = librosa.feature.spectral_centroid(y=inp, sr=sr)
    centroid_out = librosa.feature.spectral_centroid(y=out, sr=sr)

    mean_in = float(np.mean(centroid_in))
    mean_out = float(np.mean(centroid_out))

    return mean_out - mean_in
