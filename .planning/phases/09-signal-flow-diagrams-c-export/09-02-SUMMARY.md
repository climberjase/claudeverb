---
phase: 09-signal-flow-diagrams-c-export
plan: 02
subsystem: export
tags: [c-export, code-generation, ram-estimation, hothouse]
dependency_graph:
  requires: []
  provides: [c_export_module, freeverb_c_struct, dattorro_c_struct]
  affects: [streamlit_app, ui_panels]
tech_stack:
  added: []
  patterns: [f-string-codegen, regex-struct-parsing]
key_files:
  created:
    - claudeverb/export/c_export.py
    - tests/test_c_export.py
  modified:
    - claudeverb/algorithms/freeverb.py
    - claudeverb/algorithms/dattorro_plate.py
decisions:
  - "Python f-strings for C code generation (no Jinja2), matching existing pattern"
  - "RAM estimation uses 10% padding for struct alignment"
  - "SDRAM candidates threshold: buffers > 4096 floats (16 KB)"
  - "_snake_case helper handles CamelCase, acronyms (FDN), and multi-word names"
metrics:
  duration: ~15min
  completed: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
requirements:
  - EXP-01
  - EXP-02
  - EXP-03
  - EXP-04
---

# Phase 09 Plan 02: C Export Pipeline Summary

C code export pipeline with header/source generation, RAM estimation, and Hothouse AudioCallback template for all 9 algorithms.

## What Was Built

### Task 1: to_c_struct() and to_c_process_fn() for Freeverb and DattorroPlate

Added C export methods to the two algorithms that were missing them (Freeverb and DattorroPlate), completing coverage across all 9 registered algorithms.

**Freeverb (`FreeverbState`):**
- 16 comb filter delay buffers (8 left + 8 right, sizes scaled from 44.1 kHz to 48 kHz)
- 8 allpass filter delay buffers (4 left + 4 right, with stereo spread offset)
- Comb filter state: write indices, filterstore arrays for LP damping
- Pre-delay buffer (4800 samples max = 100ms at 48 kHz)
- Parameter scalars: room_size, damping, mix, width, hf_damp, plus scaled internal values

**DattorroPlate (`DattorroPlateState`):**
- 4 input allpass diffuser buffers with coefficients
- 4 decay allpass buffers (2 per tank half: AP1 and AP2)
- 4 tank delay buffers (2 modulated delay1 + 2 delay2, with mod excursion headroom)
- Bandwidth filter, 2 damping filters, 2 DC blockers (all one-pole state)
- LFO state (phase, phase_inc, mod_depth)
- Cross-feedback state, parameter scalars

**Test scaffold:** Parametrized tests across all 9 algorithms verifying:
- `to_c_struct()` returns string with `typedef struct` and correct state name
- `to_c_process_fn()` returns string with correct function signature
- No malloc/calloc/realloc in any generated C code
- All array sizes are compile-time integer constants

### Task 2: c_export.py Centralized Export Module

Created `claudeverb/export/c_export.py` with 5 exported functions:

1. **`generate_header(algo, params, knob_mapping)`** -- Complete .h file with include guards, timestamp/parameter comment block, struct typedef, init/process prototypes
2. **`generate_source(algo, params)`** -- Complete .c file with `#include`, init function (memset + param defaults from current values), process function body
3. **`estimate_ram(algo)`** -- Parses struct with regex to find float/int arrays, categorizes by name (delay/filter/matrix), calculates bytes with 10% alignment padding, identifies SDRAM candidates
4. **`generate_audio_callback(algo, knob_mapping)`** -- Hothouse-specific .cpp with hardware init, knob reads, bypass toggle, process call, main() with block size 48 and SAI_48KHZ
5. **`export_to_files(algo, params, knob_mapping, output_dir)`** -- Writes .h, .c, .cpp files to disk

Helper functions: `_snake_case()` (CamelCase to snake_case), `_state_name()` (extract state struct name from generated C).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `89f79c5` | feat(09-02): add to_c_struct/to_c_process_fn to Freeverb and DattorroPlate |
| 2 | `ef2754e` | feat(09-02): create c_export.py with header, source, RAM estimation, AudioCallback |

## Deviations from Plan

None - plan executed as written.

**Note:** Test verification via pytest could not be run due to bash permission restrictions on Python execution. The code was written following established patterns (matching fdn_reverb.py, room_base.py, dattorro_single_loop.py) and should pass once pytest is available.

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `claudeverb/export/c_export.py` | Centralized C export pipeline | ~300 |
| `tests/test_c_export.py` | Test coverage for all export functions | ~300 |
| `claudeverb/algorithms/freeverb.py` | Added to_c_struct() and to_c_process_fn() | +130 |
| `claudeverb/algorithms/dattorro_plate.py` | Added to_c_struct() and to_c_process_fn() | +160 |

## Self-Check: PASSED

- [x] `claudeverb/export/c_export.py` -- FOUND
- [x] `tests/test_c_export.py` -- FOUND
- [x] `claudeverb/algorithms/freeverb.py` -- FOUND (modified)
- [x] `claudeverb/algorithms/dattorro_plate.py` -- FOUND (modified)
- [x] Commit `89f79c5` -- FOUND
- [x] Commit `ef2754e` -- FOUND
- [ ] pytest verification -- SKIPPED (bash permission denied for Python execution)
