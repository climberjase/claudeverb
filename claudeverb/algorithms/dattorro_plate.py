"""Dattorro Plate reverb algorithm for claudeverb.

Implements Jon Dattorro's 1997 JAES paper "Effect Design Part 1:
Reverberator and Other Filters" figure-eight tank topology.

Mono input -> 4 input allpass diffusers -> figure-eight tank with
2 crossed delay paths -> stereo output tapped from multiple points.

All delay lengths rescaled from the paper's 29761 Hz to 48 kHz.

C struct equivalent:
    typedef struct {
        AllpassFilter input_diffusers[4];
        AllpassFilter decay_diffusers[4];
        DelayLine tank_delays[4];
        DelayLine pre_delay;
        OnePole bandwidth_filter;
        OnePole damping_filters[2];
        DCBlocker dc_blockers[2];
        float decay, bandwidth, tank_damping, diffusion;
        float pre_delay_ms, mod_depth;
        int switch1, switch2;
        // Scaled internal parameters
        float decay_scaled, bandwidth_scaled, damping_scaled;
        float input_diff1_scaled, input_diff2_scaled;
        float decay_diff1_scaled, decay_diff2_scaled;
        float mod_depth_scaled;
        int pre_delay_samples;
        float lfo_phase;
        float tank_left_out, tank_right_out;
    } DattorroPlate;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.algorithms.filters import AllpassFilter, DelayLine
from claudeverb.config import SAMPLE_RATE


# ---------------------------------------------------------------------------
# Helper DSP classes (C-portable, __slots__)
# ---------------------------------------------------------------------------

class OnePole:
    """Simple one-pole lowpass for bandwidth/damping filters.

    y[n] = x[n] * coeff + y[n-1] * (1 - coeff)
    """

    __slots__ = ("_coeff", "_state")

    def __init__(self, coeff: float = 0.9995) -> None:
        self._coeff = np.float32(coeff)
        self._state = np.float32(0.0)

    def process_sample(self, x: float) -> float:
        self._state = np.float32(
            x * self._coeff + float(self._state) * (1.0 - float(self._coeff))
        )
        return float(self._state)

    def reset(self) -> None:
        self._state = np.float32(0.0)


class DCBlocker:
    """First-order DC blocking filter (~5 Hz highpass).

    y[n] = x[n] - x[n-1] + R * y[n-1], R ~= 0.99935 at 48 kHz
    """

    __slots__ = ("_r", "_x_prev", "_y_prev")

    def __init__(self, r: float = 0.99935) -> None:
        self._r = np.float32(r)
        self._x_prev = np.float32(0.0)
        self._y_prev = np.float32(0.0)

    def process_sample(self, x: float) -> float:
        y = x - float(self._x_prev) + float(self._r) * float(self._y_prev)
        self._x_prev = np.float32(x)
        self._y_prev = np.float32(y)
        return float(y)

    def reset(self) -> None:
        self._x_prev = np.float32(0.0)
        self._y_prev = np.float32(0.0)


# ---------------------------------------------------------------------------
# Constants from Dattorro 1997 paper
# ---------------------------------------------------------------------------

DATTORRO_SR = 29761

# Input allpass diffuser lengths at 29761 Hz
INPUT_AP_LENGTHS = [142, 107, 379, 277]
INPUT_AP_COEFFS = [0.75, 0.75, 0.625, 0.625]

# Tank elements at 29761 Hz [left_half, right_half]
DECAY_AP1_LENGTHS = [672, 908]
TANK_DELAY1_LENGTHS = [4453, 4217]  # modulated by LFO
DECAY_AP2_LENGTHS = [1800, 2656]
TANK_DELAY2_LENGTHS = [3720, 3163]

# Output tap positions at 29761 Hz (from paper Table 2)
# Left output taps: (delay_element_index, tap_position, sign)
# delay_element indices: 0=tank_delay1_L, 1=tank_delay2_L,
#                        2=tank_delay1_R, 3=tank_delay2_R
# decay_ap indices: 0=decay_ap2_L, 1=decay_ap2_R (accessed via delay line)
LEFT_TAPS_29761 = [
    ("tank_delay1_R", 266, +1),
    ("tank_delay1_R", 2974, +1),
    ("decay_ap2_R", 1913, -1),
    ("tank_delay2_R", 1996, +1),
    ("tank_delay1_L", 1990, -1),
    ("decay_ap2_L", 187, -1),
    ("tank_delay2_L", 1066, -1),
]

RIGHT_TAPS_29761 = [
    ("tank_delay1_L", 353, +1),
    ("tank_delay1_L", 3627, +1),
    ("decay_ap2_L", 1228, -1),
    ("tank_delay2_L", 2673, +1),
    ("tank_delay1_R", 2111, -1),
    ("decay_ap2_R", 335, -1),
    ("tank_delay2_R", 121, -1),
]

# LFO
LFO_RATE_HZ = 1.0
LFO_PHASE_INC = 2.0 * math.pi * LFO_RATE_HZ / SAMPLE_RATE

# Max mod excursion in samples (at knob=100)
MAX_MOD_EXCURSION = 16

# Shimmer blend (15%)
SHIMMER_BLEND = 0.2

# Output gain scaling
OUTPUT_GAIN = 1.5


# ---------------------------------------------------------------------------
# DattorroPlate algorithm
# ---------------------------------------------------------------------------

class DattorroPlate(ReverbAlgorithm):
    """Dattorro Plate reverb (1997 paper figure-eight tank topology).

    6 knobs: decay, bandwidth, tank_damping, diffusion, pre_delay, mod_depth
    2 switches: switch1 (Freeze/Normal/Shimmer), switch2 (Mono/Stereo/Wide)
    """

    __slots__ = (
        # DSP components
        "_input_diffusers",
        "_decay_diffusers",
        "_tank_delays",
        "_damping_filters",
        "_bandwidth_filter",
        "_dc_blockers",
        "_pre_delay_line",
        # Parameters (0-100 knobs)
        "_decay", "_bandwidth", "_tank_damping",
        "_diffusion", "_pre_delay", "_mod_depth",
        "_switch1", "_switch2",
        # Scaled internal parameters
        "_decay_scaled", "_bandwidth_scaled", "_damping_scaled",
        "_input_diff1_scaled", "_input_diff2_scaled",
        "_decay_diff1_scaled", "_decay_diff2_scaled",
        "_mod_depth_scaled", "_pre_delay_samples",
        # LFO state
        "_lfo_phase",
        # Shimmer read pointers (advance at half rate for octave-up)
        "_shimmer_phase_L", "_shimmer_phase_R",
        # Tank cross-feedback state
        "_tank_left_out", "_tank_right_out",
        # Output tap positions (scaled to 48 kHz)
        "_left_taps", "_right_taps",
    )

    def __init__(self) -> None:
        # Default knob values
        self._decay = 60
        self._bandwidth = 70
        self._tank_damping = 30
        self._diffusion = 80
        self._pre_delay = 10
        self._mod_depth = 30
        self._switch1 = 0   # Normal
        self._switch2 = 0   # Stereo

        # Init scaled values
        self._decay_scaled = 0.0
        self._bandwidth_scaled = 0.0
        self._damping_scaled = 0.0
        self._input_diff1_scaled = 0.0
        self._input_diff2_scaled = 0.0
        self._decay_diff1_scaled = 0.0
        self._decay_diff2_scaled = 0.0
        self._mod_depth_scaled = 0.0
        self._pre_delay_samples = 0

        # LFO
        self._lfo_phase = 0.0

        # Shimmer read pointers
        self._shimmer_phase_L = 0.0
        self._shimmer_phase_R = 0.0

        # Cross-feedback
        self._tank_left_out = 0.0
        self._tank_right_out = 0.0

        self._initialize()

    @staticmethod
    def _scale_length(length_29761: int) -> int:
        """Scale delay length from 29761 Hz to 48 kHz."""
        return round(length_29761 * SAMPLE_RATE / DATTORRO_SR)

    def _initialize(self) -> None:
        """Allocate all DSP components."""
        # 4 input allpass diffusers
        self._input_diffusers = [
            AllpassFilter(self._scale_length(length), feedback=coeff)
            for length, coeff in zip(INPUT_AP_LENGTHS, INPUT_AP_COEFFS)
        ]

        # 4 decay allpass diffusers (2 per tank half)
        # AP1 uses negative feedback (decay_diff1), AP2 uses positive (decay_diff2)
        self._decay_diffusers = [
            AllpassFilter(self._scale_length(DECAY_AP1_LENGTHS[0])),  # left AP1
            AllpassFilter(self._scale_length(DECAY_AP2_LENGTHS[0])),  # left AP2
            AllpassFilter(self._scale_length(DECAY_AP1_LENGTHS[1])),  # right AP1
            AllpassFilter(self._scale_length(DECAY_AP2_LENGTHS[1])),  # right AP2
        ]

        # 4 tank delay lines (with extra room for modulation on delay1s)
        max_excursion = MAX_MOD_EXCURSION + 2  # safety margin
        self._tank_delays = [
            DelayLine(self._scale_length(TANK_DELAY1_LENGTHS[0]) + max_excursion),  # left delay1 (modulated)
            DelayLine(self._scale_length(TANK_DELAY2_LENGTHS[0])),                   # left delay2
            DelayLine(self._scale_length(TANK_DELAY1_LENGTHS[1]) + max_excursion),  # right delay1 (modulated)
            DelayLine(self._scale_length(TANK_DELAY2_LENGTHS[1])),                   # right delay2
        ]

        # Bandwidth filter (one-pole LP on input)
        self._bandwidth_filter = OnePole(0.9995)

        # Damping filters (one-pole LP in tank loop, one per half)
        self._damping_filters = [OnePole(0.5), OnePole(0.5)]

        # DC blockers (one per tank half)
        self._dc_blockers = [DCBlocker(), DCBlocker()]

        # Pre-delay line (max 100ms at 48 kHz)
        max_pre_delay = math.ceil(0.1 * SAMPLE_RATE)
        self._pre_delay_line = DelayLine(max_pre_delay)

        # Pre-compute output tap positions scaled to 48 kHz
        self._left_taps = [
            (name, self._scale_length(pos), sign)
            for name, pos, sign in LEFT_TAPS_29761
        ]
        self._right_taps = [
            (name, self._scale_length(pos), sign)
            for name, pos, sign in RIGHT_TAPS_29761
        ]

        self._scale_params()

    def _scale_params(self) -> None:
        """Convert 0-100 integer knob values to internal float ranges."""
        # Decay: 0-100 -> 0.1 to 0.9999 (exponential feel)
        self._decay_scaled = 0.1 + (self._decay / 100.0) ** 1.5 * 0.8999

        # Bandwidth: 0-100 -> 0.1 to 0.9999
        self._bandwidth_scaled = 0.1 + (self._bandwidth / 100.0) * 0.8999

        # Tank Damping: 0-100 -> 0.0 to 0.9
        self._damping_scaled = (self._tank_damping / 100.0) * 0.9

        # Diffusion: 0-100 -> scales both input and decay diffusion
        diff_scale = self._diffusion / 100.0
        self._input_diff1_scaled = diff_scale * 0.75
        self._input_diff2_scaled = diff_scale * 0.625
        self._decay_diff1_scaled = diff_scale * 0.7
        self._decay_diff2_scaled = diff_scale * 0.5

        # Pre-delay: 0-100 -> 0 to 4800 samples (0 to 100ms)
        self._pre_delay_samples = int((self._pre_delay / 100.0) * 0.1 * SAMPLE_RATE)

        # Mod Depth: 0-100 -> 0.0 to 16.0 samples excursion
        self._mod_depth_scaled = (self._mod_depth / 100.0) * MAX_MOD_EXCURSION

        # Apply diffusion coefficients to allpass filters
        # Input diffusers: first 2 use input_diff1, last 2 use input_diff2
        for i in range(4):
            if i < 2:
                self._input_diffusers[i].feedback = self._input_diff1_scaled
            else:
                self._input_diffusers[i].feedback = self._input_diff2_scaled

        # Decay diffusers: AP1 (indices 0, 2) use negative decay_diff1
        # AP2 (indices 1, 3) use positive decay_diff2
        self._decay_diffusers[0].feedback = -self._decay_diff1_scaled
        self._decay_diffusers[2].feedback = -self._decay_diff1_scaled
        self._decay_diffusers[1].feedback = self._decay_diff2_scaled
        self._decay_diffusers[3].feedback = self._decay_diff2_scaled

        # Update bandwidth filter coefficient
        self._bandwidth_filter._coeff = np.float32(self._bandwidth_scaled)

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
            # Sum stereo to mono
            mono_in = (audio[0] + audio[1]) * np.float32(0.5)

        n_samples = len(mono_in)
        left_out = np.zeros(n_samples, dtype=np.float32)
        right_out = np.zeros(n_samples, dtype=np.float32)

        # Cache frequently used values
        freeze = self._switch1 == -1
        shimmer = self._switch1 == 1
        mono_mode = self._switch2 == -1
        wide_mode = self._switch2 == 1

        decay = self._decay_scaled
        if freeze:
            decay = 1.0

        mod_depth = self._mod_depth_scaled

        # Base delay lengths (scaled to 48 kHz)
        base_delay1_L = self._scale_length(TANK_DELAY1_LENGTHS[0])
        base_delay1_R = self._scale_length(TANK_DELAY1_LENGTHS[1])
        base_delay2_L = self._scale_length(TANK_DELAY2_LENGTHS[0])
        base_delay2_R = self._scale_length(TANK_DELAY2_LENGTHS[1])

        # Width crossmix (same pattern as Freeverb)
        # Stereo: width=1.0 -> wet1=1.0, wet2=0.0 (full L/R separation)
        # Wide: width=2.0 -> wet1=1.5, wet2=-0.5 (exaggerated separation)
        width = 1.0
        if wide_mode:
            width = 2.0

        wet1 = (1.0 + width) / 2.0
        wet2 = (1.0 - width) / 2.0

        for i in range(n_samples):
            x = float(mono_in[i])

            # In freeze mode, zero input gain
            if freeze:
                x = 0.0

            # Pre-delay
            if self._pre_delay_samples > 0:
                delayed = self._pre_delay_line.read(self._pre_delay_samples)
                self._pre_delay_line.write(x)
                x = delayed
            else:
                self._pre_delay_line.write(x)

            # Bandwidth filter (input LP)
            x = self._bandwidth_filter.process_sample(x)

            # 4 input allpass diffusers (cascaded)
            for ap in self._input_diffusers:
                x = ap.process_sample(x)

            tank_input = x

            # --- LFO ---
            lfo_left = math.sin(self._lfo_phase) * mod_depth
            lfo_right = math.sin(self._lfo_phase + math.pi) * mod_depth
            self._lfo_phase += LFO_PHASE_INC
            if self._lfo_phase >= 2.0 * math.pi:
                self._lfo_phase -= 2.0 * math.pi

            # ====== LEFT TANK HALF ======
            # Input: tank_input + decay * cross_feedback_from_right
            left_in = tank_input + decay * self._tank_right_out

            # Decay diffusion AP1 (negative feedback)
            left_in = self._decay_diffusers[0].process_sample(left_in)

            # Modulated delay line 1 (left)
            self._tank_delays[0].write(left_in)
            read_delay_L = base_delay1_L + lfo_left
            read_delay_L = max(1.0, read_delay_L)  # safety clamp
            tank1_L_out = self._tank_delays[0].read(read_delay_L)

            # Shimmer: add octave-up via half-delay read
            if shimmer:
                half_delay = max(1.0, read_delay_L * 0.5)
                octave_up = self._tank_delays[0].read(half_delay)
                tank1_L_out = tank1_L_out + SHIMMER_BLEND * octave_up

            # Damping filter
            tank1_L_out = self._damping_filters[0].process_sample(tank1_L_out)

            # Apply decay
            tank1_L_out *= decay

            # Decay diffusion AP2
            tank1_L_out = self._decay_diffusers[1].process_sample(tank1_L_out)

            # Delay line 2 (left)
            self._tank_delays[1].write(tank1_L_out)
            tank2_L_out = self._tank_delays[1].read(base_delay2_L)

            # DC blocker
            tank2_L_out = self._dc_blockers[0].process_sample(tank2_L_out)

            # Store cross-feedback for right half
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

            # Shimmer: add octave-up via half-delay read
            if shimmer:
                half_delay = max(1.0, read_delay_R * 0.5)
                octave_up = self._tank_delays[2].read(half_delay)
                tank1_R_out = tank1_R_out + SHIMMER_BLEND * octave_up

            # Damping filter
            tank1_R_out = self._damping_filters[1].process_sample(tank1_R_out)

            # Apply decay
            tank1_R_out *= decay

            # Decay diffusion AP2
            tank1_R_out = self._decay_diffusers[3].process_sample(tank1_R_out)

            # Delay line 2 (right)
            self._tank_delays[3].write(tank1_R_out)
            tank2_R_out = self._tank_delays[3].read(base_delay2_R)

            # DC blocker
            tank2_R_out = self._dc_blockers[1].process_sample(tank2_R_out)

            # Store cross-feedback for left half (used next sample)
            self._tank_right_out = tank2_R_out

            # ====== OUTPUT TAPS ======
            out_l = 0.0
            for name, tap_pos, sign in self._left_taps:
                out_l += sign * self._get_tap_value(name, tap_pos)

            out_r = 0.0
            for name, tap_pos, sign in self._right_taps:
                out_r += sign * self._get_tap_value(name, tap_pos)

            out_l *= OUTPUT_GAIN
            out_r *= OUTPUT_GAIN

            # Width crossmix
            final_l = out_l * wet1 + out_r * wet2
            final_r = out_r * wet1 + out_l * wet2

            left_out[i] = np.float32(final_l)
            right_out[i] = np.float32(final_r)

        # Mono mode: copy left to right
        if mono_mode:
            right_out[:] = left_out

        # Hard clip to [-1.0, 1.0]
        np.clip(left_out, -1.0, 1.0, out=left_out)
        np.clip(right_out, -1.0, 1.0, out=right_out)

        return np.stack([left_out, right_out])

    def update_params(self, params: dict) -> None:
        """Update algorithm parameters from dict."""
        if "decay" in params:
            self._decay = params["decay"]
        if "bandwidth" in params:
            self._bandwidth = params["bandwidth"]
        if "tank_damping" in params:
            self._tank_damping = params["tank_damping"]
        if "diffusion" in params:
            self._diffusion = params["diffusion"]
        if "pre_delay" in params:
            self._pre_delay = params["pre_delay"]
        if "mod_depth" in params:
            self._mod_depth = params["mod_depth"]
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
        self._bandwidth_filter.reset()
        for f in self._damping_filters:
            f.reset()
        for dc in self._dc_blockers:
            dc.reset()
        self._pre_delay_line.reset()
        self._lfo_phase = 0.0
        self._shimmer_phase_L = 0.0
        self._shimmer_phase_R = 0.0
        self._tank_left_out = 0.0
        self._tank_right_out = 0.0

    @property
    def param_specs(self) -> dict:
        """Parameter specifications for UI/automation."""
        return {
            "decay": {
                "type": "knob", "min": 0, "max": 100, "default": 60,
                "label": "Decay",
            },
            "bandwidth": {
                "type": "knob", "min": 0, "max": 100, "default": 70,
                "label": "Bandwidth",
            },
            "tank_damping": {
                "type": "knob", "min": 0, "max": 100, "default": 30,
                "label": "Tank Damping",
            },
            "diffusion": {
                "type": "knob", "min": 0, "max": 100, "default": 80,
                "label": "Diffusion",
            },
            "pre_delay": {
                "type": "knob", "min": 0, "max": 100, "default": 10,
                "label": "Pre-Delay",
            },
            "mod_depth": {
                "type": "knob", "min": 0, "max": 100, "default": 30,
                "label": "Mod Depth",
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
