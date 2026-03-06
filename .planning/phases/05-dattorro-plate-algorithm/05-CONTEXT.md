# Phase 5: Dattorro Plate Algorithm - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The Dattorro Plate reverb is available in the workbench, producing the lush plate sound characteristic of the 1997 paper's figure-eight tank topology. Includes modulated delay lines, shimmer mode, and stereo output from the inherently stereo tank. This phase delivers one new algorithm registered alongside Freeverb — no UI changes, no new analysis, no new audio I/O.

</domain>

<decisions>
## Implementation Decisions

### Knob Mapping (6 knobs, 0-100 int)
- Knob 1: **Decay** — tank feedback coefficient (reverb tail length, short slap to near-infinite sustain)
- Knob 2: **Bandwidth** — input HF rolloff before the tank (how bright the signal entering the reverb is)
- Knob 3: **Tank Damping** — in-loop HF decay (how fast high frequencies die within the tank)
- Knob 4: **Diffusion** — combined input + decay diffusion (low = discrete echoes, high = smooth wash). Single knob scales both input diffusion and decay diffusion coefficients together
- Knob 5: **Pre-delay** — 0-100ms delay before tank input, implemented with existing DelayLine primitive
- Knob 6: **Mod Depth** — tank modulation amount (LFO excursion in samples). No dedicated mix knob since the UI's wet/dry slider already handles that

### Switch Mapping (2 switches, 3-position: -1, 0, 1)
- Switch 1: **Freeze (-1) / Normal (0) / Shimmer (+1)**
  - Freeze: infinite hold with zero input gain (same concept as Freeverb freeze)
  - Normal: standard plate reverb operation
  - Shimmer: subtle octave-up pitch shift blended into tank feedback (~10-20% blend). Airy, ethereal quality without being obviously pitch-shifted
- Switch 2: **Mono (-1) / Stereo (0) / Wide (+1)**
  - Consistent with Freeverb's Switch 2 for interface familiarity
  - Mono sums both tank output taps
  - Wide doubles width scaling (capped at 1.0)

### Tank Modulation
- LFO shape: **Sine** — faithful to the paper, smooth modulation, maps to C sinf()
- LFO rate: **Fixed ~1 Hz** — slow, gentle modulation for lushness without chorusing
- Mod behavior: **Off at depth=0, active above** — mod depth knob at 0 means fully static delays (no unnecessary computation). Depth knob controls excursion only, not rate

### Shimmer Implementation
- Simple octave-up via half-rate sample reading in the tank feedback path
- C-portable (no FFT or granular processing), low CPU
- Reverb tail masks pitch-shift artifacts naturally
- Subtle blend level (~10-20%) for ethereal texture, not obvious pitch effect

### Topology & Paper Fidelity
- Follow Dattorro's 1997 paper topology exactly: 4 input allpass diffusers → figure-eight tank with 2 crossed delay paths, each containing embedded allpass filters
- Rescale all delay line lengths from the paper's 29761 Hz sample rate to 48 kHz
- Mono input → stereo tank → stereo output (even mono signals get spatial spread from the tank)
- Stereo outputs tapped from different points in the figure-eight loop as the paper describes

### Claude's Discretion
- Exact delay line length values after 48 kHz rescaling
- Default knob values (0-100) for each parameter
- Internal parameter scaling ranges (how 0-100 maps to algorithm coefficients)
- Output gain/scaling to match Freeverb's output level
- Whether to add a DC blocker in the tank loop (common plate reverb practice)
- Tank output tap positions and mix coefficients

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **DelayLine** (`filters.py`): Supports fractional delays via linear interpolation — essential for tank modulation. Pre-delay reuses this directly (max 4800 samples at 48 kHz)
- **AllpassFilter** (`filters.py`): Schroeder allpass with configurable feedback — used for input diffusers and tank-embedded allpasses. May need multiple instances with different feedback coefficients
- **CombFilter** (`filters.py`): Lowpass-feedback-comb — not directly used in Dattorro topology but feedback/damp pattern is instructive
- **Biquad** (`filters.py`): Available for input bandwidth filtering (lowpass) and any tank tone shaping
- **ReverbAlgorithm** (`base.py`): ABC with `_initialize()`, `_process_impl()`, `reset()`, `update_params()`, `param_specs` — DattorroPlate subclasses this
- **ALGORITHM_REGISTRY** (`algorithms/__init__.py`): Register as "plate" or "dattorro_plate"
- **Freeverb** (`freeverb.py`): Reference for `__slots__`, `_scale_params()` pattern, `param_specs` format, mono/stereo dispatch, hard clip output

### Established Patterns
- Sample-by-sample core with block wrapper (all primitives and Freeverb follow this)
- float32 enforcement with TypeError on float64 (ReverbAlgorithm.process() validates)
- `__slots__` on all DSP classes for C-struct alignment
- `reset()` zeroes all delay lines and filter state
- No dynamic allocation after `_initialize()`
- Hard clip output to [-1.0, 1.0] for C portability
- `_scale_params()` converts 0-100 knob values to internal float ranges

### Integration Points
- Register in `ALGORITHM_REGISTRY` in `algorithms/__init__.py`
- `config.py` provides SAMPLE_RATE=48000, BUFFER_SIZE=48
- Streamlit UI auto-generates controls from `param_specs` — no UI changes needed
- Engine facade (`engine.py`) works with any registered algorithm via the ReverbAlgorithm interface

</code_context>

<specifics>
## Specific Ideas

- The Dattorro plate should sound audibly distinct from Freeverb — lusher, more diffuse, with visible frequency smearing in spectrograms from tank modulation
- Shimmer should be subtle and ethereal, not an obvious pitch-shift effect — think ambient guitar textures
- The algorithm is the primary target for eventual guitar pedal deployment on Daisy Seed, so C portability is paramount

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-dattorro-plate-algorithm*
*Context gathered: 2026-03-05*
