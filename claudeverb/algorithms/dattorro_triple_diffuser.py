"""Dattorro Triple-Diffuser reverb algorithm for claudeverb.

Extends the standard Dattorro figure-eight topology with 6 input allpass
diffusers (vs 4 in the standard plate). The Diffusion Density knob controls
how many input diffusers are active (2-6), providing control over onset
smoothness from clear transients to ultra-smooth pads.

Mono input -> 6 input allpass diffusers (density-controlled) ->
figure-eight tank -> stereo output tapped from multiple points.

C struct equivalent:
    typedef struct {
        AllpassFilter input_diffusers[6];
        AllpassFilter decay_diffusers[4];
        DelayLine tank_delays[4];
        DelayLine pre_delay;
        OnePole damping_filters[2];
        DCBlocker dc_blockers[2];
        float decay, diffusion_density, damping, mod, mix, pre_delay_ms;
        int switch1, switch2;
        float decay_scaled, damping_scaled;
        float mod_depth_scaled;
        int pre_delay_samples;
        float lfo_phase;
        float tank_left_out, tank_right_out;
        float input_ap_coeffs[6];
    } DattorroTripleDiffuser;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.algorithms.filters import AllpassFilter, DelayLine
from claudeverb.algorithms.dattorro_plate import (
    OnePole, DCBlocker,
    DATTORRO_SR,
    DECAY_AP1_LENGTHS, DECAY_AP2_LENGTHS,
    TANK_DELAY1_LENGTHS, TANK_DELAY2_LENGTHS,
    LEFT_TAPS_29761, RIGHT_TAPS_29761,
    MAX_MOD_EXCURSION, OUTPUT_GAIN, SHIMMER_BLEND,
)
from claudeverb.config import SAMPLE_RATE


# ---------------------------------------------------------------------------
# Constants for 6 input diffusers (scaled from 29761 Hz to 48 kHz)
# ---------------------------------------------------------------------------

# 6 input allpass diffuser lengths at 29761 Hz
INPUT_AP_LENGTHS_6 = [142, 107, 379, 277, 191, 331]
# Target coefficients at full activation
INPUT_AP_COEFFS_6 = [0.75, 0.75, 0.625, 0.625, 0.6, 0.6]

# LFO
LFO_RATE_HZ = 1.0
LFO_PHASE_INC = 2.0 * math.pi * LFO_RATE_HZ / SAMPLE_RATE

# Max pre-delay: 100ms
MAX_PRE_DELAY_SAMPLES = int(0.1 * SAMPLE_RATE)


def _scale_length(length_29761: int) -> int:
    """Scale delay length from 29761 Hz to 48 kHz."""
    return round(length_29761 * SAMPLE_RATE / DATTORRO_SR)


# ---------------------------------------------------------------------------
# DattorroTripleDiffuser algorithm
# ---------------------------------------------------------------------------

class DattorroTripleDiffuser(ReverbAlgorithm):
    """Dattorro Triple-Diffuser reverb (6 input allpass + figure-eight tank).

    6 knobs: decay, diffusion_density, damping, mod, mix, pre_delay
    2 switches: switch1 (Freeze/Normal/Shimmer), switch2 (Mono/Stereo/Wide)
    """

    __slots__ = (
        # DSP components
        "_input_diffusers",
        "_decay_diffusers",
        "_tank_delays",
        "_damping_filters",
        "_dc_blockers",
        "_pre_delay_line",
        # Parameters (0-100 knobs)
        "_decay", "_diffusion_density", "_damping", "_mod",
        "_mix", "_pre_delay",
        "_switch1", "_switch2",
        # Scaled internal parameters
        "_decay_scaled", "_damping_scaled",
        "_mod_depth_scaled", "_pre_delay_samples",
        # Active diffuser coefficients (density-controlled)
        "_active_coeffs",
        # Decay diffuser coefficients
        "_decay_diff1_scaled", "_decay_diff2_scaled",
        # LFO state
        "_lfo_phase",
        # Tank cross-feedback state
        "_tank_left_out", "_tank_right_out",
        # Output tap positions (scaled to 48 kHz)
        "_left_taps", "_right_taps",
    )

    def __init__(self) -> None:
        # Default knob values
        self._decay = 60
        self._diffusion_density = 70
        self._damping = 30
        self._mod = 30
        self._mix = 50
        self._pre_delay = 10
        self._switch1 = 0   # Normal
        self._switch2 = 0   # Stereo

        # Scaled values
        self._decay_scaled = 0.0
        self._damping_scaled = 0.0
        self._mod_depth_scaled = 0.0
        self._pre_delay_samples = 0
        self._active_coeffs = list(INPUT_AP_COEFFS_6)
        self._decay_diff1_scaled = 0.0
        self._decay_diff2_scaled = 0.0

        # LFO
        self._lfo_phase = 0.0

        # Cross-feedback
        self._tank_left_out = 0.0
        self._tank_right_out = 0.0

        self._left_taps = []
        self._right_taps = []

        self._initialize()

    def _initialize(self) -> None:
        """Allocate all DSP components."""
        # 6 input allpass diffusers
        self._input_diffusers = [
            AllpassFilter(_scale_length(length), feedback=coeff)
            for length, coeff in zip(INPUT_AP_LENGTHS_6, INPUT_AP_COEFFS_6)
        ]

        # 4 decay allpass diffusers (2 per tank half) -- same as standard plate
        self._decay_diffusers = [
            AllpassFilter(_scale_length(DECAY_AP1_LENGTHS[0])),  # left AP1
            AllpassFilter(_scale_length(DECAY_AP2_LENGTHS[0])),  # left AP2
            AllpassFilter(_scale_length(DECAY_AP1_LENGTHS[1])),  # right AP1
            AllpassFilter(_scale_length(DECAY_AP2_LENGTHS[1])),  # right AP2
        ]

        # 4 tank delay lines (with extra room for modulation)
        max_excursion = MAX_MOD_EXCURSION + 2
        self._tank_delays = [
            DelayLine(_scale_length(TANK_DELAY1_LENGTHS[0]) + max_excursion),
            DelayLine(_scale_length(TANK_DELAY2_LENGTHS[0])),
            DelayLine(_scale_length(TANK_DELAY1_LENGTHS[1]) + max_excursion),
            DelayLine(_scale_length(TANK_DELAY2_LENGTHS[1])),
        ]

        # Damping filters (one per half)
        self._damping_filters = [OnePole(0.5), OnePole(0.5)]

        # DC blockers (one per half)
        self._dc_blockers = [DCBlocker(), DCBlocker()]

        # Pre-delay line
        self._pre_delay_line = DelayLine(MAX_PRE_DELAY_SAMPLES + 4)

        # Pre-compute output tap positions scaled to 48 kHz
        self._left_taps = [
            (name, _scale_length(pos), sign)
            for name, pos, sign in LEFT_TAPS_29761
        ]
        self._right_taps = [
            (name, _scale_length(pos), sign)
            for name, pos, sign in RIGHT_TAPS_29761
        ]

        self._scale_params()

    def _scale_params(self) -> None:
        """Convert 0-100 knob values to internal parameters."""
        # Decay: 0-100 -> 0.1 to 0.9999 (exponential feel)
        self._decay_scaled = 0.1 + (self._decay / 100.0) ** 1.5 * 0.8999

        # Damping: 0-100 -> 0.0 to 0.9
        self._damping_scaled = (self._damping / 100.0) * 0.9

        # Mod Depth: 0-100 -> 0.0 to 16.0 samples excursion
        self._mod_depth_scaled = (self._mod / 100.0) * MAX_MOD_EXCURSION

        # Pre-delay: 0-100 -> 0 to 100ms
        self._pre_delay_samples = int((self._pre_delay / 100.0) * MAX_PRE_DELAY_SAMPLES)

        # Diffusion Density: 0-100 -> 2.0 to 6.0 active diffusers
        active_count = 2.0 + (self._diffusion_density / 100.0) * 4.0
        # Compute per-diffuser coefficients with crossfade
        self._active_coeffs = []
        for idx in range(6):
            target = INPUT_AP_COEFFS_6[idx]
            if idx < int(active_count):
                # Fully active
                self._active_coeffs.append(target)
            elif idx == int(active_count):
                # Crossfade: fractional part controls this diffuser
                frac = active_count - int(active_count)
                self._active_coeffs.append(target * frac)
            else:
                # Inactive: passthrough (coefficient = 0)
                self._active_coeffs.append(0.0)

        # Apply to input diffusers
        for i, coeff in enumerate(self._active_coeffs):
            self._input_diffusers[i].feedback = coeff

        # Decay diffuser coefficients (fixed, similar to plate)
        self._decay_diff1_scaled = 0.7
        self._decay_diff2_scaled = 0.5
        self._decay_diffusers[0].feedback = -self._decay_diff1_scaled
        self._decay_diffusers[2].feedback = -self._decay_diff1_scaled
        self._decay_diffusers[1].feedback = self._decay_diff2_scaled
        self._decay_diffusers[3].feedback = self._decay_diff2_scaled

        # Update damping filter coefficients
        damp_coeff = 1.0 - self._damping_scaled
        for f in self._damping_filters:
            f._coeff = np.float32(damp_coeff)

    def _get_tap_value(self, name: str, tap_pos: int) -> float:
        """Read a tap from the named delay element."""
        if name == "tank_delay1_L":
            return self._tank_delays[0].read(tap_pos)
        elif name == "tank_delay2_L":
            return self._tank_delays[1].read(tap_pos)
        elif name == "tank_delay1_R":
            return self._tank_delays[2].read(tap_pos)
        elif name == "tank_delay2_R":
            return self._tank_delays[3].read(tap_pos)
        elif name == "decay_ap2_L":
            return self._decay_diffusers[1]._delay.read(tap_pos)
        elif name == "decay_ap2_R":
            return self._decay_diffusers[3]._delay.read(tap_pos)
        return 0.0

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        """Process audio -- mono input always produces stereo output."""
        if audio.ndim == 1:
            mono_in = audio
        else:
            mono_in = (audio[0] + audio[1]) * np.float32(0.5)

        n_samples = len(mono_in)
        left_out = np.zeros(n_samples, dtype=np.float32)
        right_out = np.zeros(n_samples, dtype=np.float32)

        # Cache state
        freeze = self._switch1 == -1
        shimmer = self._switch1 == 1
        mono_mode = self._switch2 == -1
        wide_mode = self._switch2 == 1

        decay = self._decay_scaled
        if freeze:
            decay = 1.0

        mod_depth = self._mod_depth_scaled if not freeze else 0.0

        # Base delay lengths (scaled to 48 kHz)
        base_delay1_L = _scale_length(TANK_DELAY1_LENGTHS[0])
        base_delay1_R = _scale_length(TANK_DELAY1_LENGTHS[1])
        base_delay2_L = _scale_length(TANK_DELAY2_LENGTHS[0])
        base_delay2_R = _scale_length(TANK_DELAY2_LENGTHS[1])

        # Width crossmix
        width = 1.0
        if wide_mode:
            width = 2.0
        wet1 = (1.0 + width) / 2.0
        wet2 = (1.0 - width) / 2.0

        # Mix
        mix_wet = self._mix / 100.0
        mix_dry = 1.0 - mix_wet

        # Freeze output gain
        freeze_gain = 2.0 if freeze else 1.0

        # Cache DSP objects
        input_diffs = self._input_diffusers
        pre_delay = self._pre_delay_line
        pre_delay_samples = self._pre_delay_samples

        for i in range(n_samples):
            dry_sample = float(mono_in[i])
            x = dry_sample

            # In freeze mode, zero input gain
            if freeze:
                x = 0.0

            # Pre-delay
            if pre_delay_samples > 0:
                delayed = pre_delay.read(pre_delay_samples)
                pre_delay.write(x)
                x = delayed
            else:
                pre_delay.write(x)

            # 6 input allpass diffusers (cascaded, density-controlled via coefficients)
            for ap in input_diffs:
                x = ap.process_sample(x)

            tank_input = x

            # --- LFO ---
            lfo_left = math.sin(self._lfo_phase) * mod_depth
            lfo_right = math.sin(self._lfo_phase + math.pi) * mod_depth
            self._lfo_phase += LFO_PHASE_INC
            if self._lfo_phase >= 2.0 * math.pi:
                self._lfo_phase -= 2.0 * math.pi

            # ====== LEFT TANK HALF ======
            left_in = tank_input + decay * self._tank_right_out

            # Decay diffusion AP1 (negative feedback)
            left_in = self._decay_diffusers[0].process_sample(left_in)

            # Modulated delay line 1 (left)
            self._tank_delays[0].write(left_in)
            read_delay_L = base_delay1_L + lfo_left
            read_delay_L = max(1.0, read_delay_L)
            tank1_L_out = self._tank_delays[0].read(read_delay_L)

            # Shimmer
            if shimmer:
                half_delay = max(1.0, read_delay_L * 0.5)
                octave_up = self._tank_delays[0].read(half_delay)
                tank1_L_out = tank1_L_out + SHIMMER_BLEND * octave_up

            # Damping filter
            if not freeze:
                tank1_L_out = self._damping_filters[0].process_sample(tank1_L_out)

            # Apply decay
            tank1_L_out *= decay

            # Decay diffusion AP2
            tank1_L_out = self._decay_diffusers[1].process_sample(tank1_L_out)

            # Delay line 2 (left)
            self._tank_delays[1].write(tank1_L_out)
            tank2_L_out = self._tank_delays[1].read(base_delay2_L)

            # DC blocker
            if not freeze:
                tank2_L_out = self._dc_blockers[0].process_sample(tank2_L_out)

            self._tank_left_out = tank2_L_out

            # ====== RIGHT TANK HALF ======
            right_in = tank_input + decay * self._tank_left_out

            # Decay diffusion AP1 (negative feedback)
            right_in = self._decay_diffusers[2].process_sample(right_in)

            # Modulated delay line 1 (right)
            self._tank_delays[2].write(right_in)
            read_delay_R = base_delay1_R + lfo_right
            read_delay_R = max(1.0, read_delay_R)
            tank1_R_out = self._tank_delays[2].read(read_delay_R)

            # Shimmer
            if shimmer:
                half_delay = max(1.0, read_delay_R * 0.5)
                octave_up = self._tank_delays[2].read(half_delay)
                tank1_R_out = tank1_R_out + SHIMMER_BLEND * octave_up

            # Damping filter
            if not freeze:
                tank1_R_out = self._damping_filters[1].process_sample(tank1_R_out)

            # Apply decay
            tank1_R_out *= decay

            # Decay diffusion AP2
            tank1_R_out = self._decay_diffusers[3].process_sample(tank1_R_out)

            # Delay line 2 (right)
            self._tank_delays[3].write(tank1_R_out)
            tank2_R_out = self._tank_delays[3].read(base_delay2_R)

            # DC blocker
            if not freeze:
                tank2_R_out = self._dc_blockers[1].process_sample(tank2_R_out)

            self._tank_right_out = tank2_R_out

            # ====== OUTPUT TAPS ======
            out_l = 0.0
            for name, tap_pos, sign in self._left_taps:
                out_l += sign * self._get_tap_value(name, tap_pos)

            out_r = 0.0
            for name, tap_pos, sign in self._right_taps:
                out_r += sign * self._get_tap_value(name, tap_pos)

            out_l *= OUTPUT_GAIN * freeze_gain
            out_r *= OUTPUT_GAIN * freeze_gain

            # Width crossmix
            final_l = out_l * wet1 + out_r * wet2
            final_r = out_r * wet1 + out_l * wet2

            # Mix dry/wet
            final_l = dry_sample * mix_dry + final_l * mix_wet
            final_r = dry_sample * mix_dry + final_r * mix_wet

            left_out[i] = np.float32(final_l)
            right_out[i] = np.float32(final_r)

        # Mono mode
        if mono_mode:
            right_out[:] = left_out

        # Hard clip
        np.clip(left_out, -1.0, 1.0, out=left_out)
        np.clip(right_out, -1.0, 1.0, out=right_out)

        return np.stack([left_out, right_out])

    def update_params(self, params: dict) -> None:
        """Update algorithm parameters from dict."""
        if "decay" in params:
            self._decay = params["decay"]
        if "diffusion_density" in params:
            self._diffusion_density = params["diffusion_density"]
        if "damping" in params:
            self._damping = params["damping"]
        if "mod" in params:
            self._mod = params["mod"]
        if "mix" in params:
            self._mix = params["mix"]
        if "pre_delay" in params:
            self._pre_delay = params["pre_delay"]
        if "switch1" in params:
            self._switch1 = params["switch1"]
        if "switch2" in params:
            self._switch2 = params["switch2"]
        self._scale_params()

    def reset(self) -> None:
        """Reset all internal state to initial values."""
        for ap in self._input_diffusers:
            ap.reset()
        for ap in self._decay_diffusers:
            ap.reset()
        for dl in self._tank_delays:
            dl.reset()
        for f in self._damping_filters:
            f.reset()
        for dc in self._dc_blockers:
            dc.reset()
        self._pre_delay_line.reset()
        self._lfo_phase = 0.0
        self._tank_left_out = 0.0
        self._tank_right_out = 0.0
        self._scale_params()

    @property
    def param_specs(self) -> dict:
        """Parameter specifications for UI/automation."""
        return {
            "decay": {
                "type": "knob", "min": 0, "max": 100, "default": 60,
                "label": "Decay",
            },
            "diffusion_density": {
                "type": "knob", "min": 0, "max": 100, "default": 70,
                "label": "Diffusion Density",
            },
            "damping": {
                "type": "knob", "min": 0, "max": 100, "default": 30,
                "label": "Damping",
            },
            "mod": {
                "type": "knob", "min": 0, "max": 100, "default": 30,
                "label": "Mod",
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
                "labels": ["Freeze", "Normal", "Shimmer"],
            },
            "switch2": {
                "type": "switch", "positions": [-1, 0, 1], "default": 0,
                "label": "Stereo Mode",
                "labels": ["Mono", "Stereo", "Wide"],
            },
        }

    def to_c_struct(self) -> str:
        """Return C typedef struct for the Triple-Diffuser state."""
        input_ap_sizes = [_scale_length(l) for l in INPUT_AP_LENGTHS_6]
        decay_ap1_sizes = [_scale_length(l) for l in DECAY_AP1_LENGTHS]
        decay_ap2_sizes = [_scale_length(l) for l in DECAY_AP2_LENGTHS]
        tank_d1_sizes = [_scale_length(l) + MAX_MOD_EXCURSION + 2 for l in TANK_DELAY1_LENGTHS]
        tank_d2_sizes = [_scale_length(l) for l in TANK_DELAY2_LENGTHS]

        return f"""\
