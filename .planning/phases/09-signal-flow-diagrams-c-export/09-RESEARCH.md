# Phase 9: Signal-Flow Diagrams & C Export - Research

**Researched:** 2026-04-03
**Domain:** Graphviz DOT rendering in Streamlit, C code generation for Daisy Seed / Hothouse pedal
**Confidence:** HIGH

## Summary

This phase adds two major features: signal-flow diagram visualization via Graphviz DOT and C code export targeting the Cleveland Music Co. Hothouse pedal (Daisy Seed platform). The codebase already has `to_c_struct()` and `to_c_process_fn()` on 7 of 9 algorithm classes (FDN, RoomReverbBase covering SmallRoom/LargeRoom/Chamber, DattorroSingleLoop, DattorroTripleDiffuser, DattorroAsymmetric). Two algorithms still need these methods: Freeverb and DattorroPlate. Both already have C struct comments in their docstrings that serve as reference.

Streamlit's `st.graphviz_chart()` accepts raw DOT strings directly, rendering via dagre-d3 on the frontend. The `graphviz>=0.19.0` Python package is required as a dependency. Each algorithm will need a `to_dot(detail_level, params)` method that returns a DOT string. The Hothouse pedal has 6 knobs (KNOB_1-6), 3 toggle switches (TOGGLESWITCH_1-3), 2 footswitches, and 2 LEDs -- matching the existing `param_specs` pattern of 6 knobs + 2 switches per algorithm.

**Primary recommendation:** Add `to_dot()` to each algorithm class (or a generic introspection-based builder), add `to_c_struct()`/`to_c_process_fn()` to Freeverb and DattorroPlate, then build the export module and UI integration.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Graphviz DOT rendering via `st.graphviz_chart()`
- Two detail levels with toggle: block-level (~5-10 nodes) and component-level (~15-30 nodes)
- Live parameter values in diagram labels, regenerating when knobs change
- Diagram appears in a new expander/tab in the main content area
- "Export to C" button in sidebar below algorithm controls
- Show generated .h and .c code in a preview before writing to disk
- Output files: `daisyexport/AlgorithmName.h` and `daisyexport/AlgorithmName.c`
- Current parameter settings as both header comments and default values in init function
- RAM estimation counting delay line buffers, filter states, mixing matrices
- Detailed per-component breakdown with fit indicator against SRAM (512 KB) and SDRAM (64 MB)
- User-configurable knob-to-parameter mapping in the UI before export
- Ready-to-compile AudioCallback with Hothouse hardware init, ADC reads, GPIO reads
- Build instructions as header comments only, no generated Makefile
- Python f-strings for C code generation (no Jinja2)

### Claude's Discretion
- Graphviz DOT graph styling (colors, shapes, edge styles, layout direction)
- Exact node grouping for block-level vs component-level diagrams per algorithm
- Knob mapping UI widget choice (drag-and-drop vs dropdowns vs reorderable list)
- RAM estimation precision (whether to count padding/alignment)
- Export preview layout (tabs for .h/.c vs single scrollable view)
- Whether each algorithm needs a custom `to_dot()` method or if a generic graph builder can introspect algorithm structure

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIZ-01 | User can view signal-flow diagram for each algorithm rendered via Graphviz in the UI | `st.graphviz_chart()` accepts raw DOT strings; each algorithm needs `to_dot()` method; `graphviz>=0.19.0` required |
| EXP-01 | User can export algorithm as working .c and .h files to /daisyexport via UI button | 7/9 algorithms already have `to_c_struct()`/`to_c_process_fn()`; need Freeverb + DattorroPlate; new `export/c_export.py` module |
| EXP-02 | Exported C code includes current parameter settings as default values in comments | Existing methods return static strings; need to parameterize with current knob values |
| EXP-03 | User can see estimated RAM usage (KB) before exporting | Count float buffer sizes from struct definitions; Daisy Seed has 512 KB SRAM + 64 MB SDRAM |
| EXP-04 | Exported C code includes Daisy Seed AudioCallback template for Hothouse pedal | Hothouse has 6 knobs + 3 toggles + 2 footswitches + 2 LEDs; uses `hothouse.h` + `daisysp.h` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| graphviz | >=0.19.0 | Python package for DOT string construction | Required by `st.graphviz_chart()`; adds type-safe graph building |
| streamlit | >=1.38 (existing) | `st.graphviz_chart()` renders DOT | Already in project dependencies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none) | -- | -- | All other needs met by stdlib |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| graphviz Python pkg | Raw DOT strings | Raw strings work fine; `st.graphviz_chart()` accepts both. Raw strings are simpler for this use case since the DOT is generated programmatically anyway |
| Jinja2 for C codegen | Python f-strings | User decision: f-strings match existing `to_c_struct()`/`to_c_process_fn()` pattern |

