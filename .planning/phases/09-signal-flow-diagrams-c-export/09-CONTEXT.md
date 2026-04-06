# Phase 9: Signal-Flow Diagrams & C Export - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can visualize algorithm topology as signal-flow diagrams and export working C code for the Daisy Seed Hothouse pedal. Covers all 10 registered algorithms. No real-time playback (Phase 10), no new algorithms, no hardware flashing.

</domain>

<decisions>
## Implementation Decisions

### Diagram Rendering
- Graphviz DOT rendering via `st.graphviz_chart()`
- Two detail levels with toggle: block-level (~5-10 nodes showing major DSP stages) and component-level (~15-30 nodes showing individual delay lines, allpass filters, feedback paths)
- Live parameter values in diagram labels — diagram regenerates when knobs change (e.g., "DelayLine [601 samples]", "Feedback: 0.72")
- Diagram appears in a new expander/tab in the main content area alongside waveform/spectrogram views

### C Export Workflow
- "Export to C" button in sidebar below algorithm controls
- Exports currently selected algorithm with current knob settings
- Show generated .h and .c code in a preview (expander/code block) before writing to disk; user clicks "Save" to confirm
- Output files: `daisyexport/AlgorithmName.h` and `daisyexport/AlgorithmName.c` (re-exporting overwrites)
- Current parameter settings appear as both header comments and default values in an init function

### RAM Estimation
- Count delay line buffers (float32 * length), filter state variables (allpass, comb, OnePole, DCBlocker), and mixing matrices
- Detailed per-component breakdown: "Delay lines: 18.2 KB, Filters: 3.1 KB, Matrices: 0.5 KB, Total: 21.8 KB"
- Show fit indicator against both Daisy Seed SRAM (64 KB) and SDRAM (64 MB) thresholds
- Displayed in the export preview step, before the user saves files

### AudioCallback Template
- User-configurable knob-to-parameter mapping in the UI before export (drag-and-drop or dropdown assignment of which algorithm param goes to which physical Hothouse knob 1-6)
- Ready-to-compile AudioCallback: #include guards, Hothouse hardware init, ADC reads for knobs, GPIO reads for switches, process call, audio output
- Build instructions as header comments only (toolchain, compile flags, flash command) — no generated Makefile
- Python f-strings for C code generation (matches existing to_c_struct()/to_c_process_fn() pattern, no Jinja2 dependency)

### Claude's Discretion
- Graphviz DOT graph styling (colors, shapes, edge styles, layout direction)
- Exact node grouping for block-level vs component-level diagrams per algorithm
- Knob mapping UI widget choice (drag-and-drop vs dropdowns vs reorderable list)
- RAM estimation precision (whether to count padding/alignment)
- Export preview layout (tabs for .h/.c vs single scrollable view)
- Whether each algorithm needs a custom `to_dot()` method or if a generic graph builder can introspect algorithm structure

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `to_c_struct()` on all 10 algorithms: Returns C typedef struct string. Foundation for .h file generation.
- `to_c_process_fn()` on all 10 algorithms: Returns C process function string. Foundation for .c file generation.
- `param_specs` property on all algorithms: Dict of 6 knobs + 2 switches with min/max/default. Drives knob mapping UI and default value export.
- `st.graphviz_chart()`: Built-in Streamlit widget for rendering DOT graphs. No custom rendering needed.
- Streamlit sidebar pattern: Existing algorithm selector, knob controls, EQ toggle — export button fits naturally below.

### Established Patterns
- Algorithm registry (`ALGORITHM_REGISTRY` in `__init__.py`): Iterate all algorithms for diagram/export support
- Parameter interface: `param_specs` returns consistent dict structure across all algorithms — enables generic knob mapping UI
- C struct docstring convention: Each algorithm file starts with C struct typedef comment — can be used as reference for code generation
- Session state management: Streamlit `st.session_state` for persisting UI state (knob mapping, export preview)

### Integration Points
- Sidebar: Add "Export to C" button below algorithm controls
- Main content area: Add "Signal Flow" expander alongside waveform/spectrogram
- Each algorithm class: Add `to_dot(detail_level, params)` method returning DOT string
- New module: `claudeverb/export/c_export.py` for centralized export logic (file writing, RAM calculation, AudioCallback generation)
- `graphviz` Python package: New dependency for DOT rendering

</code_context>

<specifics>
## Specific Ideas

- Knob mapping defaults should match UI order (Knob 1 = first param spec) but user can rearrange before export
- RAM breakdown should clearly distinguish what can go in SRAM vs what needs SDRAM
- AudioCallback should reference Hothouse-specific pin definitions (from Cleveland Audio documentation)
- Block-level diagrams should be the default view — component-level is opt-in for DSP deep-dives
- Export preview is the natural place to show RAM breakdown alongside the generated code

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-signal-flow-diagrams-c-export*
*Context gathered: 2026-04-03*
