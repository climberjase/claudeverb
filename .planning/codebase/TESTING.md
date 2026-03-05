# Testing Patterns

**Analysis Date:** 2026-03-04

## Test Framework

**Runner:**
- `pytest` (standard Python testing framework)
- Config: `pytest.ini` or `pyproject.toml` (to be created in setup phase)
- Plugins: `pytest-cov` for coverage reporting

**Assertion Library:**
- `pytest` built-in assertions (no additional library needed)
- NumPy assertions: `np.testing.assert_allclose()` for DSP signal comparison with tolerance

**Run Commands:**
```bash
pytest                          # Run all tests
pytest -v                       # Verbose output with test names
pytest --tb=short               # Short traceback format
pytest tests/test_algorithms/   # Run only algorithm tests
pytest -k "freeverb"            # Run tests matching pattern
pytest --cov=claudeverb         # Generate coverage report
pytest --cov=claudeverb --cov-report=html  # HTML coverage report
pytest -x                       # Stop on first failure
```

## Test File Organization

**Location:**
- Separate `tests/` directory at project root (not co-located)
- Structure mirrors source: `tests/test_algorithms/`, `tests/test_audio/`, `tests/test_analysis/`, `tests/test_export/`

**Naming:**
- Test files: `test_<module_name>.py` or `test_<feature>.py`
- Test classes: `Test<ClassName>` — e.g., `TestFreeverb`, `TestCombFilter`
- Test functions: `test_<behavior_description>` — e.g., `test_process_mono_audio`, `test_update_params_validates_room_size`

**Structure:**
```
tests/
├── conftest.py                  # Shared fixtures (audio generators, paths)
├── test_algorithms/
│   ├── conftest.py              # Algorithm-specific fixtures
│   ├── test_freeverb.py
│   ├── test_schroeder.py
│   ├── test_filters.py
│   └── test_base.py
├── test_audio/
│   └── test_io.py
├── test_analysis/
│   ├── test_spectral.py
│   └── test_metrics.py
└── test_export/
    └── test_c_codegen.py
```

## Test Structure

**Suite Organization:**
```python
import pytest
import numpy as np
from claudeverb.algorithms.freeverb import Freeverb, FreeverbParams
from claudeverb.audio import load, save


class TestFreeverb:
    """Tests for Freeverb algorithm."""

    def test_initialize_allocates_state(self):
        """Freeverb._initialize() allocates delay line arrays."""
        algo = Freeverb(FreeverbParams())
        assert algo.comb_buffers is not None
        assert len(algo.comb_buffers) == 8
        assert all(buf.shape[0] > 0 for buf in algo.comb_buffers)

    def test_process_mono_maintains_shape(self, mono_sine):
        """process() preserves mono audio shape (N,)."""
        algo = Freeverb(FreeverbParams())
        output = algo.process(mono_sine)
        assert output.shape == mono_sine.shape
        assert output.dtype == np.float32

    def test_process_stereo_maintains_shape(self, stereo_sine):
        """process() preserves stereo audio shape (2, N)."""
        algo = Freeverb(FreeverbParams())
        output = algo.process(stereo_sine)
        assert output.shape == stereo_sine.shape
        assert output.dtype == np.float32

    def test_update_params_recomputes_coefficients(self):
        """update_params() changes filter behavior without resetting state."""
        algo = Freeverb(FreeverbParams(room_size=0.5))
        audio = np.random.randn(480).astype(np.float32)
        output1 = algo.process(audio)

        # Change parameter and process same audio
        algo.update_params(FreeverbParams(room_size=0.9))
        output2 = algo.process(audio)

        # Outputs should differ due to changed room_size
        assert not np.allclose(output1, output2)

    def test_process_does_not_allocate(self, mono_sine):
        """process() uses only pre-allocated buffers (C-portable)."""
        algo = Freeverb(FreeverbParams())
        # Verify no new arrays created during process
        initial_buffer_ids = {id(buf) for buf in algo.comb_buffers}
        algo.process(mono_sine)
        final_buffer_ids = {id(buf) for buf in algo.comb_buffers}
        assert initial_buffer_ids == final_buffer_ids

    def test_reset_clears_state(self, mono_sine):
        """reset() zeros all delay lines and filter state."""
        algo = Freeverb(FreeverbParams())
        algo.process(mono_sine)  # Fill buffers
        algo.reset()
        # Verify buffers are zeroed
        assert all(np.allclose(buf, 0.0) for buf in algo.comb_buffers)
```

