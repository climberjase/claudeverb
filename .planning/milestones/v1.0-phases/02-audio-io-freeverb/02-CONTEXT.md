# Phase 2: Audio I/O + Freeverb - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

First complete audio path: load audio files, process through Freeverb with tweakable parameters (6 knobs + 2 switches), and output processed audio. This phase delivers the first end-to-end signal chain — file in, reverb, file out. UI, analysis metrics, and playback controls are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Freeverb Knob Mapping
- Combine wet+dry into a single **mix** knob (0=fully dry, 100=fully wet)
- 6th knob is **pre-delay** (0-100ms range), implemented with existing DelayLine primitive
- Final 6 knobs: room_size, damping, mix, width, pre-delay, + 1 TBD (or room_size, damping, mix, width, pre-delay with one spare)
- Full 0-100 range for all knobs — no constraining to "safe" values; workbench users can explore extreme settings
- Knob values are integers 0-100, internally scaled to algorithm-appropriate float ranges

### Bundled Test Samples
- Mix of synthesized signals (for testing/analysis) and real recordings (for listening evaluation)
- Synthesized: at minimum an impulse click; Claude's discretion on additional signals (white noise burst, sine sweep) for Phase 3 analysis readiness
- Real recordings: Claude's discretion on instrument focus, clip lengths, and sourcing

### Claude's Discretion
- **Switch mapping**: What the 2 three-position switches (-1, 0, 1) control (freeze mode, stereo mode, quality mode, etc.)
- **Stereo/mono conversion**: How to handle mono vs stereo input/output routing
- **File format support**: Whether to accept only WAV/AIFF or also MP3/FLAC/OGG via librosa
- **Multi-channel handling**: How to handle >2 channel files
- **Duration limits**: Whether to warn or limit on very long files
- **Module layout**: Whether audio I/O lives in `claudeverb/audio/` subpackage or flat
- **Output destination**: Memory-only vs auto-save behavior
- **Save format**: WAV 32-bit float vs 24-bit PCM
- **Reverb tail handling**: Whether to extend output to capture full decay tail
- **Clipping strategy**: Hard clip, soft clip, or no clip on output
- **Synth signal selection**: Which generated test signals beyond impulse
- **Sample clip lengths**: Duration of bundled recording clips
- **Sample instrument focus**: Guitar-focused vs mixed instruments

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **DelayLine** (`filters.py`): Ready for pre-delay implementation — instantiate with max_delay = ceil(0.1 * 48000) = 4800 samples
- **CombFilter** (`filters.py`): Lowpass-feedback-comb with damp1/damp2, exactly Freeverb's topology
- **AllpassFilter** (`filters.py`): Schroeder allpass with feedback=0.5, matches Freeverb default
- **Biquad** (`filters.py`): Available for any input/output tone shaping if needed
- **ReverbAlgorithm** (`base.py`): ABC with `_initialize()`, `_process_impl()`, `reset()`, `update_params()`, `param_specs` — Freeverb subclasses this directly
- **ALGORITHM_REGISTRY** (`algorithms/__init__.py`): Empty dict, ready for Freeverb registration

### Established Patterns
- Sample-by-sample core with block wrapper (all primitives follow this)
- float32 enforcement with TypeError on float64 (ReverbAlgorithm.process() validates)
- `__slots__` on all DSP classes for C-struct alignment
- `reset()` method zeroes all state on every primitive
- No dynamic allocation after `__init__` / `_initialize()`

### Integration Points
- `config.py` provides SAMPLE_RATE=48000, BUFFER_SIZE=48
- Freeverb delay line lengths must be scaled for 48 kHz (not Jezar's 44.1 kHz reference)
- `ALGORITHM_REGISTRY` needs Freeverb registered (key → class or factory)
- Audio I/O module will be imported by future Streamlit UI (Phase 4) and analysis pipeline (Phase 3)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Freeverb should follow Jezar's reference implementation topology (8 parallel combs → 4 series allpasses per channel) with the knob remapping decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-audio-io-freeverb*
*Context gathered: 2026-03-04*
