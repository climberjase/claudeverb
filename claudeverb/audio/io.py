"""Audio file I/O: load and save with automatic resampling to project sample rate."""

import logging

import librosa
import numpy as np
import soundfile as sf

from claudeverb.config import SAMPLE_RATE

logger = logging.getLogger(__name__)


def load(path: str) -> np.ndarray:
    """Load an audio file and resample to SAMPLE_RATE (48 kHz).

    Returns float32 ndarray with shape (N,) for mono or (2, N) for stereo.
    Files with more than 2 channels are reduced to the first 2 channels.
    Files longer than 60 seconds trigger a warning.

    Args:
        path: Path to audio file (WAV, AIFF, FLAC, OGG supported via librosa).

    Returns:
        Audio data as float32 ndarray.
    """
    # librosa.load with mono=False returns shape (channels, N) for multi-channel
    # and (N,) for mono files
    audio, sr = librosa.load(path, sr=SAMPLE_RATE, mono=False)
    audio = np.asarray(audio, dtype=np.float32)

    # Handle channel count
    if audio.ndim == 2:
        n_channels = audio.shape[0]
        if n_channels > 2:
            logger.warning(
                "File %s has %d channels; taking first 2.", path, n_channels
            )
            audio = audio[:2]
    # ndim == 1 is mono, return as-is

    # Warn for long files
    n_samples = audio.shape[-1]
    duration_s = n_samples / SAMPLE_RATE
    if duration_s > 60.0:
        logger.warning(
            "File %s is %.1f seconds long; consider trimming.", path, duration_s
        )

    return audio


def save(path: str, audio: np.ndarray, subtype: str = "FLOAT") -> None:
    """Save audio data to a WAV file.

    Args:
        path: Output file path.
        audio: Float32 ndarray, shape (N,) for mono or (2, N) for stereo.
        subtype: Soundfile subtype, e.g. "FLOAT" (32-bit float) or "PCM_24".
    """
    data = audio
    # Transpose stereo from our convention (2, N) to soundfile's (N, 2)
    if data.ndim == 2 and data.shape[0] == 2:
        data = data.T

    sf.write(path, data, SAMPLE_RATE, subtype=subtype)
