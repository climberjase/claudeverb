"""RoomReverbBase shared base class for Room/Chamber reverb algorithms.

Composes EarlyReflections -> FDNCore in serial with ER Level crossfade,
pre-delay, stereo width control, and freeze/bright switches.

Subclasses override _get_config() to provide algorithm-specific parameters
(tap positions, decay range, FDN delays, etc.).

C struct equivalent:
    typedef struct {
        EarlyReflections er;
        FDNCore fdn;

        // Pre-delay line
        float pre_delay_buf[4800];  // max 100ms at 48kHz
        int pre_delay_write_idx;
        int pre_delay_samples;

        // Parameters
        float decay;        // RT60 in seconds
        float size_scale;   // 0.5 - 2.0x
        float damping;      // OnePole coefficient
        float er_level;     // 0.0 - 1.0 crossfade
        float mix;          // 0.0 - 1.0 wet/dry
        int pre_delay_ms;   // 0 - 100ms

        // Switches
        int switch1;        // -1=Freeze, 0=Normal, 1=Bright
        int switch2;        // -1=Mono, 0=Stereo, 1=Wide

        int sample_rate;
    } RoomReverbState;
"""

from __future__ import annotations

from abc import abstractmethod

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.algorithms.early_reflections import EarlyReflections
from claudeverb.algorithms.fdn_reverb import FDNCore
from claudeverb.algorithms.filters import DelayLine

SAMPLE_RATE = 48000
MAX_PRE_DELAY_SAMPLES = int(0.1 * SAMPLE_RATE)  # 100ms


