# Phase 6: Playback Enhancements & EQ - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can load multiple audio files, control playback looping, preserve reverb tails with silence padding, shape reverb tone with post-reverb EQ, and explore Dattorro parameter presets. No real-time playback (Phase 10), no new algorithms (Phase 7-8), no C export (Phase 9).

</domain>

<decisions>
## Implementation Decisions

### Silence Padding
- Slider control, 0-5 seconds range, continuous
- On by default at 2 seconds -- new users hear full reverb tail immediately
- Silence is appended to input audio before processing
- Padded region visually marked in the output waveform display (shaded or annotated)

### EQ Controls & Signal Flow
- Checkbox toggle to enable/disable EQ, sliders appear inline below when enabled
- 3-band: low shelf, mid parametric, high shelf
- EQ applies to the wet (reverb) signal only, before wet/dry mix -- dry signal untouched
- Existing Biquad class in filters.py has all needed factory methods (lowpass, highpass, parametric, shelving via parametric)

### Dattorro Presets
- Preset selector appears below algorithm dropdown, only visible when Dattorro Plate is selected
- When preset is selected, all knobs snap to preset values (transparent, educational)
- If user tweaks any knob after selecting preset, label changes to "Custom"
- Presets are Dattorro-specific for now (not a general system)

### Multi-file & Playback
- Users can load multiple files from /samples and switch between them
- Loop toggle controls Streamlit st.audio loop parameter

### Claude's Discretion
- Silence padding placement in sidebar (near audio source vs near Process button)
- Default EQ frequencies, gain range (dB), and whether mid Q is adjustable or fixed
- Number and naming of Dattorro presets (aim for distinct reverb characters)
- Multi-file switching UX pattern (selectbox vs tabs vs file manager)
- Whether to cache processed results per file or reprocess on switch
- Whether uploaded files merge into the same file list as bundled samples
- Loop toggle placement (sidebar checkbox vs per-player control)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Biquad` class (`claudeverb/algorithms/filters.py`): Complete biquad EQ with lowpass, highpass, notch, bandpass, parametric factory methods. Has `set_coefficients()` for smooth parameter changes and `process()` for block processing. Ready to wire into signal path.
- `DattorroPlate` class (`claudeverb/algorithms/dattorro_plate.py`): Full implementation with `param_specs` and `update_params()`. Presets are dicts of param values that feed directly into `update_params()`.
- `_audio_to_wav_bytes()` (`claudeverb/streamlit_app.py`): Pre-encodes WAV to bypass Streamlit normalization. Reuse for all new audio players.
- `get_sample()` / `list_samples()` (`claudeverb/audio/samples.py`): Current sample loading system. Extend for multi-file.

### Established Patterns
- Engine facade (`claudeverb/engine.py`): All DSP processing goes through `process_audio()`. EQ and silence padding should integrate here, not in the UI layer.
- Session state management: Streamlit session state used for `dry_audio`, `wet_audio`, `results`, `audio_loaded`. Multi-file will extend this pattern.
- Algorithm param specs: `param_specs` property on each algorithm drives auto-generated UI controls. Preset system should work alongside this.
- Mix override: Engine forces `mix=100` internally; UI wet/dry handles blend. EQ goes between algorithm output and wet/dry blend.

### Integration Points
- `engine.process_audio()`: Add silence padding (pre-process) and EQ (post-process) here
- Sidebar audio source section: Extend for multi-file loading
- Sidebar algorithm section: Add preset dropdown below algorithm selectbox
- `st.audio()` calls: Add loop parameter control

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 06-playback-enhancements-eq*
*Context gathered: 2026-03-08*
