# Codebase Structure

**Analysis Date:** 2026-03-04

## Directory Layout

```
claudeverb/
├── algorithms/              # Reverb algorithm implementations and filters
│   ├── __init__.py         # ALGORITHM_REGISTRY (source of truth for UI dropdown)
│   ├── base.py             # ReverbAlgorithm abstract base, ReverbParams dataclass
│   ├── filters.py          # CombFilter, AllpassFilter, DelayLine, EQFilters
│   ├── freeverb.py         # Freeverb implementation (Jezar's Schroeder-Moorer)
│   ├── schroeder.py        # Schroeder implementation (1962 original design) — stub
│   └── plate.py            # Dattorro plate reverb implementation — stub
├── analysis/                # Audio analysis and acoustic metrics
│   ├── __init__.py
│   ├── spectral.py         # Mel spectrogram, STFT, FFT via librosa
│   └── metrics.py          # RT60, DRR, C80, C50, spectral centroid
├── audio/                   # Audio file I/O with resampling
│   ├── __init__.py
│   └── io.py               # load(path) → (audio, 48000), save(path, audio)
├── ui/                      # Web/GUI interface (PySide6 + matplotlib)
│   ├── __init__.py
│   ├── app.py              # MainWindow, application entry point
│   └── panels/             # Reusable UI components
│       ├── __init__.py
│       ├── algorithm_selector.py
│       ├── parameter_knobs.py
│       ├── analysis_display.py
│       └── waveform_display.py
├── export/                  # C code generation for Daisy Seed
│   ├── __init__.py
│   └── c_codegen.py        # export_algorithm(algo, output_dir)
├── config.py               # Global constants (SAMPLE_RATE=48000, BUFFER_SIZE=48)
└── __init__.py             # Package initialization
tests/
├── conftest.py             # Pytest fixtures: mono_sine, stereo_sine, impulse
├── test_algorithms/        # Algorithm-specific test files
│   ├── __init__.py
│   ├── test_freeverb.py
│   ├── test_schroeder.py
│   └── test_plate.py
├── test_analysis/          # Analysis module tests
│   ├── __init__.py
│   └── test_metrics.py
├── test_audio/             # Audio I/O tests
│   ├── __init__.py
│   └── test_io.py
└── test_export/            # C export tests
    ├── __init__.py
    └── test_c_codegen.py
setup.py or pyproject.toml  # Project metadata, dependencies, entry points
main.py                     # UI entry point: python main.py launches workbench
```

## Directory Purposes

**`claudeverb/algorithms/`:**
- Purpose: Home of all reverb algorithm implementations and DSP primitives
- Contains: Abstract base (ReverbAlgorithm), concrete implementations (Freeverb, Schroeder, Plate), reusable filters
- Key files:
  - `base.py`: Defines contract all algorithms must follow
  - `filters.py`: Foundational DSP building blocks (delay lines, comb/allpass filters, EQs)
  - `freeverb.py`: Reference implementation with complete C generation support
  - `__init__.py`: `ALGORITHM_REGISTRY` dict — single source of truth for UI dropdown

**`claudeverb/analysis/`:**
- Purpose: Compute audio metrics and generate visualizations for algorithm evaluation
- Contains: Pure functions for spectral analysis and acoustic measurements
- Key files:
  - `spectral.py`: Mel spectrograms, STFT, FFT (wraps librosa)
  - `metrics.py`: RT60 (Schroeder backward integration), DRR, C80/C50, spectral centroid

**`claudeverb/audio/`:**
- Purpose: Handle audio file I/O with automatic resampling to 48 kHz
- Contains: File loading/saving functions, resampling logic
- Key files:
  - `io.py`: `load(path)` with polyphase resampling, `save(path, audio)` as 24-bit PCM

**`claudeverb/ui/`:**
- Purpose: Interactive GUI workbench for algorithm development and testing
- Contains: PySide6 application with matplotlib visualizations
- Key files:
  - `app.py`: MainWindow class and application initialization
  - `panels/`: Modular UI components (algorithm selector, knobs, waveform display, analysis)

**`claudeverb/export/`:**
- Purpose: Generate production-ready C code for STM32 Daisy Seed
- Contains: Code generation logic targeting libDaisy framework
- Key files:
  - `c_codegen.py`: `export_algorithm()` orchestrates struct and function generation

**`tests/`:**
- Purpose: Comprehensive test coverage for all modules
- Contains: Unit tests, integration tests, test fixtures
- Key files:
  - `conftest.py`: Pytest fixtures used across test suite (audio signals)
  - `test_algorithms/`: Algorithm-specific tests including audio quality checks
  - `test_analysis/`: Metrics computation verification
  - `test_audio/`: Resampling and file I/O verification

## Key File Locations

**Entry Points:**
- `main.py`: Launch interactive UI workbench
- `pytest` (via setup.py/pyproject.toml): Run test suite

**Configuration:**
- `claudeverb/config.py`: SAMPLE_RATE (48000), BUFFER_SIZE (48), audio conventions
- `pyproject.toml` or `setup.py`: Dependencies, development tools, test configuration

**Core Logic:**
- `claudeverb/algorithms/base.py`: ReverbAlgorithm abstract base, ReverbParams
- `claudeverb/algorithms/filters.py`: DSP primitives (building blocks for all algorithms)
- `claudeverb/algorithms/freeverb.py`: Reference implementation with C generation

