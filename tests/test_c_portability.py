"""Tests that all DSP primitives use only C-portable state.

Every value in a primitive's instance state must be one of:
- int (maps to int32/int64 in C)
- float or np.float32 or np.float64 (maps to float/double)
- np.ndarray with dtype=float32 (maps to float array in C struct)

No Python lists, dicts, strings, or other objects are allowed in state,
ensuring all primitives can be directly mapped to C structs.
"""

import numpy as np
import pytest

from claudeverb.algorithms.filters import (
    AllpassFilter,
    Biquad,
    CombFilter,
    DelayLine,
)

# Allowed types for C-struct-portable state
ALLOWED_TYPES = (int, float, np.float32, np.float64, np.ndarray)


def _check_state_portability(instance, class_name: str):
    """Check that all instance state values are C-portable types."""
    # Handle __slots__-based classes: collect slot values
    if hasattr(instance, "__slots__"):
        state = {}
        for slot in instance.__slots__:
            if hasattr(instance, slot):
                state[slot] = getattr(instance, slot)
    else:
        state = instance.__dict__

    for attr_name, value in state.items():
        # Recursively check sub-primitives (e.g. CombFilter._delay is a DelayLine)
        if hasattr(value, "__slots__") or hasattr(value, "__dict__"):
            sub_class = type(value).__name__
            _check_state_portability(value, f"{class_name}.{attr_name} ({sub_class})")
            continue

        assert isinstance(value, ALLOWED_TYPES), (
            f"{class_name}.{attr_name} is {type(value).__name__} = {value!r}, "
            f"expected one of {[t.__name__ for t in ALLOWED_TYPES]}"
        )

        # If ndarray, must be float32
        if isinstance(value, np.ndarray):
            assert value.dtype == np.float32, (
                f"{class_name}.{attr_name} is ndarray with dtype={value.dtype}, "
                f"expected float32"
            )


class TestCPortability:
    """All primitives store only C-portable state."""

    def test_delay_line_state(self):
        """DelayLine state is all fixed-size arrays/scalars."""
        dl = DelayLine(max_delay=64)
        _check_state_portability(dl, "DelayLine")

    def test_comb_filter_state(self):
        """CombFilter state is all fixed-size arrays/scalars."""
        cf = CombFilter(delay_length=1116, feedback=0.84, damp=0.2)
        _check_state_portability(cf, "CombFilter")

    def test_allpass_filter_state(self):
        """AllpassFilter state is all fixed-size arrays/scalars."""
        ap = AllpassFilter(delay_length=556, feedback=0.5)
        _check_state_portability(ap, "AllpassFilter")

    def test_biquad_state(self):
        """Biquad state is all fixed-size arrays/scalars."""
        bq = Biquad.lowpass(1000, 0.707)
        _check_state_portability(bq, "Biquad")
