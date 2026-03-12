"""Algorithm registry for claudeverb reverb algorithms."""

from claudeverb.algorithms.dattorro_plate import DattorroPlate
from claudeverb.algorithms.fdn_reverb import FDNReverb
from claudeverb.algorithms.freeverb import Freeverb

ALGORITHM_REGISTRY = {
    "freeverb": Freeverb,
    "dattorro_plate": DattorroPlate,
    "fdn": FDNReverb,
}

__all__ = ["ALGORITHM_REGISTRY", "DattorroPlate", "FDNReverb", "Freeverb"]