typedef struct {{
    // 6 input diffusion allpass buffers
    float input_ap_buf_0[{input_ap_sizes[0]}];
    float input_ap_buf_1[{input_ap_sizes[1]}];
    float input_ap_buf_2[{input_ap_sizes[2]}];
    float input_ap_buf_3[{input_ap_sizes[3]}];
    float input_ap_buf_4[{input_ap_sizes[4]}];
    float input_ap_buf_5[{input_ap_sizes[5]}];
    int input_ap_write_idx[6];
    float input_ap_coeffs[6];

    // 4 decay diffusion allpass buffers
    float decay_ap1_L_buf[{decay_ap1_sizes[0]}];
    float decay_ap2_L_buf[{decay_ap2_sizes[0]}];
    float decay_ap1_R_buf[{decay_ap1_sizes[1]}];
    float decay_ap2_R_buf[{decay_ap2_sizes[1]}];
    int decay_ap_write_idx[4];

    // 4 tank delay buffers
    float tank_d1_L_buf[{tank_d1_sizes[0]}];
    float tank_d2_L_buf[{tank_d2_sizes[0]}];
    float tank_d1_R_buf[{tank_d1_sizes[1]}];
    float tank_d2_R_buf[{tank_d2_sizes[1]}];
    int tank_d_write_idx[4];

    // 2 one-pole damping filter states
    float damp_coeff;
    float damp_state[2];

    // 2 DC blocker states
    float dc_r;
    float dc_x_prev[2];
    float dc_y_prev[2];

    // LFO state
    float lfo_phase;
    float mod_depth;

    // Tank cross-feedback
    float tank_left_out;
    float tank_right_out;

    // Pre-delay line
    float pre_delay_buf[{MAX_PRE_DELAY_SAMPLES + 4}];
    int pre_delay_write_idx;
    int pre_delay_samples;

    // Config
    float decay;
    float diffusion_density;
    int sample_rate;
    int frozen;
    int shimmer;
    float width;
    float mix;
}} DattorroTripleDiffuserState;
"""

    def to_c_process_fn(self) -> str:
        """Return C process function template for Triple-Diffuser."""
        return """\
