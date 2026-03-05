# Codebase Concerns

**Analysis Date:** 2026-03-04

## Critical Project Status

**Pre-Implementation Stage:**
- Issue: Project has detailed architecture specification but zero source code implementation
- Files: Only ARCHITECTURE.md, readme.md, CLAUDE.md, and GSD infrastructure exist in repository
- Impact: No runnable code, no way to validate architectural decisions until implementation begins
- Fix approach: Use this CONCERNS.md to identify risks before writing first line of code

## Missing Core Infrastructure

**Algorithm Base Classes:**
- Issue: `claudeverb/algorithms/base.py` does not exist - ReverbAlgorithm abstract base and ReverbParams dataclass are unimplemented
- Files: Should be at `claudeverb/algorithms/base.py`
- Impact: Cannot begin algorithm development until base classes are in place
- Blocks: All algorithm implementations (Freeverb, Schroeder, Plate stubs)
- Fix approach: Implement ReverbAlgorithm ABC with required methods (_initialize, process, reset, update_params, param_specs) before adding any algorithms

**Filter Primitives Missing:**
- Issue: `claudeverb/algorithms/filters.py` does not exist - CombFilter, AllpassFilter, DelayLine, EQFilters are unimplemented
- Files: Should be at `claudeverb/algorithms/filters.py`
- Impact: Cannot build any reverb algorithms without these fundamental DSP building blocks
- Fix approach: Implement all filter classes with clear docstrings documenting C struct equivalents (as required for Daisy Seed portability)

**Audio I/O Layer Missing:**
- Issue: `claudeverb/audio/io.py` unimplemented - load() and save() functions don't exist
- Files: Should be at `claudeverb/audio/io.py`
- Impact: Cannot load audio files or save results for testing
- Fix approach: Implement using librosa for resampling to 48 kHz and soundfile for 24-bit PCM output

**Analysis Metrics Missing:**
- Issue: `claudeverb/analysis/spectral.py` and `claudeverb/analysis/metrics.py` don't exist
- Files: Should be at `claudeverb/analysis/spectral.py` and `claudeverb/analysis/metrics.py`
- Impact: Cannot perform RT60, DRR, C80/C50 analysis or spectral comparisons
- Fix approach: Implement using librosa and scipy, ensure functions handle both mono (N,) and stereo (2, N) shapes

**Export Module Missing:**
- Issue: `claudeverb/export/c_codegen.py` doesn't exist - C code generation is unimplemented
- Files: Should be at `claudeverb/export/c_codegen.py`
- Impact: Cannot export algorithms to Daisy Seed compatible C code
- Blocks: Phase 4 (algorithm export to C)
- Fix approach: Defer until Freeverb implementation complete; use it as reference for code generation patterns

**UI Layer Incomplete:**
- Issue: ARCHITECTURE.md explicitly marks UI layer (`claudeverb/ui/`) as "TODO"
- Files: Should be in `claudeverb/ui/`
- Impact: No way to interact with algorithms or perform listening tests
- Blocks: Phase 1 (basic UI workbench)
- Fix approach: Implement using Streamlit (simpler than PySide6 per readme) for quick iteration

## Architectural Risks

**C Portability Constraints Not Validated:**
- Issue: Architecture mandates strict C portability (no dynamic allocation after _initialize, fixed-size arrays, circular buffers) but no code exists to validate these constraints
- Files: Affects all files in `claudeverb/algorithms/`
- Risk: Algorithms could be written in Pythonic style that cannot be ported to C, breaking Phase 4 requirements
- Mitigation: Create validation helper in `claudeverb/algorithms/base.py` to check C portability constraints; document C struct signatures in docstrings before implementation
- Fix approach: Add `validate_c_portability()` method to ReverbAlgorithm base class; require all algorithms to pass this check

**Audio Shape Handling Not Centralized:**
- Issue: Architecture requires functions to handle both mono (N,) and stereo (2, N) float32 shapes, but no utilities exist
- Files: Affects `claudeverb/analysis/`, `claudeverb/audio/io.py`, algorithm implementations
- Risk: Inconsistent handling across modules, bugs in stereo processing
- Fix approach: Create shape validation utility in `claudeverb/audio/` - function to ensure and convert shapes; use consistently across all modules

**Sample Rate Assumptions Scattered:**
- Issue: SAMPLE_RATE = 48000 and BUFFER_SIZE = 48 are documented in architecture but not centralized in code
- Files: Should be in `claudeverb/config.py`
- Impact: If values change (e.g., for testing), easy to miss updates in multiple files
- Fix approach: Create `claudeverb/config.py` with SAMPLE_RATE and BUFFER_SIZE constants; import everywhere

