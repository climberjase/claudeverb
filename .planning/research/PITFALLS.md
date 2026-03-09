# Domain Pitfalls

**Domain:** DSP reverb workbench v1.1 -- adding Dattorro variants, FDN reverb, Room/Chamber reverb, real-time audio, EQ on trails, C export, signal-flow diagrams
**Researched:** 2026-03-07
**Context:** Building on v1.0 (Freeverb + Dattorro Plate working, Streamlit UI, process-then-play workflow, 152 tests passing). These pitfalls are specific to the v1.1 feature set.

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: FDN Feedback Matrix Instability

**What goes wrong:** The FDN reverb blows up (output goes to infinity) or decays unevenly across frequencies because the feedback matrix has eigenvalues with modulus > 1 or has coupled repeated poles.

**Why it happens:** FDN stability requires a unitary (or orthogonal) feedback matrix -- all eigenvalues must have modulus exactly 1. Developers often use arbitrary matrices, random rotations with rounding errors, or matrices that are "close to unitary" but not exactly so. At 48 kHz with long delay lines, even tiny deviations from unitarity accumulate over millions of samples and cause exponential blowup or uneven frequency decay.

**Consequences:** Audio clips, distorts, or blows up. If eigenvalues are merely close to 1 but not exact, the reverb may sound fine for short inputs but explode on sustained sounds or long tails. This is the single hardest bug to diagnose because it manifests differently depending on input material and parameter settings.

**Prevention:**
- Use a mathematically guaranteed unitary matrix: Hadamard (for power-of-2 sizes), Householder reflection (`I - 2vv^T/||v||^2`), or an explicitly constructed orthogonal matrix.
- For the Daisy Seed target (Cortex-M7 with FPU), Householder is ideal: O(N) multiply per sample vs O(N^2) for general unitary. A 4x4 or 8x8 Householder with `v = [1,1,1,...,1]` gives the classic "all-ones" reflection matrix.
- Test with a 10-second silence input after a click -- output energy must monotonically decrease. Add an automated test that checks `max(abs(output[-48000:])) < max(abs(output[:48000]))` for any parameter combination.
- Never construct the matrix at runtime from user parameters. Pre-define 2-3 fixed unitary matrices and let the user select between them via a switch. Parameters should control delay lengths, feedback gain (scaling applied AFTER the unitary matrix), and damping -- not the matrix itself.

**Detection:** Output energy increasing over time. DC offset growing. Clipping at the end of long reverb tails. The existing `measure_rt60()` function returning negative or infinite values.

