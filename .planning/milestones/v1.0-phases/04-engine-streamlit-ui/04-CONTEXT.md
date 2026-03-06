# Phase 4: Engine + Streamlit UI - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A developer can open a web browser, load audio, select an algorithm, tweak parameters, process, listen, and see analysis results -- the complete workbench workflow. Real-time processing, preset save/load, and side-by-side algorithm comparison are out of scope (v2).

</domain>

<decisions>
## Implementation Decisions

### Page Layout
- Sidebar controls + main canvas layout
- Sidebar contains: audio source selection, algorithm dropdown, 6 knob sliders, 2 switch selectors, wet/dry slider, Process button
- Main area contains: audio player(s), waveform display, spectrograms, FFT overlay, metric readouts
- Visualizations stacked vertically in the main area (not tabbed)

### Claude's Discretion
- **Audio source widget**: Whether to use dropdown, radio buttons, or another Streamlit widget for bundled sample selection; file uploader placement
- **Knob value display**: Whether sliders show just 0-100 or also the scaled internal value (e.g., "75 -> 0.84") -- developer workbench context favors showing both but Claude decides
- **Processing engine**: In-memory pipeline vs file-based pipeline for processed audio storage
- **Audio transport**: Whether to use st.audio built-in or build custom play/stop/loop controls
- **A/B comparison**: Two audio players (input + output) side by side, or single player with toggle/wet-dry switching
- **Download button**: Whether to include a download button for processed audio after processing
- **Wet/dry mix design**: Whether the UI-level wet/dry slider replaces the algorithm's internal mix knob or operates independently as a post-processing blend
- **Wet/dry placement**: Whether the slider lives in the sidebar with other controls or in the main area near audio playback
- **Wet/dry update behavior**: Whether changing wet/dry re-processes or blends stored dry+wet signals in real-time (real-time blend recommended)
- **Wet/dry + analysis interaction**: Whether analysis displays update when wet/dry changes or only on Process click
- **Default visualizations**: Which analysis panels show by default vs. behind checkboxes/expanders
- **Metrics display format**: st.metric() cards vs table vs other layout for RT60, DRR, C80, C50, centroid delta
- **IR generation trigger**: Separate "Generate IR" button vs auto-generate behind the scenes with Process (note: RT60/DRR/C80 metrics require an IR)
- **Reset to defaults button**: Whether to include a button that restores all knobs/switches to default values

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ALGORITHM_REGISTRY` (`algorithms/__init__.py`): Dict mapping "freeverb" -> Freeverb class. Streamlit dropdown populates from this.
- `ReverbAlgorithm.param_specs` property: Returns dict of parameter specs (name, min, max, default, unit). Sliders auto-generate from this.
- `SAMPLE_REGISTRY` + `get_sample()` (`audio/samples.py`): 6 bundled samples (impulse, white_noise_burst, sine_sweep, drum, guitar, vocal). Dropdown/radio populates from `list_samples()`.
- `audio.io.load()`: Handles WAV/AIFF/FLAC/OGG loading with auto-resample to 48kHz. File upload feeds into this.
- `audio.io.save()`: Saves WAV float32. Can generate in-memory bytes for st.audio or download.
- `audio.impulse.generate_impulse_response()`: Generates IR from any algorithm instance. Takes algorithm + duration, returns float32 array.
- `analysis.metrics`: `measure_rt60()`, `measure_rt60_bands()`, `compute_drr()`, `compute_clarity()`, `spectral_centroid_delta()` -- all accept mono/stereo float32.
- `analysis.spectral`: `plot_mel_comparison()`, `plot_fft_comparison()` -- return matplotlib figures, which Streamlit can display via `st.pyplot()`.

### Established Patterns
- All audio is float32, mono (N,) or stereo (2,N), 48kHz
- Algorithms reset between runs via `algorithm.reset()`
- `param_specs` property defines all algorithm parameters -- UI should be fully data-driven from this
- CombFilter/AllpassFilter/DelayLine are internal to algorithms; UI never touches them directly

### Integration Points
- `Freeverb` class instantiated with `Freeverb()`, calls `_initialize()` internally
- `algorithm.update_params({"room_size": 75, ...})` updates parameters
- `algorithm.process(audio)` returns processed audio (same shape/dtype)
- Spectral plots return matplotlib Figure objects; use `st.pyplot(fig)` to render
- Metric functions return floats/dicts; format for display

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard Streamlit approaches. The UI should feel like a developer workbench (functional, not flashy).

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 04-engine-streamlit-ui*
*Context gathered: 2026-03-05*
