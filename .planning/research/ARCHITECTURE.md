# Architecture Patterns

**Domain:** DSP reverb workbench -- v1.1 feature integration
**Researched:** 2026-03-07

## Existing Architecture Snapshot

Before defining integration points, here is the current system structure as built in v1.0:

```
claudeverb/
  config.py              -- SAMPLE_RATE=48000, BUFFER_SIZE=48
  engine.py              -- Facade: process_audio(), blend_wet_dry(), plot_waveform_comparison()
  streamlit_app.py       -- UI layer (sidebar params, main area results)
  algorithms/
    base.py              -- ReverbAlgorithm ABC (_initialize, _process_impl, reset, update_params, param_specs)
    filters.py           -- DelayLine, CombFilter, AllpassFilter, Biquad (5 factory methods)
    freeverb.py          -- 8 combs + 4 allpass per channel, stereo spread
    dattorro_plate.py    -- Figure-eight tank, OnePole, DCBlocker, LFO modulation
    __init__.py          -- ALGORITHM_REGISTRY dict
  audio/
    io.py                -- load/save with 48 kHz resample
    samples.py           -- Bundled sample discovery
    impulse.py           -- IR generation via unit impulse
    __init__.py
  analysis/
    metrics.py           -- RT60, DRR, C80/C50, spectral centroid delta
    spectral.py          -- Mel spectrogram, FFT comparison plots
    __init__.py
```

**Established patterns carried forward unchanged:**
- Registry-based algorithm discovery (dict in `algorithms/__init__.py`)
- ABC with `param_specs` property driving auto-generated UI controls (knobs 0-100, switches -1/0/1)
- Engine facade decouples DSP from Streamlit -- UI never calls algorithm methods directly
- All DSP primitives use `__slots__`, float32, sample-by-sample `process_sample()` + block `process()`
- C portability: fixed-size delay lines, no dynamic alloc after `_initialize()`
- Process-then-play workflow via `st.audio()` with pre-encoded WAV bytes

## Recommended Architecture for v1.1

### Component Map: New vs Modified

```
NEW COMPONENTS:
  claudeverb/
    algorithms/
      dattorro_variants.py   -- NEW: Dattorro parameter/topology variants
      fdn_reverb.py          -- NEW: Feedback Delay Network reverb
      room_reverb.py         -- NEW: Small/large room algorithms
      chamber_reverb.py      -- NEW: Chamber reverb algorithm
    audio/
      realtime.py            -- NEW: Real-time playback engine (sounddevice callback thread)
      padding.py             -- NEW: Silence padding for reverb tail capture
    export/
      __init__.py            -- NEW
      c_codegen.py           -- NEW: C struct/process code generation
      templates/             -- NEW: C code template strings or files
    diagrams/
      __init__.py            -- NEW
      signal_flow.py         -- NEW: Algorithm signal-flow diagram rendering

MODIFIED COMPONENTS:
  claudeverb/
    algorithms/
      __init__.py            -- MODIFIED: Register new algorithms in ALGORITHM_REGISTRY
      filters.py             -- MODIFIED: Add TappedDelayLine, BiquadChain
      base.py                -- MODIFIED: Add signal_flow_description() concrete method (returns None by default)
    engine.py                -- MODIFIED: Add EQ post-processing, silence padding, C export orchestration
    streamlit_app.py         -- MODIFIED: Real-time controls, EQ panel, export button, diagram display, multi-file
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| New algorithm files | DSP processing, param specs, signal flow metadata | `base.py` (inherit ABC), `filters.py` (use primitives) |
| `audio/realtime.py` | Threaded audio playback via sounddevice, parameter callback bridge | `engine.py` (gets algorithm instance), `streamlit_app.py` (receives param updates via session_state) |
| `audio/padding.py` | Append silence to audio for reverb tail capture | `engine.py` (called before processing) |
| `export/c_codegen.py` | Generate C source files from algorithm instances + current params | Algorithm instances (reads state/param values), `export/templates/` |
| `diagrams/signal_flow.py` | Render signal-flow block diagrams as matplotlib figures | Algorithm instances (reads `signal_flow_description()`), `streamlit_app.py` (displays figure) |
| `filters.py` additions | `TappedDelayLine` for early reflections, `BiquadChain` for EQ trails | Algorithms (use TappedDelayLine), `engine.py` (uses BiquadChain post-reverb) |

### Data Flow Changes

**Current v1.0 flow (process-then-play):**
```
Audio File -> load() -> engine.process_audio(algo_name, params, audio)
  -> algo.process(audio.copy()) -> wet signal
  -> generate_impulse_response() -> IR
  -> metrics + figures
  -> blend_wet_dry(dry, wet, mix_pct) -> st.audio()
