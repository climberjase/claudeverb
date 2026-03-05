# Technology Stack

**Analysis Date:** 2025-02-18

## Languages

**Primary:**
- Python 3.x - DSP algorithms, analysis, UI, and C code generation

**Secondary:**
- C - Target output for STM32 Daisy Seed embedded platform (generated via C codegen)

## Runtime

**Environment:**
- CPython (reference implementation assumed, though not explicitly specified)
- Deployment target: STM32 microcontroller (Daisy Seed for real-time guitar pedal effects)

**Package Manager:**
- pip - Python package installation
- Lockfile: Not detected in current codebase

## Frameworks

**Core:**
- Streamlit - Web-based UI frontend (mentioned in ARCHITECTURE.md for browser interface)
- PySide6 - Desktop GUI framework (referenced in MEMORY.md)

**Audio Processing:**
- librosa - Spectral analysis and mel spectrogram computation (`claudeverb/analysis/`)
- scipy - Digital signal processing (implied for filter design and audio processing)
- NumPy - Numerical array operations

**Audio I/O:**
- soundfile - Audio file loading/saving with 24-bit PCM support
- sounddevice - Local macOS audio playback for listening tests

**Testing:**
- pytest - Test framework (referenced in setup instructions)

**Build/Dev:**
- matplotlib - Visualization of spectral analysis results and metrics

## Key Dependencies

**Critical:**
- NumPy - Core numerical computation for audio signal processing
- scipy - Filters, signal analysis, DSP algorithms
- librosa - Mel spectrogram, STFT, FFT magnitude analysis
- soundfile - Audio file I/O at 48 kHz with automatic resampling
- sounddevice - Real-time audio playback and monitoring

**Infrastructure:**
- Streamlit - Web UI framework for algorithm comparison and parameter tuning
- PySide6 - Desktop UI (mentioned in project memory)
- matplotlib - Visualization of spectral data and acoustic metrics

## Configuration

**Environment:**
- Sample rate hardcoded as `SAMPLE_RATE = 48000` in `claudeverb/config.py`
- Buffer size: `BUFFER_SIZE = 48` (matches Daisy Seed callback size)
- Audio format: float32 in range [-1.0, 1.0], mono `(N,)` or stereo `(2, N)`

**Build:**
- `setup.py` or `pyproject.toml` expected (standard Python project structure)
- Installation: `pip install -e ".[dev]"`

## Platform Requirements

**Development:**
- macOS (primary development platform noted in project context)
- Python 3.x with pip
- Local AU (Audio Unit) plugin support for commercial algorithm comparison

**Production:**
- STM32 Daisy Seed microcontroller (target deployment platform)
- libDaisy framework (C library for Daisy Seed audio DSP)
- Real-time audio processing at 48 kHz with 48-sample buffer blocks

## C Portability Requirements

**Code Generation Target:**
- Generated C files: `.h` and `.c` targeting libDaisy framework
- Algorithms must support fixed-size delay lines (circular buffers)
- No dynamic allocation after `_initialize()`
- State representable as C arrays and scalars
- Output: Daisy Seed compatible code for guitar pedal deployment

---

*Stack analysis: 2025-02-18*