**Testing:**
- `tests/conftest.py`: Shared test fixtures and test audio signals
- `tests/test_algorithms/test_freeverb.py`: Algorithm validation tests
- `tests/test_analysis/test_metrics.py`: Metric computation verification

## Naming Conventions

**Files:**
- Algorithm implementations: `[name_lowercase].py` (e.g., `freeverb.py`, `schroeder.py`)
- Test files: `test_[module].py` (e.g., `test_freeverb.py`, `test_metrics.py`)
- C export output: `[AlgorithmName].h`, `[AlgorithmName].c` (e.g., `Freeverb.h`, `Freeverb.c`)

**Directories:**
- Feature-based organization: `analysis/`, `audio/`, `export/`, `ui/`, `algorithms/`
- Test parallel structure: `tests/test_[module]/` mirrors main package structure

**Classes:**
- Algorithm implementations: PascalCase (e.g., `Freeverb`, `Schroeder`, `PlateReverb`)
- Parameter classes: `[AlgorithmName]Params` (e.g., `FreeverbParams`, `SchroederParams`)
- Filter classes: PascalCase (e.g., `CombFilter`, `AllpassFilter`, `DelayLine`)

**Functions:**
- Public API: `snake_case` (e.g., `load()`, `save()`, `export_algorithm()`)
- Private/internal: `_snake_case` prefix (e.g., `_initialize()` in algorithms, `_process_chunk()`)

**Variables:**
- Constants: `UPPER_CASE` (e.g., `SAMPLE_RATE`, `BUFFER_SIZE`)
- Parameters: `snake_case` (e.g., `room_size`, `damping`, `wet_dry_mix`)
- Audio buffers: descriptive snake_case (e.g., `input_audio`, `processed_audio`, `impulse_response`)

**Types:**
- Use type hints throughout (PEP 484)
- Audio arrays: `np.ndarray[float32]` for shape `(N,)` mono or `(2, N)` stereo
- Parameter classes: Frozen dataclasses with `@dataclass(frozen=True)`

## Where to Add New Code

**New Algorithm Implementation:**
- Primary code: Create `claudeverb/algorithms/[name].py` subclassing `ReverbAlgorithm`
  - Implement: `_initialize()`, `process(audio)`, `reset()`, `update_params()`, `param_specs`
  - Add C generation: `to_c_struct()` and `to_c_process_fn()` methods
- Register: Add class to `ALGORITHM_REGISTRY` in `claudeverb/algorithms/__init__.py`
- Tests: Create `tests/test_algorithms/test_[name].py` with test cases using fixtures from `conftest.py`
- Validation: Test with impulse responses, sine waves, real audio samples; verify against analysis metrics

**New Filter Primitive:**
- Location: Add class to `claudeverb/algorithms/filters.py`
- Documentation: Include docstring with C struct equivalent for future portability
- Methods: `process(audio)`, state management, parameter update without reallocation
- Usage: Import and compose in algorithm implementations

**New Analysis Metric:**
- Location: Add function to `claudeverb/analysis/metrics.py`
- Signature: Accept `(N,)` or `(2, N)` float32 audio, return scalar or array
- Channel handling: Internally average stereo to mono if needed
- Tests: Add to `tests/test_analysis/test_metrics.py` with known test cases

**New UI Component:**
- Panel component: Create class in `claudeverb/ui/panels/[name].py` inheriting from QWidget
- Integration: Import and add to MainWindow in `claudeverb/ui/app.py`
- Data binding: Use Qt signals/slots to connect to algorithm parameters

**Command-line Tooling:**
- Export CLI: Add script at `bin/export.py` or enhance `export/c_codegen.py`
- Analysis script: Add at `bin/analyze.py` for batch processing

## Special Directories

**`tests/conftest.py`:**
- Purpose: Shared test fixtures and test data
- Contents: `mono_sine()`, `stereo_sine()`, `impulse()` fixtures providing standard test signals
- Generated: Fixtures create in-memory audio arrays at 48 kHz
- Committed: Yes (essential for reproducible testing)

**`claudeverb/export/`:**
- Purpose: C code generation exclusively
- Generated files: `.h` and `.c` files written to user-specified output directory (not committed)
- Committed: Yes (contains generation logic), no (generated C files)

**Configuration files (implied):**
- `setup.py` or `pyproject.toml`: Project metadata, dependencies list, optional dev extras `[dev]`
- `.env` (if used): Not committed, contains local API keys if needed (unlikely for this project)
- `.gitignore`: Should exclude `__pycache__/`, `.pytest_cache/`, `*.pyc`, generated C files

## Standard Test Fixtures

Available in `tests/conftest.py` for all test modules:

```python
@pytest.fixture
def mono_sine(freq=440, duration=1.0, sample_rate=48000):
    # Returns mono sine wave at specified frequency, duration in seconds
    # Shape: (N,), dtype: float32, range: [-1.0, 1.0]

@pytest.fixture
def stereo_sine(freq=440, duration=1.0, sample_rate=48000):
    # Returns stereo sine wave (same frequency both channels)
    # Shape: (2, N), dtype: float32, range: [-1.0, 1.0]

@pytest.fixture
def impulse(sample_rate=48000):
    # Returns impulse response: [1.0, 0, 0, ...]
    # Used for algorithm frequency response analysis
    # Shape: (N,), dtype: float32
```

---

*Structure analysis: 2026-03-04*
