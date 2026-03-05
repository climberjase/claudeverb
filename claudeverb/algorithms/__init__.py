"""Algorithm registry for claudeverb reverb algorithms."""

from claudeverb.algorithms.freeverb import Freeverb

ALGORITHM_REGISTRY = {
    "freeverb": Freeverb,
}

__all__ = ["ALGORITHM_REGISTRY", "Freeverb"]