**Patterns:**

1. **Setup/Teardown:**
   - Use pytest fixtures in `conftest.py` for reusable test data
   - Fixtures handle resource cleanup automatically
   - No explicit `setup()` or `teardown()` methods needed

   ```python
   @pytest.fixture
   def mono_sine(sample_rate=48000, duration=1.0, frequency=440):
       """Generate 1-second 440 Hz sine wave at 48 kHz."""
       t = np.arange(int(sample_rate * duration)) / sample_rate
       return np.sin(2 * np.pi * frequency * t).astype(np.float32)
   ```

2. **Assertion Pattern:**
   - Use `np.testing.assert_allclose()` for DSP signals with tolerance
   - Use `pytest.approx()` for scalar comparisons
   - Use `assert` for shape and type checks

   ```python
   def test_spectral_similarity(self, audio1, audio2):
       spec1 = compute_mel_spectrogram(audio1)
       spec2 = compute_mel_spectrogram(audio2)
       # Allow small numeric differences due to FFT rounding
       np.testing.assert_allclose(spec1, spec2, rtol=1e-5)
   ```

3. **Parametrized Tests:**
   ```python
   @pytest.mark.parametrize("room_size", [0.0, 0.5, 1.0])
   def test_process_with_varying_room_size(self, mono_sine, room_size):
       algo = Freeverb(FreeverbParams(room_size=room_size))
       output = algo.process(mono_sine)
       assert output.shape == mono_sine.shape
   ```

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**
```python
from unittest.mock import Mock, patch, MagicMock


def test_load_audio_resamples(tmp_path):
    """load() resamples audio to 48 kHz."""
    with patch('claudeverb.audio.io.librosa.load') as mock_load:
        mock_load.return_value = (np.random.randn(44100), 44100)

        audio, sr = load('test.wav')

        assert sr == 48000  # Resampled to 48 kHz
        mock_load.assert_called_once_with('test.wav', sr=44100)


def test_export_algorithm_writes_files(tmp_path):
    """export_algorithm() generates .h and .c files."""
    from claudeverb.export.c_codegen import export_algorithm

    algo = Freeverb(FreeverbParams())
    output_dir = tmp_path / "export"

    export_algorithm(algo, str(output_dir))

    assert (output_dir / "freeverb.h").exists()
    assert (output_dir / "freeverb.c").exists()
```

**What to Mock:**
- File I/O (`open()`, `pathlib.Path`)
- External audio library calls (`librosa.load()`)
- System resources (sounddevice output for listening tests)
- Database/network calls (none yet, but pattern when added)

**What NOT to Mock:**
- Algorithm internals (test actual DSP behavior)
- NumPy/SciPy operations (test real signal processing)
- Audio shape/dtype transformations (critical for C export)
- Delay line buffers (test actual state management)

## Fixtures and Factories

