"""ClaudeVerb Streamlit web application.

Provides a browser-based workbench for loading audio, selecting reverb
algorithms, tweaking parameters, processing, and analyzing results.

Run with: streamlit run claudeverb/streamlit_app.py
"""

from __future__ import annotations

import io

import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
import streamlit as st

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.audio.samples import get_sample, list_samples
from claudeverb.config import SAMPLE_RATE
from claudeverb import engine

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="ClaudeVerb", layout="wide")

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

for key in ["dry_audio", "wet_audio", "results", "audio_loaded"]:
    if key not in st.session_state:
        st.session_state[key] = None


def _audio_to_wav_bytes(audio: np.ndarray) -> bytes:
    """Encode audio to WAV bytes preserving true levels.

    Streamlit's built-in numpy handling normalizes to peak, which makes
    everything sound louder than it really is.  By pre-encoding to 16-bit
    WAV via soundfile we bypass that normalization.
    """
    buf = io.BytesIO()
    if audio.ndim == 2 and audio.shape[0] == 2:
        sf.write(buf, audio.T, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    else:
        sf.write(buf, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buf.getvalue()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("ClaudeVerb")

    # -- Audio source --
    audio_source = st.radio("Audio Source", ["Bundled Sample", "Upload File"])

    audio_data: np.ndarray | None = None

    if audio_source == "Bundled Sample":
        sample_name = st.selectbox("Sample", list_samples())
        audio_data = get_sample(sample_name)
    else:
        uploaded_file = st.file_uploader(
            "Upload Audio", type=["wav", "aiff", "flac", "ogg"]
        )
        if uploaded_file is not None:
            import librosa

            uploaded_file.seek(0)
            audio_data, _ = librosa.load(
                uploaded_file, sr=SAMPLE_RATE, mono=False
            )
            audio_data = audio_data.astype(np.float32)

    if audio_data is not None:
        st.session_state["audio_loaded"] = True

    # -- Algorithm --
    algo_name = st.selectbox("Algorithm", list(ALGORITHM_REGISTRY.keys()))

    # Clear stale widget keys when the user switches algorithms
    if st.session_state.get("current_algo") is not None and st.session_state["current_algo"] != algo_name:
        for k in list(st.session_state.keys()):
            if k.startswith("knob_") or k.startswith("switch_"):
                del st.session_state[k]
        for k in ["results", "dry_audio", "wet_audio"]:
            st.session_state[k] = None
        st.session_state["current_algo"] = algo_name
        st.rerun()
    st.session_state.setdefault("current_algo", algo_name)

    # Instantiate to read param_specs
    algo_cls = ALGORITHM_REGISTRY[algo_name]
    algo_instance = algo_cls()
    specs = algo_instance.param_specs

    # -- Auto-generated controls from param_specs --
    for param_name, spec in specs.items():
        # Skip the mix knob (engine forces mix=100; UI wet/dry replaces it)
        if param_name == "mix":
            continue

        if spec["type"] == "knob":
            st.slider(
                spec["label"],
                spec["min"],
                spec["max"],
                spec["default"],
                key=f"knob_{param_name}",
            )
        elif spec["type"] == "switch":
            positions = spec["positions"]
            labels = spec["labels"]
            st.select_slider(
                spec["label"],
                options=positions,
                value=spec["default"],
                format_func=lambda x, _labels=labels, _positions=positions: _labels[
                    _positions.index(x)
                ],
                key=f"switch_{param_name}",
            )

    # -- Wet/Dry slider --
    st.slider("Wet/Dry Mix", 0, 100, 75, key="wet_dry")

    # -- Process button --
    process_clicked = st.button(
        "Process", type="primary", use_container_width=True
    )

    # -- Reset button --
    reset_clicked = st.button("Reset to Defaults")

# ---------------------------------------------------------------------------
# Reset handler
# ---------------------------------------------------------------------------

if reset_clicked:
    # Clear algorithm param keys from session state
    for param_name, spec in specs.items():
        if param_name == "mix":
            continue
        if spec["type"] == "knob":
            key = f"knob_{param_name}"
            if key in st.session_state:
                del st.session_state[key]
        elif spec["type"] == "switch":
            key = f"switch_{param_name}"
            if key in st.session_state:
                del st.session_state[key]
    if "wet_dry" in st.session_state:
        del st.session_state["wet_dry"]
    if "current_algo" in st.session_state:
        del st.session_state["current_algo"]
    st.rerun()

# ---------------------------------------------------------------------------
# Process handler
# ---------------------------------------------------------------------------

if process_clicked and audio_data is not None:
    # Collect params from sidebar widget values
    params: dict = {}
    for param_name, spec in specs.items():
        if param_name == "mix":
            continue
        if spec["type"] == "knob":
            params[param_name] = st.session_state.get(
                f"knob_{param_name}", spec["default"]
            )
        elif spec["type"] == "switch":
            params[param_name] = st.session_state.get(
                f"switch_{param_name}", spec["default"]
            )

    with st.spinner("Processing..."):
        results = engine.process_audio(algo_name, params, audio_data)

    st.session_state["dry_audio"] = results["dry"]
    st.session_state["wet_audio"] = results["wet"]
    st.session_state["results"] = results

# ---------------------------------------------------------------------------
# Main area -- display results
# ---------------------------------------------------------------------------

if st.session_state["results"] is not None:
    results = st.session_state["results"]
    dry = st.session_state["dry_audio"]
    wet = st.session_state["wet_audio"]
    wet_dry_value = st.session_state.get("wet_dry", 75)

    # -- Audio Players --
    st.subheader("Audio Players")
    col_in, col_out = st.columns(2)

    with col_in:
        st.markdown("**Input**")
        st.audio(_audio_to_wav_bytes(dry), format="audio/wav", loop=True)

    with col_out:
        st.markdown("**Output**")
        blended = engine.blend_wet_dry(dry, wet, wet_dry_value)
        st.audio(_audio_to_wav_bytes(blended), format="audio/wav", loop=True)

        # Download button for processed audio
        st.download_button(
            "Download WAV",
            _audio_to_wav_bytes(blended),
            "processed.wav",
            "audio/wav",
        )

    # -- Waveform --
    st.subheader("Waveform Comparison")
    fig_waveform = engine.plot_waveform_comparison(dry, wet)
    st.pyplot(fig_waveform, use_container_width=False)
    plt.close(fig_waveform)

    # -- Spectrograms --
    st.subheader("Mel Spectrogram Comparison")
    fig_mel = results["figures"]["mel"]
    st.pyplot(fig_mel, use_container_width=False)
    plt.close(fig_mel)

    # -- FFT Overlay --
    st.subheader("FFT Overlay")
    fig_fft = results["figures"]["fft"]
    st.pyplot(fig_fft, use_container_width=False)
    plt.close(fig_fft)

    # -- Metrics --
    st.subheader("Metrics")
    metrics = results["metrics"]

    # Parse RT60 bands for display
    rt60_bands_str = metrics.get("RT60 Bands", "")
    band_values = {}
    for part in rt60_bands_str.split(", "):
        if ": " in part:
            band_name, band_val = part.split(": ", 1)
            band_values[band_name] = band_val

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("RT60 (broadband)", metrics.get("RT60", "N/A"))
        st.metric("DRR", metrics.get("DRR", "N/A"))
    with col2:
        st.metric("RT60 Low", band_values.get("low", "N/A"))
        st.metric("C80", metrics.get("C80", "N/A"))
    with col3:
        st.metric("RT60 Mid", band_values.get("mid", "N/A"))
        st.metric("C50", metrics.get("C50", "N/A"))
    with col4:
        st.metric("RT60 High", band_values.get("high", "N/A"))
        st.metric("Centroid Delta", metrics.get("Centroid Delta", "N/A"))

    # -- Impulse Response --
    st.subheader("Impulse Response")
    ir = results["ir"]
    st.audio(_audio_to_wav_bytes(ir), format="audio/wav", loop=True)

    # Small IR waveform plot
    fig_ir, ax_ir = plt.subplots(figsize=(10, 1.5))
    t_ir = np.arange(len(ir)) / SAMPLE_RATE
    ax_ir.plot(t_ir, ir, linewidth=0.5)
    ax_ir.set_xlabel("Time (s)")
    ax_ir.set_ylabel("Amplitude")
    ax_ir.set_title("Impulse Response")
    fig_ir.tight_layout()
    st.pyplot(fig_ir, use_container_width=False)
    plt.close(fig_ir)