**Installation:**
```bash
pip install graphviz>=0.19.0
```

Note: The `graphviz` Python package also requires the Graphviz system binary (`dot`) to be installed. However, `st.graphviz_chart()` renders using dagre-d3 on the frontend, so the system binary is needed only if using the Python package's render methods (not needed for our use case of passing DOT strings to Streamlit).

## Architecture Patterns

### Recommended Project Structure
```
claudeverb/
├── algorithms/
│   ├── base.py              # Add abstract to_dot() to ReverbAlgorithm
│   ├── freeverb.py          # Add to_c_struct(), to_c_process_fn(), to_dot()
│   ├── dattorro_plate.py    # Add to_c_struct(), to_c_process_fn(), to_dot()
│   ├── [all others]         # Add to_dot() methods
│   └── ...
├── export/
│   ├── __init__.py
│   ├── c_export.py          # File writing, AudioCallback generation, RAM estimation
│   └── dot_builder.py       # Optional: shared DOT graph construction helpers
├── streamlit_app.py          # Add signal flow tab + export sidebar section
└── ...
daisyexport/                  # Output directory for exported C files
```

### Pattern 1: Algorithm `to_dot()` Method
**What:** Each algorithm class implements `to_dot(detail_level: str, params: dict) -> str` returning a DOT-language string.
**When to use:** Every algorithm must have this for VIZ-01.
**Example:**
```python
# Per-algorithm method
def to_dot(self, detail_level: str = "block", params: dict | None = None) -> str:
    """Return Graphviz DOT string for this algorithm's signal flow.

    Args:
        detail_level: "block" for ~5-10 nodes, "component" for ~15-30 nodes.
        params: Current parameter values for labels. Uses defaults if None.

    Returns:
        DOT language string suitable for st.graphviz_chart().
    """
    if detail_level == "block":
        return self._block_dot(params)
    return self._component_dot(params)
```

### Pattern 2: C Export Module
**What:** Centralized module handling file generation, RAM calculation, and AudioCallback templating.
**When to use:** All C export operations.
**Example:**
```python
# claudeverb/export/c_export.py
def generate_header(algo, params: dict, knob_mapping: dict) -> str:
    """Generate .h file content with #include guards, struct, and init prototype."""
    name = type(algo).__name__
    c_struct = algo.to_c_struct()
    return f"""\
#ifndef {name.upper()}_H
#define {name.upper()}_H

/*
 * Generated by ClaudeVerb
 * Algorithm: {name}
 * Parameters at export time:
{_format_params_comment(params)}
 */

{c_struct}

void {_snake_case(name)}_init({name}State* state);
void {_snake_case(name)}_process({name}State* state,
    const float* input, float* output_left, float* output_right,
    int num_samples);

#endif // {name.upper()}_H
"""

def estimate_ram(algo) -> dict:
    """Estimate RAM usage from algorithm's delay line and filter state sizes.

    Returns dict with 'delay_lines_kb', 'filters_kb', 'total_kb',
    'fits_sram' (< 512 KB), 'fits_sdram' (< 64 MB).
    """
```

### Pattern 3: Hothouse AudioCallback Template
**What:** Generate a complete main.cpp-style file with Hothouse initialization and knob mapping.
**When to use:** EXP-04 -- the AudioCallback template.
**Example:**
```python
def generate_audio_callback(algo, knob_mapping: dict) -> str:
    """Generate Hothouse-compatible AudioCallback template.

    knob_mapping: dict mapping Hothouse knob/switch names to algorithm param names.
        e.g. {"KNOB_1": "decay", "KNOB_2": "damping", ...}
    """
    return f"""\
#include "daisysp.h"
#include "hothouse.h"
#include "{type(algo).__name__}.h"

using clevelandmusicco::Hothouse;

Hothouse hw;
{type(algo).__name__}State state;
Parameter knobs[6];
bool bypass = true;

void AudioCallback(AudioHandle::InputBuffer in, AudioHandle::OutputBuffer out,
                   size_t size) {{
    hw.ProcessAllControls();

    // Read knobs -> algorithm parameters
{_generate_knob_reads(knob_mapping)}

    // Process audio
    {_snake_case(type(algo).__name__)}_process(&state, in[0], out[0], out[1], size);
}}

int main(void) {{
    hw.Init();
    hw.SetAudioBlockSize(48);
    hw.SetAudioSampleRate(SaiHandle::Config::SampleRate::SAI_48KHZ);

    {_snake_case(type(algo).__name__)}_init(&state);

{_generate_knob_inits(knob_mapping)}

    hw.StartAudio(AudioCallback);
    while (1) {{ }}
}}
"""
```