```

**v1.1 enhanced batch flow:**
```
Audio File -> load() -> padding.pad_for_tail(audio, tail_s)
  -> engine.process_audio(algo_name, params, padded_audio, eq_params=...)
    -> algo.process(padded_audio) -> wet_raw
    -> eq_chain.process(wet_raw) -> wet_eq'd        [NEW: EQ on trail]
    -> generate_impulse_response() -> IR
    -> metrics + figures
    -> signal_flow_description() -> diagram figure   [NEW: signal flow]
  -> blend_wet_dry(dry_padded, wet_eq, mix_pct) -> st.audio()
  -> c_codegen.generate(algo, params) -> /daisyexport/  [NEW: on button click]
```

**v1.1 real-time playback flow:**
```
Audio File -> load() -> padding.pad_for_tail(audio)
  -> RealtimePlayer(algorithm, padded_audio, eq_chain)
    -> sounddevice.OutputStream callback (runs in separate thread):
        for each 48-sample block:
          dry_block = read next block from source audio
          wet_block = algorithm._process_impl(dry_block)  [NOTE: uses _process_impl not process -- skip validation in hot path]
          wet_block = eq_chain.process(wet_block)
          out_block = blend(dry_block, wet_block, mix)
          -> output to DAC
  <- UI knob change -> Streamlit rerun -> player.update_params(new_params)
     -> algorithm.update_params() called from audio thread's next block
```

## Integration Details by Feature

### 1. New Reverb Algorithms (Dattorro Variants, FDN, Room, Chamber)

**Integration point:** Subclass `ReverbAlgorithm`, register in `ALGORITHM_REGISTRY`. Zero UI code changes needed -- the sidebar auto-generates controls from `param_specs`.

**Dattorro variants strategy:** Do NOT create separate classes per parameter tweak. Instead, create 2-3 topology variants as separate classes that share helper code via composition:
- `DattorroPlate` -- already exists (figure-eight tank, the "classic" plate)
- `DattorroHall` -- longer delay lines, more diffusion stages, different tap positions
- `DattorroRoom` -- shorter delays, reduced diffusion, earlier reflections emphasis

Share the tank-half processing as a standalone function:
```python
def _process_tank_half(input_sample, decay_ap1, tank_delay1, damping_filter,
                       decay_ap2, tank_delay2, dc_blocker, decay, lfo_mod,
                       base_delay1, base_delay2):
    """Process one half of a Dattorro figure-eight tank. Used by all variants."""
    ...
    return tank_output
```

This avoids inheritance (which breaks C export -- no vtables) while eliminating code duplication.

**FDN reverb** (`fdn_reverb.py`): Feedback Delay Network with N=4 or N=8 delay lines and a Hadamard mixing matrix. The mixing matrix is a fixed NxN float32 array (C-portable). Delay lines reuse `DelayLine` from `filters.py`. The matrix multiply per sample is:
```python
# FDN core: output = delay_reads; feedback = matrix @ output; delay_writes = input + feedback
outputs = [dl.read(dl.max_delay) for dl in self._delay_lines]
feedback = hadamard_multiply(self._matrix, outputs)  # NxN * N -> N
for j, dl in enumerate(self._delay_lines):
    dl.write(input_sample + feedback[j] * self._decay)
