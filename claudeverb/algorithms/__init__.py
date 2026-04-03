"""Algorithm registry for claudeverb reverb algorithms."""

from claudeverb.algorithms.chamber import Chamber
from claudeverb.algorithms.dattorro_plate import DattorroPlate
from claudeverb.algorithms.dattorro_single_loop import DattorroSingleLoop
from claudeverb.algorithms.dattorro_triple_diffuser import DattorroTripleDiffuser
from claudeverb.algorithms.fdn_reverb import FDNReverb
from claudeverb.algorithms.freeverb import Freeverb
from claudeverb.algorithms.large_room import LargeRoom
from claudeverb.algorithms.small_room import SmallRoom

ALGORITHM_REGISTRY = {
    "freeverb": Freeverb,
    "dattorro_plate": DattorroPlate,
    "fdn": FDNReverb,
    "dattorro_single_loop": DattorroSingleLoop,
    "dattorro_triple_diffuser": DattorroTripleDiffuser,
    "small_room": SmallRoom,
    "large_room": LargeRoom,
    "chamber": Chamber,
}

__all__ = [
    "ALGORITHM_REGISTRY",
    "Chamber",
    "DattorroPlate",
    "DattorroSingleLoop",
    "DattorroTripleDiffuser",
    "FDNReverb",
    "Freeverb",
    "LargeRoom",
    "SmallRoom",
]
