# Coding Conventions

**Analysis Date:** 2026-03-04

## Project Context

ClaudeVerb is a Python DSP workbench for reverb algorithm development. The project prioritizes Python as the primary language but requires C portability for algorithms targeting STM32 Daisy Seed export. These conventions ensure code is maintainable, testable, and ready for C transpilation.

## Naming Patterns

**Files:**
- Modules use `snake_case`: `freeverb.py`, `c_codegen.py`, `spectral.py`
- Test files follow pattern: `test_<module_name>.py` or `test_<feature>.py`
- Algorithm implementations: `<algorithm_name>.py` in `claudeverb/algorithms/`
- Filter primitives: `filters.py` contains all shared DSP building blocks
- Export targets: `c_codegen.py` for code generation

**Functions:**
- Regular functions use `snake_case`: `process()`, `update_params()`, `load_audio()`
- Private/internal functions prefix with `_`: `_initialize()`, `_process_frame()`
- DSP processing functions: `process()` — core hot-path function that cannot allocate memory
- Initialization functions: `_initialize()` — called once, performs all allocations

**Variables:**
- Local variables use `snake_case`: `room_size`, `sample_rate`, `delay_buffer`
- Constants use `UPPER_CASE`: `SAMPLE_RATE = 48000`, `BUFFER_SIZE = 48`, `NUM_CHANNELS = 2`
- Parameters use `snake_case`: function parameters and dataclass fields match C struct member names for export consistency
- Private/internal variables prefix with `_`: `_state`, `_buffer_index`

**Types & Classes:**
- Class names use `PascalCase`: `Freeverb`, `ReverbAlgorithm`, `CombFilter`
- Abstract base classes use `PascalCase`: `ReverbAlgorithm` in `claudeverb/algorithms/base.py`
- Dataclasses use `PascalCase` with `Params` suffix: `FreeverbParams`, `ReverbParams`
- Type hints use modern syntax: `from typing import Optional, Tuple` (prefer Python 3.10+ union types where available)

## Code Style

**Formatting:**
- Line length: 100 characters (DSP code with complex math benefits from readable length)
- Indentation: 4 spaces (Python standard)
- String quotes: Double quotes for docstrings and regular strings, single quotes acceptable in f-strings

**Linting:**
- Not yet enforced; recommend `black` for formatting and `ruff` for linting during setup phase
- Comment style: Inline comments above code, explanatory docstrings for functions

## Import Organization

**Order:**
1. Standard library imports (`import sys`, `from typing import...`, `from pathlib import Path`)
2. Third-party imports (`import numpy as np`, `import scipy`, `from scipy import signal`)
3. Local/relative imports (`from claudeverb.algorithms.base import ReverbAlgorithm`, `from .filters import CombFilter`)

**Path Aliases:**
- No aliases currently established; consider `from claudeverb.algorithms import ALGORITHM_REGISTRY` for registry lookups
- All DSP modules importable as `from claudeverb.algorithms.base import ReverbAlgorithm`

## Error Handling

**Patterns:**
- Use explicit exception types: `ValueError` for invalid parameters, `TypeError` for type mismatches
- DSP processing functions (`process()`) assume valid input; invalid audio shapes cause `IndexError` (acceptable, detected in tests)
- Parameter validation in `update_params()` before state changes: check valid ranges for room_size, damping, wet_dry
- Audio I/O operations catch `OSError` and re-raise as `RuntimeError` with context
- C export functions raise `ValueError` if algorithm not fully portable (missing `to_c_struct()` or `to_c_process_fn()`)

**Example:**
```python
def update_params(self, params: FreeverbParams) -> None:
    if not 0.0 <= params.room_size <= 1.0:
        raise ValueError(f"room_size must be in [0, 1], got {params.room_size}")
    if not 0.0 <= params.wet <= 1.0:
        raise ValueError(f"wet must be in [0, 1], got {params.wet}")
    self.params = params
    # Recompute filter coefficients without resetting delay lines
    self._update_filter_coeff()
```

## Logging

**Framework:** `logging` module (standard library)

**Patterns:**
- Algorithm classes use `logger = logging.getLogger(__name__)`
- Log levels: `DEBUG` for parameter updates, `INFO` for algorithm state changes, `WARNING` for performance degradation
- No logging in hot-path functions (`process()` — DSP code must not allocate)
- Analysis functions log timing and metrics at `INFO` level
- Import tracking: `from claudeverb.algorithms.base import ALGORITHM_REGISTRY` with `logger.info(f"Registered {len(ALGORITHM_REGISTRY)} algorithms")`

