# Architecture

**Analysis Date:** 2026-03-04

## Pattern Overview

**Overall:** Layered modular architecture with clear separation of concerns across algorithm development, analysis, I/O, and C code generation.

**Key Characteristics:**
- Algorithms as isolated, stateless processing units with fixed-size internal state
- Pure functional analysis layer (no state management needed)
- Fixed-size delay lines and circular buffers throughout (C portability requirement)
- No dynamic memory allocation after initialization
- Algorithms are self-contained with embedded C generation capability

## Layers

**Algorithm Layer:**
- Purpose: Core DSP algorithm implementations that can be ported to C
- Location: `claudeverb/algorithms/`
- Contains: Abstract base class `ReverbAlgorithm`, concrete algorithm implementations, filter primitives
- Depends on: Nothing (self-contained, stateless filter building blocks)
- Used by: UI layer, export layer, analysis pipeline

**Filter Primitives Layer:**
- Purpose: Reusable DSP building blocks for all algorithms
- Location: `claudeverb/algorithms/filters.py`
- Contains: `CombFilter`, `AllpassFilter`, `DelayLine`, `EQFilters` (high-pass, low-pass, notch, band-pass, parametric)
- Depends on: NumPy (numerical computation)
- Used by: Concrete algorithm implementations in `claudeverb/algorithms/`

**Analysis Layer:**
- Purpose: Audio analysis and metric computation (RT60, DRR, C80, spectral analysis)
- Location: `claudeverb/analysis/`
- Contains: `spectral.py` (mel spectrograms, STFT, FFT via librosa), `metrics.py` (acoustic measurements)
- Depends on: NumPy, scipy, librosa
- Used by: Test harnesses, UI for display of algorithm characteristics

**Audio I/O Layer:**
- Purpose: File loading and saving with automatic resampling
- Location: `claudeverb/audio/io.py`
- Contains: `load(path)` with auto-resampling to 48 kHz, `save(path, audio)` as 24-bit PCM
- Depends on: soundfile, librosa (for resampling)
- Used by: Test harnesses, UI for loading test signals

**Export/Code Generation Layer:**
- Purpose: Convert algorithms to C code for STM32 Daisy Seed deployment
- Location: `claudeverb/export/c_codegen.py`
- Contains: `export_algorithm(algo, output_dir)` calling `algo.to_c_struct()` and `algo.to_c_process_fn()`
- Depends on: Algorithm layer (accesses C generation methods)
- Used by: CLI or UI export functionality

**UI Layer:**
- Purpose: Interactive workbench for algorithm development, testing, parameter tuning
- Location: `claudeverb/ui/`
- Contains: PySide6-based interface, matplotlib integration for visualizations
- Depends on: Algorithm layer, analysis layer, audio I/O layer
- Used by: End user for algorithm evaluation and tuning

**Configuration Layer:**
- Purpose: Project-wide constants and configuration
- Location: `claudeverb/config.py`
- Contains: `SAMPLE_RATE = 48000`, `BUFFER_SIZE = 48`
- Depends on: Nothing
- Used by: All layers

## Data Flow

**Algorithm Processing Pipeline:**

1. User loads audio file via UI or test harness
2. `audio/io.py` loads and resamples to 48 kHz
3. Audio processed through algorithm in `BUFFER_SIZE` chunks (48 samples)
4. Algorithm maintains internal circular buffers across buffer boundaries
5. Processed audio output

**Analysis Pipeline:**

1. Original audio + processed audio fed to `analysis/metrics.py`
2. Compute RT60 via Schroeder backward integration
3. Compute frequency domain metrics (DRR, C80, spectral centroid)
4. Generate mel spectrograms via `spectral.py`
5. Return metrics for UI display or test assertions

**C Export Pipeline:**

1. User triggers export on configured algorithm instance
2. `export_algorithm()` calls `algo.to_c_struct()` to generate `.h` file with state definition
3. `algo.to_c_process_fn()` generates `.c` implementation
4. Files written to output directory with libDaisy framework compatibility

**State Management:**
- Algorithms maintain state only as fixed-size NumPy arrays and scalars
- State must not include Python objects in hot path
- State reset via `reset()`, updated via `update_params()` without full reinitialization
- All state representable as C arrays and scalars for portability

## Key Abstractions

**ReverbAlgorithm (Abstract Base):**
- Purpose: Define contract for all reverb algorithm implementations
- Examples: `claudeverb/algorithms/freeverb.py`, `claudeverb/algorithms/schroeder.py`
- Pattern: Abstract base class with required methods: `_initialize()`, `process(audio)`, `reset()`, `update_params()`, `param_specs`, `to_c_struct()`, `to_c_process_fn()`
- Implementation requirement: Must use only fixed-size arrays, circular buffers, no post-init allocation

**ReverbParams (Dataclass):**
- Purpose: Parameter container for algorithm configuration
- Pattern: Frozen dataclass with attributes matching algorithm-specific parameters (wet/dry, room size, damping, etc.)
- Implementation: Each algorithm subclasses with its own parameter set

**ParamSpec:**
- Purpose: Define parameter UI representation and ranges
- Pattern: Describes knob/switch behavior: knobs have 0-100 range, switches have -1/0/1 values
- Used by: UI to generate appropriate controls

**Filter Classes (CombFilter, AllpassFilter, DelayLine, EQFilters):**
- Purpose: Reusable DSP primitives with documented C struct equivalents
- Pattern: Classes encapsulating state (delay buffer, coefficients) and process methods
- Constraint: Must be convertible to C via `to_c_struct()` patterns in docstrings

**AudioBuffer:**
- Purpose: Standardized audio representation throughout pipeline
- Pattern: NumPy float32 array - mono as `(N,)`, stereo as `(2, N)` where N = sample count
- Range: Always normalized to `[-1.0, 1.0]`

## Entry Points

**main.py:**
- Location: `main.py` (implied in memory/setup documentation)
- Triggers: `python main.py` to launch PySide6 UI workbench
- Responsibilities: Create and show main window, initialize analysis/algorithm system

**CLI Export:**
- Location: Likely in root or `bin/export.py` (not yet created)
- Triggers: Command-line invocation for batch C code generation
- Responsibilities: Parse algorithm parameters, call export pipeline, write C files

**Test Suite Entry:**
- Location: `pytest` via `tests/` directory (conftest fixtures referenced)
- Triggers: `pytest` or `pytest tests/test_algorithms/test_[algo].py`
- Responsibilities: Load test fixtures, execute algorithm, verify outputs against audio analysis

## Error Handling

**Strategy:** Validation at layer boundaries, early failure on invalid input

**Patterns:**
- Audio I/O: Validate sample rate, bit depth, channel count; resample if needed
- Algorithms: Validate parameter ranges before `update_params()`, maintain invariants after `process()`
- Analysis: Handle mono/stereo seamlessly via averaging, validate buffer sizes match expected
- C Export: Validate algorithm state is C-compatible before generating code, check for post-init allocations

## Cross-Cutting Concerns

**Logging:** Console output via Python `logging` module (not yet configured but expected in setup)

**Validation:**
- Parameter range checking in `update_params()` before applying
- Audio buffer shape and dtype validation at layer boundaries
- C portability constraints checked during export

**Audio Conventions:**
- All audio is float32 in range [-1.0, 1.0]
- Mono: shape `(N,)`, stereo: shape `(2, N)`
- Always 48 kHz sample rate
- Buffer processing in 48-sample chunks for Daisy Seed alignment

---

*Architecture analysis: 2026-03-04*
