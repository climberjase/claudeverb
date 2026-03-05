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
        st.audio(dry, sample_rate=SAMPLE_RATE)

    with col_out:
        st.markdown("**Output**")
        blended = engine.blend_wet_dry(dry, wet, wet_dry_value)
        st.audio(blended, sample_rate=SAMPLE_RATE)

        # Download button for processed audio
        buf = io.BytesIO()
        # soundfile expects (N,) mono or (N, 2) stereo
        if blended.ndim == 2 and blended.shape[0] == 2:
            sf.write(buf, blended.T, SAMPLE_RATE, format="WAV")
        else:
            sf.write(buf, blended, SAMPLE_RATE, format="WAV")
        st.download_button(
            "Download WAV",
            buf.getvalue(),
            "processed.wav",
            "audio/wav",
        )

    # -- Waveform --
    st.subheader("Waveform Comparison")
    fig_waveform = engine.plot_waveform_comparison(dry, wet)
    st.pyplot(fig_waveform)
    plt.close(fig_waveform)

    # -- Spectrograms --
    st.subheader("Mel Spectrogram Comparison")
    fig_mel = results["figures"]["mel"]
    st.pyplot(fig_mel)
    plt.close(fig_mel)

    # -- FFT Overlay --
    st.subheader("FFT Overlay")
    fig_fft = results["figures"]["fft"]
    st.pyplot(fig_fft)
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
    st.audio(ir, sample_rate=SAMPLE_RATE)

    # Small IR waveform plot
    fig_ir, ax_ir = plt.subplots(figsize=(12, 2))
    t_ir = np.arange(len(ir)) / SAMPLE_RATE
    ax_ir.plot(t_ir, ir, linewidth=0.5)
    ax_ir.set_xlabel("Time (s)")
    ax_ir.set_ylabel("Amplitude")
    ax_ir.set_title("Impulse Response")
    fig_ir.tight_layout()
    st.pyplot(fig_ir)
    plt.close(fig_ir)
