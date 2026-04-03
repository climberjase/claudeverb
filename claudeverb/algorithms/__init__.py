"""Algorithm registry for claudeverb reverb algorithms."""

from claudeverb.algorithms.dattorro_plate import DattorroPlate
from claudeverb.algorithms.dattorro_single_loop import DattorroSingleLoop
from claudeverb.algorithms.fdn_reverb import FDNReverb
from claudeverb.algorithms.freeverb import Freeverb

ALGORITHM_REGISTRY = {
    "freeverb": Freeverb,
    "dattorro_plate": DattorroPlate,
    "fdn": FDNReverb,
    "dattorro_single_loop": DattorroSingleLoop,
}

__all__ = ["ALGORITHM_REGISTRY", "DattorroPlate", "DattorroSingleLoop", "FDNReverb", "Freeverb"]