### Anti-Patterns to Avoid
- **Generating C code by string concatenation across multiple files:** Keep all C generation in the algorithm's own methods (`to_c_struct()`, `to_c_process_fn()`) and a single export module. Do not scatter C code templates across the codebase.
- **Dynamic buffer sizing in generated C:** All delay line buffers must be compile-time constants. Never generate `malloc()` or `calloc()` calls.
- **Hardcoding knob mappings:** The user must be able to rearrange which algorithm parameter maps to which physical Hothouse knob. Default to `param_specs` order but allow override.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOT graph rendering | Custom SVG/canvas renderer | `st.graphviz_chart()` + raw DOT strings | Built into Streamlit, handles layout automatically |
| C syntax validation | Custom C parser | Simple string assertions (typedef present, no malloc) | Full C parsing is enormous scope; basic checks sufficient |
| Hothouse hardware abstraction | Custom pin definitions | Reference `hothouse.h` include | Cleveland Music Co. maintains the official header |

## Common Pitfalls

### Pitfall 1: Missing `to_c_struct()` on Freeverb and DattorroPlate
**What goes wrong:** Export button fails for 2 of 9 algorithms.
**Why it happens:** These were implemented in earlier phases before the C export pattern was established.
**How to avoid:** Add `to_c_struct()` and `to_c_process_fn()` to both before building the export UI.
**Warning signs:** `AttributeError` when exporting Freeverb or DattorroPlate.

### Pitfall 2: RAM Estimation Undercount
**What goes wrong:** Estimated RAM is lower than actual C compilation shows.
**Why it happens:** Forgetting to count: filter state variables (OnePole, DCBlocker have 2-3 floats each), write index integers, LFO phase state, pre-delay buffers. Also struct padding/alignment can add 5-15%.
**How to avoid:** Parse the `to_c_struct()` output to count all `float[]` and `int[]` declarations. Add 10% padding overhead for struct alignment.
**Warning signs:** Estimated < 50% of actual compiled size.

### Pitfall 3: Stale Diagrams After Parameter Change
**What goes wrong:** Diagram shows old parameter values after user moves a knob.
**Why it happens:** DOT string was cached or generated only on "Process" click.
**How to avoid:** Regenerate DOT string on every Streamlit rerun (which happens automatically when any widget changes). The `to_dot()` call is cheap (string formatting only).
**Warning signs:** Diagram labels don't match current slider positions.

### Pitfall 4: DOT String Escaping Issues
**What goes wrong:** Graphviz rendering fails or shows garbled labels.
**Why it happens:** Special characters in parameter labels (quotes, braces, angle brackets).
**How to avoid:** Escape all user-facing text in DOT labels. Use `\"` for quotes, avoid HTML-like labels unless needed.
**Warning signs:** Graphviz parse errors in browser console.

