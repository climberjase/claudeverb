---
status: testing
phase: 02-audio-io-freeverb
source: 02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md
started: 2026-03-05T09:15:00Z
updated: 2026-03-05T09:15:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Load and Resample Audio
expected: |
  Run: `python -c "from claudeverb.audio import load; audio = load('test.wav'); print(audio.shape, audio.dtype)"`
  (We'll generate a test file first.) Audio loads as float32 numpy array at 48 kHz. Mono files return shape (N,), stereo return (2, N).
awaiting: user response

## Tests

### 1. Load and Resample Audio
expected: Audio files load as float32 numpy arrays, automatically resampled to 48 kHz. Mono = (N,), stereo = (2, N).
result: [pending]

### 2. Save Processed Audio
expected: save() writes a valid WAV file that can be loaded back with matching shape and values.
result: [pending]

### 3. Bundled Test Samples
expected: list_samples() returns 6 names (impulse, white_noise_burst, sine_sweep, drum, guitar, vocal). get_sample(name) returns float32 arrays in [-1, 1].
result: [pending]

### 4. Freeverb Default Processing
expected: Processing a dry sample through Freeverb at defaults produces audible reverb tail (output is longer/different than input, not silent).
result: [pending]

### 5. Freeverb Parameter Response
expected: Changing room_size knob (0 vs 100) produces measurably different output. Higher room_size = longer reverb tail.
result: [pending]

### 6. Freeverb Stability at Extremes
expected: All knobs at 0 and all knobs at 100 both produce valid output (no NaN, no inf, values in [-1, 1]).
result: [pending]

### 7. Freeverb Freeze Mode
expected: Switch1 set to -1 (freeze) sustains reverb tail indefinitely -- output energy does not decay.
result: [pending]

### 8. Algorithm Registry
expected: ALGORITHM_REGISTRY["freeverb"] returns the Freeverb class. Instantiation and process() work through registry lookup.
result: [pending]

### 9. Impulse Response Generation
expected: generate_impulse_response(algorithm) returns deterministic IR arrays. Calling twice with same algorithm produces identical output.
result: [pending]

### 10. End-to-End Signal Path
expected: Complete path works: load bundled sample -> process through Freeverb -> save to WAV -> load saved WAV. Output is valid audio.
result: [pending]

## Summary

total: 10
passed: 0
issues: 0
pending: 10
skipped: 0

## Gaps

[none yet]
