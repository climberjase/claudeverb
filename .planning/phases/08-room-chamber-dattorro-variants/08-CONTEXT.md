# Phase 8: Room, Chamber & Dattorro Variants - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can apply room-character reverbs with early reflections (Small Room, Large Room, Chamber) and explore Dattorro topology modifications (Single-Loop Tank, Triple-Diffuser, Asymmetric Tank). 6 new algorithms total. No signal-flow diagrams (Phase 9), no C export UI (Phase 9), no real-time playback (Phase 10).

</domain>

<decisions>
## Implementation Decisions

### Early Reflections Design
- **Hybrid approach:** Tapped delay line for discrete wall reflections + short allpass chain for density
- **Serial routing:** ER output feeds into FDNCore as its input (ER -> FDN, not parallel)
- **Shared engine:** One `EarlyReflections` class with configurable tap count, tap positions, and diffuser settings; each algorithm passes different config
- **Standalone composable class:** `EarlyReflections` in its own file (early_reflections.py), composed with FDNCore by Room/Chamber algorithms (follows FDNCore pattern)
- **6-8 taps:** Small Room uses 6 taps, Large Room and Chamber use 8
- **Per-tap lowpass filtering:** Later taps get more HF rolloff (OnePole per tap), simulating air absorption
- **Stereo imaging:** Alternating L/R taps (odd taps left, even taps right)
- **ER Level knob:** Dedicated knob (replaces Mod), range 0 = no ER (pure FDN tail) to 100 = ER only (no tail), default ~40

### Room vs Chamber Character

**Small Room — Small concert space / chapel:**
- Decay: 0.5 - 2.0s
- ER: moderate density, wider tap spacing
- Character: warm, musical
- Use case: acoustic instruments, ensembles

**Large Room — Large studio live room (Abbey Road):**
- Decay: 1.0 - 3.5s
- ER: dense, controlled
- Character: professional, balanced
- Use case: full band recording, orchestral sessions

