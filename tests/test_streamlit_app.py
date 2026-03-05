"""Integration tests for the ClaudeVerb Streamlit application.

Uses Streamlit's AppTest framework to verify the app loads correctly
and has the expected sidebar controls.
"""

import pytest
from streamlit.testing.v1 import AppTest


def test_app_loads_without_error():
    """App loads and runs without raising exceptions."""
    at = AppTest.from_file("claudeverb/streamlit_app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"App raised exception: {at.exception}"


def test_sidebar_has_algorithm_selector():
    """Sidebar contains an Algorithm selectbox."""
    at = AppTest.from_file("claudeverb/streamlit_app.py", default_timeout=30)
    at.run()
    selectboxes = at.selectbox
    algo_found = any("Algorithm" in sb.label for sb in selectboxes)
    assert algo_found, "Algorithm selectbox not found"


def test_sidebar_has_process_button():
    """Sidebar contains a Process button."""
    at = AppTest.from_file("claudeverb/streamlit_app.py", default_timeout=30)
    at.run()
    buttons = at.button
    process_found = any("Process" in b.label for b in buttons)
    assert process_found, "Process button not found"


def test_sidebar_has_knob_sliders():
    """Sidebar has at least 6 sliders (5 knobs + wet/dry)."""
    at = AppTest.from_file("claudeverb/streamlit_app.py", default_timeout=30)
    at.run()
    sliders = at.slider
    # Should have at least 6: room_size, damping, width, pre_delay, hf_damp + wet/dry
    assert len(sliders) >= 6, f"Expected at least 6 sliders, got {len(sliders)}"


def test_sidebar_has_switch_selectors():
    """Sidebar has 2 switch select_sliders (Freeze, Stereo Mode)."""
    at = AppTest.from_file("claudeverb/streamlit_app.py", default_timeout=30)
    at.run()
    select_sliders = at.select_slider
    assert len(select_sliders) >= 2, (
        f"Expected at least 2 select_sliders, got {len(select_sliders)}"
    )


def test_sidebar_has_audio_source_radio():
    """Sidebar has Audio Source radio with Bundled Sample and Upload File."""
    at = AppTest.from_file("claudeverb/streamlit_app.py", default_timeout=30)
    at.run()
    radios = at.radio
    source_found = any("Audio Source" in r.label for r in radios)
    assert source_found, "Audio Source radio not found"
