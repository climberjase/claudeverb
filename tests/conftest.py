"""Shared pytest fixtures for claudeverb tests."""

import numpy as np
import pytest

from claudeverb.config import BUFFER_SIZE, SAMPLE_RATE


@pytest.fixture
def impulse() -> np.ndarray:
    """Unit impulse signal: 1-second, float32, value 1.0 at sample 0."""
    signal = np.zeros(SAMPLE_RATE, dtype=np.float32)
    signal[0] = 1.0
    return signal


@pytest.fixture
def mono_sine() -> np.ndarray:
    """440 Hz sine wave, 1 second, float32."""
    t = np.arange(SAMPLE_RATE, dtype=np.float32) / SAMPLE_RATE
    return np.sin(2 * np.pi * 440.0 * t).astype(np.float32)


@pytest.fixture
def stereo_sine() -> np.ndarray:
    """440 Hz sine wave on both channels, shape (2, SAMPLE_RATE), float32."""
    t = np.arange(SAMPLE_RATE, dtype=np.float32) / SAMPLE_RATE
    mono = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    return np.stack([mono, mono])


@pytest.fixture
def short_impulse() -> np.ndarray:
    """Short unit impulse, 256 samples, for quick tests."""
    signal = np.zeros(256, dtype=np.float32)
    signal[0] = 1.0
    return signal


@pytest.fixture
def comb_ir() -> np.ndarray:
    """IR from CombFilter(delay_samples=1557, feedback=0.84, damp=0.0).

    3-second impulse processed through the comb filter in BUFFER_SIZE blocks.
    Analytical RT60 ~ 1.28s.
    """
    from claudeverb.algorithms.filters import CombFilter

    comb = CombFilter(delay_length=1557, feedback=0.84, damp=0.0)
    duration_samples = SAMPLE_RATE * 3  # 3 seconds
    impulse = np.zeros(duration_samples, dtype=np.float32)
    impulse[0] = 1.0

    output = np.zeros(duration_samples, dtype=np.float32)
    for start in range(0, duration_samples, BUFFER_SIZE):
        end = min(start + BUFFER_SIZE, duration_samples)
        block = impulse[start:end]
        output[start:end] = comb.process(block)

    return output
