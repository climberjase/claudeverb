"""Impulse response generation from reverb algorithms.

Generates an IR by passing a unit impulse through a reverb algorithm,
capturing the full reverb tail for analysis (RT60, spectral analysis, etc.).
"""

from __future__ import annotations

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.config import SAMPLE_RATE


def generate_impulse_response(
    algorithm: ReverbAlgorithm,
    duration_seconds: float = 3.0,
    mono: bool = True,
) -> np.ndarray:
    """Generate an impulse response from a reverb algorithm.

    Creates a unit impulse, resets the algorithm for deterministic results,
    then processes the impulse to capture the full reverb tail.

    Args:
        algorithm: Any ReverbAlgorithm instance (e.g. Freeverb).
        duration_seconds: Length of the IR in seconds. Default 3.0s captures
            most reverb tails at typical settings.
        mono: If True, generate mono (N,) IR. If False, stereo (2, N).

    Returns:
        Float32 ndarray: shape (N,) if mono, (2, N) if stereo,
        where N = int(duration_seconds * SAMPLE_RATE).
    """
    n_samples = int(duration_seconds * SAMPLE_RATE)

    # Create unit impulse
    impulse = np.zeros(n_samples, dtype=np.float32)
    impulse[0] = 1.0

    # Stack to stereo if needed
    if not mono:
        impulse = np.stack([impulse, impulse.copy()])

    # Reset algorithm for deterministic results
    algorithm.reset()

    # Process and return
    result = algorithm.process(impulse)
    return result
