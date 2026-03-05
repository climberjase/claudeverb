# Phase 1: DSP Foundation - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

All DSP building blocks (delay lines, comb/allpass filters, EQ) exist, are tested, and enforce C-portability constraints so every algorithm built on them is portable by construction. No algorithm implementations in this phase — just the primitives.

</domain>

<decisions>
## Implementation Decisions

### Delay Line Design
- Support fractional (non-integer) tap positions from the start via linear interpolation
- Linear interpolation only (two-point lerp) — cheap, C-portable, sufficient for chorus/modulation effects
- Single read method called multiple times — no special multi-tap API
- Max size specified in samples (not milliseconds) — maps 1:1 to C array size

### Primitive Processing Style
- Sample-by-sample core with block wrapper: core logic is per-sample (`process_sample(x) -> y`), with a `process(block)` method that loops over samples
- Stateful objects: each primitive (CombFilter, AllpassFilter, DelayLine) holds its own state (delay buffer, index). Maps to C struct + function pair
- Fully encapsulated: CombFilter owns its DelayLine internally; users interact only via `process_sample()` and `reset()`

### Stereo Handling
- Primitives are mono-only — each processes one channel. Algorithms create two instances for stereo (left/right)
- Mono/stereo conversion happens in the algorithm's `process()` method, not in primitives
- Stereo reverbs use offset delay line lengths for width (e.g., Freeverb's +23 sample offset on right channel)
- Base ReverbAlgorithm validates float32 dtype and shape, raises TypeError for float64

### EQ Filter Design
- Biquad topology: Direct Form II Transposed — industry standard, numerically stable, C-portable
- Single `Biquad` class with factory methods: `Biquad.lowpass(freq, q)`, `Biquad.highpass(freq, q)`, `Biquad.notch(freq, q)`, `Biquad.bandpass(freq, q)`, `Biquad.parametric(freq, q, gain)`
- Smooth coefficient updates without resetting filter state — calling `set_frequency()` or `set_q()` recalculates coefficients without clearing delay state
- Hand-coded coefficient calculation from Robert Bristow-Johnson's Audio EQ Cookbook — no scipy dependency in DSP module, maps directly to C

### Claude's Discretion
- Whether to add a lightweight Protocol/ABC for DSP primitives (duck typing vs formal interface)
- Exact circular buffer implementation details
- Test fixture design beyond what conftest.py already specifies

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- No source code exists yet — greenfield project
- Architecture docs define the target structure: `claudeverb/algorithms/filters.py` for all primitives
- `tests/conftest.py` planned with `mono_sine`, `stereo_sine`, `impulse` fixtures

### Established Patterns
- `ReverbAlgorithm` abstract base in `base.py` defines the contract: `_initialize()`, `process()`, `reset()`, `update_params()`, `param_specs`
- All state as fixed-size arrays/scalars (np.ndarray with fixed shapes for delay lines, scalars for coefficients)
- No memory allocation inside `process()` — all allocation in `_initialize()`

### Integration Points
- `filters.py` is imported by all algorithm implementations (freeverb.py, plate.py)
- `config.py` provides SAMPLE_RATE=48000, BUFFER_SIZE=48
- `ALGORITHM_REGISTRY` in `algorithms/__init__.py` — not relevant for Phase 1 but primitives must support it

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The primitives should follow well-established DSP conventions (Jezar's Freeverb for comb/allpass, Bristow-Johnson's Cookbook for EQ).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-dsp-foundation*
*Context gathered: 2026-03-04*
