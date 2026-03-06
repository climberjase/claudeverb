---
phase: 05-dattorro-plate-algorithm
plan: 03
subsystem: ui
tags: [streamlit, audio-playback, session-state, gap-closure]

# Dependency graph
requires:
  - phase: 05-dattorro-plate-algorithm
    plan: 02
    provides: DattorroPlate verified in UI with audio playback
provides:
  - Correct audio playback volume matching external players (iTunes, QuickTime)
  - Robust session state cleanup on algorithm switching
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [pre-encoded-wav-bytes, session-state-algo-tracking]

key-files:
  created: []
  modified:
    - claudeverb/streamlit_app.py

key-decisions:
  - "Pre-encode audio to WAV bytes via soundfile to bypass Streamlit peak normalization"
  - "Track current_algo in session state to detect algorithm switches and clear stale widget keys"

patterns-established:
  - "_audio_to_wav_bytes helper for consistent audio encoding across playback and download"

requirements-completed: [ALG-02]
gap_closure: true

# Metrics
duration: 5min
completed: 2026-03-06
---

# Phase 5 Plan 3: Fix Streamlit UI Session State & Audio Playback Summary

**Fixed audio volume normalization and session state cleanup for algorithm switching**

## Performance

- **Duration:** ~5 min (including diagnosis)
- **Completed:** 2026-03-06
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments
- Identified root cause of loud audio: Streamlit's `_validate_and_normalize` divides by `max_abs_value` then scales to 32767, normalizing every signal to full 16-bit range
- Added `_audio_to_wav_bytes()` helper that pre-encodes via soundfile with PCM_16 subtype, bypassing Streamlit's peak normalization
- All three `st.audio()` calls and the download button now use the same WAV encoding path
- Added `current_algo` session state tracking — algorithm switch clears all stale `knob_*` and `switch_*` keys, then reruns
- Reset handler also clears `current_algo` for clean defaults
- Human verified: audio volume matches external players, UI stable through algorithm switching

## Task Commits

1. **Task 1: Fix audio shape and session state** - `51ec54a` (fix)
2. **Task 2: Human verification** - approved by user

## Files Modified
- `claudeverb/streamlit_app.py` - Added `_audio_to_wav_bytes()`, replaced all `st.audio()` numpy calls with pre-encoded WAV bytes, added algorithm switch detection with session state cleanup

## Decisions Made
- **Pre-encoded WAV bytes:** Streamlit normalizes numpy arrays to peak internally (`data / max_abs_value * 32767`), making all audio sound at maximum volume. By encoding to WAV bytes ourselves via soundfile, we preserve true signal levels.
- **Session state algo tracking:** Simple `current_algo` key comparison detects algorithm switches and triggers cleanup of stale widget keys to prevent DuplicateWidgetID errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Root cause different] Audio volume, not channel shape**
- **Found during:** First attempt (reverted)
- **Issue:** Plan diagnosed audio issue as channels-first/last mismatch. Actual root cause was Streamlit's peak normalization making audio too loud.
- **Fix:** Pre-encode to WAV bytes instead of transposing channels
- **Files modified:** claudeverb/streamlit_app.py
- **Verification:** Human confirmed volume now matches iTunes/QuickTime

---

**Total deviations:** 1 (root cause correction)
**Impact on plan:** Different fix than planned but solves the actual user-reported issue.

## Issues Encountered
- First attempt (commit 99ba70d) implemented channel transposition per plan but caused `struct.error: 'H' format requires 0 <= number <= 65535`. Reverted and correctly diagnosed as Streamlit peak normalization issue.

## Self-Check: PASSED

- FOUND: claudeverb/streamlit_app.py contains `_audio_to_wav_bytes`
- FOUND: claudeverb/streamlit_app.py contains `current_algo` tracking
- FOUND: commit 51ec54a (fix)
- VERIFIED: All st.audio calls use _audio_to_wav_bytes
- VERIFIED: Human approved audio quality and UI stability

---
*Phase: 05-dattorro-plate-algorithm*
*Completed: 2026-03-06*
