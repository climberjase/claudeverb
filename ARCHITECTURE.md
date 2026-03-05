# Architecture

ClaudeVerb is an audio algorithm development workbench that runs in a web frontend (with streamlit) with a Python backend for the testing, verfication and development
of reverb plugins, with an emphasis on providing the ability to try out and tune the sound of reverb algorithms that can eventually be exported to C code for execution
on a DaisySeed STM32 based microprocessor board for real-time effects processing in a guitar pedal.

All algorithms should support up to 6 parametric parameters that will be controlled by knobs with ranges of 0-100.

All algorithms should also have the ability to support "switched" parameters with two 3-position switches (with ranges of -1, 0 and 1).

## Phases

The development of this project will be braken into the following phases:

1. basic UI workbench for development and testing of different styles of reverb DSP algorithms
2. algorithm development and test harnesses, which include listening tests, audio tests, and variaous audio analysis functions like Mel Spectrogram comparison, RT60 comparison etc.
3. algorithm testing and audio listening tests using the local MacOS system sound
4. algorithm export to Daisy Seed compatible C code that can be run inside a Hothouse DSP host pedal from Cleveland Audio
5. an algorithm tuning guide that allows for hyperparameter searches and parameter/switch position searches to try to as closely as possible match the resuls of .AU plugins loaded locally

This is a python application which can serve content to a streamlit frontend UI that will run in a web browser.

## Audio conventions
All audio is `float32` in `[-1.0, 1.0]`. Shape `(N,)` for mono, `(2, N)` for stereo. 

Sample rate is always `SAMPLE_RATE = 48000`

`BUFFER_SIZE = 48` matches the expected Daisy Seed audio callback block size so that locally developed 

## Algorithm layer (`claudeverb/algorithms/`)

No convolution reverbs should be supported - this workbench is only for development of algorithm based reverbs.

### Pure C Reverb Algoritms
`base.py` defines `ReverbAlgorithm` (abstract) and `ReverbParams` (dataclass) used for local testing.

Algorithms will be processed in Python code for local testing of the algorithms.

 Every concrete algorithm must implement:
- `_initialize()` — allocate fixed-size delay lines, no alloc after this
- `process(audio)` — process a full buffer; must not allocate
- `reset()` — zero all delay lines and filter state
- `update_params()` — recompute coefficients from `self.params` without resetting state
- `param_specs` — dict of `ParamSpec` used by the UI to build knobs (with ranges of 0 to 100) and 2 switches with 3 positions each (with values -1, 0, 1).

### Local Audio Units

The system should also allow commercial DSP Audio Plugin Units (.au files) to be loaded from the local systems' installed list of plugins, and these should
be able to also be applied as test algorithms to the input and output audio algorithms.

### Filter Algorithms

`filters.py` contains the shared DSP primitives: `CombFilter`, `AllpassFilter`, `DelayLine`, `EQFilters`.

Each class documents its C struct equivalent in its docstring. These are the building blocks for all algorithms.

The ability to provide tone shaping should be provided by the EQFilters with a selection of filter types possible, including:
- high pass filters
- low pass filters
- notch filters
- band pass filters
- parametric boost/cut filters

All libraries must be implemented in pure python functions that can be exportable to C functions after verification and testing.

`ALGORITHM_REGISTRY` in `__init__.py` is the single source of truth for which algorithms appear in the UI dropdown.

## C portability constraints
Algorithms must be portable to C (STM32 Daisy Seed). This means:
- State is representable as fixed-size C arrays and scalars (no Python objects in hot path)
- No dynamic allocation after `_initialize()` — mirrors C stack/static allocation
- Delay lines are always circular buffers
- `to_c_struct()` and `to_c_process_fn()` generate the actual C code
- `Freeverb` is the reference implementation with full C generation support

## UI layer (`claudeverb/ui/`)
TODO


## Analysis layer (`claudeverb/analysis/`)
Pure functions — no state. `spectral.py` wraps librosa for mel spectrograms, STFT, and FFT magnitude. 
`metrics.py` implements RT60 (Schroeder backward integration), DRR, C80/C50, and spectral centroid. 
All functions accept `(N,)` or `(2, N)` float32 arrays and handle channel averaging internally.

This layer must allow for a selection of set audio input files as samples to have reverb applied, in addition to an impulse response generation from the algorithimic reverb.

## Audio I/O (`claudeverb/audio/io.py`)
`load(path)` → `(audio, 48000)` — resamples to 48 kHz automatically using polyphase filtering. `save(path, audio)` writes 24-bit PCM.

## Export (`claudeverb/export/c_codegen.py`)
`export_algorithm(algo, output_dir)` calls `algo.to_c_struct()` and `algo.to_c_process_fn()` and writes `.h`/`.c` files. Generated files target the libDaisy framework but are straightforward to adapt to bare-metal STM32.

## Adding a new algorithm

1. Create `claudeverb/algorithms/myalgo.py` — subclass `ReverbAlgorithm`, implement all abstract methods, document the C struct in a docstring.
2. Add it to `ALGORITHM_REGISTRY` in `claudeverb/algorithms/__init__.py`.
3. Add tests to `tests/test_algorithms/test_myalgo.py` (use `conftest.py` fixtures: `mono_sine`, `stereo_sine`, `impulse`).
4. Implement `to_c_struct()` and `to_c_process_fn()` when ready for Daisy Seed port.
