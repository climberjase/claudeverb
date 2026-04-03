"""Algorithm registry for claudeverb reverb algorithms."""

from claudeverb.algorithms.dattorro_plate import DattorroPlate
from claudeverb.algorithms.dattorro_single_loop import DattorroSingleLoop
from claudeverb.algorithms.fdn_reverb import FDNReverb
from claudeverb.algorithms.freeverb import Freeverb
from claudeverb.algorithms.small_room import SmallRoom

ALGORITHM_REGISTRY = {
    "freeverb": Freeverb,
    "dattorro_plate": DattorroPlate,
    "fdn": FDNReverb,
    "dattorro_single_loop": DattorroSingleLoop,
    "small_room": SmallRoom,
}

__all__ = ["ALGORITHM_REGISTRY", "DattorroPlate", "DattorroSingleLoop", "FDNReverb", "Freeverb", "SmallRoom"]