```

**Room reverb** (`room_reverb.py`): Early reflections (tapped delay line) + late reverb (comb-allpass network, shorter than Freeverb). Requires new `TappedDelayLine` primitive.

**Chamber reverb** (`chamber_reverb.py`): Similar to room but with denser early reflections and a longer, more diffuse tail. Can use FDN for the late part or a modified comb network.

**New filter primitive needed in `filters.py`:**
```python
class TappedDelayLine:
    """Multi-tap delay line for early reflections.
    Fixed number of taps with per-tap delay and gain.
    C-portable: MAX_TAPS defined at init, no dynamic allocation.
    """
    MAX_TAPS = 16  # Fixed upper bound for C struct

    def __init__(self, max_delay: int, taps: list[tuple[int, float]]):
        # taps: [(delay_samples, gain), ...]
        self._delay = DelayLine(max_delay)
        self._tap_delays = np.zeros(self.MAX_TAPS, dtype=np.int32)
        self._tap_gains = np.zeros(self.MAX_TAPS, dtype=np.float32)
        self._n_taps = min(len(taps), self.MAX_TAPS)
        for i, (d, g) in enumerate(taps[:self.MAX_TAPS]):
            self._tap_delays[i] = d
            self._tap_gains[i] = np.float32(g)

    def process_sample(self, x: float) -> float:
        """Write input, return sum of all taps."""
        self._delay.write(x)
        output = 0.0
        for i in range(self._n_taps):
            output += self._tap_gains[i] * self._delay.read(self._tap_delays[i])
        return float(output)
```

### 2. Real-Time Audio Playback

**Integration point:** New `audio/realtime.py` module, stored in `st.session_state`, UI controls in `streamlit_app.py`.

**Why sounddevice callback thread, not Streamlit audio:** Streamlit's `st.audio()` encodes WAV bytes and sends them to the browser. There is no way to interrupt playback or change parameters mid-stream. Real-time requires a server-side audio thread that reads blocks, processes through the algorithm, and outputs to the system DAC.

```python
# audio/realtime.py
import threading
import sounddevice as sd
import numpy as np

class RealtimePlayer:
    """Plays audio through sounddevice with live DSP processing.

    The sounddevice callback runs in a separate thread. Parameter updates
    are passed via a thread-safe mechanism (simple dict swap -- Python's
    GIL makes dict assignment atomic for our purposes).
    """

    def __init__(self, algorithm: ReverbAlgorithm, audio: np.ndarray,
                 eq_chain=None, sample_rate: int = 48000, block_size: int = 48):
        self._algorithm = algorithm
        self._audio = audio  # padded source audio
        self._eq_chain = eq_chain
        self._position = 0
        self._loop = False
        self._mix_pct = 75
        self._playing = False
        self._stream = None
        self._pending_params = None  # Set by UI thread, consumed by audio thread

    def play(self, loop: bool = False) -> None:
        """Start playback. Creates sounddevice.OutputStream."""
        self._loop = loop
        self._algorithm.reset()
        if self._eq_chain:
            self._eq_chain.reset()
        self._position = 0
        self._stream = sd.OutputStream(
            samplerate=self._sample_rate,
            blocksize=self._block_size,
            channels=2,  # always stereo output
            dtype='float32',
            callback=self._audio_callback,
        )
        self._stream.start()
        self._playing = True

    def stop(self) -> None: ...
    def update_params(self, params: dict) -> None:
        """Called from Streamlit thread. Consumed by audio callback."""
        self._pending_params = params  # Atomic dict assignment

    def _audio_callback(self, outdata, frames, time_info, status):
        """sounddevice callback -- runs in audio thread."""
        # Check for pending param updates
        params = self._pending_params
        if params is not None:
            self._algorithm.update_params(params)
            self._pending_params = None
        # Read block, process, output
        ...
```

**Streamlit lifecycle management:** The `RealtimePlayer` must survive Streamlit reruns. Store it in `st.session_state["player"]`. On each rerun, check if it exists and is playing. The UI shows Play/Stop buttons and knobs. Knob changes trigger `player.update_params()` on each rerun.

**Block size:** 48 samples at 48 kHz = 1ms. This matches `BUFFER_SIZE` in `config.py` and the Daisy Seed callback size. Excellent latency.

**Multi-file and loop/single-shot:** The player holds one audio array. Switching files requires `player.stop()`, load new audio, create new player. Loop mode wraps the read pointer; single-shot stops at end.

### 3. EQ on Reverb Trails

**Integration point:** New `BiquadChain` class in `filters.py`, applied in `engine.py` between reverb output and wet/dry mix.

```python
# Addition to filters.py
class BiquadChain:
    """Ordered chain of Biquad filters for reverb trail EQ.
    C-portable: fixed maximum number of bands."""
    MAX_BANDS = 4

    def __init__(self):
        self._filters: list[Biquad] = []
        self._enabled = True

    def add(self, biquad: Biquad) -> None:
        if len(self._filters) >= self.MAX_BANDS:
            raise ValueError(f"Maximum {self.MAX_BANDS} EQ bands")
        self._filters.append(biquad)

    def process_sample(self, x: float) -> float:
        if not self._enabled:
            return x
        for f in self._filters:
            x = f.process_sample(x)
        return x

    def process(self, block: np.ndarray) -> np.ndarray:
        if not self._enabled:
            return block
        for f in self._filters:
            block = f.process(block)
        return block

    def reset(self) -> None:
        for f in self._filters:
            f.reset()