**Confidence:** HIGH -- well-established DSP theory. See [CCRMA FDN reference](https://ccrma.stanford.edu/~jos/pasp/FDN_Reverberation.html) and [KVR FDN discussion](https://www.kvraudio.com/forum/viewtopic.php?t=123095).

---

### Pitfall 2: Real-Time Audio in Streamlit is Architecturally Impossible Without a Hybrid Approach

**What goes wrong:** Developers try to add "live knob tweaking with real-time playback" inside Streamlit and discover that Streamlit's architecture makes true real-time audio impossible. `st.audio` plays pre-rendered WAV bytes -- there is no streaming audio output. Parameter changes trigger full page reruns.

**Why it happens:** Streamlit is a reactive framework: every widget interaction causes the entire script to re-execute. There is no persistent audio output stream, no callback mechanism for continuous playback, and `st.*` methods cannot be called from background threads. The existing `sounddevice` dependency could provide real-time audio via PortAudio callbacks, but `sounddevice` operates in a separate thread that cannot interact with Streamlit widgets.

**Consequences:** If you try to build real-time playback purely in Streamlit, you end up with one of: (a) a "process-then-play" workflow that is functionally identical to what v1.0 already has, (b) a fragile hack using `streamlit-webrtc` that adds massive complexity, or (c) a hybrid architecture where `sounddevice` runs audio in a background thread while Streamlit provides the UI, communicating via shared state with locks.

**Prevention:**
- Accept that "real-time" in Streamlit means: `sounddevice.OutputStream` runs the audio callback in a PortAudio thread, reading from a shared audio buffer. Streamlit UI writes parameter changes to a thread-safe shared state. The audio callback reads current parameters each block and applies them.
- The audio callback must process exactly `BUFFER_SIZE=48` samples per call (matching Daisy Seed), reading the current algorithm state and writing output to the sounddevice buffer.
- Use `sd.OutputStream(callback=..., blocksize=48, samplerate=48000)` for the audio thread.
- Keep Streamlit responsible ONLY for: loading files, displaying parameters, showing analysis. Audio playback is entirely via sounddevice.
- Do NOT try to synchronize Streamlit UI updates with audio playback position -- accept that analysis/visualization updates lag behind audio.
- The current engine's `process_audio()` function creates a fresh algorithm instance each call. Real-time mode needs a persistent algorithm instance that lives across Streamlit reruns -- store it in `st.session_state` or a module-level singleton.

**Detection:** Audio glitches (buffer underruns), Streamlit freezing during playback, inability to change parameters while audio plays.

**Confidence:** HIGH -- verified via [Streamlit community discussion on real-time audio](https://discuss.streamlit.io/t/experience-report-working-with-realtime-audio-in-streamlit/86637) and [sounddevice threading docs](https://python-sounddevice.readthedocs.io/en/latest/api/streams.html).

---

### Pitfall 3: Dattorro Topology Modifications Breaking Stability and Character

**What goes wrong:** Modifications to the Dattorro plate topology (adding diffusion stages, changing tank structure, modifying tap positions) produce metallic artifacts, uneven decay, channel bouncing, or a persistent tail that never fully decays.

**Why it happens:** The Dattorro topology is a carefully tuned figure-eight feedback network. The delay lengths, diffusion coefficients, tap positions, and cross-feedback points were chosen together as an interdependent system. The existing `DattorroPlate` implementation has 14 output taps at specific positions scaled from the 1997 paper -- moving or adding taps changes the frequency coloration. The paper itself notes that topology changes require complete re-tuning.

**Consequences:** Variants that sound metallic, colored, or unstable. Stereo modifications that cause the reverb to "bounce" between channels. Topology changes that require complete re-tuning of all parameters, effectively designing a new reverb from scratch. Per [KVR discussion](https://www.kvraudio.com/forum/viewtopic.php?t=564078): modifying the topology for stereo input "results in non-smooth response with uneven decay time" and "unbalanced tank feeding can cause output bouncing between channels."

**Consequences for v1.1 specifically:** The project scopes "Dattorro parameter variants" AND "topology variants." These are very different risk levels. Parameter variants are safe tweaks to the existing `DattorroPlate` class. Topology variants are effectively new algorithms.

**Prevention:**
- **Parameter variants are safe:** Changing `decay`, `bandwidth`, `damping`, `diffusion`, `pre_delay`, `mod_depth` ranges, scaling curves, or default values. Adding new switch modes (e.g., "dark" mode that reduces bandwidth and increases damping). These modify `_scale_params()` but not the topology in `_process_impl()`. Low risk.
- **Topology variants are high-risk:** Treat each topology change as a new algorithm class. Create `DattorroHall`, `DattorroAmbience`, etc. as separate classes sharing primitives from `filters.py` but with independently tuned delay lengths, tap positions, and diffusion structure.
- **Never modify tap positions without listening tests.** The tap positions in the current implementation (`LEFT_TAPS_29761`, `RIGHT_TAPS_29761`) are from Table 2 of the paper.
- **Do not add extra feedback paths** without understanding the resulting transfer function. Each additional path changes the pole structure and can create instability.
- Budget 2x the expected time for each topology variant. The Dattorro paper itself states tuning is 70% of reverb development effort.

**Detection:** A/B listening test against the reference `DattorroPlate` with identical parameter settings. RT60 measurement should be consistent across frequency bands. Impulse response FFT should not show new resonant peaks.

**Confidence:** HIGH -- corroborated by [KVR Dattorro improvements thread](https://www.kvraudio.com/forum/viewtopic.php?t=564078), the [original paper](https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf), and the existing codebase structure.

---

### Pitfall 4: C Export Generating Non-Functional Code

**What goes wrong:** The C code export produces syntactically correct `.h`/`.c` files that compile but do not produce the same output as the Python implementation, or crash on the Daisy Seed due to stack overflow, uninitialized memory, or floating-point edge cases.

**Why it happens:** Multiple failure modes specific to this codebase:
1. **Python-to-C intermediate precision:** The Python code uses `np.float32` for state variables (verified by `test_c_portability.py`), but intermediate calculations like `x * self._feedback + delay_out` in `AllpassFilter.process_sample()` happen in Python 64-bit float before being cast back to `np.float32`. The C code uses 32-bit throughout, producing different rounding.
2. **Uninitialized delay lines:** Python `np.zeros()` initializes to zero. C stack arrays do not. The Dattorro algorithm has ~30,000 total delay samples across its 13 delay components -- that is ~120KB of float32 that must be zero-initialized.
3. **Stack overflow on Daisy Seed:** 120KB of delay buffers on the stack will crash immediately. The STM32H750 on the Daisy Seed has limited stack (typically 8-16KB default). All delay line arrays must go in BSS (static) or SDRAM.
4. **Modulo wrapping:** Python's `%` returns positive results for negative operands; C's `%` preserves the sign. The `DelayLine.read()` method computes `read_pos = self._write_index - delay` which can be negative. The C equivalent `read_pos % max_delay` will produce a negative index.
5. **Math library differences:** `math.sin()` (Python) vs `sinf()` (C) vs `arm_sin_f32()` (CMSIS-DSP) produce slightly different results. The LFO in Dattorro uses `math.sin(self._lfo_phase)` per sample.

**Consequences:** C code that compiles but sounds different, crashes, or produces silence. Code that works in a desktop C test but fails on the actual Daisy Seed.

**Prevention:**
- Generate code that uses `static` arrays for all delay lines (BSS segment, not stack). For Daisy Seed, use the SDRAM section annotation: `float buffer[SIZE] __attribute__((section(".sdram_bss")))`.
- Use `memset(buf, 0, sizeof(buf))` in the init function.
- For circular buffer indexing, use: `int idx = ((raw_idx % len) + len) % len;` or always keep indices positive with `if (idx < 0) idx += len;`.
- Add a Python-side "C simulation" test: process audio using `np.float32` for ALL intermediates (wrap every arithmetic operation in `np.float32(...)`), not just state. Compare outputs sample-by-sample against the normal Python output.
- Generate a test harness alongside the `.c`/`.h` files: a `main.c` that reads a WAV, processes it, writes a WAV. Compare this output against the Python output.
- Match the Daisy Seed `AudioCallback` signature: `void AudioCallback(AudioHandle::InputBuffer in, AudioHandle::OutputBuffer out, size_t size)`.
- The existing C struct comments in `freeverb.py` and `dattorro_plate.py` are a good starting template but need to become actual generated code.

**Detection:** Compile the generated C code as part of CI (even just `gcc -c` to verify compilation). Run the generated test harness and compare output WAV against Python reference. Any sample-level difference > 1e-4 is a red flag.

**Confidence:** HIGH -- the project already enforces C-portability constraints in state types, but behavioral equivalence is an entirely separate problem.

---

## Moderate Pitfalls

### Pitfall 5: Room/Chamber Reverbs Sounding Like Plate With Different Settings

**What goes wrong:** New "Room" and "Chamber" algorithms end up being the Dattorro plate with tweaked delay lengths and decay times. They don't sound perceptually different -- they all have the same diffuse, metallic plate character.

**Why it happens:** Room and chamber reverbs need early reflections that encode the geometry of a physical space. Plate reverbs deliberately avoid early reflections (a physical plate has no "walls"). Without a distinct early reflection pattern, all algorithmic reverbs collapse to "diffuse tail with different decay time." The current `DattorroPlate` has no early reflection section -- its 4 input allpass diffusers smear the input, which is the opposite of discrete early reflections.

**Prevention:**
- Room/Chamber algorithms MUST have an explicit early reflection (ER) section before the diffuse tail. The ER section uses a tapped delay line with 6-20 taps at positions corresponding to wall reflections.
- Use a structurally different architecture from Dattorro: Moorer's design (ER tapped delay -> mixing matrix -> late reverb via comb filters or FDN) is a natural fit and reuses existing `CombFilter` and `DelayLine` primitives.
- Distinct character targets:
  - Small room: ER delays 1-15ms, high ER density, RT60 0.3-0.8s, noticeable discrete echoes
  - Large room: ER delays 5-40ms, lower density, RT60 0.8-2.5s, wider stereo
  - Chamber: ER delays 3-20ms, very high density, smooth tail, RT60 0.5-1.5s
- The parameter set should differ from Plate: "room size" controls ER pattern and tail length together. "Wall absorption" instead of "bandwidth." "Reflectivity" instead of "diffusion."

**Detection:** Generate impulse responses for Room, Chamber, and Plate with similar decay times. Compare the first 50ms in the time domain -- if they look the same (smooth onset), the Room/Chamber lacks early reflections. Room should show discrete spikes in the first 20-50ms.

**Confidence:** MEDIUM -- based on DSP literature and reverb design practice. The specific implementation details will need phase-specific research.

---

### Pitfall 6: Biquad EQ on Trails Causing DC Offset or Zipper Noise

**What goes wrong:** Inserting a biquad EQ post-reverb causes DC offset buildup, low-frequency rumble, or clicks/zips when parameters change during playback.

**Why it happens:**
1. **DC offset:** The existing `DCBlocker` in `DattorroPlate` operates inside the reverb's tank. An EQ placed after the reverb (especially a low-shelf boost or parametric boost at low frequencies) can reintroduce DC or near-DC content.
2. **Zipper noise:** The `Biquad.set_coefficients()` method updates coefficients instantly. During real-time playback, abrupt coefficient changes cause discontinuities in the output.
3. **Filter ordering:** If someone mistakenly places EQ inside the reverb's feedback loop (rather than post-reverb), it changes the reverb character unpredictably and can cause instability.

**Prevention:**
- Place EQ strictly AFTER the reverb algorithm output, never inside the feedback path. In the signal chain: `audio -> reverb.process() -> eq.process() -> output`.
- Add a `DCBlocker` after the EQ chain.
- For real-time parameter changes, interpolate biquad coefficients over one block (48 samples). Calculate coefficients for old and new settings, process half the block with old coefficients and half with new, with a crossfade. Or simpler: just accept that coefficient updates happen at block boundaries (every 1ms), which produces at most a tiny click that is nearly inaudible.
- Limit EQ boost range to +/-12 dB.
- The existing `Biquad` class is correct and C-portable. No structural changes needed.

**Detection:** Process 10 seconds of silence after a short impulse through reverb + EQ. Check that the final 1 second has max amplitude < 1e-6.

**Confidence:** HIGH -- the `Biquad` class exists and is tested. The risk is integration, not implementation.

---

### Pitfall 7: Real-Time Parameter Changes Causing Audio Glitches

**What goes wrong:** Changing algorithm parameters (knobs/switches) during real-time playback causes clicks, pops, or momentary silence.

**Why it happens:** The current `update_params()` + `_scale_params()` pattern updates all internal coefficients atomically from Python's perspective, but in a multi-threaded real-time context, the audio callback thread may read partially-updated state. Additionally, some parameter changes are inherently discontinuous -- changing allpass feedback coefficients mid-stream changes the delay line contribution instantly.

**Consequences for v1.1:** This is the #1 UX risk for real-time playback. Users expect to turn knobs and hear smooth changes. Clicks and pops make the tool feel broken.

**Prevention:**
- Use a double-buffer or lock-free parameter update: the UI thread writes new parameters to a "pending" snapshot (a plain dict of scalars). The audio callback checks for pending updates at the START of each block (not mid-block) and applies them atomically via `update_params()`.
- Use a `queue.Queue(maxsize=1)` for parameter passing. The UI thread does `queue.put(params_dict)` (non-blocking). The audio callback does `queue.get_nowait()` at block start, ignoring `queue.Empty`.
- For parameters that affect delay line lengths (pre_delay), crossfade between old and new delay lengths over one block rather than switching instantly.
- Never call `reset()` when changing parameters during playback. `reset()` zeros all delay lines and causes a gap. The existing `update_params()` method correctly avoids this.
- `BUFFER_SIZE=48` (1ms at 48 kHz) means parameter updates have at most 1ms latency, which is inaudible.

**Detection:** Automate a test that changes parameters every 100ms during a 5-second sine wave and checks for discontinuities (sample-to-sample differences > 0.5).

**Confidence:** HIGH -- standard real-time audio engineering.

---

### Pitfall 8: Thread Safety Between Streamlit and Audio Callback

**What goes wrong:** Race conditions between the Streamlit main thread and the `sounddevice` audio callback thread corrupt algorithm state or cause audio dropouts.

**Why it happens:** Python's GIL does not fully protect numpy array operations. If the UI thread triggers `algorithm.reset()` or `algorithm.update_params()` while the audio callback is in the middle of `algorithm._process_impl()`, the callback may read half-reset delay line buffers, producing a burst of noise or silence.

**Prevention:**
- The algorithm instance used by the audio callback must be SEPARATE from any instance used for analysis/visualization. The current `engine.process_audio()` creates a fresh instance each call -- this is fine for analysis but the real-time instance must be persistent.
- The audio callback must NEVER acquire a blocking lock. Use lock-free communication:
  - `queue.Queue(maxsize=1)` for parameter updates (UI -> audio)
  - `queue.Queue` for status/metrics (audio -> UI)
- Audio file data (the loaded WAV) should be loaded into a numpy array once and shared read-only. Both threads read from it; neither writes.
- Store the real-time algorithm instance and audio stream in `st.session_state` so they persist across Streamlit reruns. Use a wrapper class that manages the sounddevice stream lifecycle.

**Detection:** Run real-time playback for 60 seconds while rapidly changing parameters. Count buffer underruns (`sounddevice` reports these via the `status` argument to the callback). Any underruns indicate a threading or performance issue.

**Confidence:** HIGH -- standard concurrent programming, verified via [sounddevice threading issue #187](https://github.com/spatialaudio/python-sounddevice/issues/187).

---

### Pitfall 9: Silence Padding Not Adapting to Algorithm/Parameters

**What goes wrong:** Silence padding is either too short (tail cut off) or too long (10x file size) because it uses a fixed duration rather than adapting to the actual RT60.

**Why it happens:** Different algorithms and parameter settings produce wildly different tail lengths. Freeverb with room_size=20 has a 0.3s tail; Dattorro with decay=95 has a 10s+ tail. A fixed padding of "3 seconds" is wrong for both.

**Prevention:**
- Calculate padding from the algorithm's measured RT60: `padding_samples = int(rt60 * 1.5 * SAMPLE_RATE)`. The 1.5x multiplier ensures the tail decays below audibility (-90 dB).
- The existing `engine.process_audio()` already generates an impulse response and measures RT60 -- use that measurement to determine padding.
- Cap maximum padding at 10 seconds to prevent runaway file sizes.
- For real-time playback with loop mode, padding is irrelevant -- the algorithm state persists across loop boundaries. Only apply padding for process-then-play and file export.

**Detection:** Check that the last 100ms of padded output has energy below -80 dB relative to peak.

**Confidence:** HIGH -- straightforward engineering but easy to get wrong with hardcoded values.

---

## Minor Pitfalls

### Pitfall 10: FDN Delay Line Lengths Causing Metallic Resonances

**What goes wrong:** The FDN sounds metallic or "ringy" instead of smooth and diffuse.

**Why it happens:** Delay line lengths share common factors, causing mode clustering. If delays are 1000, 2000, 3000, 4000 samples, their modes overlap at multiples of 48 Hz, creating an audible pitch.

**Prevention:** Use mutually prime delay lengths. Start from prime numbers near desired lengths. For a 4-channel FDN at 48 kHz: 1153, 1399, 1613, 1823 (all prime). For 8-channel: 887, 1013, 1153, 1327, 1499, 1613, 1823, 1987. The existing `Freeverb` and `DattorroPlate` already use carefully chosen non-coprime lengths from their reference papers -- FDN does not have established reference lengths.

**Confidence:** HIGH -- [CCRMA FDN reference](https://ccrma.stanford.edu/~jos/pasp/FDN_Reverberation.html).

---

### Pitfall 11: Signal-Flow Diagram Rendering Blocking the UI

**What goes wrong:** Generating signal-flow diagrams for complex algorithms (Dattorro has ~20 components) takes several seconds and blocks Streamlit.

**Prevention:** Pre-render signal-flow diagrams as static SVG/PNG per algorithm class, not per parameter set. The topology does not change with parameters -- only coefficients do. Generate once at app startup or commit pre-rendered images to the repo. Use matplotlib for rendering (already a dependency) rather than adding graphviz.

**Confidence:** MEDIUM -- depends on rendering approach.

---

### Pitfall 12: Multi-File Loading Exhausting Memory

**What goes wrong:** Loading 4-5 audio files at 48 kHz with their processed outputs, impulse responses, and spectrograms exhausts available memory.

**Prevention:** Set a maximum file duration (30 seconds). Only keep the currently selected file's processed output in memory. Reprocess when switching files (the processing is fast enough for process-then-play). Clear matplotlib figures after rendering.

**Confidence:** MEDIUM -- depends on typical file sizes.

---

### Pitfall 13: Loop/Single-Shot Toggle Resetting Algorithm State

**What goes wrong:** Toggling between loop and single-shot during real-time playback restarts the audio and loses the reverb tail.

**Prevention:** Loop/single-shot only affects whether the file read position wraps to 0 at EOF. The algorithm state (delay lines, filters) must persist across loop boundaries. Never call `algorithm.reset()` on loop toggle. The reverb tail from the end of one loop iteration blends naturally into the beginning of the next.

**Confidence:** HIGH -- straightforward but easy to get wrong.

---

### Pitfall 14: Dattorro Variants Exceeding the 6-Knob Constraint

**What goes wrong:** Adding parameters for tank size, diffusion block count, modulation rate pushes past the 6-knob + 2-switch hardware constraint.

**Prevention:** Each algorithm variant gets the same 6 knobs + 2 switches, but the knobs map to different internal parameters. `DattorroHall` might map knob 6 to "tank size" instead of "mod depth." The mapping is fixed per algorithm class. The existing `param_specs` property already defines this -- just ensure each variant class returns exactly 6 knobs and 2 switches.

**Confidence:** HIGH -- hardware constraint from the Cleveland Audio Hothouse pedal's physical interface.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dattorro parameter variants | Pitfall 3 (topology breakage if scope creeps), Pitfall 14 (exceeding 6 knobs) | Stay within `_scale_params()` changes. New switch modes are safe. New topology is a separate class. |
| Dattorro topology variants | Pitfall 3 (stability/character loss) | Treat as new algorithm classes. Independent tuning. Budget 2x expected time. Phase-specific research likely needed. |
| FDN reverb | Pitfall 1 (matrix instability), Pitfall 10 (metallic resonances) | Use Householder matrix. Prime delay lengths. Automated energy-decay stability test. |
| Room/Chamber reverb | Pitfall 5 (sounding like plate) | Mandatory early reflection section. Moorer architecture, not Dattorro derivative. Phase-specific research likely needed on ER patterns. |
| Real-time playback | Pitfall 2 (Streamlit limitations), Pitfall 7 (parameter glitches), Pitfall 8 (thread safety) | sounddevice in background thread. Lock-free parameter passing via Queue. Separate algorithm instances for audio vs analysis. |
| Biquad EQ on trails | Pitfall 6 (DC offset, zipper noise) | Post-reverb placement. DC blocker after EQ. Coefficient update at block boundaries only. |
| C code export | Pitfall 4 (non-functional code) | Generate test harness. Static arrays for delay lines (SDRAM on Daisy). Positive-modulo indexing. Float32 behavioral test. |
| Signal-flow diagrams | Pitfall 11 (UI blocking) | Pre-render as static images per algorithm class. |
| Silence padding | Pitfall 9 (wrong padding length) | RT60-based adaptive padding with 10s cap. |
| Multi-file loading | Pitfall 12 (memory), Pitfall 13 (loop state) | Duration cap, lazy processing, persist algorithm state across loops. |

---

## Sources

- [CCRMA FDN Reverberation -- Julius O. Smith](https://ccrma.stanford.edu/~jos/pasp/FDN_Reverberation.html)
- [Dattorro "Effect Design Part 1" (1997 JAES paper)](https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf)
- [KVR Forum: Dattorro reverb improvements](https://www.kvraudio.com/forum/viewtopic.php?t=564078)
- [KVR Forum: FDN Reverb discussion](https://www.kvraudio.com/forum/viewtopic.php?t=123095)
- [Dense Reverberation With Delay Feedback Matrices](https://www.researchgate.net/publication/336855119_Dense_Reverberation_With_Delay_Feedback_Matrices)
- [Streamlit community: working with realtime audio](https://discuss.streamlit.io/t/experience-report-working-with-realtime-audio-in-streamlit/86637)
- [sounddevice thread safety discussion](https://github.com/spatialaudio/python-sounddevice/issues/187)
- [sounddevice API: NumPy streams](https://python-sounddevice.readthedocs.io/en/latest/api/streams.html)
- [Efficient Optimization of FDN for Smooth Reverberation (2024)](https://arxiv.org/html/2402.11216v2)
