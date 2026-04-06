"""FDN (Feedback Delay Network) reverb algorithm for claudeverb.

Implements a 4-channel Hadamard FDN with coprime delay lines,
per-channel damping, LFO modulation, and DC blocking.

FDNCore is the composable DSP engine; FDNReverb wraps it as a
ReverbAlgorithm for the UI/registry (implemented in Plan 02).

C struct equivalent:
    typedef struct {
        // 4 delay line buffers (circular, fixed-size)
        float delay_buf_0[MAX_DELAY_0];
        float delay_buf_1[MAX_DELAY_1];
        float delay_buf_2[MAX_DELAY_2];
        float delay_buf_3[MAX_DELAY_3];
        int delay_write_idx[4];
        int delay_max[4];

        // 4 one-pole damping filter states
        float damp_coeff[4];
        float damp_state[4];

        // 4 DC blocker states
        float dc_r;
        float dc_x_prev[4];
        float dc_y_prev[4];

        // LFO state
        float lfo_phase;
        float lfo_phase_inc;
        float mod_depth;

        // Gains and delays
        float channel_gains[4];
        int base_delays[4];
        int current_delays[4];
        float rt60;

        // Config
        int sample_rate;
        int frozen;
    } FDNCore;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.algorithms.filters import AllpassFilter, DelayLine
from claudeverb.algorithms.dattorro_plate import OnePole, DCBlocker


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

BASE_DELAYS = [601, 773, 1009, 1249]  # all prime, coprime, ~12-26ms at 48kHz
SAMPLE_RATE = 48000
MAX_MOD_EXCURSION = 16  # max LFO excursion in samples


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def hadamard_4(a: float, b: float, c: float, d: float) -> tuple[float, float, float, float]:
    """Fast 4-point Walsh-Hadamard Transform (butterfly).

    Two-stage butterfly with 0.5 normalization factor.
    The transform is its own inverse: H(H(x)) = x.

    Returns:
        Tuple of 4 floats after Hadamard mixing.
    """
    # Stage 1: pairs
    s0 = a + b
    s1 = a - b
    s2 = c + d
    s3 = c - d

    # Stage 2: cross-pairs + normalize by 0.5
    r0 = (s0 + s2) * 0.5
    r1 = (s1 + s3) * 0.5
    r2 = (s0 - s2) * 0.5
    r3 = (s1 - s3) * 0.5

    return (r0, r1, r2, r3)


def rt60_to_gain(rt60_seconds: float, delay_samples: int, sample_rate: int = 48000) -> float:
    """Convert RT60 decay time to per-loop feedback gain.

    Formula: 10^(-3 * delay_samples / (rt60_seconds * sample_rate))

    Args:
        rt60_seconds: Desired RT60 in seconds.
        delay_samples: Delay line length in samples.
        sample_rate: Sample rate in Hz.

    Returns:
        Feedback gain clamped to [0.0, 0.9999].
    """
    if rt60_seconds <= 0.0:
        return 0.0
    gain = 10.0 ** (-3.0 * delay_samples / (rt60_seconds * sample_rate))
    return min(gain, 0.9999)


# ---------------------------------------------------------------------------
# FDNCore class
# ---------------------------------------------------------------------------

class FDNCore:
    """Composable 4-channel Hadamard Feedback Delay Network.

    Can be used independently or composed into higher-level algorithms.
    Uses coprime prime delay lengths for maximal echo density.

    Args:
        base_delays: List of 4 delay lengths in samples (default: BASE_DELAYS).
        sample_rate: Sample rate in Hz (default: 48000).
    """

    __slots__ = (
        "_delay_lines", "_damping_filters", "_dc_blockers",
        "_base_delays", "_current_delays", "_channel_gains",
        "_lfo_phase", "_lfo_phase_inc", "_mod_depth",
        "_rt60", "_sample_rate", "_frozen",
    )

    def __init__(self, base_delays: list[int] | None = None, sample_rate: int = 48000) -> None:
        if base_delays is None:
            base_delays = list(BASE_DELAYS)

        self._base_delays = list(base_delays)
        self._current_delays = list(base_delays)
        self._sample_rate = sample_rate

        # Create 4 delay lines with extra room for modulation
        self._delay_lines = [
            DelayLine(d + MAX_MOD_EXCURSION + 2) for d in base_delays
        ]

        # Create 4 one-pole damping filters (default coefficient 0.3)
        self._damping_filters = [OnePole(0.3) for _ in range(4)]

        # Create 4 DC blockers
        self._dc_blockers = [DCBlocker() for _ in range(4)]

        # LFO state
        self._lfo_phase = 0.0
        self._lfo_phase_inc = 2.0 * math.pi * 0.7 / sample_rate  # 0.7 Hz
        self._mod_depth = 0.0  # samples

        # Feedback gains
        self._rt60 = 2.0  # default 2 seconds
        self._channel_gains = [0.0] * 4
        self._frozen = False

        # Compute initial gains
        self._recompute_gains()

    def _recompute_gains(self) -> None:
        """Recompute channel gains from current RT60 and delay lengths."""
        if self._frozen:
            self._channel_gains = [1.0] * 4
        else:
            self._channel_gains = [
                rt60_to_gain(self._rt60, d, self._sample_rate)
                for d in self._current_delays
            ]

    def process_sample(self, inputs: list[float]) -> list[float]:
        """Process one sample through the 4-channel FDN.

        Args:
            inputs: List of 4 input samples, one per channel.

        Returns:
            List of 4 output samples (pre-mixing tap points).
        """
        # Compute LFO value (disabled in freeze mode to preserve energy)
        if self._frozen:
            lfo_val = 0.0
        else:
            lfo_val = math.sin(self._lfo_phase) * self._mod_depth

        # Read from delay lines with LFO modulation
        # Channels 0,2 get +lfo, channels 1,3 get -lfo
        outputs = [0.0] * 4
        for ch in range(4):
            delay = float(self._current_delays[ch])
            if ch in (0, 2):
                delay += lfo_val
            else:
                delay -= lfo_val
            delay = max(1.0, delay)
            outputs[ch] = self._delay_lines[ch].read(delay)

        # Advance LFO phase
        self._lfo_phase += self._lfo_phase_inc
        if self._lfo_phase >= 2.0 * math.pi:
            self._lfo_phase -= 2.0 * math.pi

        # Per-channel processing: damping -> DC blocker -> gain
        # In freeze mode, bypass damping and DC blocking to preserve energy
        processed = [0.0] * 4
        for ch in range(4):
            if self._frozen:
                val = outputs[ch] * self._channel_gains[ch]
            else:
                val = self._damping_filters[ch].process_sample(outputs[ch])
                val = self._dc_blockers[ch].process_sample(val)
                val *= self._channel_gains[ch]
            processed[ch] = val

        # Hadamard butterfly mixing
        mixed = hadamard_4(processed[0], processed[1], processed[2], processed[3])

        # Write back to delay lines: input + mixed feedback
        for ch in range(4):
            self._delay_lines[ch].write(inputs[ch] + mixed[ch])

        # Return PRE-mixing outputs (tap points for stereo output)
        return outputs

    def set_decay(self, rt60_seconds: float) -> None:
        """Set the RT60 decay time in seconds."""
        self._rt60 = rt60_seconds
        self._recompute_gains()

    def set_damping(self, coefficient: float) -> None:
        """Set damping for all channels (0=bright, 1=dark)."""
        for f in self._damping_filters:
            f._coeff = np.float32(coefficient)

    def set_modulation(self, depth: float, rate: float) -> None:
        """Set LFO modulation depth and rate.

        Args:
            depth: Modulation depth in samples (0 to MAX_MOD_EXCURSION).
            rate: LFO rate in Hz.
        """
        self._mod_depth = min(depth, MAX_MOD_EXCURSION)
        self._lfo_phase_inc = 2.0 * math.pi * rate / self._sample_rate

    def set_size(self, scale: float) -> None:
        """Scale delay lengths by a factor.

        Args:
            scale: Scale factor (e.g., 0.5 = half size, 2.0 = double).
        """
        self._current_delays = [
            max(1, int(d * scale)) for d in self._base_delays
        ]
        self._recompute_gains()

    def set_freeze(self, frozen: bool) -> None:
        """Enable or disable freeze mode (infinite sustain)."""
        self._frozen = frozen
        self._recompute_gains()

    def reset(self) -> None:
        """Reset all internal state."""
        for dl in self._delay_lines:
            dl.reset()
        for f in self._damping_filters:
            f.reset()
        for dc in self._dc_blockers:
            dc.reset()
        self._lfo_phase = 0.0
        self._current_delays = list(self._base_delays)
        self._recompute_gains()


# ---------------------------------------------------------------------------
# FDNReverb ReverbAlgorithm wrapper
# ---------------------------------------------------------------------------

class FDNReverb(ReverbAlgorithm):
    """FDN Reverb algorithm (4-channel Hadamard FDN with input diffusion).

    Wraps FDNCore in the standard ReverbAlgorithm interface for the UI/registry.
    Mono input is diffused through 3 cascaded allpass filters, fed into the
    4-channel FDN, and tapped for stereo output with width control.

    6 knobs: decay_time, size, damping, modulation, mix, pre_delay
    2 switches: switch1 (Freeze/Normal/Bright), switch2 (Mono/Stereo/Wide)
    """

    __slots__ = (
        "_fdn_core",
        "_input_diffusers",
        "_pre_delay_line",
        # Parameter state
        "_decay_time", "_size", "_damping", "_modulation",
        "_mix", "_pre_delay",
        "_switch1", "_switch2",
    )

    def __init__(self) -> None:
        self._fdn_core = FDNCore(BASE_DELAYS)
        self._input_diffusers = [
            AllpassFilter(149, feedback=0.5),
            AllpassFilter(233, feedback=0.5),
            AllpassFilter(347, feedback=0.5),
        ]
        self._pre_delay_line = DelayLine(int(0.1 * SAMPLE_RATE))  # up to 100ms

        # Parameter state defaults
        self._decay_time = 50
        self._size = 50
        self._damping = 40
        self._modulation = 30
        self._mix = 75
        self._pre_delay = 0
        self._switch1 = 0   # Normal
        self._switch2 = 0   # Stereo

        self._initialize()

    def _initialize(self) -> None:
        """Apply default parameters to FDNCore."""
        self.update_params({
            "decay_time": self._decay_time,
            "size": self._size,
            "damping": self._damping,
            "modulation": self._modulation,
            "mix": self._mix,
            "pre_delay": self._pre_delay,
            "switch1": self._switch1,
            "switch2": self._switch2,
        })

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        """Process audio -- mono input always produces stereo output."""
        if audio.ndim == 1:
            mono_in = audio
        else:
            # Sum stereo to mono
            mono_in = (audio[0] + audio[1]) * np.float32(0.5)

        n_samples = len(mono_in)
        left_out = np.zeros(n_samples, dtype=np.float32)
        right_out = np.zeros(n_samples, dtype=np.float32)

        # Width crossmix based on stereo mode
        if self._switch2 == -1:    # Mono
            width = 0.0
        elif self._switch2 == 1:   # Wide
            width = 2.0
        else:                      # Stereo
            width = 1.0

        wet1 = (1.0 + width) / 2.0
        wet2 = (1.0 - width) / 2.0

        # Pre-delay samples
        pre_delay_samples = int((self._pre_delay / 100.0) * 0.1 * SAMPLE_RATE)

        # Freeze mode output gain: compensate for FDN delay geometry
        # (stored energy is distributed across delay buffers, so instantaneous
        # output is lower than the perceived level during active decay)
        freeze_active = self._switch1 == -1
        freeze_gain = 4.0 if freeze_active else 1.0

        # Mix: 0-100 -> dry/wet blend (0=fully dry, 100=fully wet)
        mix_wet = self._mix / 100.0
        mix_dry = 1.0 - mix_wet

        for i in range(n_samples):
            dry_sample = float(mono_in[i])
            x = dry_sample

            # Pre-delay
            if pre_delay_samples > 0:
                delayed = self._pre_delay_line.read(pre_delay_samples)
                self._pre_delay_line.write(x)
                x = delayed
            else:
                self._pre_delay_line.write(x)

            # Input diffusion: 3 cascaded allpass filters
            for ap in self._input_diffusers:
                x = ap.process_sample(x)

            # Distribute to 4 FDN channels (equal distribution)
            inputs = [x, x, x, x]

            # FDN core processing
            outputs = self._fdn_core.process_sample(inputs)

            # Stereo tap: L = out[0] + out[2], R = out[1] + out[3]
            raw_l = (outputs[0] + outputs[2]) * freeze_gain
            raw_r = (outputs[1] + outputs[3]) * freeze_gain

            # Width crossmix
            wet_l = raw_l * wet1 + raw_r * wet2
            wet_r = raw_r * wet1 + raw_l * wet2

            # Mix dry/wet
            final_l = dry_sample * mix_dry + wet_l * mix_wet
            final_r = dry_sample * mix_dry + wet_r * mix_wet

            # Hard clip
            final_l = max(-1.0, min(1.0, final_l))
            final_r = max(-1.0, min(1.0, final_r))

            left_out[i] = np.float32(final_l)
            right_out[i] = np.float32(final_r)

        return np.stack([left_out, right_out])

    def update_params(self, params: dict) -> None:
        """Update algorithm parameters from dict.

        Maps 0-100 knob values to internal FDNCore parameters.
        """
        if "decay_time" in params:
            self._decay_time = params["decay_time"]
        if "size" in params:
            self._size = params["size"]
        if "damping" in params:
            self._damping = params["damping"]
        if "modulation" in params:
            self._modulation = params["modulation"]
        if "mix" in params:
            self._mix = params["mix"]
        if "pre_delay" in params:
            self._pre_delay = params["pre_delay"]
        if "switch1" in params:
            self._switch1 = params["switch1"]
        if "switch2" in params:
            self._switch2 = params["switch2"]

        # Switch1 modes -- check freeze first to skip disruptive changes
        if self._switch1 == -1:
            # Freeze mode: infinite sustain, bypass damping/DC/modulation
            # Do NOT change size or decay -- preserve delay line state
            self._fdn_core.set_freeze(True)
            return
        else:
            self._fdn_core.set_freeze(False)

        # Map decay_time 0-100 -> 0.2s to 20.0s RT60 (exponential)
        val = max(self._decay_time, 0)
        rt60 = 0.2 * (100.0 ** (val / 100.0))
        self._fdn_core.set_decay(rt60)

        # Map size 0-100 -> 0.5x to 2.0x delay scale
        size_scale = 0.5 + (self._size / 100.0) * 1.5
        self._fdn_core.set_size(size_scale)

        # Map damping 0-100 -> OnePole coefficient (0=bright/1.0, 100=dark/0.05)
        # OnePole: y = x * coeff + y_prev * (1 - coeff); coeff=1.0 is transparent
        damp_coeff = 1.0 - (self._damping / 100.0) * 0.95

        if self._switch1 == 1:
            # Bright mode: override damping to fully transparent
            damp_coeff = 1.0

        self._fdn_core.set_damping(damp_coeff)

        # Map modulation 0-100 -> 0 to 12 samples depth, rate stays 0.7 Hz
        mod_depth = (self._modulation / 100.0) * 12.0
        self._fdn_core.set_modulation(mod_depth, 0.7)

    def reset(self) -> None:
        """Reset all internal state to initial values."""
        self._fdn_core.reset()
        for ap in self._input_diffusers:
            ap.reset()
        self._pre_delay_line.reset()
        # Re-apply current parameters (reset() reverts delays to base)
        self.update_params({
            "decay_time": self._decay_time,
            "size": self._size,
            "damping": self._damping,
            "modulation": self._modulation,
            "mix": self._mix,
            "pre_delay": self._pre_delay,
            "switch1": self._switch1,
            "switch2": self._switch2,
        })

    @property
    def param_specs(self) -> dict:
        """Parameter specifications for UI/automation."""
        return {
            "decay_time": {
                "type": "knob", "min": 0, "max": 100, "default": 50,
                "label": "Decay Time",
            },
            "size": {
                "type": "knob", "min": 0, "max": 100, "default": 50,
                "label": "Size",
            },
            "damping": {
                "type": "knob", "min": 0, "max": 100, "default": 40,
                "label": "Damping",
            },
            "modulation": {
                "type": "knob", "min": 0, "max": 100, "default": 30,
                "label": "Modulation",
            },
            "mix": {
                "type": "knob", "min": 0, "max": 100, "default": 75,
                "label": "Mix",
            },
            "pre_delay": {
                "type": "knob", "min": 0, "max": 100, "default": 0,
                "label": "Pre-Delay",
            },
            "switch1": {
                "type": "switch", "positions": [-1, 0, 1], "default": 0,
                "label": "Freeze",
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
        """Generate Graphviz DOT string for FDN Reverb signal flow."""
        from claudeverb.export.dot_builder import (
            digraph_wrap, dsp_node, io_node, edge, feedback_edge, subgraph,
        )
        p = params if params else {
            k: v["default"] for k, v in self.param_specs.items()
            if v.get("type") == "knob"
        }
        decay_t = p.get("decay_time", 50)
        size = p.get("size", 50)
        damp = p.get("damping", 40)
        mod = p.get("modulation", 30)
        mix_val = p.get("mix", 75)
        pre_d = p.get("pre_delay", 0)

        if detail_level == "component":
            body = io_node("input", "Input")
            body += dsp_node("pre_delay", f"Pre-Delay\\n[{pre_d}]")
            body += edge("input", "pre_delay")

            # 3 input diffusers
            diff_nodes = ""
            for i, (length, fb) in enumerate([(149, 0.5), (233, 0.5), (347, 0.5)]):
                diff_nodes += dsp_node(f"diff{i}", f"Diffuser {i}\\n[{length} smp]\\nfb: {fb}")
            body += subgraph("diffusers", "Input Diffusion", diff_nodes)

            body += edge("pre_delay", "diff0")
            body += edge("diff0", "diff1")
            body += edge("diff1", "diff2")

            # 4 delay channels
            ch_nodes = ""
            for i, d in enumerate(BASE_DELAYS):
                ch_nodes += dsp_node(f"delay{i}", f"Delay Ch{i}\\n[{d} smp]")
                ch_nodes += dsp_node(f"damp{i}", f"Damping {i}\\n[{damp}]")
                ch_nodes += dsp_node(f"dc{i}", f"DC Block {i}")
            body += subgraph("channels", f"4 FDN Channels (size: {size})", ch_nodes)

            for i in range(4):
                body += edge("diff2", f"delay{i}")
                body += edge(f"delay{i}", f"damp{i}")
                body += edge(f"damp{i}", f"dc{i}")

            body += dsp_node("hadamard", "Hadamard Mix\\n(4x4 butterfly)")
            body += dsp_node("lfo", f"LFO Mod\\n[{mod}]")
            body += dsp_node("stereo_tap", f"Stereo Tap\\nmix: {mix_val}")
            body += io_node("output", "Output")

            for i in range(4):
                body += edge(f"dc{i}", "hadamard")
            body += feedback_edge("hadamard", "delay0", label=f"decay: {decay_t}")
            body += feedback_edge("hadamard", "delay1")
            body += feedback_edge("hadamard", "delay2")
            body += feedback_edge("hadamard", "delay3")
            body += edge("lfo", "delay0", style="dotted", color="blue")
            body += edge("lfo", "delay2", style="dotted", color="blue")

            for i in range(4):
                body += edge(f"delay{i}", "stereo_tap", style="dotted")
            body += edge("stereo_tap", "output")

            return digraph_wrap("FDNReverb", body)
        else:
            # Block level
            body = io_node("input", "Input")
            body += dsp_node("pre_delay", f"Pre-Delay\\n[{pre_d}]")
            body += dsp_node("diffusers", "3 Input Diffusers")
            body += dsp_node("delays", f"4-Ch Delays\\n[{BASE_DELAYS}]\\nsize: {size}")
            body += dsp_node("hadamard", f"Hadamard Mix\\ndecay: {decay_t}")
            body += dsp_node("damping", f"Damping\\n[{damp}]\\nmod: {mod}")
            body += io_node("output", "Output")

            body += edge("input", "pre_delay")
            body += edge("pre_delay", "diffusers")
            body += edge("diffusers", "delays")
            body += edge("delays", "hadamard")
            body += edge("hadamard", "damping")
            body += feedback_edge("damping", "delays", label="feedback")
            body += edge("delays", "output", label="stereo tap")

            return digraph_wrap("FDNReverb", body)

    def to_c_struct(self) -> str:
        """Return C typedef struct for the FDN reverb state."""
        return """\
