---
status: diagnosed
trigger: "KeyError when selecting Dattorro Plate preset in Streamlit UI"
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - see Resolution below
test: static code analysis of both files
expecting: n/a
next_action: report delivered to user

## Symptoms

expected: Selecting a Dattorro Plate preset from the dropdown loads the preset values without error
actual: KeyError raised at `claudeverb/algorithms/dattorro_presets.py:93` inside `get_preset()`
errors: |
  File "claudeverb/streamlit_app.py", line 125
      preset_vals = get_preset(preset_name)
  File "claudeverb/algorithms/dattorro_presets.py", line 93
      return dict(DATTORRO_PRESETS[name])
  KeyError
reproduction: Switch to Dattorro Plate algorithm; select any named preset from the dropdown
started: Unknown; likely triggered consistently on algorithm switch followed by preset selection

## Eliminated

- hypothesis: Key name mismatch between list_presets() output and DATTORRO_PRESETS keys
  evidence: list_presets() calls `sorted(DATTORRO_PRESETS.keys())` and the selectbox
            uses that directly - same keys, no transformation applied
  timestamp: 2026-03-09

- hypothesis: Dropdown contains extra names not in DATTORRO_PRESETS
  evidence: preset_options = ["Custom"] + list_presets() — list_presets() only ever
            returns existing keys; "Custom" is guarded by `if preset_name != "Custom"`
  timestamp: 2026-03-09

## Evidence

- timestamp: 2026-03-09
  checked: claudeverb/algorithms/dattorro_presets.py — DATTORRO_PRESETS keys
  found: |
    Keys (unsorted): "Small Plate", "Large Hall", "Bright Room",
    "Dark Chamber", "Shimmer Pad", "Frozen Space"
    list_presets() returns these sorted:
    ["Bright Room", "Dark Chamber", "Frozen Space", "Large Hall", "Shimmer Pad", "Small Plate"]
  implication: The preset names themselves are well-formed and consistent

- timestamp: 2026-03-09
  checked: claudeverb/streamlit_app.py lines 96-125 — algorithm-switch cleanup and selectbox
  found: |
    On algorithm switch (line 101):
        st.session_state["preset_name"] = None
    This sets the key to None (not deletes it).

    The selectbox (lines 115-121) uses `key="preset_name"`.
    In Streamlit, when a widget key already exists in session_state, the widget's
    rendered value is the session_state value — not the `index` argument.
    The `index` argument is IGNORED when the key is already present.

    After the algorithm switch + st.rerun(), session_state["preset_name"] == None.
    The selectbox therefore renders with value None.
    The local variable `preset_name` on line 121 is bound to None.

    Line 124: `if preset_name != "Custom"` evaluates True (None != "Custom").
    Line 125: `get_preset(None)` is called.
    Line 93 in dattorro_presets.py: `DATTORRO_PRESETS[None]` — KeyError.
  implication: Root cause confirmed. The bug is triggered whenever session_state["preset_name"]
               is None and the Dattorro Plate algorithm is active.

- timestamp: 2026-03-09
  checked: Streamlit widget key/value contract
  found: |
    When `key=` is passed to st.selectbox, Streamlit writes the selected value
    back to session_state[key] after each interaction. But on first render of
    that widget, if the key already exists in session_state, Streamlit uses
    that existing value as the widget's current value, bypassing `index`.
    Setting session_state["preset_name"] = None before rendering the selectbox
    causes the selectbox to hold None as its value.
  implication: The guard `index=... if ... in preset_options else 0` on lines 117-119
               has no effect when the key is already in session_state.

## Resolution

root_cause: |
  When the user switches away from Dattorro Plate and back (or loads the page
  fresh after a prior session), the cleanup block at line 101 sets
  `st.session_state["preset_name"] = None`.

  On the next render, the st.selectbox at line 115 uses `key="preset_name"`.
  Because Streamlit respects existing session_state values over the `index`
  argument, the selectbox is bound to None — a value not in `preset_options`.
  The local variable `preset_name` becomes None.

  The guard `if preset_name != "Custom"` on line 124 is True (None != "Custom"),
  so `get_preset(None)` is called. Inside get_preset(), the lookup
  `DATTORRO_PRESETS[None]` raises KeyError because None is not a key in the dict.

fix: NOT APPLIED (diagnose-only mode)

  Suggested fix directions:
  1. Change the cleanup on line 101 to DELETE the key instead of setting it None:
       st.session_state.pop("preset_name", None)
     This lets the `index=0` fallback take effect, rendering "Custom" by default.

  2. OR add a None-guard before calling get_preset():
       if preset_name is not None and preset_name != "Custom":

  Option 1 is cleaner because it addresses the root cause (stale None in session_state)
  rather than papering over it downstream.

verification: NOT PERFORMED (diagnose-only mode)
files_changed: []
