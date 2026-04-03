# Phase 7: FDN Reverb Algorithm - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can apply a Feedback Delay Network reverb that sounds fundamentally different from Freeverb and Dattorro Plate -- denser, more even decay without metallic coloration. 4-channel Hadamard FDN with coprime delays and per-band decay. No early reflections (Phase 8), no C export UI (Phase 9), no real-time playback (Phase 10).

</domain>

<decisions>
## Implementation Decisions

### Knob Mapping
- **Knob 1: Decay Time** -- maps 0-100 to decay time range (e.g., 0.2s to 20s), most intuitive control
- **Knob 2: Size** -- scales all delay line lengths independently from decay, controls perceived room dimension
- **Knob 3: Damping** -- HF rolloff in feedback loop (dark-to-bright)
- **Knob 4: Modulation** -- chorus-like delay modulation depth for lushness and metallic coloration reduction
- **Knob 5: Mix** -- wet/dry (engine forces mix=100 internally, UI handles blend)
- **Knob 6: Pre-Delay** -- delay before reverb onset
- **Switch 1: Freeze** -- Freeze/Normal/Bright (consistent with Freeverb)
- **Switch 2: Stereo Mode** -- Mono/Stereo/Wide (consistent with Freeverb)

### Tonal Character
- Target: smooth and dense, even colorless decay -- "transparent concert hall" sound
- Opposite of Freeverb's comb-filter coloration
- Per-band decay: low and high frequencies decay at different rates (damping knob controls HF; separate mechanism for LF)
- No specific reference target (Lexicon, Valhalla, etc.) -- just distinct from existing algorithms
- Dense from the start -- no gradual build-up (early reflections are Phase 8's concern)

### FDN Topology
- 4-channel Hadamard mixing matrix (4x4), coprime delay line lengths
- Input diffusers: 2-4 allpass filters before the FDN to smear input and reduce plinky attacks
- Modulated delays: slow LFO on delay times to break up metallic resonances
- Stereo output: channels 0+2 to Left, channels 1+3 to Right, width knob controls cross-feed
- DC blockers in feedback loop to prevent DC buildup (reuse DCBlocker from dattorro_plate.py)
- Per-channel damping filters (OnePole lowpass) in the feedback path

### Phase 8 Reuse Architecture
- Composable design: FDN reverb algorithm wraps an internal FDNCore class
- FDNCore handles delay network + feedback matrix + damping + modulation
- Phase 8 Room/Chamber algorithms will compose FDNCore with their own early-reflection stage
- FDNCore should have a clean process() API that Phase 8 can call independently

### C Export Support
- Include to_c_struct() and to_c_process_fn() methods following Freeverb's pattern
- FDN C struct: 4 delay lines, Hadamard matrix (4x4 float array), 4 damping filters, 4 DC blockers, input diffusers, LFO state
- All state as fixed-size arrays and scalars -- no dynamic allocation after _initialize()

### Presets
- Include 3-4 presets (e.g., Small Hall, Large Hall, Cathedral, Ambient)
- Follow Dattorro preset pattern: dict of param values feeding update_params()
- Presets help users explore FDN's range immediately

### Claude's Discretion
- Exact coprime delay line lengths (at 48 kHz)
- Number of input diffusers (2, 3, or 4) and their delay lengths
- LFO rate and maximum modulation depth range
- Per-band decay implementation (crossover frequency, LF decay mechanism)
- Hadamard matrix normalization factor
- Exact preset parameter values (tuned by ear/metrics)
- Input distribution strategy (how mono input maps to 4 FDN channels)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DelayLine` (filters.py): Fixed-size circular buffer with fractional delay interpolation -- core building block for FDN channels
- `AllpassFilter` (filters.py): Schroeder allpass with process_sample/process -- use for input diffusion stage
- `OnePole` (dattorro_plate.py): Simple one-pole lowpass -- use for per-channel damping in feedback loop
- `DCBlocker` (dattorro_plate.py): First-order DC blocking filter -- use in FDN feedback path
- `Biquad` (filters.py): Full biquad EQ with shelf/parametric factories -- available if per-band decay needs crossover filter
- `ReverbAlgorithm` base class (base.py): Abstract base with process/reset/update_params/param_specs interface

### Established Patterns
- Algorithm registration: `ALGORITHM_REGISTRY` dict in `__init__.py` maps string key to class
- Parameter interface: `param_specs` property returns dict of 6 knobs (type=knob, min=0, max=100) + 2 switches (type=switch, positions=[-1,0,1])
- C struct docstring: Each algorithm file starts with a C struct typedef comment showing the equivalent C representation
- Sample-by-sample processing: All algorithms use inner loops with process_sample() calls, not vectorized numpy
- float32 throughout: All state stored as np.float32 scalars, all buffers float32 arrays

### Integration Points
- `ALGORITHM_REGISTRY` in `claudeverb/algorithms/__init__.py`: Add "fdn" -> FDNReverb entry
- `engine.process_audio()`: No changes needed -- FDN plugs in via the registry like any algorithm
- Streamlit UI auto-generates controls from `param_specs` -- FDN gets UI controls automatically
- Preset system: Follow `dattorro_presets.py` pattern for FDN presets

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches. Target is "sounds good and distinct from Freeverb/Dattorro."

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 07-fdn-reverb-algorithm*
*Context gathered: 2026-03-11*