void dattorro_triple_diffuser_process(DattorroTripleDiffuserState* state,
                                      const float* input,
                                      float* output_left, float* output_right,
                                      int num_samples) {
    float wet1 = (1.0f + state->width) / 2.0f;
    float wet2 = (1.0f - state->width) / 2.0f;
    float mix_wet = state->mix / 100.0f;
    float mix_dry = 1.0f - mix_wet;
    float freeze_gain = state->frozen ? 2.0f : 1.0f;
    float decay = state->frozen ? 1.0f : state->decay;

    for (int i = 0; i < num_samples; i++) {
        float dry = input[i];
        float x = state->frozen ? 0.0f : dry;

        // 1. Pre-delay (circular buffer read then write)
        // ...

        // 2. Input diffusion (6 cascaded allpass with density control)
        for (int d = 0; d < 6; d++) {
            float coeff = state->input_ap_coeffs[d];
            // allpass: v = x + coeff * buf[read]; y = buf[read] - coeff * v; buf[write] = v
        }
        float tank_input = x;

        // 3. LFO
        float lfo_left = sinf(state->lfo_phase) * state->mod_depth;
        float lfo_right = sinf(state->lfo_phase + M_PI) * state->mod_depth;
        state->lfo_phase += 2.0f * M_PI * 1.0f / state->sample_rate;
        if (state->lfo_phase >= 2.0f * M_PI)
            state->lfo_phase -= 2.0f * M_PI;

        // 4. Left tank half: AP1 -> D1(mod) -> damp -> decay -> AP2 -> D2 -> DC
        // 5. Right tank half: same structure, cross-fed
        // 6. Output taps (7 per channel, same as standard plate)
        // 7. Width crossmix + dry/wet mix + clip

        output_left[i] = /* final_l */;
        output_right[i] = /* final_r */;
    }
}
"""
