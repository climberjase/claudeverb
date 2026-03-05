# Domain Pitfalls

**Domain:** Algorithmic reverb DSP workbench (Python with C portability to STM32 Daisy Seed)
**Researched:** 2026-03-04
**Sources:** Training data (established DSP domain, Freeverb circa 2000, Dattorro 1997). Web search unavailable. Core DSP principles are stable and unlikely to have changed. Confidence is HIGH for algorithmic/DSP pitfalls, MEDIUM for tooling-specific pitfalls.

---

## Critical Pitfalls

Mistakes that cause rewrites, inaudible output, or broken C portability.

### Pitfall 1: Sample-Rate-Dependent Delay Line Lengths

**What goes wrong:** Freeverb's original delay line lengths (1557, 1617, 1491, 1422, 225, 556, 441, 341) are tuned for 44.1 kHz. Using them at 48 kHz without scaling produces a reverb with wrong decay character -- shorter perceived room size, different modal density, and metallic coloring.

**Why it happens:** Most Freeverb references (including Jezar's original C++ code) hardcode lengths for 44.1 kHz. Developers copy these constants without understanding they encode physical room dimensions via `delay_samples = time_seconds * sample_rate`.

**Consequences:** The reverb sounds "off" -- slightly pitched, wrong decay time, unnatural resonances. Worse, if you tune parameters to compensate, the algorithm is no longer a proper Freeverb and the tuning won't transfer to other sample rates.

**Prevention:**
- Scale all delay line lengths by `target_rate / reference_rate` (48000/44100 = 1.0884)
- Round to nearest prime number after scaling (primes prevent resonance buildup from common factors)
- Store delay lengths as computed values from a `_compute_delay_lengths(sample_rate)` method, never as hardcoded constants
- Document the reference sample rate for any delay lengths taken from literature

**Detection:** Compare RT60 measurements of your implementation against reference implementations at the same parameter settings. If RT60 or spectral shape differs significantly, check delay lengths first.

**Phase relevance:** Must be addressed in initial algorithm implementation (Phase 1/2). Wrong from day one means all subsequent tuning is wasted.

**Confidence:** HIGH

---

### Pitfall 2: Python Float64 vs C Float32 Numerical Divergence

**What goes wrong:** NumPy defaults to float64. Your Python reverb sounds great, you export to C (float32 on STM32), and the output sounds different -- sometimes subtly (slightly different decay tail), sometimes catastrophically (filter instability, DC offset buildup, or outright blowup).

**Why it happens:** Recursive filters (comb filters, allpass filters) accumulate rounding errors over thousands of samples. The difference between float64 and float32 precision in feedback paths compounds exponentially. A comb filter with feedback 0.84 running at 48 kHz processes ~48000 multiply-accumulates per second, each slightly different between precisions.

**Consequences:** Two separate bugs: (1) The Python prototype gives false confidence -- it sounds good but the C version won't match. (2) Subtle instabilities that only appear in float32 after long audio passages (DC drift, denormal slowdowns on x86, NaN propagation).

**Prevention:**
- Enforce `np.float32` everywhere from day one. Set `audio = audio.astype(np.float32)` at load time and assert float32 in every process() entry point
- Use `np.float32` for all internal state arrays (delay lines, filter coefficients, accumulators)
- Add a `_validate_state_dtype()` method to the base class that asserts all state arrays are float32
- Add denormal flushing: clamp values below ~1e-15 to zero (prevents CPU slowdowns on x86 and matches ARM behavior)
- Test with 30+ second audio files to catch slow-building numerical issues

**Detection:** Run the same audio through Python (float32-enforced) and C implementations, compute sample-by-sample difference. If max absolute error exceeds ~1e-3 after 5 seconds, you have a divergence problem.

**Phase relevance:** Must be a rule from the very first line of algorithm code. Retrofitting float32 into a float64 codebase means retuning every coefficient.

**Confidence:** HIGH

---

### Pitfall 3: Circular Buffer Index Bugs (Off-by-One and Modulo Errors)

**What goes wrong:** Circular buffer implementations silently produce wrong output -- clicks, pops, short bursts of noise, or subtly wrong delay times. These bugs are intermittent and hard to reproduce because they depend on buffer position.

**Why it happens:** Three common variants:
1. **Read-before-write vs write-before-read:** Determines whether delay is N or N-1 samples. Getting this wrong shifts all delay lengths by 1 sample.
2. **Modulo arithmetic bugs:** `index % length` works in Python but in C, negative modulo behaves differently (`-1 % 5` is `-1` in C but `4` in Python).
3. **Index update timing:** Updating the write pointer before or after reading from it changes the output.

**Consequences:** Wrong delay times (subtle pitch/resonance issues), occasional clicks at buffer wraparound, or -- worst case -- reading uninitialized memory in C.

**Prevention:**
- Implement a single `DelayLine` class used by ALL algorithms. Never inline circular buffer logic.
- The DelayLine must have exactly two public methods: `write(sample)` and `read(delay_taps)` with clear documentation of the delay semantics
- Use `& (length - 1)` instead of `% length` for power-of-2 buffers (faster in C, no negative modulo issue) -- but this means delay lengths must be rounded up to power-of-2
- OR use the pattern `index = (index + 1) if (index + 1) < length else 0` which avoids modulo entirely
- Write a unit test that verifies exact delay: write an impulse, read it back after N samples, confirm it appears at exactly sample N
- Write a stress test: process 10 million samples and check for any sample outside [-1.0, 1.0]

**Detection:** Impulse response test. Send a single `1.0` sample followed by zeros. The output should show taps at exactly the expected delay times. If taps are off by 1, you have a read/write ordering bug.

**Phase relevance:** Foundation. The DelayLine class should be the first thing built and tested before any algorithm code.

**Confidence:** HIGH

---

### Pitfall 4: Comb Filter Feedback Coefficient Instability

**What goes wrong:** Comb filter feedback values >= 1.0 cause exponential blowup. Values very close to 1.0 (e.g., 0.999) cause extremely long, unrealistic decay that sounds like ringing. The mapping from user-facing "decay" parameter (0-100) to internal feedback coefficient is where most reverb tuning bugs live.

**Why it happens:** The relationship between feedback gain `g`, delay length `D`, and RT60 is: `g = 10^(-3 * D / (RT60 * sample_rate))`. Getting this formula wrong, or applying knob-to-parameter mapping that allows `g >= 1.0`, produces unstable filters.

**Consequences:** Audio blows up to infinity (clipping, distortion, speaker damage). On embedded hardware without overflow protection, this can cause hardware-level issues.

**Prevention:**
- Hard-clamp all feedback coefficients to `abs(g) < 0.999` in `update_params()`, regardless of what the parameter mapping computes
- Derive feedback from RT60 using the correct formula, not by arbitrary scaling
- The parameter mapping function from knob (0-100) to feedback should be tested at all 101 integer values to verify no value produces `g >= 1.0`
- Add output clamping in `process()`: if any output sample exceeds [-1.0, 1.0], hard-clip and log a warning
- In the base class, add a `_validate_coefficients()` called after every `update_params()`

**Detection:** Set all "decay" or "room size" knobs to maximum (100). Process 30 seconds of audio. If output amplitude grows over time rather than staying bounded, feedback is too high.

**Phase relevance:** Algorithm implementation. Must be verified before any listening tests are meaningful.

**Confidence:** HIGH

---

### Pitfall 5: Processing Full Files vs Block-Based Processing Mismatch

**What goes wrong:** The Python workbench processes entire audio files at once (e.g., a 10-second clip as a single 480,000-sample array), but the Daisy Seed processes in 48-sample blocks. The algorithm works perfectly in Python but produces clicks, dropouts, or wrong output when ported to block-based C code.

**Why it happens:** When processing the full buffer at once, developers use vectorized numpy operations that implicitly process all samples simultaneously. This hides bugs where state isn't properly carried between blocks. For example, a filter's internal state at the end of one block must be exactly the starting state for the next block.

**Consequences:** The C port sounds different from the Python prototype. Debugging requires comparing sample-by-sample output between two completely different execution models.

**Prevention:**
- The `process()` method must internally loop over BUFFER_SIZE (48) sample blocks, even when given a larger input
- Implement a `_process_block(block)` method that handles exactly 48 samples, and have `process()` call it in a loop
- This is the single most important architectural decision for C portability
- Verify block-based equivalence: process audio as one big chunk vs. as sequential 48-sample blocks. Output must be bit-identical.
- Add a test: `test_block_equivalence()` that splits audio into 48-sample blocks, processes them sequentially, concatenates results, and compares against processing the full audio

**Detection:** Process the same audio in two modes: (1) as a single call to `process(full_audio)`, (2) as a loop of `process(block)` calls with 48-sample blocks. Diff the output. Any difference indicates state management bugs.

**Phase relevance:** Must be the core architecture from Phase 1. Retrofitting block-based processing into a vectorized implementation is essentially a rewrite.

**Confidence:** HIGH

---

### Pitfall 6: Dattorro Plate Reverb Tank Modulation Errors

**What goes wrong:** The Dattorro plate reverb uses modulated allpass filters in the tank section. Implementing the modulation wrong produces either: (1) no audible modulation (sounds static/metallic), (2) pitch-wobble artifacts, or (3) clicks from reading fractional delay positions without interpolation.

**Why it happens:** Dattorro's 1997 paper specifies modulation depth and rate precisely, but the notation is dense and easy to misread. The modulated delay requires fractional delay line reads (linear or cubic interpolation), which adds complexity. Many implementations skip or simplify the modulation, producing a reverb that sounds thin and metallic compared to the paper's intended result.

**Consequences:** The reverb sounds "digital" and harsh. The whole point of plate reverb is the lush, modulated decay -- without correct modulation it's just a mediocre feedback delay network.

**Prevention:**
- Implement a `ModulatedDelayLine` that extends `DelayLine` with fractional-sample read capability using linear interpolation (cubic is overkill for this application)
- Use Dattorro's exact excursion values: max excursion of 16 samples at modulation frequencies of ~1 Hz (the paper specifies `f1 = 1.0 Hz`, `f2 = 0.7071 Hz` for the two modulated allpasses)
- Fractional delay: `output = buffer[int_part] * (1 - frac) + buffer[int_part + 1] * frac` -- this is C-portable
- Verify modulation by examining the spectrogram of the reverb tail of a click: it should show slight frequency smearing, not discrete spectral lines

**Detection:** Process a click (impulse) through the plate reverb and examine the spectrogram of the tail. Without modulation, you'll see sharp horizontal lines (standing waves). With correct modulation, those lines should be slightly blurred/smeared.

**Phase relevance:** Dattorro implementation phase. Getting the tank topology right first, then adding modulation.

**Confidence:** HIGH (Dattorro's paper is extremely well-documented)

---

## Moderate Pitfalls

### Pitfall 7: DC Offset Accumulation in Feedback Loops

**What goes wrong:** After processing several seconds of audio, the reverb output develops a slowly growing DC offset that causes asymmetric clipping and a "pumping" sound.

**Why it happens:** Tiny numerical biases in feedback paths accumulate over time. Float32 rounding is not symmetric. Each feedback iteration adds a tiny DC component that, over thousands of iterations, becomes audible.

**Prevention:**
- Add a simple DC-blocking filter at the output of each comb filter: `y[n] = x[n] - x[n-1] + 0.995 * y[n-1]`
- This is a single-pole highpass at ~38 Hz (inaudible) that removes DC drift
- The DC blocker is cheap (2 multiplies, 2 adds) and C-portable
- Test by processing 60 seconds of silence after a short impulse -- the output should converge to exactly zero

**Detection:** Process audio, then measure the mean of the last 1 second of output. If it's significantly non-zero (> 1e-4), DC is accumulating.

**Phase relevance:** Algorithm implementation. Add DC blockers during initial filter design, not as an afterthought.

**Confidence:** HIGH

---

### Pitfall 8: Ignoring the Wet/Dry Mix Implementation Details

**What goes wrong:** The wet/dry mix sounds wrong -- either phase cancellation artifacts, volume jumps when adjusting the mix, or the "50% wet" setting doesn't sound like half reverb.

**Why it happens:** Naive implementation `output = dry * (1-mix) + wet * mix` has two problems: (1) linear crossfade causes a perceived volume dip at 50% (should use equal-power: `dry * cos(mix * pi/2) + wet * sin(mix * pi/2)`), and (2) the wet signal may be out of phase or have latency relative to dry, causing comb filtering artifacts.

**Consequences:** Users perceive the reverb as "hollow" or "thin" at intermediate mix settings. A/B comparison between dry and wet is unreliable.

**Prevention:**
- Use equal-power crossfade for the wet/dry mix
- Ensure the dry signal passes through the same latency as the wet signal (even if it's zero-latency, document this)
- Normalize wet signal level to approximately match dry signal RMS before mixing
- Make 100% wet truly 100% wet (no dry signal) for analysis purposes

**Detection:** Process a sine wave at 50% mix. If the output amplitude is noticeably lower than either 0% or 100%, you're using linear crossfade.

**Phase relevance:** UI/playback implementation. Should be addressed when building the wet/dry control.

**Confidence:** HIGH

---

### Pitfall 9: Streamlit Audio Playback Limitations

**What goes wrong:** Streamlit's `st.audio()` widget doesn't support seamless A/B comparison, has limited format support, and reloads the entire page on parameter changes, making iterative tuning painful.

**Why it happens:** Streamlit re-runs the entire script on any widget interaction. This means: (1) audio processing runs again on every knob change (slow for complex algorithms), (2) playback position resets, making A/B comparison impossible, (3) no way to sync playback between two audio widgets.

**Consequences:** The core workflow -- "tweak a knob, hear the difference" -- is frustratingly slow. Developers end up bypassing the UI and testing in scripts, defeating the purpose of the workbench.

**Prevention:**
- Use `st.cache_data` aggressively: cache audio loading, cache processing results keyed on (algorithm_name, params_hash, input_file_hash)
- Use `st.session_state` to preserve playback state across reruns
- Consider processing audio in a background thread and showing a progress indicator for long files
- Keep test audio files short (2-5 seconds) for iteration; longer files for final evaluation only
- Pre-process at multiple parameter settings and cache results so A/B switching is instant
- Design the UI around "Process" button (explicit trigger) rather than auto-processing on every knob change

**Detection:** Time how long it takes to change a parameter and hear the result. If it's more than 2 seconds, the iteration loop is too slow.

**Phase relevance:** UI implementation phase. Architectural decision that affects the entire UX.

**Confidence:** MEDIUM (Streamlit behavior is well-known, but specific workarounds depend on version)

---

### Pitfall 10: RT60 Measurement Implementation Errors

**What goes wrong:** RT60 measurements give wildly wrong values -- either negative, absurdly long (>30s for a small room reverb), or inconsistent between runs.

**Why it happens:** RT60 requires Schroeder backward integration of the impulse response energy decay curve, then linear regression on the dB-scale decay. Common errors: (1) not using backward integration (forward integration gives wrong results), (2) fitting the regression to the wrong portion of the curve (noise floor corrupts the tail), (3) not handling the noise floor truncation point.

**Consequences:** The primary metric for evaluating reverb quality is unreliable. Developers tune by ear because the numbers don't make sense, losing the quantitative advantage of the workbench.

**Prevention:**
- Use Schroeder backward integration: `energy_decay[n] = sum(h[k]^2 for k = n to N)`
- Convert to dB: `decay_dB = 10 * log10(energy_decay / energy_decay[0])`
- Find the noise floor: where the decay curve levels off (derivative approaches zero)
- Fit linear regression only to the range from 0 dB to 5 dB above the noise floor
- RT60 = -60 / slope (extrapolated)
- Validate against known reference: a comb filter with feedback `g` and delay `D` has RT60 = `-3 * D / (fs * log10(abs(g)))` -- compare analytical vs measured
- Return T20 or T30 (extrapolated from -5 to -25 dB, or -5 to -35 dB range) rather than trying to measure a full 60 dB decay, which often hits the noise floor

**Detection:** Measure RT60 of a simple comb filter where the analytical RT60 is known. If measured differs by more than 10%, the implementation is wrong.

**Phase relevance:** Analysis/metrics implementation phase.

**Confidence:** HIGH

---

### Pitfall 11: Allpass Filter "Not Actually Allpass" Implementation

**What goes wrong:** The allpass filter doesn't have flat magnitude response -- it colors the sound instead of just diffusing it.

**Why it happens:** The allpass filter topology requires a very specific sign convention. The transfer function is `H(z) = (-g + z^-D) / (1 - g*z^-D)`. Getting the signs wrong (e.g., `(g + z^-D) / (1 + g*z^-D)`) produces a filter that is NOT allpass -- it has magnitude response ripples.

**Consequences:** The reverb has unwanted coloration that can't be fixed by adjusting other parameters. Developers waste hours tuning other parts of the algorithm to compensate for a broken fundamental building block.

**Prevention:**
- Implement the allpass as: `output = -g * input + buffer[read_pos]; buffer[write_pos] = input + g * output`
- Verify allpass property: process white noise, compute magnitude spectrum -- it must be flat (within 0.1 dB across the spectrum)
- The coefficient `g` controls diffusion amount (typically 0.5-0.7 for reverb allpasses)
- Write a unit test: FFT of `output / input` for white noise should have constant magnitude

**Detection:** Process 10 seconds of white noise through a single allpass. Plot the magnitude spectrum of input vs output. They should be nearly identical (flat). Any peaks or notches indicate a sign error.

**Phase relevance:** Filter primitives implementation -- must be correct before building any algorithm.

**Confidence:** HIGH

---

## Minor Pitfalls

### Pitfall 12: Stereo Reverb as "Two Mono Reverbs"

**What goes wrong:** Stereo reverb sounds like two independent mono reverbs panned left and right, with no spatial connection. It lacks the "enveloping" quality of good stereo reverb.

**Prevention:**
- Use cross-coupling between left and right channels in the feedback network
- Dattorro's plate design inherently handles this with its figure-8 tank topology (two outputs tapped from a single recirculating network)
- For Freeverb stereo: use slightly different delay lengths for L and R channels (Jezar uses a +23 sample offset for the right channel)
- Test with mono input: the output should still be stereo with decorrelated L/R channels

**Phase relevance:** Algorithm implementation, after mono is working correctly.

**Confidence:** HIGH

---

### Pitfall 13: Parameter Mapping Without Perceptual Scaling

**What goes wrong:** Turning the "room size" knob from 50 to 60 produces a huge change, but 0 to 10 produces almost no change. The knobs feel non-linear and unintuitive.

**Prevention:**
- Use perceptually-scaled parameter mappings. Most audio parameters need logarithmic or exponential mapping.
- Decay/room size: exponential mapping (`value = min + (max - min) * (knob/100)^2`)
- Damping/tone: linear mapping is usually fine
- Pre-delay: logarithmic mapping (humans perceive time ratios, not differences)
- Document the mapping function for each parameter in the param_specs
- Test all 101 knob positions (0-100) and verify the output changes smoothly with no sudden jumps

**Phase relevance:** Algorithm parameter design, before tuning begins.

**Confidence:** HIGH

---

### Pitfall 14: Not Validating Impulse Responses Early

**What goes wrong:** Developers tune reverb by listening to music through it, which makes subtle problems hard to hear. They miss resonances, flutter echoes, and frequency coloration that would be immediately obvious in an impulse response.

**Prevention:**
- Generate and visually inspect impulse responses FIRST, before any music-based listening
- Check for: (1) smooth exponential decay envelope, (2) dense reflection pattern (no periodic "echoes"), (3) flat-ish frequency response in the reverb tail
- Use the impulse response for all RT60/metric calculations
- Compare your impulse response visually against published impulse responses of the same algorithm type

**Phase relevance:** Should be part of the test harness from the earliest algorithm work.

**Confidence:** HIGH

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| DSP primitives (DelayLine, Comb, Allpass) | Circular buffer index bugs (#3), allpass sign errors (#11) | Exhaustive unit tests with impulse verification before building algorithms |
| Freeverb implementation | Wrong delay lengths for 48 kHz (#1), float64 default (#2) | Scale from 44.1 kHz reference, enforce float32 from line 1 |
| Dattorro Plate implementation | Modulation errors (#6), DC accumulation (#7) | Implement ModulatedDelayLine with interpolation, add DC blockers |
| Block-based processing | Full-file vs block processing mismatch (#5) | Architect process() around 48-sample _process_block() from the start |
| Parameter interface | Feedback instability at extreme settings (#4), non-perceptual mapping (#13) | Hard-clamp coefficients, test all 101 knob positions |
| Streamlit UI | Slow iteration loop (#9), wet/dry mix issues (#8) | Aggressive caching, equal-power crossfade |
| Analysis/metrics | RT60 measurement errors (#10) | Validate against known analytical results from simple filters |
| C export (future) | Float32 divergence (#2), block processing mismatch (#5) | Already mitigated if float32 and block-based processing enforced from start |

---

## Meta-Pitfall: Testing by Ear Alone

The single most important meta-lesson for reverb development: **ears lie, metrics don't.** The entire point of this workbench is to combine listening with quantitative analysis. Every algorithm change should be evaluated both by listening AND by metrics (RT60, spectral analysis, impulse response shape). Developers who skip the metrics end up chasing subjective impressions and can't reproduce their own tuning decisions.

## Sources

- Dattorro, J. (1997). "Effect Design Part 1: Reverberator and Other Filters." Journal of the Audio Engineering Society, 45(9), 660-684.
- Jezar's Freeverb source code and documentation (public domain, ~2000)
- Smith, J.O. "Physical Audio Signal Processing" - CCRMA Stanford (online textbook)
- General DSP engineering knowledge (float32 behavior, circular buffers, filter stability)
- Confidence note: All pitfalls are drawn from well-established DSP engineering principles that have not changed. Freeverb and Dattorro are 25+ year old algorithms with extensive community implementation experience. HIGH confidence in the domain knowledge despite inability to verify against current web sources.