**Chamber — Classic echo chamber (Capitol Studios):**
- Decay: 1.0 - 4.0s
- ER: subtle, quickly diffused (4 taps + 3 allpass diffusers vs Room's 6-8 taps + 1-2 diffusers)
- Character: thick, warm, smooth, less spatial definition
- Warmer FDN damping defaults than Rooms

### Room/Chamber Architecture
- **Separate files:** small_room.py, large_room.py, chamber.py
- **Shared base class:** RoomReverbBase handles ER->FDN serial chain, param routing, C export boilerplate; subclasses override config (tap positions, decay range, diffuser count)
- **Different FDN delays per algorithm:** Each passes different coprime prime base_delays to FDNCore, scaled to perceived room dimension
- **Size knob scales both ER + FDN:** Tap positions and FDN delay lengths scale together — whole space grows/shrinks
- **Internal modulation:** FDNCore still applies subtle fixed modulation (depth ~0.3, rate ~0.5 Hz) as anti-metallic insurance; not user-controllable
- **General purpose tuning:** Defaults optimized for drums, vocals, guitar, keys — Hothouse-specific tuning deferred to hardware testing
- **2-3 presets each:** Small Room (Vocal Booth, Drum Room), Large Room (Live Room, Orchestra Hall), Chamber (Echo Chamber, Bright Chamber)

### Dattorro Topology Variants
- **Fully independent implementations:** Each variant is its own algorithm with distinct tank topology, not subclassed from DattorroPlate
- **Each has own input section:** No shared code with existing DattorroPlate

**Single-Loop Tank — Griesinger-style:**
- One long modulated delay loop with nested allpass sections
- Based on David Griesinger's single-loop reverberator design
- Denser, less stereo separation than figure-eight; stereo from output tap spacing
- Research needed on specific Griesinger topology details

**Triple-Diffuser:**
- 6 input allpass diffusers (double Dattorro's 4) feeding standard figure-eight tank
- Ultra-smooth onset, no discernible attack transients
- Tank topology same as Plate; input section is the differentiator

**Asymmetric Tank:**
- Different L/R delay lengths AND different diffuser counts between left and right paths
- Maximum asymmetry for widest stereo image
- Both timing and tonal asymmetry between channels

### Knob Mapping

**Room/Chamber knobs (shared layout):**
1. Decay — decay time
2. Size — scales ER taps + FDN delays together
3. Damping — HF rolloff
4. ER Level — early reflections prominence (0=none, 100=ER only)
5. Mix — wet/dry
6. Pre-Delay — delay before reverb onset

**Room/Chamber switches:**
- Switch 1: Freeze / Normal / Bright
- Switch 2: Mono / Stereo / Wide

**Dattorro variant knobs (mostly shared, knob 2 unique):**

Single-Loop Tank:
1. Decay  2. Loop Length (30-150ms)  3. Damping  4. Mod  5. Mix  6. Pre-Delay

Triple-Diffuser:
1. Decay  2. Diffusion Density (2-6 active diffusers)  3. Damping  4. Mod  5. Mix  6. Pre-Delay

Asymmetric Tank:
1. Decay  2. Spread (symmetric->max asymmetry)  3. Damping  4. Mod  5. Mix  6. Pre-Delay

**Dattorro variant switches:**
- Switch 1: Freeze / Normal / Shimmer (inherits Plate's Shimmer)
- Switch 2: Mono / Stereo / Wide

**Unique knob ranges (0-100 with clear sonic endpoints):**
- Loop Length: 0 = short (~30ms, tight) to 100 = long (~150ms, spacious)
- Diffusion Density: 0 = 2 diffusers active (some attack) to 100 = all 6 active (zero attack)
- Spread: 0 = symmetric (like Plate) to 100 = max asymmetry (widest stereo)

### Presets
- All 6 algorithms get 2-3 presets each
- Follow existing preset pattern (dict of param values feeding update_params())

### Claude's Discretion
- Exact ER tap positions and gains per algorithm (tuned by metrics)
- Exact allpass diffuser delay lengths and coefficients
- Exact FDN base delay values per algorithm (coprime primes at appropriate scale)
- Exact damping coefficient defaults per algorithm
- Griesinger single-loop topology details (from research)
- ER Level default value per algorithm
- Preset parameter values (tuned by ear/metrics)
- Number of allpass diffusers in ER stage per algorithm (1-2 for Rooms, 3 for Chamber)
- RoomReverbBase file location (room_base.py or similar)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FDNCore` (fdn_reverb.py:116): Composable 4-channel Hadamard FDN — Room/Chamber compose this with EarlyReflections. Accepts custom base_delays and has set_rt60/set_damping/set_modulation APIs.
- `DelayLine` (filters.py): Fixed-size circular buffer with fractional delay — used for ER tapped delay line
- `AllpassFilter` (filters.py): Schroeder allpass — used for ER diffusion stage and Dattorro variant diffusers
- `OnePole` (dattorro_plate.py): One-pole lowpass — used for per-tap ER filtering and FDN damping
- `DCBlocker` (dattorro_plate.py): DC blocking filter — used in all feedback loops
- `DattorroPlate` (dattorro_plate.py:154): Reference for Dattorro tank topology, tap positions, shimmer implementation. Variants are independent but can reference this for DSP patterns.
- `ReverbAlgorithm` base class (base.py): Abstract base with process/reset/update_params/param_specs/to_c_struct/to_c_process_fn interface
- `fdn_presets.py` / `dattorro_presets.py`: Preset pattern to follow for all new algorithms

### Established Patterns
- Algorithm registration: `ALGORITHM_REGISTRY` dict in `__init__.py` — add 6 new entries
- Parameter interface: `param_specs` property returns dict of 6 knobs (0-100) + 2 switches (-1/0/1)
- C struct docstring: Each algorithm file starts with C struct typedef comment
- Sample-by-sample processing: Inner loops with process_sample() calls
- Composable DSP: FDNCore pattern — clean process() API that wraps internal state
- Preset files: Separate `*_presets.py` files with get_presets()/get_preset() functions

### Integration Points
- `ALGORITHM_REGISTRY` in `claudeverb/algorithms/__init__.py`: Add 6 new entries (small_room, large_room, chamber, dattorro_single_loop, dattorro_triple_diffuser, dattorro_asymmetric)
- `engine.process_audio()`: No changes needed — all algorithms plug in via registry
- Streamlit UI: Auto-generates controls from param_specs. Preset dropdown needs to recognize new algorithms.
- Preset system: Streamlit shows preset dropdown when algorithm has presets (conditional on algorithm key)

### New Files Needed
- `claudeverb/algorithms/early_reflections.py` — EarlyReflections composable class
- `claudeverb/algorithms/room_base.py` (or similar) — RoomReverbBase shared base class
- `claudeverb/algorithms/small_room.py` — SmallRoom algorithm
- `claudeverb/algorithms/large_room.py` — LargeRoom algorithm
- `claudeverb/algorithms/chamber.py` — Chamber algorithm
- `claudeverb/algorithms/small_room_presets.py` — SmallRoom presets
- `claudeverb/algorithms/large_room_presets.py` — LargeRoom presets
- `claudeverb/algorithms/chamber_presets.py` — Chamber presets
- `claudeverb/algorithms/dattorro_single_loop.py` — Single-Loop Tank variant
- `claudeverb/algorithms/dattorro_triple_diffuser.py` — Triple-Diffuser variant
- `claudeverb/algorithms/dattorro_asymmetric.py` — Asymmetric Tank variant
- `claudeverb/algorithms/dattorro_single_loop_presets.py` — Single-Loop presets
- `claudeverb/algorithms/dattorro_triple_diffuser_presets.py` — Triple-Diffuser presets
- `claudeverb/algorithms/dattorro_asymmetric_presets.py` — Asymmetric presets

</code_context>

<specifics>
## Specific Ideas

- Griesinger single-loop topology needs research — well-documented in DSP literature but specifics TBD
- Chamber's "fewer taps + more diffusers" ER config is key to its distinct character
- Size knob scaling both ER + FDN together is the most natural room size control
- Dattorro variants at Spread=0 / Diffusion Density=0 should approximate standard Plate behavior

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-room-chamber-dattorro-variants*
*Context gathered: 2026-04-02*