**Test Data:**
```python
# tests/conftest.py

import pytest
import numpy as np


@pytest.fixture
def mono_sine():
    """1-second 440 Hz sine wave at 48 kHz."""
    sr = 48000
    duration = 1.0
    freq = 440
    t = np.arange(int(sr * duration)) / sr
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


@pytest.fixture
def stereo_sine(mono_sine):
    """Stereo version of mono_sine."""
    return np.stack([mono_sine, mono_sine * 0.5])


@pytest.fixture
def impulse():
    """Impulse response test signal: delta function."""
    x = np.zeros(480, dtype=np.float32)  # One buffer
    x[0] = 1.0
    return x


@pytest.fixture
def white_noise():
    """1-second white noise at 48 kHz."""
    return np.random.randn(48000).astype(np.float32) * 0.1


@pytest.fixture
def freeverb_algo():
    """Freeverb instance with default parameters."""
    from claudeverb.algorithms.freeverb import Freeverb, FreeverbParams
    return Freeverb(FreeverbParams())


@pytest.fixture
def tmp_audio_file(tmp_path, mono_sine):
    """Create temporary audio file for testing I/O."""
    from claudeverb.audio import save
    path = tmp_path / "test_audio.wav"
    save(str(path), mono_sine)
    return path
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Algorithm-specific fixtures: `tests/test_algorithms/conftest.py`
- Test data files: `tests/fixtures/audio/` (e.g., `tests/fixtures/audio/piano.wav`)

## Coverage

**Requirements:**
- Recommend 85% coverage target for core algorithms (`claudeverb/algorithms/`)
- Recommend 100% coverage for audio I/O (`claudeverb/audio/io.py`) due to criticality
- Not yet enforced; can be configured in `pyproject.toml` with `[tool.pytest.ini_options]`

**View Coverage:**
```bash
pytest --cov=claudeverb --cov-report=term-missing  # Terminal with missing lines
pytest --cov=claudeverb --cov-report=html          # Open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- Scope: Individual functions/methods in isolation (algorithm components, filters, utilities)
- Approach: Fast, deterministic, use fixtures for test data
- Location: `tests/test_algorithms/test_<module>.py`
- Focus: Correctness of DSP operations, parameter validation, state management

**Integration Tests:**
- Scope: Multiple components together (algorithm + analysis pipeline, audio I/O + processing)
- Approach: Test realistic workflows (load audio → process with algorithm → compute RT60)
- Location: `tests/test_algorithms/test_integration.py` or separate `tests/integration/`
- Focus: End-to-end signal flow, format handling (mono vs stereo), buffer boundaries

**E2E Tests:**
- Framework: Not used yet; can add when UI (Streamlit) and playback are implemented
- Scope: Would test audio playback, UI interactions, file export
- Approach: Screenshot comparison, audio file comparison (if headless)

**Example Integration Test:**
```python
def test_load_process_analyze_pipeline(tmp_audio_file):
    """Full pipeline: load audio → process reverb → compute RT60."""
    from claudeverb.audio import load
    from claudeverb.algorithms.freeverb import Freeverb, FreeverbParams
    from claudeverb.analysis.metrics import compute_rt60

    # Load audio
    audio, sr = load(tmp_audio_file)
    assert sr == 48000

    # Process with reverb
    algo = Freeverb(FreeverbParams(room_size=0.8))
    processed = algo.process(audio)

    # Analyze
    rt60 = compute_rt60(processed)
    assert 0.5 < rt60 < 5.0  # Reasonable RT60 for reverb
```

## Common Patterns

**Async Testing:**
- Not applicable (DSP code is synchronous)
- Audio playback tests would use `sounddevice` in blocking mode

**Error Testing:**
```python
def test_invalid_room_size_raises_error(self):
    """FreeverbParams rejects room_size outside [0, 1]."""
    with pytest.raises(ValueError, match="room_size"):
        FreeverbParams(room_size=1.5)


def test_process_invalid_shape_raises_error(self):
    """process() raises on invalid audio shape."""
    algo = Freeverb(FreeverbParams())
    invalid_audio = np.zeros((3, 100), dtype=np.float32)  # Wrong shape

    with pytest.raises((ValueError, IndexError)):
        algo.process(invalid_audio)
```

**Audio Shape Testing:**
```python
@pytest.mark.parametrize("shape", [(100,), (2, 100), (3, 100)])
def test_process_shape_handling(freeverb_algo, shape):
    """Verify algorithm handles mono and stereo correctly."""
    if shape[0] == 3:
        with pytest.raises((ValueError, IndexError)):
            freeverb_algo.process(np.zeros(shape, dtype=np.float32))
    else:
        output = freeverb_algo.process(np.zeros(shape, dtype=np.float32))
        assert output.shape == shape
```

**Buffer Boundary Testing:**
```python
def test_process_handles_buffer_boundaries(freeverb_algo):
    """Circular buffer indices wrap correctly at boundaries."""
    # Process multiple buffers to verify index wrapping
    for _ in range(100):
        audio = np.random.randn(48).astype(np.float32) * 0.1
        output = freeverb_algo.process(audio)
        assert not np.any(np.isnan(output))  # No NaN from buffer errors
        assert not np.any(np.isinf(output))  # No infinity
```

---

*Testing analysis: 2026-03-04*
