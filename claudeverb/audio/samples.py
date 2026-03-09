"""Bundled test sample generation for the ClaudeVerb workbench.

Provides analysis-oriented signals (impulse, noise, sweep) and instrument-like
synthesized clips (drums, guitar, vocals) for listening evaluation.
All generated signals are float32 at SAMPLE_RATE (48 kHz).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.signal import chirp, butter, sosfilt

from claudeverb.config import SAMPLE_RATE

# Path to the bundled WAV samples directory
_SAMPLES_DIR = Path(__file__).parent.parent / "samples"


# ---------------------------------------------------------------------------
# Analysis signals
# ---------------------------------------------------------------------------


def generate_impulse_click(duration_s: float = 1.0) -> np.ndarray:
    """Unit impulse at sample 0, zeros elsewhere.

    Args:
        duration_s: Duration in seconds.

    Returns:
        Float32 array of length int(SAMPLE_RATE * duration_s).
    """
    n = int(SAMPLE_RATE * duration_s)
    out = np.zeros(n, dtype=np.float32)
    out[0] = 1.0
    return out


def generate_white_noise_burst(
    duration_s: float = 0.5, burst_s: float = 0.1
) -> np.ndarray:
    """White noise burst followed by silence.

    Args:
        duration_s: Total duration in seconds.
        burst_s: Duration of the noise burst in seconds.

    Returns:
        Float32 array with noise (amplitude 0.5) in the burst region, zeros after.
    """
    n = int(SAMPLE_RATE * duration_s)
    burst_n = int(SAMPLE_RATE * burst_s)
    rng = np.random.default_rng(42)
    out = np.zeros(n, dtype=np.float32)
    out[:burst_n] = (rng.uniform(-1.0, 1.0, burst_n) * 0.5).astype(np.float32)
    return out


def generate_sine_sweep(
    duration_s: float = 2.0, f_start: float = 20.0, f_end: float = 20000.0
) -> np.ndarray:
    """Logarithmic chirp from f_start to f_end.

    Args:
        duration_s: Duration in seconds.
        f_start: Start frequency in Hz.
        f_end: End frequency in Hz.

    Returns:
        Float32 array with amplitude 0.8.
    """
    n = int(SAMPLE_RATE * duration_s)
    t = np.arange(n) / SAMPLE_RATE
    sig = chirp(t, f0=f_start, f1=f_end, t1=duration_s, method="logarithmic")
    return (sig * 0.8).astype(np.float32)


# ---------------------------------------------------------------------------
# Instrument-like clips
# ---------------------------------------------------------------------------


def generate_drum_transient(duration_s: float = 0.5) -> np.ndarray:
    """Synthesized kick/snare-like percussive transient.

    Band-limited noise (200-8000 Hz) with fast exponential decay envelope.

    Args:
        duration_s: Duration in seconds.

    Returns:
        Float32 array with amplitude up to 0.9.
    """
    n = int(SAMPLE_RATE * duration_s)
    rng = np.random.default_rng(123)
    noise = rng.uniform(-1.0, 1.0, n)

    # Bandpass filter 200-8000 Hz
    sos = butter(4, [200.0, 8000.0], btype="bandpass", fs=SAMPLE_RATE, output="sos")
    filtered = sosfilt(sos, noise)

    # Fast exponential decay envelope (tau ~0.02s)
    tau = 0.02
    t = np.arange(n) / SAMPLE_RATE
    envelope = np.exp(-t / tau)

    result = filtered * envelope
    # Normalize peak to 0.9
    peak = np.max(np.abs(result))
    if peak > 0:
        result = result * (0.9 / peak)

    return result.astype(np.float32)


def generate_guitar_pluck(
    duration_s: float = 1.5, frequency: float = 220.0
) -> np.ndarray:
    """Karplus-Strong plucked string synthesis.

    Initializes a delay buffer with random noise, then iteratively averages
    adjacent samples with a decay factor for a realistic plucked-string timbre.

    Args:
        duration_s: Duration in seconds.
        frequency: Fundamental frequency in Hz.

    Returns:
        Float32 array with peak normalized to 0.8.
    """
    n = int(SAMPLE_RATE * duration_s)
    delay_len = int(SAMPLE_RATE / frequency)
    if delay_len < 2:
        delay_len = 2

    rng = np.random.default_rng(77)
    buf = rng.uniform(-1.0, 1.0, delay_len).astype(np.float64)

    out = np.zeros(n, dtype=np.float64)
    decay = 0.996
    idx = 0

    for i in range(n):
        out[i] = buf[idx]
        # Average adjacent samples with decay
        next_idx = (idx + 1) % delay_len
        buf[idx] = decay * 0.5 * (buf[idx] + buf[next_idx])
        idx = next_idx

    # Normalize peak to 0.8
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out * (0.8 / peak)

    return out.astype(np.float32)


def generate_vocal_tone(
    duration_s: float = 2.0, fundamental: float = 180.0
) -> np.ndarray:
    """Synthesized vowel-like tone with formant filtering.

    Generates a sawtooth wave at the fundamental frequency, then applies
    two bandpass filters at F1 (~700 Hz) and F2 (~1200 Hz) to approximate
    an "ah" vowel.

    Args:
        duration_s: Duration in seconds.
        fundamental: Fundamental frequency in Hz.

    Returns:
        Float32 array with peak normalized to 0.7.
    """
    n = int(SAMPLE_RATE * duration_s)
    t = np.arange(n) / SAMPLE_RATE

    # Sawtooth wave
    phase = (t * fundamental) % 1.0
    sawtooth = 2.0 * phase - 1.0

    # Formant filters (bandpass using second-order sections)
    # F1: ~700 Hz, bandwidth ~130 Hz
    f1_low = 700.0 - 65.0
    f1_high = 700.0 + 65.0
    sos_f1 = butter(2, [f1_low, f1_high], btype="bandpass", fs=SAMPLE_RATE, output="sos")

    # F2: ~1200 Hz, bandwidth ~70 Hz
    f2_low = 1200.0 - 35.0
    f2_high = 1200.0 + 35.0
    sos_f2 = butter(2, [f2_low, f2_high], btype="bandpass", fs=SAMPLE_RATE, output="sos")

    # Apply both formant filters and sum
    formant1 = sosfilt(sos_f1, sawtooth)
    formant2 = sosfilt(sos_f2, sawtooth)
    result = formant1 + formant2

    # Amplitude envelope: 0.1s attack, 0.2s release
    attack_n = int(SAMPLE_RATE * 0.1)
    release_n = int(SAMPLE_RATE * 0.2)
    envelope = np.ones(n, dtype=np.float64)
    if attack_n > 0:
        envelope[:attack_n] = np.linspace(0.0, 1.0, attack_n)
    if release_n > 0:
        release_start = max(0, n - release_n)
        envelope[release_start:] = np.linspace(1.0, 0.0, n - release_start)

    result = result * envelope

    # Normalize peak to 0.7
    peak = np.max(np.abs(result))
    if peak > 0:
        result = result * (0.7 / peak)

    return result.astype(np.float32)


# ---------------------------------------------------------------------------
# Sample registry
# ---------------------------------------------------------------------------

SAMPLE_REGISTRY: dict[str, callable] = {
    "impulse": generate_impulse_click,
    "white_noise_burst": generate_white_noise_burst,
    "sine_sweep": generate_sine_sweep,
    "drum": generate_drum_transient,
    "guitar": generate_guitar_pluck,
    "vocal": generate_vocal_tone,
}


def get_sample(name: str) -> np.ndarray:
    """Look up a sample by name and generate or load it.

    Supports both synthesized samples (from SAMPLE_REGISTRY) and WAV files
    from the samples directory (names ending with " [WAV]").

    Args:
        name: Sample name (e.g. "impulse", "drum", "audio1-acoustic [WAV]").

    Returns:
        Float32 ndarray of the sample audio.

    Raises:
        ValueError: If name is not in the registry and not a valid WAV sample.
    """
    # WAV file path handling
    if name.endswith(" [WAV]"):
        stem = name[: -len(" [WAV]")]
        wav_path = _SAMPLES_DIR / f"{stem}.wav"
        if not wav_path.exists():
            raise ValueError(
                f"Unknown sample '{name}'. WAV file not found: {wav_path}"
            )
        from claudeverb.audio.io import load

        audio = load(str(wav_path))
        # If stereo, return left channel (mono) for consistency with synthesized samples
        if audio.ndim == 2:
            audio = audio[0]
        return audio

    if name not in SAMPLE_REGISTRY:
        raise ValueError(
            f"Unknown sample '{name}'. Available: {sorted(SAMPLE_REGISTRY.keys())}"
        )
    return SAMPLE_REGISTRY[name]()


def list_samples() -> list[str]:
    """Return sorted list of all synthesized sample names."""
    return sorted(SAMPLE_REGISTRY.keys())


def list_wav_samples() -> list[str]:
    """Return sorted list of WAV file stems in the samples directory.

    Returns:
        List of stem names (e.g. ["audio1-acoustic", "audio1-bass", ...]).
    """
    if not _SAMPLES_DIR.is_dir():
        return []
    return sorted(p.stem for p in _SAMPLES_DIR.glob("*.wav"))


def list_all_samples() -> list[str]:
    """Return sorted list of all available samples (synthesized + WAV).

    WAV samples are labeled with " [WAV]" suffix to distinguish them
    from synthesized samples.

    Returns:
        Sorted list combining synthesized names and WAV names with labels.
    """
    synth = list(SAMPLE_REGISTRY.keys())
    wav = [f"{stem} [WAV]" for stem in list_wav_samples()]
    return sorted(synth + wav)
