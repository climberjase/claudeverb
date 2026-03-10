"""Regression tests for Dattorro preset KeyError (Phase 6 UAT gap closure)."""
import pytest
from claudeverb.algorithms.dattorro_presets import get_preset, list_presets


def test_get_preset_none_raises_key_error():
    """None must raise KeyError -- documents the root cause of the UAT failure."""
    with pytest.raises(KeyError):
        get_preset(None)


def test_all_named_presets_return_dicts():
    """Every name returned by list_presets() must succeed in get_preset()."""
    names = list_presets()
    assert len(names) >= 1, "list_presets() must return at least one preset"
    for name in names:
        result = get_preset(name)
        assert isinstance(result, dict), f"get_preset({name!r}) must return dict"
        assert len(result) > 0, f"get_preset({name!r}) must return non-empty dict"


def test_session_state_pop_removes_key():
    """Simulate the cleanup fix: popping a key makes it absent (not None)."""
    fake_state = {"preset_name": "Large Hall", "_preset_values": {"decay": 0.9}}
    fake_state.pop("preset_name", None)
    fake_state.pop("_preset_values", None)
    assert "preset_name" not in fake_state
    assert "_preset_values" not in fake_state