**Algorithm Registry Not Implemented:**
- Issue: ARCHITECTURE.md mentions `ALGORITHM_REGISTRY` in `claudeverb/algorithms/__init__.py` as "single source of truth" but it doesn't exist
- Files: Should be in `claudeverb/algorithms/__init__.py`
- Impact: UI cannot discover available algorithms
- Fix approach: Implement ALGORITHM_REGISTRY as dict mapping algorithm names to classes; UI uses this for dropdown

## Implementation Approach Ambiguities

**AU Plugin Loading Scope Unclear:**
- Issue: ARCHITECTURE.md states "system should also allow commercial DSP Audio Plugin Units (.au files) to be loaded" but no implementation plan exists
- Files: Unspecified
- Impact: Phase 3 (audio listening tests) mentions comparing to commercial algorithms, but approach is undefined
- Risk: AU plugin loading is non-trivial on macOS (requires CoreAudio/AU Framework); scope creep
- Fix approach: Defer AU loading; implement algorithm import/export for A/B testing first; AU loading is enhancement, not MVP

**Hyperparameter Search Scope Undefined:**
- Issue: Phase 5 mentions "hyperparameter searches" to match commercial algorithms but no algorithm for optimization is specified
- Files: Will be in `claudeverb/tuning/` or similar
- Impact: Scope is unclear - grid search vs. genetic algorithm vs. gradient descent?
- Fix approach: Document optimization approach in Phase 5 planning; defer until algorithms exist to optimize

**Streamlit vs. PySide6 Decision:**
- Issue: ARCHITECTURE.md mentions "Streamlit" in readme but earlier mentions PySide6 in ui/panels/
- Files: Affects entire `claudeverb/ui/` layer
- Impact: Framework choice affects UI implementation approach
- Fix approach: Clarify: readme.md says Streamlit, ARCHITECTURE.md says "web frontend", but PySide6 implies Qt desktop app - choose one before starting UI

## Testing Gaps

**No Test Infrastructure:**
- Issue: ARCHITECTURE.md references `tests/test_algorithms/test_myalgo.py` and `conftest.py` but these don't exist
- Files: Should be in `tests/` directory
- Impact: Cannot validate algorithms work correctly
- Fix approach: Create pytest infrastructure with fixtures (mono_sine, stereo_sine, impulse as documented)

**Algorithm Test Coverage Strategy Missing:**
- Issue: readme.md says "Multiple tests should test that the algorithms function as designed" but no test taxonomy exists
- Files: `tests/test_algorithms/`
- Risk: Unclear what "function as designed" means for reverb algorithms
- Fix approach: Define test categories: unit (filter components), integration (algorithm with test signals), comparative (vs. commercial AU), perceptual (listening tests)

**No Continuous Integration:**
- Issue: No CI/CD pipeline exists (.github/workflows, tox.ini, etc.)
- Files: Missing
- Impact: Cannot validate code quality or regressions
- Fix approach: Add pytest + coverage to pre-commit hooks; set up GitHub Actions for CI

## Dependencies Not Specified

**Missing Requirements File:**
- Issue: No `requirements.txt` or `setup.py`/`pyproject.toml` in repository
- Files: Should be at project root
- Impact: Reproducibility unclear; dependencies unmanaged
- Fix approach: Create `pyproject.toml` with:
  - Core: numpy, scipy, librosa, soundfile
  - UI: streamlit (or PySide6 if desktop route chosen)
  - Testing: pytest, pytest-cov
  - Export: jinja2 (for C code template generation)

**Python Version Not Specified:**
- Issue: No `.python-version` or Python version constraint in documentation
- Impact: Code may be written with Python 3.12 syntax but need to support 3.10
- Fix approach: Add Python >=3.10 constraint to pyproject.toml and create .python-version file