```

**Signal chain placement -- EQ on wet only:**
```
algorithm.process(audio) -> BiquadChain.process(wet) -> blend_wet_dry(dry, wet) -> output
```

The EQ shapes the reverb trail only, not the dry signal. This matches hardware reverb pedals with built-in EQ.

**UI controls:** Add an expander in the sidebar with:
- EQ enable/disable toggle
- 2 bands default (low cut + high cut covers 80% of use cases for reverb shaping)
- Per-band: type dropdown (LP/HP/peak/notch), frequency slider, Q slider, gain_db slider (for peak only)

**engine.py modification:** `process_audio()` gains an optional `eq_params: list[dict] | None` argument. If provided, build `BiquadChain` from the param dicts, apply after `algo.process()`.

### 4. Silence Padding for Reverb Tails

**Integration point:** New `audio/padding.py`, called in `engine.py` before processing.

```python
# audio/padding.py
def pad_for_tail(audio: np.ndarray, tail_seconds: float = 3.0,
                 sample_rate: int = 48000) -> tuple[np.ndarray, int]:
    """Append silence so reverb tail is captured after input ends.

    Returns:
        (padded_audio, original_length) -- original_length needed to
        reconstruct the dry signal for blend.
    """
    pad_samples = int(tail_seconds * sample_rate)
    if audio.ndim == 1:
        padding = np.zeros(pad_samples, dtype=np.float32)
        return np.concatenate([audio, padding]), len(audio)
    else:
        padding = np.zeros((2, pad_samples), dtype=np.float32)
        return np.concatenate([audio, padding], axis=1), audio.shape[1]
```

**Where to apply:** In `engine.process_audio()`, before calling `algo.process()`. The dry signal must also be padded (with zeros) to match length for `blend_wet_dry()`. Currently `blend_wet_dry()` assumes same-length arrays, which is correct -- both dry and wet will be `original_length + pad_samples`.

### 5. C Code Export

**Integration point:** New `export/` package, UI button in `streamlit_app.py`.

**Architecture: Template-based code generation with explicit type mapping.**

Do NOT parse C struct descriptions from docstrings (fragile). Instead, add a concrete method to `base.py`:

```python
# Addition to base.py
def c_state_fields(self) -> list[tuple[str, str, any]] | None:
    """Return C struct field definitions: [(c_type, field_name, current_value), ...]
    Returns None if C export is not implemented for this algorithm.
    Override in subclasses that support C export."""
    return None
```

The codegen module reads this + the algorithm's current params to produce:

**Output structure in `/daisyexport/`:**
```
daisyexport/
  dsp_primitives.h    -- DelayLine, CombFilter, AllpassFilter, Biquad, BiquadChain structs + inline functions
  dsp_primitives.c    -- Implementation of non-inline functions
  {algorithm_name}.h  -- Algorithm struct typedef + API declarations
  {algorithm_name}.c  -- init(), process_sample(), update_params() implementations
  main.c              -- Daisy Seed AudioCallback harness with libDaisy
  Makefile             -- arm-none-eabi-gcc build rules
```

**UI integration:** "Export to C" button in sidebar. Uses current algorithm + current param values as `#define` defaults. Writes files to `daisyexport/` directory and offers ZIP download.

### 6. Signal-Flow Diagrams

**Integration point:** `base.py` gets a concrete (not abstract) `signal_flow_description()` method returning `None` by default. New `diagrams/signal_flow.py` renders these.

**Making it concrete with a None default is critical** -- it means existing algorithms (Freeverb, DattorroPlate) continue working without modification. New algorithms can opt in by overriding.

