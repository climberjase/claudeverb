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
from claudeverb.algorithms.dattorro_presets import get_preset, list_presets
from claudeverb.audio.samples import get_sample, list_all_samples
from claudeverb.config import SAMPLE_RATE
from claudeverb import engine

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="ClaudeVerb", layout="wide")

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

for key in ["dry_audio", "wet_audio", "results", "audio_loaded", "original_length"]:
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
        sample_name = st.selectbox("Sample", list_all_samples())
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

    # -- Silence padding slider --
    st.slider(
        "Silence Padding (seconds)", 0.0, 5.0, 2.0, step=0.1,
        key="silence_padding",
    )

    # -- Loop toggle --
    st.checkbox("Loop Playback", value=False, key="loop_playback")

    # -- Algorithm --
    algo_name = st.selectbox("Algorithm", list(ALGORITHM_REGISTRY.keys()))

    # Clear stale widget keys when the user switches algorithms
    if st.session_state.get("current_algo") is not None and st.session_state["current_algo"] != algo_name:
        for k in list(st.session_state.keys()):
            if k.startswith("knob_") or k.startswith("switch_"):
                del st.session_state[k]
        prev = st.session_state.get("results")
        if prev and "figures" in prev:
            for fig in prev["figures"].values():
                plt.close(fig)
        for k in ["results", "dry_audio", "wet_audio"]:
            st.session_state[k] = None
        st.session_state.pop("preset_name", None)
        st.session_state.pop("_preset_values", None)
        st.session_state["current_algo"] = algo_name
        st.rerun()
    st.session_state.setdefault("current_algo", algo_name)

    # Instantiate to read param_specs
    algo_cls = ALGORITHM_REGISTRY[algo_name]
    algo_instance = algo_cls()
    specs = algo_instance.param_specs

    # -- Dattorro preset dropdown (only for dattorro_plate) --
    if algo_name == "dattorro_plate":
        preset_options = ["Custom"] + list_presets()
        preset_name = st.selectbox(
            "Preset", preset_options,
            index=preset_options.index(st.session_state.get("preset_name", "Custom"))
            if st.session_state.get("preset_name", "Custom") in preset_options
            else 0,
            key="preset_name",
        )

        # When a preset is selected (not Custom), snap knobs to preset values
        if preset_name and preset_name != "Custom":
            preset_vals = get_preset(preset_name)
            stored_preset = st.session_state.get("_preset_values")
            # Only snap if this is a new preset selection
            if stored_preset is None or stored_preset.get("_name") != preset_name:
                for param, value in preset_vals.items():
                    if param in specs:
                        if specs[param]["type"] == "knob":
                            st.session_state[f"knob_{param}"] = value
                        elif specs[param]["type"] == "switch":
                            st.session_state[f"switch_{param}"] = value
                st.session_state["_preset_values"] = {**preset_vals, "_name": preset_name}
                st.rerun()

    # -- Auto-generated controls from param_specs --
    for param_name, spec in specs.items():
        # Skip the mix knob (engine forces mix=100; UI wet/dry replaces it)
        if param_name == "mix":
            continue

        if spec["type"] == "knob":
            knob_key = f"knob_{param_name}"
            knob_kwargs = dict(
                label=spec["label"],
                min_value=spec["min"],
                max_value=spec["max"],
                key=knob_key,
            )
            if knob_key not in st.session_state:
                knob_kwargs["value"] = spec["default"]
            st.slider(**knob_kwargs)
        elif spec["type"] == "switch":
            positions = spec["positions"]
            labels = spec["labels"]
            switch_key = f"switch_{param_name}"
            switch_kwargs = dict(
                label=spec["label"],
                options=positions,
                format_func=lambda x, _labels=labels, _positions=positions: _labels[
                    _positions.index(x)
                ],
                key=switch_key,
            )
            if switch_key not in st.session_state:
                switch_kwargs["value"] = spec["default"]
            st.select_slider(**switch_kwargs)

    # -- Detect if user tweaked knobs away from preset --
    if algo_name == "dattorro_plate" and st.session_state.get("_preset_values"):
        stored = st.session_state["_preset_values"]
        preset_still_matches = True
        for param, value in stored.items():
            if param == "_name":
                continue
            if param in specs:
                if specs[param]["type"] == "knob":
                    current = st.session_state.get(f"knob_{param}")
                elif specs[param]["type"] == "switch":
                    current = st.session_state.get(f"switch_{param}")
                else:
                    continue
                if current is not None and current != value:
                    preset_still_matches = False
                    break
        if not preset_still_matches:
            st.caption("Preset: **Custom** (modified)")

    # -- Wet/Dry slider --
    st.slider("Wet/Dry Mix", 0, 100, 75, key="wet_dry")

    # -- EQ controls --
    st.checkbox("Enable EQ", value=False, key="eq_enabled")
    if st.session_state.get("eq_enabled"):
        st.markdown("**Low Shelf**")
        st.slider("Low Freq", 80, 500, 200, key="eq_low_freq")
        st.slider("Low Gain (dB)", -12.0, 12.0, 0.0, step=0.5, key="eq_low_gain")
        st.markdown("**Mid Parametric**")
        st.slider("Mid Freq", 200, 5000, 1000, key="eq_mid_freq")
        st.slider("Mid Gain (dB)", -12.0, 12.0, 0.0, step=0.5, key="eq_mid_gain")
        st.slider("Mid Q", 0.5, 5.0, 1.5, step=0.1, key="eq_mid_q")
        st.markdown("**High Shelf**")
        st.slider("High Freq", 2000, 16000, 6000, key="eq_high_freq")
        st.slider("High Gain (dB)", -12.0, 12.0, 0.0, step=0.5, key="eq_high_gain")

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
    # Close any leaked matplotlib figures before clearing state
    prev = st.session_state.get("results")
    if prev and "figures" in prev:
        for fig in prev["figures"].values():
            plt.close(fig)
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
    for k in ["preset_name", "_preset_values"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

# ---------------------------------------------------------------------------
# Process handler
# ---------------------------------------------------------------------------

if process_clicked and audio_data is not None:
    # Close any matplotlib figures from previous processing run
    prev_results = st.session_state.get("results")
    if prev_results and "figures" in prev_results:
        for fig in prev_results["figures"].values():
            plt.close(fig)

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

    # Collect silence padding
    silence_seconds = st.session_state.get("silence_padding", 2.0)

    # Collect EQ params
    eq_params = None
    if st.session_state.get("eq_enabled"):
        eq_params = {
            "enabled": True,
            "low_freq": st.session_state.get("eq_low_freq", 200),
            "low_gain": st.session_state.get("eq_low_gain", 0.0),
            "mid_freq": st.session_state.get("eq_mid_freq", 1000),
            "mid_gain": st.session_state.get("eq_mid_gain", 0.0),
            "mid_q": st.session_state.get("eq_mid_q", 1.5),
            "high_freq": st.session_state.get("eq_high_freq", 6000),
            "high_gain": st.session_state.get("eq_high_gain", 0.0),
        }

    with st.spinner("Processing..."):
        results = engine.process_audio(
            algo_name, params, audio_data,
            silence_seconds=silence_seconds,
            eq_params=eq_params,
        )

    st.session_state["dry_audio"] = results["dry"]
    st.session_state["wet_audio"] = results["wet"]
    st.session_state["results"] = results
    st.session_state["original_length"] = results.get("original_length")

# ---------------------------------------------------------------------------
# Main area -- display results
# ---------------------------------------------------------------------------

if st.session_state["results"] is not None:
    results = st.session_state["results"]
    dry = st.session_state["dry_audio"]
    wet = st.session_state["wet_audio"]
    wet_dry_value = st.session_state.get("wet_dry", 75)
    loop_value = st.session_state.get("loop_playback", False)

    # -- Audio Players --
    st.subheader("Audio Players")
    col_in, col_out = st.columns(2)

    with col_in:
        st.markdown("**Input**")
        st.audio(_audio_to_wav_bytes(dry), format="audio/wav", loop=loop_value)

    with col_out:
        st.markdown("**Output**")
        blended = engine.blend_wet_dry(dry, wet, wet_dry_value)
        st.audio(_audio_to_wav_bytes(blended), format="audio/wav", loop=loop_value)

        # Download button for processed audio
        st.download_button(
            "Download WAV",
            _audio_to_wav_bytes(blended),
            "processed.wav",
            "audio/wav",
        )

    # -- Waveform --
    st.subheader("Waveform Comparison")
    original_length = st.session_state.get("original_length")
    fig_waveform = engine.plot_waveform_comparison(
        dry, wet, padding_start_sample=original_length,
    )
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
    st.audio(_audio_to_wav_bytes(ir), format="audio/wav", loop=loop_value)

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