**Audio Hardware Dependencies Unclear:**
- Issue: Phase 3 mentions "audio listening tests using the local MacOS system sound" but sounddevice/CoreAudio integration not planned
- Files: `claudeverb/audio/playback.py` (doesn't exist)
- Risk: Real-time audio callbacks are complex; Daisy Seed BUFFER_SIZE = 48 @ 48 kHz = 1ms latency requirement is tight
- Fix approach: Defer real-time playback; start with file-based testing; add sounddevice integration later if needed

## C Code Generation Risks

**No C Code Generation Validation:**
- Issue: `claudeverb/export/c_codegen.py` doesn't exist; no way to validate generated C code compiles or runs
- Files: Should be at `claudeverb/export/c_codegen.py`
- Impact: Generated C code could be syntactically correct but functionally wrong
- Blocks: Phase 4 (Daisy Seed export)
- Fix approach: Create mock C compilation step; validate generated headers and function signatures match expectations

**Freeverb C Generation Not Yet Implemented:**
- Issue: ARCHITECTURE.md says "Freeverb is the reference implementation with full C generation support" but this code doesn't exist
- Files: Should be in `claudeverb/algorithms/freeverb.py` with `to_c_struct()` and `to_c_process_fn()` methods
- Impact: No reference for how other algorithms should implement C portability
- Fix approach: Implement Freeverb first with full C generation; use as template for Schroeder and Plate

**Daisy Seed API Assumptions:**
- Issue: Architecture mentions "libDaisy framework" but libDaisy API compatibility not verified in code
- Files: Generated C code in `claudeverb/export/`
- Risk: Generated code may not match actual libDaisy callback signatures or memory layouts
- Fix approach: Document exact libDaisy version target; link to or embed relevant header files in `claudeverb/export/daisy_compat/`

## Incomplete Documentation in Code

**Missing Docstrings for Filter Classes:**
- Issue: ARCHITECTURE.md requires that filter classes "document their C struct equivalent in docstring" but no implementation exists yet
- Files: Will be in `claudeverb/algorithms/filters.py`
- Impact: Without C struct documentation, code generators cannot produce correct C code
- Fix approach: Template docstring example:
  ```python
  class CombFilter:
      """
      C struct equivalent:
      typedef struct {
          float delay_line[MAX_DELAY];
          int write_pos;
          float feedback;
      } CombFilter;
      """
  ```

**Algorithm Parameter Documentation:**
- Issue: ParamSpec for knob ranges (0-100) and switch positions (-1, 0, 1) mentioned but format undefined
- Files: `claudeverb/algorithms/base.py` will define ParamSpec
- Impact: UI cannot render controls without parameter specification
- Fix approach: Define ParamSpec as dataclass with name, min_value, max_value, default, description

## Performance Concerns (Pre-Implementation)

**No Profiling Infrastructure:**
- Issue: BUFFER_SIZE = 48 @ 48 kHz = 1ms callback deadline is very tight; no profiling tools planned
- Files: Missing profiling utilities
- Risk: Algorithms could exceed real-time deadline without detection during development
- Fix approach: Add benchmark suite; measure processing time per algorithm at various parameter settings

**Memory Overhead Not Analyzed:**
- Issue: Daisy Seed has ~192 KB RAM; no analysis of how much each algorithm will use
- Impact: An algorithm could be perfect in Python but fail on Daisy due to memory constraints
- Fix approach: Document fixed buffer sizes per algorithm; calculate maximum memory before C generation

## Security Considerations

**File Path Handling Not Secured:**
- Issue: `claudeverb/audio/io.py` load() will read arbitrary audio files; no path validation planned
- Files: `claudeverb/audio/io.py`
- Risk: Path traversal if used in web context (unlikely but possible with Streamlit)
- Mitigation: Restrict file paths to designated audio directory; use pathlib with resolve()

**Numerical Stability in DSP Filters:**
- Issue: Filter implementations must be numerically stable (denormalized float handling, feedback coefficient ranges)
- Files: `claudeverb/algorithms/filters.py`
- Risk: Direct form IIR filters can become unstable; library/cascade form more stable
- Fix approach: Document filter implementation choice; prefer transposed direct form II for biquads; add underflow protection (subnormal float denormals)

## Known Incomplete Implementations

**Schroeder Algorithm Stub:**
- Status: Marked as "🚧 Stub" in readme.md
- Files: Should be in `claudeverb/algorithms/schroeder.py`
- Missing: Full implementation
- Priority: Phase 2 algorithm development

**Plate (Dattorro) Algorithm Stub:**
- Status: Marked as "🚧 Stub" in readme.md
- Files: Should be in `claudeverb/algorithms/plate.py`
- Missing: Full implementation
- Priority: Phase 2 algorithm development

**Freeverb Implementation Status Ambiguous:**
- Status: Listed as "✅ Complete" in readme but source code doesn't exist
- Files: Should be in `claudeverb/algorithms/freeverb.py`
- Risk: Contradicts project state (no source code exists)
- Fix approach: Clarify: if Freeverb is truly complete, it must be committed; if not, change status to "🚧 Stub" in readme

## Deployment & Distribution Gaps

**No Package Distribution:**
- Issue: No setup.py, no wheel building, no PyPI target
- Files: Missing setup.py or pyproject.toml
- Impact: Cannot distribute workbench to other developers
- Fix approach: Create pyproject.toml with build backend; add GitHub Actions for wheel builds

**No Version Management:**
- Issue: No version numbering in code or git tags
- Files: Missing __version__ in `claudeverb/__init__.py`
- Impact: Unclear what version of algorithm was exported to C
- Fix approach: Use semantic versioning; tag releases in git

**Daisy Seed Export Target Documentation Missing:**
- Issue: C code generation mentions "libDaisy framework" and "Hothouse DSP host pedal from Cleveland Audio" but no integration docs
- Files: Should be in `docs/daisy_deployment.md`
- Risk: Generated C code may not work out-of-box on target platform
- Fix approach: Document exact platform (Daisy Seed PCM3060 board), libDaisy version, and Hothouse integration points

---

*Concerns audit: 2026-03-04*