typedef struct {
    // 4 delay line buffers (circular, fixed-size)
    float delay_buf_0[1265];   // BASE_DELAYS[0] + MAX_MOD_EXCURSION + 2
    float delay_buf_1[1437];   // BASE_DELAYS[1] + MAX_MOD_EXCURSION + 2
    float delay_buf_2[1673];   // BASE_DELAYS[2] + MAX_MOD_EXCURSION + 2
    float delay_buf_3[1913];   // BASE_DELAYS[3] + MAX_MOD_EXCURSION + 2
    int delay_write_idx[4];
    int delay_max[4];

    // 4 one-pole damping filter states
    float damp_coeff;
    float damp_state[4];

    // 4 DC blocker states
    float dc_r;
    float dc_x_prev[4];
    float dc_y_prev[4];

    // LFO state
    float lfo_phase;
    float lfo_phase_inc;
    float mod_depth;

    // Feedback gains and delay lengths
    float channel_gains[4];
    int base_delays[4];
    int current_delays[4];
    float rt60;

    // Input diffusers (3 allpass filters)
    float diffuser_buf_0[149];
    float diffuser_buf_1[233];
    float diffuser_buf_2[347];
    int diffuser_write_idx[3];
    float diffuser_gain;       // 0.5 for all three

    // Pre-delay line
    float pre_delay_buf[4800]; // max 100ms at 48kHz
    int pre_delay_write_idx;
    int pre_delay_samples;

    // Config
    int sample_rate;
    int frozen;
    float width;               // stereo width (0.0=mono, 1.0=stereo, 2.0=wide)
} FDNReverbState;
"""

    def to_c_process_fn(self) -> str:
        """Return C process function template for FDN reverb."""
        return """\