### Pitfall 5: `st.graphviz_chart` with `use_container_width=True`
**What goes wrong:** Chart renders blank or fails.
**Why it happens:** Known regression in Streamlit 1.40.0 (GitHub issue #9866).
**How to avoid:** Do not use `use_container_width=True`. Use `width="stretch"` instead (newer API).
**Warning signs:** Empty graph area in the UI.

### Pitfall 6: Daisy Seed SRAM vs SDRAM Confusion
**What goes wrong:** User thinks algorithm doesn't fit, or puts too-large buffers in SRAM.
**Why it happens:** Daisy Seed has 512 KB SRAM (fast, limited) and 64 MB SDRAM (slower, large). Large delay buffers should go in SDRAM via `DSY_SDRAM_BSS` attribute.
**How to avoid:** RAM breakdown should distinguish SRAM-appropriate (< 512 KB total) vs SDRAM-needed (large delay buffers). Add `DSY_SDRAM_BSS` attribute hint in generated code for large buffers.
**Warning signs:** Algorithm state exceeds 512 KB when it could fit with SDRAM offloading.

## Code Examples

### Existing `to_c_struct()` Pattern (from fdn_reverb.py)
```python
# Source: claudeverb/algorithms/fdn_reverb.py:529-578
def to_c_struct(self) -> str:
    return """\
typedef struct {
    float delay_buf_0[1265];   // BASE_DELAYS[0] + MAX_MOD_EXCURSION + 2
    float delay_buf_1[1437];
    // ... fixed-size buffers, scalars, write indices
    int sample_rate;
    int frozen;
    float width;
} FDNReverbState;
"""
```

### Existing `to_c_process_fn()` Pattern (from fdn_reverb.py)
```python
# Source: claudeverb/algorithms/fdn_reverb.py:580-640+
def to_c_process_fn(self) -> str:
    return """\
void fdn_reverb_process(FDNReverbState* state, const float* input,
                        float* output_left, float* output_right,
                        int num_samples) {
    // ... sample-by-sample processing with circular buffers
}
"""
```

### Hothouse AudioCallback Pattern (from HothouseExamples)
```cpp
// Source: github.com/clevelandmusicco/HothouseExamples
#include "daisysp.h"
#include "hothouse.h"

using clevelandmusicco::Hothouse;
Hothouse hw;

// 6 knobs: KNOB_1 through KNOB_6
// 3 toggle switches: TOGGLESWITCH_1 through TOGGLESWITCH_3
// 2 footswitches: FOOTSWITCH_1, FOOTSWITCH_2
// 2 LEDs: LED_1, LED_2

Parameter knob1;

void AudioCallback(AudioHandle::InputBuffer in, AudioHandle::OutputBuffer out,
                   size_t size) {
    hw.ProcessAllControls();
    float val = knob1.Process();
    // ... process audio
}

int main(void) {
    hw.Init();
    hw.SetAudioBlockSize(4);  // or 48 for claudeverb's BUFFER_SIZE
    hw.SetAudioSampleRate(SaiHandle::Config::SampleRate::SAI_48KHZ);
    knob1.Init(hw.knobs[Hothouse::KNOB_1], 0.0f, 1.0f, Parameter::LINEAR);
    hw.StartAudio(AudioCallback);
    while (1) { }
}
```

### DOT String for Signal Flow (block-level example)
```python
def _block_dot(self, params: dict) -> str:
    decay = params.get("decay", 50)
    return f'''\
digraph FreeverbBlock {{
    rankdir=LR;
    node [shape=box, style=rounded, fontname="Arial"];

    input [label="Input", shape=ellipse];
    predelay [label="Pre-Delay\\n{params.get('pre_delay', 0)} ms"];
    combs [label="8 Parallel\\nComb Filters\\nRoom: {params.get('room_size', 75)}"];
    allpasses [label="4 Series\\nAllpass Filters"];
    output [label="Output\\n(Stereo)", shape=ellipse];

    input -> predelay -> combs -> allpasses -> output;
}}'''
```

### RAM Estimation Logic
```python
import re

def estimate_ram_from_struct(c_struct: str) -> dict:
    """Parse a C struct string and estimate RAM usage."""
    float_arrays = re.findall(r'float\s+\w+\[(\d+)\]', c_struct)
    int_arrays = re.findall(r'int\s+\w+\[(\d+)\]', c_struct)
    float_scalars = len(re.findall(r'float\s+\w+;', c_struct))
    int_scalars = len(re.findall(r'int\s+\w+;', c_struct))

    float_array_bytes = sum(int(n) * 4 for n in float_arrays)
    int_array_bytes = sum(int(n) * 4 for n in int_arrays)
    scalar_bytes = (float_scalars + int_scalars) * 4

    total = float_array_bytes + int_array_bytes + scalar_bytes
    return {
        "delay_lines_kb": float_array_bytes / 1024,
        "filters_kb": scalar_bytes / 1024,
        "total_kb": total / 1024,
        "fits_sram": total < 512 * 1024,
        "fits_sdram": total < 64 * 1024 * 1024,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `use_container_width` in st.graphviz_chart | `width="stretch"` or `width="content"` | Streamlit 1.40+ | Old param deprecated, can cause rendering bugs |
| PySide6 UI | Streamlit web UI | Phase 6 decision | All UI is Streamlit-based; export/diagram go in streamlit_app.py |

**Deprecated/outdated:**
- `st.graphviz_chart(use_container_width=True)`: Known regression, use `width` parameter instead

## Open Questions

1. **Generic `to_dot()` vs per-algorithm custom methods**
   - What we know: Algorithms have very different topologies (Freeverb = parallel combs + series allpass; Dattorro = figure-eight tank; FDN = 4-channel Hadamard matrix; Room = ER taps + FDN).
   - What's unclear: Whether a generic introspection-based DOT builder can produce meaningful diagrams for all topologies.
   - Recommendation: Use per-algorithm custom `to_dot()` methods. The topologies are too different for a generic builder to produce clear diagrams. A shared helper module (`dot_builder.py`) can provide common node/edge styling functions.

2. **Knob mapping UI widget choice**
   - What we know: Need to map 6 algorithm params to 6 Hothouse knobs. Default order = `param_specs` order.
   - What's unclear: Streamlit's drag-and-drop capabilities are limited.
   - Recommendation: Use `st.selectbox` dropdowns for each knob (Knob 1: [dropdown of param names]). Simple, reliable, and Streamlit-native. No external widget library needed.

3. **SDRAM annotation in generated code**
   - What we know: Large delay buffers (> ~10 KB) should use `DSY_SDRAM_BSS` attribute for SDRAM placement on Daisy Seed.
   - What's unclear: Exact threshold for when to use SDRAM vs SRAM.
   - Recommendation: Add `__attribute__((section(".sdram_bss")))` or `DSY_SDRAM_BSS` to any buffer array > 4096 floats (16 KB). Document this in generated code comments.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 7.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIZ-01 | Every algorithm returns valid DOT string from `to_dot()` | unit | `pytest tests/test_signal_flow.py -x` | No -- Wave 0 |
| EXP-01 | Export generates valid .h and .c files | unit | `pytest tests/test_c_export.py::test_export_generates_files -x` | No -- Wave 0 |
| EXP-02 | Generated C includes current param values | unit | `pytest tests/test_c_export.py::test_param_values_in_output -x` | No -- Wave 0 |
| EXP-03 | RAM estimation returns correct breakdown | unit | `pytest tests/test_c_export.py::test_ram_estimation -x` | No -- Wave 0 |
| EXP-04 | AudioCallback template includes Hothouse init | unit | `pytest tests/test_c_export.py::test_audio_callback_template -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_signal_flow.py tests/test_c_export.py -x -q`
- **Per wave merge:** `pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_signal_flow.py` -- covers VIZ-01 (to_dot for all algorithms, DOT validity)
- [ ] `tests/test_c_export.py` -- covers EXP-01, EXP-02, EXP-03, EXP-04
- [ ] No new framework install needed (pytest already configured)

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `claudeverb/algorithms/*.py` -- verified which algorithms have/lack `to_c_struct()`
- Codebase inspection: `claudeverb/streamlit_app.py` -- current UI structure for integration planning
- [Streamlit st.graphviz_chart docs](https://docs.streamlit.io/develop/api-reference/charts/st.graphviz_chart) -- confirmed DOT string acceptance, graphviz>=0.19.0 requirement
- [Cleveland Music Co. HothouseExamples](https://github.com/clevelandmusicco/HothouseExamples) -- Hothouse hardware layout: 6 knobs, 3 toggles, 2 footswitches, 2 LEDs

### Secondary (MEDIUM confidence)
- [Electro-Smith Daisy Seed specs](https://electro-smith.com/products/daisy-seed) -- 512 KB SRAM, 64 MB SDRAM, ARM Cortex-M7 480 MHz
- [Streamlit graphviz_chart issue #9866](https://github.com/streamlit/streamlit/issues/9866) -- `use_container_width=True` regression

### Tertiary (LOW confidence)
- SDRAM threshold recommendation (4096 floats / 16 KB) -- based on general Daisy Seed community practice, not official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- `st.graphviz_chart()` verified in official docs, graphviz package requirement confirmed
- Architecture: HIGH -- existing codebase patterns well-understood, integration points clear
- Pitfalls: HIGH -- known Streamlit regression verified, RAM estimation approach validated against existing struct patterns
- Hothouse hardware: MEDIUM -- hardware layout confirmed from examples repo, but exact GPIO pin mappings not extracted from header file

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable domain, 30 days)