```python
# Addition to base.py (NOT abstract -- concrete with None default)
def signal_flow_description(self) -> dict | None:
    """Declarative signal flow for diagram rendering.
    Override to provide algorithm-specific signal flow.

    Returns dict with:
      nodes: [{id, label, type}] -- type: input|output|delay|filter|mixer|splitter|allpass|comb
      edges: [{from_id, to_id, label?}]
      groups: [{id, label, node_ids}] -- for visual grouping (e.g., "Left Tank", "Right Tank")
    """
    return None
```

**Renderer** (`diagrams/signal_flow.py`):
```python
def render_signal_flow(description: dict) -> plt.Figure:
    """Render a block diagram from a signal_flow_description dict.
    Uses matplotlib patches and arrows. No external graph library needed.
    """
```

Use matplotlib's `FancyBboxPatch` for nodes and `FancyArrowPatch` for edges. Color-code by node type (blue for delays, green for filters, etc.). This avoids adding graphviz as a dependency.

**UI display:** In the main area, add a "Signal Flow" expander or tab that renders the diagram for the currently selected algorithm. Only shown if `signal_flow_description()` returns non-None.

### 7. Multi-File Loading

**Integration point:** `streamlit_app.py` session state only. No architectural changes.

```python
# In session_state
st.session_state["loaded_files"] = {
    "audio1-acoustic": np.ndarray,  # bundled sample
    "uploaded_guitar.wav": np.ndarray,  # user upload
    ...  # max 5
}
st.session_state["active_file"] = "audio1-acoustic"
```

UI shows a selectbox to pick the active file. When switching files during real-time playback, stop playback first, swap audio in player, restart.

## Patterns to Follow

### Pattern 1: Registry Auto-Discovery (unchanged)
All new algorithms register in `ALGORITHM_REGISTRY`. The UI auto-generates controls. Zero UI code per algorithm.

### Pattern 2: Sample-by-Sample with Block Wrapper (unchanged)
All new DSP components implement `process_sample()` for the inner loop and `process()` for block convenience. The sample-by-sample path maps directly to C.

### Pattern 3: Facade Engine Isolation (extended)
The engine gains new responsibilities (EQ application, padding, export orchestration) but remains the single coordination point. The UI never calls algorithms, analysis, or export directly.

### Pattern 4: C-Portable State (unchanged, enforced on new components)
All new filters (`TappedDelayLine`, `BiquadChain`) and algorithms use `__slots__`, float32, fixed-size arrays. The `test_c_portability.py` tests must be extended to cover all new components.

### Pattern 5: Thread-Safe Parameter Updates for Real-Time
**New pattern.** The real-time player uses atomic dict swap for parameter updates. The Streamlit thread writes `player._pending_params = new_dict`. The audio callback thread reads and clears it. Python's GIL makes single-attribute assignment atomic.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Inheritance for Algorithm Variants
**What:** Making `DattorroHall(DattorroPlate)` inheritance hierarchies.
**Why bad:** Topologies differ structurally (different delay counts, tap patterns). Inheritance forces shared `_process_impl()` that becomes conditional spaghetti. Also breaks C export (no vtables in C structs).
**Instead:** Composition. Share helper functions and filter primitives. Each algorithm is standalone.

### Anti-Pattern 2: Real-Time Processing in Streamlit's Main Thread
**What:** Running sounddevice callbacks synchronized with Streamlit reruns.
**Why bad:** Streamlit reruns the entire script on every widget interaction. The audio thread must be fully decoupled.
**Instead:** Store `RealtimePlayer` in `st.session_state`. It owns the sounddevice thread independently.

### Anti-Pattern 3: Putting EQ Inside Algorithm Classes
**What:** Adding EQ bands as part of each algorithm's `_process_impl()`.
**Why bad:** EQ is a post-processing step that applies identically to ALL algorithms. Duplicating it in each algorithm violates DRY and complicates C export.
**Instead:** `BiquadChain` applied in `engine.py` after `algorithm.process()` returns.

### Anti-Pattern 4: Generating C Code from Docstrings
**What:** Parsing the C struct comments in algorithm docstrings to generate code.
**Why bad:** Fragile, no type checking, breaks silently when comments drift from implementation.
**Instead:** Structured `c_state_fields()` method or explicit codegen registry.