void fdn_reverb_process(FDNReverbState* state, const float* input,
                        float* output_left, float* output_right,
                        int num_samples) {
    float wet1 = (1.0f + state->width) / 2.0f;
    float wet2 = (1.0f - state->width) / 2.0f;

    for (int i = 0; i < num_samples; i++) {
        float x = input[i];

        // 1. Pre-delay (circular buffer read/write)
        float delayed = state->pre_delay_buf[
            (state->pre_delay_write_idx - state->pre_delay_samples
             + 4800) % 4800];
        state->pre_delay_buf[state->pre_delay_write_idx] = x;
        state->pre_delay_write_idx = (state->pre_delay_write_idx + 1) % 4800;
        x = (state->pre_delay_samples > 0) ? delayed : x;

        // 2. Input diffusion (3 cascaded allpass filters)
        for (int d = 0; d < 3; d++) {
            // allpass: v = x + g * delay_out; y = delay_out - g * v
            // write v to delay line
        }

        // 3. FDN core: distribute to 4 channels
        float inputs[4] = {x, x, x, x};

        // 4. Read from delay lines with LFO modulation
        float lfo_val = sinf(state->lfo_phase) * state->mod_depth;
        float outputs[4];
        for (int ch = 0; ch < 4; ch++) {
            float delay = (float)state->current_delays[ch];
            delay += (ch % 2 == 0) ? lfo_val : -lfo_val;
            if (delay < 1.0f) delay = 1.0f;
            // Linear interpolation read from circular buffer
            outputs[ch] = /* delay_line_read(state, ch, delay) */;
        }
        state->lfo_phase += state->lfo_phase_inc;
        if (state->lfo_phase >= 2.0f * M_PI)
            state->lfo_phase -= 2.0f * M_PI;

        // 5. Per-channel: damping -> DC blocker -> gain
        float processed[4];
        for (int ch = 0; ch < 4; ch++) {
            // One-pole LP: y = x * coeff + y_prev * (1 - coeff)
            state->damp_state[ch] = outputs[ch] * state->damp_coeff
                + state->damp_state[ch] * (1.0f - state->damp_coeff);
            float val = state->damp_state[ch];

            // DC blocker: y = x - x_prev + R * y_prev
            float dc_y = val - state->dc_x_prev[ch]
                + state->dc_r * state->dc_y_prev[ch];
            state->dc_x_prev[ch] = val;
            state->dc_y_prev[ch] = dc_y;
            val = dc_y;

            processed[ch] = val * state->channel_gains[ch];
        }

        // 6. Hadamard butterfly mixing
        float s0 = processed[0] + processed[1];
        float s1 = processed[0] - processed[1];
        float s2 = processed[2] + processed[3];
        float s3 = processed[2] - processed[3];
        float mixed[4] = {
            (s0 + s2) * 0.5f,
            (s1 + s3) * 0.5f,
            (s0 - s2) * 0.5f,
            (s1 - s3) * 0.5f
        };

        // 7. Write back: input + mixed feedback
        for (int ch = 0; ch < 4; ch++) {
            // delay_line_write(state, ch, inputs[ch] + mixed[ch]);
        }

        // 8. Stereo tap: L = out[0] + out[2], R = out[1] + out[3]
        float raw_l = outputs[0] + outputs[2];
        float raw_r = outputs[1] + outputs[3];

        // 9. Width crossmix
        float final_l = raw_l * wet1 + raw_r * wet2;
        float final_r = raw_r * wet1 + raw_l * wet2;

        // 10. Hard clip
        if (final_l > 1.0f) final_l = 1.0f;
        if (final_l < -1.0f) final_l = -1.0f;
        if (final_r > 1.0f) final_r = 1.0f;
        if (final_r < -1.0f) final_r = -1.0f;

        output_left[i] = final_l;
        output_right[i] = final_r;
    }
}
"""