class RoomReverbBase(ReverbAlgorithm):
    """Shared base class for Room and Chamber reverb algorithms.

    Composes EarlyReflections -> FDNCore in serial with ER Level crossfade.
    Subclasses override _get_config() to provide algorithm-specific tuning.

    6 knobs: decay, size, damping, er_level, mix, pre_delay
    2 switches: switch1 (Freeze/Normal/Bright), switch2 (Mono/Stereo/Wide)
    """

    __slots__ = (
        "_er", "_fdn", "_pre_delay_line", "_config",
        # Parameter state (0-100 knob values)
        "_decay", "_size", "_damping", "_er_level",
        "_mix", "_pre_delay", "_switch1", "_switch2",
        # Scaled internal values
        "_decay_scaled", "_size_scaled", "_damping_scaled",
        "_er_level_scaled", "_mix_scaled", "_pre_delay_samples",
    )

    def __init__(self) -> None:
        self._config = self._get_config()
        defaults = self._config["default_params"]

        # Store parameter state
        self._decay = defaults.get("decay", 50)
        self._size = defaults.get("size", 50)
        self._damping = defaults.get("damping", 40)
        self._er_level = defaults.get("er_level", 40)
        self._mix = defaults.get("mix", 50)
        self._pre_delay = defaults.get("pre_delay", 10)
        self._switch1 = defaults.get("switch1", 0)
        self._switch2 = defaults.get("switch2", 0)

        # Init scaled values
        self._decay_scaled = 1.0
        self._size_scaled = 1.0
        self._damping_scaled = 0.7
        self._er_level_scaled = 0.4
        self._mix_scaled = 0.5
        self._pre_delay_samples = 0

        self._initialize()

    @abstractmethod
    def _get_config(self) -> dict:
        """Return algorithm-specific configuration.

        Must return dict with keys:
            tap_delays, tap_gains, tap_lpf_coeffs,
            diffuser_delays, diffuser_feedback,
            fdn_delays, decay_range (min, max),
            default_params
        """

    def _initialize(self) -> None:
        """Allocate DSP components from config."""
        cfg = self._config

        # Create EarlyReflections
        self._er = EarlyReflections(
            tap_delays=cfg["tap_delays"],
            tap_gains=cfg["tap_gains"],
            tap_lpf_coeffs=cfg["tap_lpf_coeffs"],
            diffuser_delays=cfg.get("diffuser_delays", []),
            diffuser_feedback=cfg.get("diffuser_feedback", 0.5),
            sample_rate=SAMPLE_RATE,
        )

        # Create FDNCore with config-specific delays
        self._fdn = FDNCore(
            base_delays=cfg["fdn_delays"],
            sample_rate=SAMPLE_RATE,
        )

        # Pre-delay line (max 100ms)
        self._pre_delay_line = DelayLine(MAX_PRE_DELAY_SAMPLES)

        # Apply initial parameters
        self._apply_params()

    def _apply_params(self) -> None:
        """Map 0-100 knob values to internal parameters and apply to DSP components."""
        cfg = self._config
        decay_min, decay_max = cfg["decay_range"]

        # Decay: 0-100 -> decay_range (exponential mapping)
        val = max(self._decay, 0)
        t = val / 100.0
        self._decay_scaled = decay_min * ((decay_max / decay_min) ** t)

        # Size: 0-100 -> 0.5x to 2.0x
        self._size_scaled = 0.5 + (self._size / 100.0) * 1.5

        # Damping: 0-100 -> OnePole coefficient 1.0 (bright) to 0.05 (dark)
        self._damping_scaled = 1.0 - (self._damping / 100.0) * 0.95

        # ER Level: 0-100 -> 0.0 to 1.0
        self._er_level_scaled = self._er_level / 100.0

        # Mix: 0-100 -> 0.0 to 1.0
        self._mix_scaled = self._mix / 100.0

        # Pre-delay: 0-100 -> 0 to 4800 samples (0-100ms)
        self._pre_delay_samples = int((self._pre_delay / 100.0) * MAX_PRE_DELAY_SAMPLES)

        # Apply Freeze
        freeze = self._switch1 == -1
        if freeze:
            self._fdn.set_freeze(True)
            return
        else:
            self._fdn.set_freeze(False)

        # Apply to FDN
        self._fdn.set_decay(self._decay_scaled)
        self._fdn.set_size(self._size_scaled)

        # Bright mode: reduce damping coefficient by 0.3 (more transparent)
        damp_coeff = self._damping_scaled
        if self._switch1 == 1:  # Bright
            damp_coeff = min(1.0, damp_coeff + 0.3)
        self._fdn.set_damping(damp_coeff)

        # Subtle fixed modulation (anti-metallic)
        self._fdn.set_modulation(depth=0.3, rate=0.5)

        # Apply size to ER
        self._er.set_size_scale(self._size_scaled)

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        """Process audio: mono input -> ER -> FDN -> stereo output."""
        if audio.ndim == 1:
            mono_in = audio
        else:
            mono_in = (audio[0] + audio[1]) * np.float32(0.5)

        n_samples = len(mono_in)
        left_out = np.zeros(n_samples, dtype=np.float32)
        right_out = np.zeros(n_samples, dtype=np.float32)

        # Cache params
        er_level = self._er_level_scaled
        mix_wet = self._mix_scaled
        mix_dry = 1.0 - mix_wet
        pre_delay_samples = self._pre_delay_samples
        freeze = self._switch1 == -1
        freeze_gain = 4.0 if freeze else 1.0

        # Width
        if self._switch2 == -1:    # Mono
            width = 0.0
        elif self._switch2 == 1:   # Wide
            width = 2.0
        else:                      # Stereo
            width = 1.0
        wet1 = (1.0 + width) / 2.0
        wet2 = (1.0 - width) / 2.0

        for i in range(n_samples):
            dry_sample = float(mono_in[i])
            x = dry_sample

            # Freeze: zero input
            if freeze:
                x = 0.0

            # Pre-delay
            if pre_delay_samples > 0:
                delayed = self._pre_delay_line.read(pre_delay_samples)
                self._pre_delay_line.write(x)
                x = delayed
            else:
                self._pre_delay_line.write(x)

            # Early Reflections
            er_l, er_r = self._er.process_sample(x)
            er_mono = (er_l + er_r) * 0.5

            # ER Level crossfade: FDN always receives ER mono sum
            # Output ER component is scaled by er_level
            # FDN input is always er_mono (regardless of er_level)
            fdn_input = er_mono

            # FDN processing (distribute to 4 channels)
            fdn_outputs = self._fdn.process_sample([fdn_input, fdn_input, fdn_input, fdn_input])

            # Stereo tap from FDN
            fdn_l = (fdn_outputs[0] + fdn_outputs[2]) * freeze_gain
            fdn_r = (fdn_outputs[1] + fdn_outputs[3]) * freeze_gain

            # ER Level crossfade: blend ER stereo vs FDN stereo
            # er_level=0 -> pure FDN tail, er_level=1 -> ER only
            wet_l = er_level * er_l + (1.0 - er_level) * fdn_l
            wet_r = er_level * er_r + (1.0 - er_level) * fdn_r

            # Stereo width crossmix
            final_wet_l = wet_l * wet1 + wet_r * wet2
            final_wet_r = wet_r * wet1 + wet_l * wet2

            # Mix dry/wet
            final_l = dry_sample * mix_dry + final_wet_l * mix_wet
            final_r = dry_sample * mix_dry + final_wet_r * mix_wet

            # Hard clip
            final_l = max(-1.0, min(1.0, final_l))
            final_r = max(-1.0, min(1.0, final_r))

            left_out[i] = np.float32(final_l)
            right_out[i] = np.float32(final_r)

        return np.stack([left_out, right_out])

    def update_params(self, params: dict) -> None:
        """Update algorithm parameters from dict."""
        if "decay" in params:
            self._decay = params["decay"]
        if "size" in params:
            self._size = params["size"]
        if "damping" in params:
            self._damping = params["damping"]
        if "er_level" in params:
            self._er_level = params["er_level"]
        if "mix" in params:
            self._mix = params["mix"]
        if "pre_delay" in params:
            self._pre_delay = params["pre_delay"]
        if "switch1" in params:
            self._switch1 = params["switch1"]
        if "switch2" in params:
            self._switch2 = params["switch2"]
        self._apply_params()

    def reset(self) -> None:
        """Reset all internal state to initial values."""
        self._er.reset()
        self._fdn.reset()
        self._pre_delay_line.reset()
        # Re-apply current params after reset (per Phase 7 lesson)
        self._apply_params()

    @property
    def param_specs(self) -> dict:
        """Parameter specifications for UI/automation."""
        return {
            "decay": {
                "type": "knob", "min": 0, "max": 100, "default": 50,
                "label": "Decay",
            },
            "size": {
                "type": "knob", "min": 0, "max": 100, "default": 50,
                "label": "Size",
            },
            "damping": {
                "type": "knob", "min": 0, "max": 100, "default": 40,
                "label": "Damping",
            },
            "er_level": {
                "type": "knob", "min": 0, "max": 100, "default": 40,
                "label": "ER Level",
            },
            "mix": {
                "type": "knob", "min": 0, "max": 100, "default": 50,
                "label": "Mix",
            },
            "pre_delay": {
                "type": "knob", "min": 0, "max": 100, "default": 10,
                "label": "Pre-Delay",
            },
            "switch1": {
                "type": "switch", "positions": [-1, 0, 1], "default": 0,
                "label": "Mode",
                "labels": ["Freeze", "Normal", "Bright"],
            },
            "switch2": {
                "type": "switch", "positions": [-1, 0, 1], "default": 0,
                "label": "Stereo Mode",
                "labels": ["Mono", "Stereo", "Wide"],
            },
        }

    def to_dot(self, detail_level: str = "block",
               params: dict | None = None) -> str:
        """Generate Graphviz DOT string for Room/Chamber reverb signal flow."""
        from claudeverb.export.dot_builder import (
            digraph_wrap, dsp_node, io_node, edge, feedback_edge, subgraph,
        )
        p = params if params else {
            k: v["default"] for k, v in self.param_specs.items()
            if v.get("type") == "knob"
        }
        decay = p.get("decay", 50)
        size = p.get("size", 50)
        damp = p.get("damping", 40)
        er_lev = p.get("er_level", 40)
        mix_val = p.get("mix", 50)
        pre_d = p.get("pre_delay", 10)

        cfg = self._config
        algo_name = type(self).__name__
        num_taps = len(cfg["tap_delays"])
        num_diffusers = len(cfg.get("diffuser_delays", []))
        fdn_delays = cfg["fdn_delays"]

        if detail_level == "component":
            body = io_node("input", "Input")
            body += dsp_node("pre_delay", f"Pre-Delay\\n[{pre_d}]")
            body += edge("input", "pre_delay")

            # ER taps
            er_nodes = ""
            for i, (delay, gain) in enumerate(zip(cfg["tap_delays"], cfg["tap_gains"])):
                er_nodes += dsp_node(f"tap{i}", f"ER Tap {i}\\n[{delay} smp]\\ngain: {gain:.2f}")
            # ER diffusers
            for i, dd in enumerate(cfg.get("diffuser_delays", [])):
                er_nodes += dsp_node(f"er_diff{i}", f"ER Diffuser {i}\\n[{dd} smp]")
            body += subgraph("early_ref", f"Early Reflections ({num_taps} taps)", er_nodes)

            body += edge("pre_delay", "tap0")
            for i in range(1, num_taps):
                body += edge("pre_delay", f"tap{i}")

            # Connect ER diffusers after taps
            if num_diffusers > 0:
                body += dsp_node("er_sum", "ER Sum")
                for i in range(num_taps):
                    body += edge(f"tap{i}", "er_sum")
                body += edge("er_sum", "er_diff0")
                for i in range(num_diffusers - 1):
                    body += edge(f"er_diff{i}", f"er_diff{i+1}")
                last_er = f"er_diff{num_diffusers - 1}"
            else:
                body += dsp_node("er_sum", "ER Sum")
                for i in range(num_taps):
                    body += edge(f"tap{i}", "er_sum")
                last_er = "er_sum"

            # FDN channels
            fdn_nodes = ""
            for i, d in enumerate(fdn_delays):
                fdn_nodes += dsp_node(f"fdn_d{i}", f"FDN Ch{i}\\n[{d} smp]")
                fdn_nodes += dsp_node(f"fdn_damp{i}", f"Damp {i}")
            fdn_nodes += dsp_node("hadamard", "Hadamard Mix")
            body += subgraph("fdn", f"FDN ({len(fdn_delays)} channels, decay: {decay})", fdn_nodes)

            body += edge(last_er, "fdn_d0")
            body += edge(last_er, "fdn_d1")
            body += edge(last_er, "fdn_d2")
            body += edge(last_er, "fdn_d3")

            for i in range(4):
                body += edge(f"fdn_d{i}", f"fdn_damp{i}")
                body += edge(f"fdn_damp{i}", "hadamard")
            for i in range(4):
                body += feedback_edge("hadamard", f"fdn_d{i}")

            body += dsp_node("er_crossfade", f"ER/FDN Crossfade\\ner_level: {er_lev}")
            body += dsp_node("stereo_mix", f"Stereo Mix\\nmix: {mix_val}")
            body += io_node("output", "Output")

            body += edge(last_er, "er_crossfade", label="ER")
            body += edge("hadamard", "er_crossfade", label="FDN")
            body += edge("er_crossfade", "stereo_mix")
            body += edge("stereo_mix", "output")

            return digraph_wrap(algo_name, body)
        else:
            # Block level
            body = io_node("input", "Input")
            body += dsp_node("pre_delay", f"Pre-Delay\\n[{pre_d}]")
            body += dsp_node("early_ref", f"Early Reflections\\n{num_taps} taps, {num_diffusers} diffusers")
            body += dsp_node("fdn", f"Late Reverb (FDN)\\ndecay: {decay}\\nsize: {size}")
            body += dsp_node("er_xfade", f"ER/FDN Crossfade\\ner_level: {er_lev}")
            body += dsp_node("stereo_mix", f"Stereo Mix\\nmix: {mix_val}\\ndamp: {damp}")
            body += io_node("output", "Output")

            body += edge("input", "pre_delay")
            body += edge("pre_delay", "early_ref")
            body += edge("early_ref", "fdn")
            body += edge("early_ref", "er_xfade", label="ER path")
            body += edge("fdn", "er_xfade", label="FDN path")
            body += feedback_edge("fdn", "fdn", label="feedback")
            body += edge("er_xfade", "stereo_mix")
            body += edge("stereo_mix", "output")

            return digraph_wrap(algo_name, body)

    def to_c_struct(self) -> str:
        """Return C typedef struct for the room reverb state."""
        return """\
typedef struct {
    // Early Reflections
    float er_delay_buf[512];     // max tap delay + 2
    int er_delay_write_idx;
    int er_tap_delays[8];
    float er_tap_gains[8];
    float er_tap_lpf_coeffs[8];
    float er_tap_lpf_states[8];
    int er_num_taps;
    float er_diffuser_bufs[3][128];
    int er_diffuser_write_idx[3];
    int er_diffuser_delays[3];
    float er_diffuser_feedback;
    int er_num_diffusers;
    float er_output_norm;

    // FDN Core (4-channel Hadamard)
    float fdn_delay_buf_0[1024];
    float fdn_delay_buf_1[1024];
    float fdn_delay_buf_2[1024];
    float fdn_delay_buf_3[1024];
    int fdn_delay_write_idx[4];
    float fdn_damp_coeff;
    float fdn_damp_state[4];
    float fdn_dc_r;
    float fdn_dc_x_prev[4];
    float fdn_dc_y_prev[4];
    float fdn_lfo_phase;
    float fdn_lfo_phase_inc;
    float fdn_mod_depth;
    float fdn_channel_gains[4];
    int fdn_base_delays[4];
    int fdn_current_delays[4];
    float fdn_rt60;

    // Pre-delay line
    float pre_delay_buf[4800];
    int pre_delay_write_idx;
    int pre_delay_samples;

    // Parameters
    float decay;
    float size_scale;
    float damping;
    float er_level;
    float mix;
    float width;

    int sample_rate;
    int frozen;
} RoomReverbState;
"""

    def to_c_process_fn(self) -> str:
        """Return C process function template for room reverb."""
        return """\
void room_reverb_process(RoomReverbState* state, const float* input,
                         float* output_left, float* output_right,
                         int num_samples) {
    float wet1 = (1.0f + state->width) / 2.0f;
    float wet2 = (1.0f - state->width) / 2.0f;
    float er_level = state->er_level;
    float mix_wet = state->mix;
    float mix_dry = 1.0f - mix_wet;

    for (int i = 0; i < num_samples; i++) {
        float x = input[i];
        float dry = x;

        // 1. Pre-delay
        if (state->pre_delay_samples > 0) {
            float delayed = state->pre_delay_buf[
                (state->pre_delay_write_idx - state->pre_delay_samples
                 + 4800) % 4800];
            state->pre_delay_buf[state->pre_delay_write_idx] = x;
            state->pre_delay_write_idx =
                (state->pre_delay_write_idx + 1) % 4800;
            x = delayed;
        }

        // 2. Early Reflections (tapped delay + allpass diffusion)
        float er_l = 0.0f, er_r = 0.0f;
        // ... per-tap read, lowpass, panning, diffusion ...

        float er_mono = (er_l + er_r) * 0.5f;

        // 3. FDN Core processing
        float fdn_inputs[4] = {er_mono, er_mono, er_mono, er_mono};
        float fdn_outputs[4];
        // ... FDN delay read, Hadamard, damping, write back ...

        float fdn_l = fdn_outputs[0] + fdn_outputs[2];
        float fdn_r = fdn_outputs[1] + fdn_outputs[3];

        // 4. ER Level crossfade
        float wet_l = er_level * er_l + (1.0f - er_level) * fdn_l;
        float wet_r = er_level * er_r + (1.0f - er_level) * fdn_r;

        // 5. Width crossmix
        float final_l = wet_l * wet1 + wet_r * wet2;
        float final_r = wet_r * wet1 + wet_l * wet2;

        // 6. Mix and clip
        final_l = dry * mix_dry + final_l * mix_wet;
        final_r = dry * mix_dry + final_r * mix_wet;
        if (final_l > 1.0f) final_l = 1.0f;
        if (final_l < -1.0f) final_l = -1.0f;
        if (final_r > 1.0f) final_r = 1.0f;
        if (final_r < -1.0f) final_r = -1.0f;

        output_left[i] = final_l;
        output_right[i] = final_r;
    }
}
"""