### Anti-Pattern 5: Abstract Methods for Optional Features
**What:** Making `signal_flow_description()` or `c_state_fields()` abstract on the base class.
**Why bad:** Forces every existing and future algorithm to implement them even if they have nothing to provide. Breaks existing tests.
**Instead:** Concrete methods returning `None` by default. Subclasses override when ready.

## Suggested Build Order

Build in this order to respect dependencies and enable incremental testing:

```
Phase 1: Foundation Primitives (no UI changes, no breakage)
  1. audio/padding.py              -- Simple np.concatenate, enables tail preservation
  2. filters.py: TappedDelayLine   -- Needed by Room/Chamber algorithms
  3. filters.py: BiquadChain       -- Needed by EQ feature
  Tests for each.

Phase 2: New Algorithms (registry additions only)
  4. fdn_reverb.py                 -- New topology, independent
  5. room_reverb.py                -- Uses TappedDelayLine + combs/allpass
  6. chamber_reverb.py             -- Uses TappedDelayLine + FDN or combs
  7. dattorro_variants.py          -- Extends existing Dattorro work
  Register all in __init__.py. Tests for each. UI auto-discovers them.

Phase 3: Engine Enhancements (modify engine.py)
  8. engine.py: silence padding    -- Call padding.pad_for_tail() before processing
  9. engine.py: EQ post-processing -- Apply BiquadChain between reverb and mix
  10. base.py: signal_flow_description() + c_state_fields() -- Concrete defaults

Phase 4: Visualization + UI Features
  11. diagrams/signal_flow.py           -- Matplotlib block diagram renderer
  12. streamlit_app.py: EQ controls     -- Expander with band params
  13. streamlit_app.py: multi-file      -- Session state management, selectbox
  14. streamlit_app.py: diagram display -- Tab/expander for signal flow
  15. Algorithm signal_flow_description() overrides -- Per-algorithm

Phase 5: Real-Time Playback (most complex integration)
  16. audio/realtime.py                 -- sounddevice thread + param bridge
  17. streamlit_app.py: playback UI     -- Play/stop/loop, live knobs
  Manual testing required (audio thread behavior hard to unit test).

Phase 6: C Export (needs finalized algorithms)
  18. export/c_codegen.py               -- Template-based generation
  19. export/templates/                  -- Primitive + algorithm C templates
  20. Algorithm c_state_fields() overrides
  21. streamlit_app.py: export button   -- Trigger + ZIP download
```

**Phase ordering rationale:**
- Phases 1-2 are pure additions with no modifications to existing code -- zero risk of breakage
- Phase 3 modifies engine.py but changes are additive (new optional params)
- Phase 4 is UI polish that builds on Phase 3
- Phase 5 (real-time) is isolated to its own module but requires careful Streamlit lifecycle management -- benefits from all algorithms being stable first
- Phase 6 (C export) needs all algorithms finalized so the codegen covers the full set

## Scalability Considerations

| Concern | Current (2 algos) | At 8 algorithms | At 20+ algorithms |
|---------|-------------------|------------------|--------------------|
| Registry | Dict literal | Dict literal, still fine | Auto-discovery via module scanning |
| UI controls | Auto-generated from param_specs | Works unchanged | Need algorithm categories in sidebar |
| C export | Per-algorithm templates | Template per algo + shared primitives | Consider structured IR for algorithm description |
| Real-time perf | Python sample loop fine | Only 1 algo active at a time | Complex algos may need numpy vectorized batch mode |
| Signal flow diagrams | Hand-authored per algorithm | Repetitive | Consider DSL for signal flow description |

## Sources

- Existing codebase analysis -- direct inspection of all .py files (HIGH confidence)
- Dattorro, J. "Effect Design Part 1: Reverberator and Other Filters" JAES 1997 -- tank topology, output taps, figure-eight structure (HIGH confidence)
- sounddevice library -- callback-based audio streaming, already in project deps via sounddevice (HIGH confidence)
- Streamlit session_state -- persistent state across reruns, established pattern already used in v1.0 code (HIGH confidence)
- Pirkle, W. "Designing Audio Effect Plugins in C++" -- FDN topology, Hadamard matrix, room reverb early reflections patterns (MEDIUM confidence -- training data)
- Smith, J.O. "Physical Audio Signal Processing" -- FDN mixing matrices, allpass theory (MEDIUM confidence -- training data)
