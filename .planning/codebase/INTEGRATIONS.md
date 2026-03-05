# External Integrations

**Analysis Date:** 2025-02-18

## APIs & External Services

**Audio Unit Plugins (macOS):**
- Local AU (Audio Unit) plugins - Commercial reverb plugins loaded from system for A/B comparison testing
  - Purpose: Provide reference implementations for algorithm validation
  - SDK/Client: Core Audio framework (system-level AU plugin interface)
  - Authentication: None required (local system plugins)

## Data Storage

**Databases:**
- Not applicable - Project is a DSP algorithm workbench without persistent data requirements

**File Storage:**
- Local filesystem only
  - Audio files: WAV, FLAC, or other formats supported by `soundfile`
  - Generated C code: Exported to `./c_export` or specified output directory
  - Cached analysis: IR and test audio processed in-memory

**Caching:**
- In-memory processing only
  - Mel spectrograms cached during analysis session
  - Filter state and delay lines maintained in algorithm instances
  - No distributed or persistent cache layer

## Authentication & Identity

**Auth Provider:**
- Not applicable - Workbench is local-only with no multi-user or cloud features

## Monitoring & Observability

**Error Tracking:**
- Not detected - Project is local development workbench

**Logs:**
- Console/stdout only (pytest, application logging)
- No centralized logging service

## CI/CD & Deployment

**Hosting:**
- Local development on macOS (primary)
- Target deployment: STM32 Daisy Seed via Hothouse DSP host pedal (Cleveland Audio)

**CI Pipeline:**
- Not detected in codebase (no GitHub Actions, GitLab CI, or similar)

## Environment Configuration

**Required env vars:**
- None detected - All configuration via code constants (`SAMPLE_RATE`, `BUFFER_SIZE`)
- Audio device selection via `sounddevice` runtime parameters
- Output directories specified as function arguments

**Secrets location:**
- Not applicable - No API keys, credentials, or secrets required

## Webhooks & Callbacks

**Incoming:**
- None - Workbench is standalone application

**Outgoing:**
- None - No external service callbacks

## Third-Party Audio Components

**Commercial Plugin Integration:**
- Purpose: Load native AU plugins from macOS system for comparative testing
- Scope: Read-only access to installed Audio Units for analysis and comparison
- No API integration - Direct system AU framework access only

---

*Integration audit: 2025-02-18*
