# Architecture

## Audio conventions
All audio is `float32` in `[-1.0, 1.0]`. Shape `(N,)` for mono, `(2, N)` for stereo. Sample rate is always `SAMPLE_RATE = 48000` (defined in `claudeverb/config.py`). `BUFFER_SIZE = 48` matches the expected Daisy Seed audio callback block size.

## Algorithm layer (`claudeverb/algorithms/`)
`base.py` defines `ReverbAlgorithm` (abstract) and `ReverbParams` (dataclass). Every concrete algorithm must implement:
- `_initialize()` — allocate fixed-size delay lines, no alloc after this
- `process(audio)` — process a full buffer; must not allocate
- `reset()` — zero all delay lines and filter state
- `update_params()` — recompute coefficients from `self.params` without resetting state
- `param_specs` — dict of `ParamSpec` used by the UI to build sliders

`filters.py` contains the shared DSP primitives: `CombFilter`, `AllpassFilter`, `DelayLine`. Each class documents its C struct equivalent in its docstring. These are the building blocks for all algorithms.

`ALGORITHM_REGISTRY` in `__init__.py` is the single source of truth for which algorithms appear in the UI dropdown.

## C portability constraints
Algorithms must be portable to C (STM32 Daisy Seed). This means:
- State is representable as fixed-size C arrays and scalars (no Python objects in hot path)
- No dynamic allocation after `_initialize()` — mirrors C stack/static allocation
- Delay lines are always circular buffers
- `to_c_struct()` and `to_c_process_fn()` generate the actual C code
- `Freeverb` is the reference implementation with full C generation support

## UI layer (`claudeverb/ui/`)
Built with **PySide6** + **matplotlib** (embedded via `FigureCanvasQTAgg`).
- `app.py` → `MainWindow`: wires controls to visualization panels
- `panels/controls.py` → `ControlsPanel`: file picker, algorithm selector, dynamic parameter sliders. Emits `process_requested(dry_audio, algorithm)` signal.
- `panels/waveform.py` → `WaveformPanel`: side-by-side dry/wet time-domain waveforms
- `panels/spectrogram.py` → `SpectrogramPanel`: mel spectrogram (dry/wet), magnitude spectrum overlay, acoustic metrics (RT60, DRR, C80, spectral centroid)

The controls panel rebuilds its parameter sliders dynamically from `algorithm.param_specs` whenever the algorithm selection changes.

## Analysis layer (`claudeverb/analysis/`)
Pure functions — no state. `spectral.py` wraps librosa for mel spectrograms, STFT, and FFT magnitude. `metrics.py` implements RT60 (Schroeder backward integration), DRR, C80/C50, and spectral centroid. All functions accept `(N,)` or `(2, N)` float32 arrays and handle channel averaging internally.

## Audio I/O (`claudeverb/audio/io.py`)
`load(path)` → `(audio, 48000)` — resamples to 48 kHz automatically using polyphase filtering. `save(path, audio)` writes 24-bit PCM.

## Export (`claudeverb/export/c_codegen.py`)
`export_algorithm(algo, output_dir)` calls `algo.to_c_struct()` and `algo.to_c_process_fn()` and writes `.h`/`.c` files. Generated files target the libDaisy framework but are straightforward to adapt to bare-metal STM32.

## Adding a new algorithm

1. Create `claudeverb/algorithms/myalgo.py` — subclass `ReverbAlgorithm`, implement all abstract methods, document the C struct in a docstring.
2. Add it to `ALGORITHM_REGISTRY` in `claudeverb/algorithms/__init__.py`.
3. Add tests to `tests/test_algorithms/test_myalgo.py` (use `conftest.py` fixtures: `mono_sine`, `stereo_sine`, `impulse`).
4. Implement `to_c_struct()` and `to_c_process_fn()` when ready for Daisy Seed port.