## Comments

**When to Comment:**
- DSP algorithms require detailed comments explaining the filter topology (e.g., comb filter feedback path)
- C portability notes in comments: `# C: delay_line is fixed-size circular buffer`
- Avoid redundant comments; prefer clear variable names
- Complex mathematics: explain the derivation (e.g., RT60 calculation using Schroeder backward integration)

**JSDoc/TSDoc:**
- Use Python docstrings (Google style) for all public functions and classes
- Include parameter types, return types, and examples
- Document C export requirements in algorithm docstrings

**Example:**
```python
class Freeverb(ReverbAlgorithm):
    """Jezar's Schroeder-Moorer design with 8 comb filters + 4 allpass per channel.

    Architecture:
        Input → 8 parallel comb filters → 4 series allpass filters → output mix

    C Export:
        Generates fixed-size arrays for comb/allpass state. All allocations in _initialize().

    Attributes:
        params: FreeverbParams with room_size, damping, wet, dry, width
    """
```

## Function Design

**Size:** Keep functions under 50 lines; complex algorithms split into logical stages (delay line access, filtering, mixing)

**Parameters:**
- Algorithms pass `audio: np.ndarray` (mono `(N,)` or stereo `(2, N)`) and process in place or return new array
- Keyword-only parameters after `*` for configuration: `def load(path: str, *, sr: int = 48000)`
- Avoid default mutable arguments; use `None` and construct inside function

**Return Values:**
- `process()` returns modified audio as `np.ndarray` (same shape as input)
- `_initialize()` returns `None` (side effect: allocates state)
- Analysis functions return metrics as `float` or `dict`: `{"rt60": 1.2, "drr": 10.5}`

## Module Design

**Exports:**
- Public classes/functions exposed at module level: `from claudeverb.algorithms import Freeverb, FreeverbParams`
- Algorithm registry in `claudeverb/algorithms/__init__.py`: `ALGORITHM_REGISTRY = {"freeverb": Freeverb, "schroeder": Schroeder}`
- Private modules (_internal.py) used for implementation details

**Barrel Files:**
- `claudeverb/algorithms/__init__.py` imports and registers all algorithms
- `claudeverb/analysis/__init__.py` exports analysis functions (spectral, metrics)
- `claudeverb/audio/__init__.py` exports audio I/O: `load()`, `save()`

## Audio Conventions (Critical for DSP)

**Audio Shapes:**
- Mono: `audio.shape = (N,)` — 1D array
- Stereo: `audio.shape = (2, N)` — 2D array with channels on axis 0
- All audio is `dtype = np.float32` in range `[-1.0, 1.0]`
- Buffer size: `BUFFER_SIZE = 48` samples (matches Daisy Seed callback)

**Processing:**
- `process(audio)` must accept both mono and stereo without conversion
- Delay lines are circular buffers using fixed indices (C-portable)
- No memory allocation inside `process()` — allocate in `_initialize()`
- Handle buffer boundaries carefully: circular buffer wrap-around, channel dimension preservation

**Example:**
```python
def process(self, audio: np.ndarray) -> np.ndarray:
    """Process audio block.

    Args:
        audio: (N,) mono or (2, N) stereo float32 array.

    Returns:
        Processed audio, same shape.
    """
    if audio.ndim == 1:
        return self._process_mono(audio)
    else:
        return self._process_stereo(audio)
```

## C Portability Rules (Mandatory)

**State Representation:**
- All algorithm state must be representable as fixed-size arrays and scalars (no Python objects)
- Use `np.ndarray` with fixed shapes for delay lines: `self.comb_buffers = [np.zeros(delay_length, dtype=np.float32) for _ in range(8)]`
- Scalars for counters, filter coefficients: `self.comb_index = 0`, `self.feedback = 0.5`

**Memory Allocation:**
- All allocation in `_initialize()` — never allocate in `process()` or hot-path code
- Circular buffer indices and pointers only change during `process()`, not allocated

**Dataclass for Parameters:**
- Use `@dataclass` for algorithm parameters: `@dataclass\nclass FreeverbParams:\n    room_size: float = 0.7`
- All fields must map to C struct members (no Python-specific types)

**C Code Generation:**
- Implement `to_c_struct()` returning string with C struct definition
- Implement `to_c_process_fn()` returning string with C process function
- Test C generation in unit tests

---

*Convention analysis: 2026-03-04*
