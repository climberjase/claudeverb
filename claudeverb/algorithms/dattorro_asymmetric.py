"""Dattorro Asymmetric Tank reverb algorithm for claudeverb.

Extends the standard Dattorro figure-eight topology with independently
scaled L/R delay paths and diffuser count asymmetry. The Spread knob
controls how different the left and right tank halves are, from symmetric
(like standard Plate) to maximum asymmetry (widest stereo image).

Mono input -> 4 input allpass diffusers -> asymmetric figure-eight tank
(L shorter delays, R longer delays) -> stereo output.

C struct equivalent:
    typedef struct {
        AllpassFilter input_diffusers[4];
        AllpassFilter decay_diffusers_L[2];
        AllpassFilter decay_diffusers_R[2];
        DelayLine tank_delays[4];
        DelayLine pre_delay;
        OnePole damping_filters[2];
        DCBlocker dc_blockers[2];
        float decay, spread, damping, mod, mix, pre_delay_ms;
        int switch1, switch2;
        float left_scale, right_scale;
        float feedback_gain_L, feedback_gain_R;
        int tank_d1_L_len, tank_d2_L_len, tank_d1_R_len, tank_d2_R_len;
        float lfo_phase;
        float tank_left_out, tank_right_out;
    } DattorroAsymmetric;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.algorithms.filters import AllpassFilter, DelayLine
from claudeverb.algorithms.dattorro_plate import (
    OnePole, DCBlocker,
    DATTORRO_SR, INPUT_AP_LENGTHS, INPUT_AP_COEFFS,
    DECAY_AP1_LENGTHS, DECAY_AP2_LENGTHS,
    TANK_DELAY1_LENGTHS, TANK_DELAY2_LENGTHS,
    MAX_MOD_EXCURSION, OUTPUT_GAIN, SHIMMER_BLEND,
    LEFT_TAPS_29761, RIGHT_TAPS_29761,
)
from claudeverb.algorithms.fdn_reverb import rt60_to_gain
from claudeverb.config import SAMPLE_RATE


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LFO_RATE_HZ = 1.0
LFO_PHASE_INC = 2.0 * math.pi * LFO_RATE_HZ / SAMPLE_RATE

MAX_PRE_DELAY_SAMPLES = int(0.1 * SAMPLE_RATE)

# Max asymmetry scaling to keep ratio < 1.6:1 per research guidelines
# left_scale = 1.0 - spread * 0.2  -> min 0.8
# right_scale = 1.0 + spread * 0.25 -> max 1.25
# ratio: 1.25/0.8 = 1.5625


def _scale_length(length_29761: int) -> int:
    """Scale delay length from 29761 Hz to 48 kHz."""
    return round(length_29761 * SAMPLE_RATE / DATTORRO_SR)


# Base tank delay lengths at 48 kHz (before asymmetry scaling)
BASE_DECAY_AP1_L = _scale_length(DECAY_AP1_LENGTHS[0])
BASE_DECAY_AP2_L = _scale_length(DECAY_AP2_LENGTHS[0])
BASE_DECAY_AP1_R = _scale_length(DECAY_AP1_LENGTHS[1])
BASE_DECAY_AP2_R = _scale_length(DECAY_AP2_LENGTHS[1])

BASE_TANK_D1_L = _scale_length(TANK_DELAY1_LENGTHS[0])
BASE_TANK_D2_L = _scale_length(TANK_DELAY2_LENGTHS[0])
BASE_TANK_D1_R = _scale_length(TANK_DELAY1_LENGTHS[1])
BASE_TANK_D2_R = _scale_length(TANK_DELAY2_LENGTHS[1])

# Maximum buffer size: scale * 1.3 + modulation headroom
MAX_SCALE = 1.3
MAX_EXCURSION = MAX_MOD_EXCURSION + 4


# ---------------------------------------------------------------------------
# DattorroAsymmetric algorithm
# ---------------------------------------------------------------------------

class DattorroAsymmetric(ReverbAlgorithm):
    """Dattorro Asymmetric Tank reverb (different L/R delays and diffuser counts).

    6 knobs: decay, spread, damping, mod, mix, pre_delay
    2 switches: switch1 (Freeze/Normal/Shimmer), switch2 (Mono/Stereo/Wide)
    """

    __slots__ = (
        # DSP components
        "_input_diffusers",
        "_decay_diffusers",  # [L_AP1, L_AP2, R_AP1, R_AP2]
        "_tank_delays",      # [L_D1, L_D2, R_D1, R_D2]
        "_damping_filters",
        "_dc_blockers",
        "_pre_delay_line",
        # Parameters (0-100 knobs)
        "_decay", "_spread", "_damping", "_mod",
        "_mix", "_pre_delay",
        "_switch1", "_switch2",
        # Scaled internal parameters
        "_decay_scaled",
        "_damping_scaled",
        "_mod_depth_scaled", "_pre_delay_samples",
        "_left_scale", "_right_scale",
        # Current scaled delay lengths
        "_tank_d1_L_len", "_tank_d2_L_len",
        "_tank_d1_R_len", "_tank_d2_R_len",
        # Feedback gains (separate for L/R)
        "_feedback_gain_L", "_feedback_gain_R",
        # Decay diffuser coefficients
        "_decay_diff1_L", "_decay_diff2_L_coeff",
        "_decay_diff1_R", "_decay_diff2_R",
        # LFO state
        "_lfo_phase",
        # Tank cross-feedback state
        "_tank_left_out", "_tank_right_out",
        # Output tap positions (pre-computed at 48 kHz base)
        "_left_taps_base", "_right_taps_base",
    )

    def __init__(self) -> None:
        # Default knob values
        self._decay = 60
        self._spread = 50
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
        self._left_scale = 1.0
        self._right_scale = 1.0
        self._tank_d1_L_len = BASE_TANK_D1_L
        self._tank_d2_L_len = BASE_TANK_D2_L
        self._tank_d1_R_len = BASE_TANK_D1_R
        self._tank_d2_R_len = BASE_TANK_D2_R
        self._feedback_gain_L = 0.5
        self._feedback_gain_R = 0.5
        self._decay_diff1_L = -0.7
        self._decay_diff2_L_coeff = 0.5
        self._decay_diff1_R = -0.7
        self._decay_diff2_R = 0.5

        # LFO
        self._lfo_phase = 0.0

        # Cross-feedback
        self._tank_left_out = 0.0
        self._tank_right_out = 0.0

        self._left_taps_base = []
        self._right_taps_base = []

        self._initialize()

    def _initialize(self) -> None:
        """Allocate all DSP components."""
        # 4 input allpass diffusers (standard Dattorro)
        self._input_diffusers = [
            AllpassFilter(_scale_length(length), feedback=coeff)
            for length, coeff in zip(INPUT_AP_LENGTHS, INPUT_AP_COEFFS)
        ]

        # 4 decay allpass diffusers -- allocated at max possible size
        self._decay_diffusers = [
            AllpassFilter(int(BASE_DECAY_AP1_L * MAX_SCALE) + MAX_EXCURSION),  # L AP1
            AllpassFilter(int(BASE_DECAY_AP2_L * MAX_SCALE) + MAX_EXCURSION),  # L AP2
            AllpassFilter(int(BASE_DECAY_AP1_R * MAX_SCALE) + MAX_EXCURSION),  # R AP1
            AllpassFilter(int(BASE_DECAY_AP2_R * MAX_SCALE) + MAX_EXCURSION),  # R AP2
        ]

        # 4 tank delay lines -- allocated at max possible size
        self._tank_delays = [
            DelayLine(int(BASE_TANK_D1_L * MAX_SCALE) + MAX_EXCURSION),
            DelayLine(int(BASE_TANK_D2_L * MAX_SCALE) + MAX_EXCURSION),
            DelayLine(int(BASE_TANK_D1_R * MAX_SCALE) + MAX_EXCURSION),
            DelayLine(int(BASE_TANK_D2_R * MAX_SCALE) + MAX_EXCURSION),
        ]

        # Damping filters (one per half)
        self._damping_filters = [OnePole(0.5), OnePole(0.5)]

        # DC blockers (one per half)
        self._dc_blockers = [DCBlocker(), DCBlocker()]

        # Pre-delay line
        self._pre_delay_line = DelayLine(MAX_PRE_DELAY_SAMPLES + 4)

        # Pre-compute base output tap positions at 48 kHz
        self._left_taps_base = [
            (name, _scale_length(pos), sign)
            for name, pos, sign in LEFT_TAPS_29761
        ]
        self._right_taps_base = [
            (name, _scale_length(pos), sign)
            for name, pos, sign in RIGHT_TAPS_29761
        ]

        self._scale_params()

    def _scale_params(self) -> None:
        """Convert 0-100 knob values to internal parameters."""
        # Decay: 0-100 -> 0.1 to 0.9999
        self._decay_scaled = 0.1 + (self._decay / 100.0) ** 1.5 * 0.8999

        # Damping: 0-100 -> 0.0 to 0.9
        self._damping_scaled = (self._damping / 100.0) * 0.9

        # Mod Depth: 0-100 -> 0.0 to 16.0
        self._mod_depth_scaled = (self._mod / 100.0) * MAX_MOD_EXCURSION

        # Pre-delay: 0-100 -> 0 to 100ms
        self._pre_delay_samples = int((self._pre_delay / 100.0) * MAX_PRE_DELAY_SAMPLES)

        # Spread: 0-100 -> asymmetry scaling
        spread_factor = self._spread / 100.0
        self._left_scale = 1.0 - spread_factor * 0.2    # 1.0 to 0.8
        self._right_scale = 1.0 + spread_factor * 0.25  # 1.0 to 1.25

        # Scale tank delay lengths
        self._tank_d1_L_len = max(1, int(BASE_TANK_D1_L * self._left_scale))
        self._tank_d2_L_len = max(1, int(BASE_TANK_D2_L * self._left_scale))
        self._tank_d1_R_len = max(1, int(BASE_TANK_D1_R * self._right_scale))
        self._tank_d2_R_len = max(1, int(BASE_TANK_D2_R * self._right_scale))

        # Compute feedback gains separately for L and R using rt60_to_gain
        rt60 = 0.5 + (self._decay / 100.0) ** 1.5 * 9.5
        total_L = self._tank_d1_L_len + self._tank_d2_L_len + int(BASE_DECAY_AP1_L * self._left_scale) + int(BASE_DECAY_AP2_L * self._left_scale)
        total_R = self._tank_d1_R_len + self._tank_d2_R_len + int(BASE_DECAY_AP1_R * self._right_scale) + int(BASE_DECAY_AP2_R * self._right_scale)
        self._feedback_gain_L = min(rt60_to_gain(rt60, total_L, SAMPLE_RATE), 0.999)
        self._feedback_gain_R = min(rt60_to_gain(rt60, total_R, SAMPLE_RATE), 0.999)

        # Decay diffuser coefficients
        # At spread >= 50: left loses one diffuser (L_AP2 coeff fades to 0)
        if self._spread < 50:
            self._decay_diff2_L_coeff = 0.5
        else:
            # Crossfade from 0.5 to 0.0 over spread 50-100
            fade = (self._spread - 50) / 50.0
            self._decay_diff2_L_coeff = 0.5 * (1.0 - fade)

        self._decay_diff1_L = -0.7
        self._decay_diff1_R = -0.7
        self._decay_diff2_R = 0.5

        # Apply to decay diffusers
        self._decay_diffusers[0].feedback = self._decay_diff1_L
        self._decay_diffusers[1].feedback = self._decay_diff2_L_coeff
        self._decay_diffusers[2].feedback = self._decay_diff1_R
        self._decay_diffusers[3].feedback = self._decay_diff2_R

        # Update damping filter coefficients
        damp_coeff = 1.0 - self._damping_scaled
        for f in self._damping_filters:
            f._coeff = np.float32(damp_coeff)

    def _get_tap_value(self, name: str, tap_pos: int) -> float:
        """Read a tap from the named delay element, clamped to valid range."""
        if name == "tank_delay1_L":
            tap_pos = min(tap_pos, self._tank_delays[0].max_delay - 1)
            return self._tank_delays[0].read(max(1, tap_pos))
        elif name == "tank_delay2_L":
            tap_pos = min(tap_pos, self._tank_delays[1].max_delay - 1)
            return self._tank_delays[1].read(max(1, tap_pos))
        elif name == "tank_delay1_R":
            tap_pos = min(tap_pos, self._tank_delays[2].max_delay - 1)
            return self._tank_delays[2].read(max(1, tap_pos))
        elif name == "tank_delay2_R":
            tap_pos = min(tap_pos, self._tank_delays[3].max_delay - 1)
            return self._tank_delays[3].read(max(1, tap_pos))
        elif name == "decay_ap2_L":
            tap_pos = min(tap_pos, self._decay_diffusers[1]._delay.max_delay - 1)
            return self._decay_diffusers[1]._delay.read(max(1, tap_pos))
        elif name == "decay_ap2_R":
            tap_pos = min(tap_pos, self._decay_diffusers[3]._delay.max_delay - 1)
            return self._decay_diffusers[3]._delay.read(max(1, tap_pos))
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

        decay_L = self._feedback_gain_L
        decay_R = self._feedback_gain_R
        if freeze:
            decay_L = 1.0
            decay_R = 1.0

        mod_depth = self._mod_depth_scaled if not freeze else 0.0

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

        # Cache delay lengths
        d1_L = self._tank_d1_L_len
        d2_L = self._tank_d2_L_len
        d1_R = self._tank_d1_R_len
        d2_R = self._tank_d2_R_len

        # Cache DSP objects
        input_diffs = self._input_diffusers
        pre_delay = self._pre_delay_line
        pre_delay_samples = self._pre_delay_samples

        for i in range(n_samples):
            dry_sample = float(mono_in[i])
            x = dry_sample

            if freeze:
                x = 0.0

            # Pre-delay
            if pre_delay_samples > 0:
                delayed = pre_delay.read(pre_delay_samples)
                pre_delay.write(x)
                x = delayed
            else:
                pre_delay.write(x)

            # 4 input allpass diffusers (standard Dattorro)
            for ap in input_diffs:
                x = ap.process_sample(x)

            tank_input = x

            # --- LFO ---
            lfo_left = math.sin(self._lfo_phase) * mod_depth
            lfo_right = math.sin(self._lfo_phase + math.pi) * mod_depth
            self._lfo_phase += LFO_PHASE_INC
            if self._lfo_phase >= 2.0 * math.pi:
                self._lfo_phase -= 2.0 * math.pi

            # ====== LEFT TANK HALF (shorter delays) ======
            left_in = tank_input + decay_L * self._tank_right_out

            # Decay diffusion AP1 (negative feedback)
            left_in = self._decay_diffusers[0].process_sample(left_in)

            # Modulated delay line 1 (left)
            self._tank_delays[0].write(left_in)
            read_delay_L = float(d1_L) + lfo_left
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
            tank1_L_out *= decay_L

            # Decay diffusion AP2 (may be faded out at high spread)
            tank1_L_out = self._decay_diffusers[1].process_sample(tank1_L_out)

            # Delay line 2 (left)
            self._tank_delays[1].write(tank1_L_out)
            tank2_L_out = self._tank_delays[1].read(d2_L)

            # DC blocker
            if not freeze:
                tank2_L_out = self._dc_blockers[0].process_sample(tank2_L_out)

            self._tank_left_out = tank2_L_out

            # ====== RIGHT TANK HALF (longer delays) ======
            right_in = tank_input + decay_R * self._tank_left_out

            # Decay diffusion AP1 (negative feedback)
            right_in = self._decay_diffusers[2].process_sample(right_in)

            # Modulated delay line 1 (right)
            self._tank_delays[2].write(right_in)
            read_delay_R = float(d1_R) + lfo_right
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
            tank1_R_out *= decay_R

            # Decay diffusion AP2 (always active on right)
            tank1_R_out = self._decay_diffusers[3].process_sample(tank1_R_out)

            # Delay line 2 (right)
            self._tank_delays[3].write(tank1_R_out)
            tank2_R_out = self._tank_delays[3].read(d2_R)

            # DC blocker
            if not freeze:
                tank2_R_out = self._dc_blockers[1].process_sample(tank2_R_out)

            self._tank_right_out = tank2_R_out

            # ====== OUTPUT TAPS ======
            out_l = 0.0
            for name, tap_pos, sign in self._left_taps_base:
                out_l += sign * self._get_tap_value(name, tap_pos)

            out_r = 0.0
            for name, tap_pos, sign in self._right_taps_base:
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
        if "spread" in params:
            self._spread = params["spread"]
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
            "spread": {
                "type": "knob", "min": 0, "max": 100, "default": 50,
                "label": "Spread",
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

    def to_dot(self, detail_level: str = "block",
               params: dict | None = None) -> str:
        """Generate Graphviz DOT string for DattorroAsymmetric signal flow."""
        from claudeverb.export.dot_builder import (
            digraph_wrap, dsp_node, io_node, edge, feedback_edge, subgraph,
        )
        p = params if params else {
            k: v["default"] for k, v in self.param_specs.items()
            if v.get("type") == "knob"
        }
        decay = p.get("decay", 60)
        spread = p.get("spread", 50)
        damp = p.get("damping", 30)
        mod = p.get("mod", 30)
        mix_val = p.get("mix", 50)
        pre_d = p.get("pre_delay", 10)

        if detail_level == "component":
            body = io_node("input", "Input")
            body += dsp_node("pre_delay", f"Pre-Delay\\n[{pre_d}]")
            body += edge("input", "pre_delay")

            # 4 input allpass diffusers
            idiff_nodes = ""
            for i, (length, coeff) in enumerate(zip(INPUT_AP_LENGTHS, INPUT_AP_COEFFS)):
                scaled = _scale_length(length)
                idiff_nodes += dsp_node(f"iap{i}", f"Input AP {i}\\n[{scaled} smp]\\ncoeff: {coeff}")
            body += subgraph("input_diff", "Input Diffusers", idiff_nodes)

            body += edge("pre_delay", "iap0")
            for i in range(3):
                body += edge(f"iap{i}", f"iap{i+1}")

            # Left tank half (shorter at high spread)
            lt_nodes = ""
            lt_nodes += dsp_node("dap1_l", f"Decay AP1 L\\n[{BASE_DECAY_AP1_L} smp]")
            lt_nodes += dsp_node("td1_l", f"Delay 1 L (mod)\\n[{BASE_TANK_D1_L} smp]")
            lt_nodes += dsp_node("damp_l", f"Damping L\\n[{damp}]")
            lt_nodes += dsp_node("dap2_l", f"Decay AP2 L\\n(fades at spread>50)")
            lt_nodes += dsp_node("td2_l", f"Delay 2 L\\n[{BASE_TANK_D2_L} smp]")
            lt_nodes += dsp_node("dc_l", "DC Block L")
            body += subgraph("tank_left", f"Left Tank (shorter, spread: {spread})", lt_nodes)

            # Right tank half (longer at high spread)
            rt_nodes = ""
            rt_nodes += dsp_node("dap1_r", f"Decay AP1 R\\n[{BASE_DECAY_AP1_R} smp]")
            rt_nodes += dsp_node("td1_r", f"Delay 1 R (mod)\\n[{BASE_TANK_D1_R} smp]")
            rt_nodes += dsp_node("damp_r", f"Damping R\\n[{damp}]")
            rt_nodes += dsp_node("dap2_r", f"Decay AP2 R")
            rt_nodes += dsp_node("td2_r", f"Delay 2 R\\n[{BASE_TANK_D2_R} smp]")
            rt_nodes += dsp_node("dc_r", "DC Block R")
            body += subgraph("tank_right", f"Right Tank (longer, spread: {spread})", rt_nodes)

            body += dsp_node("lfo", f"LFO\\nmod: {mod}")
            body += io_node("output", "Output")

            # Left tank flow
            body += edge("iap3", "dap1_l")
            body += edge("dap1_l", "td1_l")
            body += edge("td1_l", "damp_l")
            body += edge("damp_l", "dap2_l")
            body += edge("dap2_l", "td2_l")
            body += edge("td2_l", "dc_l")

            # Right tank flow
            body += edge("iap3", "dap1_r")
            body += edge("dap1_r", "td1_r")
            body += edge("td1_r", "damp_r")
            body += edge("damp_r", "dap2_r")
            body += edge("dap2_r", "td2_r")
            body += edge("td2_r", "dc_r")

            # Cross-feedback (asymmetric gains)
            body += feedback_edge("dc_r", "dap1_l", label=f"decay: {decay}")
            body += feedback_edge("dc_l", "dap1_r", label=f"decay: {decay}")

            # LFO
            body += edge("lfo", "td1_l", style="dotted", color="blue")
            body += edge("lfo", "td1_r", style="dotted", color="blue")

            body += edge("dc_l", "output")
            body += edge("dc_r", "output")

            return digraph_wrap("DattorroAsymmetric", body)
        else:
            # Block level
            body = io_node("input", "Input")
            body += dsp_node("pre_delay", f"Pre-Delay\\n[{pre_d}]")
            body += dsp_node("input_diff", "4 Input Diffusers")
            body += dsp_node("tank_left", f"Left Tank (shorter)\\ndecay: {decay}")
            body += dsp_node("tank_right", f"Right Tank (longer)\\ndecay: {decay}")
            body += dsp_node("asym_ctrl", f"Asymmetry\\nspread: {spread}")
            body += dsp_node("lfo_mod", f"LFO Mod\\n[{mod}]")
            body += io_node("output", "Output")

            body += edge("input", "pre_delay")
            body += edge("pre_delay", "input_diff")
            body += edge("input_diff", "tank_left")
            body += edge("input_diff", "tank_right")
            body += edge("asym_ctrl", "tank_left", style="dotted")
            body += edge("asym_ctrl", "tank_right", style="dotted")
            body += edge("tank_left", "output")
            body += edge("tank_right", "output")
            body += feedback_edge("tank_right", "tank_left", label="cross-fb")
            body += feedback_edge("tank_left", "tank_right", label="cross-fb")
            body += edge("lfo_mod", "tank_left", style="dotted", color="blue")

            return digraph_wrap("DattorroAsymmetric", body)

    def to_c_struct(self) -> str:
        """Return C typedef struct for the Asymmetric Tank state."""
        input_ap_sizes = [_scale_length(l) for l in INPUT_AP_LENGTHS]
        dap1_L = int(BASE_DECAY_AP1_L * MAX_SCALE) + MAX_EXCURSION
        dap2_L = int(BASE_DECAY_AP2_L * MAX_SCALE) + MAX_EXCURSION
        dap1_R = int(BASE_DECAY_AP1_R * MAX_SCALE) + MAX_EXCURSION
        dap2_R = int(BASE_DECAY_AP2_R * MAX_SCALE) + MAX_EXCURSION
        td1_L = int(BASE_TANK_D1_L * MAX_SCALE) + MAX_EXCURSION
        td2_L = int(BASE_TANK_D2_L * MAX_SCALE) + MAX_EXCURSION
        td1_R = int(BASE_TANK_D1_R * MAX_SCALE) + MAX_EXCURSION
        td2_R = int(BASE_TANK_D2_R * MAX_SCALE) + MAX_EXCURSION

        return f"""\
typedef struct {{
    // 4 input diffusion allpass buffers
    float input_ap_buf_0[{input_ap_sizes[0]}];
    float input_ap_buf_1[{input_ap_sizes[1]}];
    float input_ap_buf_2[{input_ap_sizes[2]}];
    float input_ap_buf_3[{input_ap_sizes[3]}];
    int input_ap_write_idx[4];
    float input_ap_gain[4];

    // Decay diffusion allpass buffers (asymmetric sizes)
    float decay_ap1_L_buf[{dap1_L}];
    float decay_ap2_L_buf[{dap2_L}];
    float decay_ap1_R_buf[{dap1_R}];
    float decay_ap2_R_buf[{dap2_R}];
    int decay_ap_write_idx[4];

    // Tank delay buffers (asymmetric sizes)
    float tank_d1_L_buf[{td1_L}];
    float tank_d2_L_buf[{td2_L}];
    float tank_d1_R_buf[{td1_R}];
    float tank_d2_R_buf[{td2_R}];
    int tank_d_write_idx[4];

    // Current delay lengths (scaled by spread)
    int tank_d1_L_len, tank_d2_L_len;
    int tank_d1_R_len, tank_d2_R_len;

    // Feedback gains (separate for L/R)
    float feedback_gain_L, feedback_gain_R;

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
    float spread;
    float left_scale, right_scale;
    int sample_rate;
    int frozen;
    int shimmer;
    float width;
    float mix;
}} DattorroAsymmetricState;
"""

    def to_c_process_fn(self) -> str:
        """Return C process function template for Asymmetric Tank."""
        return """\
void dattorro_asymmetric_process(DattorroAsymmetricState* state,
                                 const float* input,
                                 float* output_left, float* output_right,
                                 int num_samples) {
    float wet1 = (1.0f + state->width) / 2.0f;
    float wet2 = (1.0f - state->width) / 2.0f;
    float mix_wet = state->mix / 100.0f;
    float mix_dry = 1.0f - mix_wet;
    float freeze_gain = state->frozen ? 2.0f : 1.0f;
    float decay_L = state->frozen ? 1.0f : state->feedback_gain_L;
    float decay_R = state->frozen ? 1.0f : state->feedback_gain_R;

    for (int i = 0; i < num_samples; i++) {
        float dry = input[i];
        float x = state->frozen ? 0.0f : dry;

        // 1. Pre-delay
        // ...

        // 2. Input diffusion (4 standard allpass)
        for (int d = 0; d < 4; d++) {
            // allpass processing
        }
        float tank_input = x;

        // 3. LFO
        float lfo_left = sinf(state->lfo_phase) * state->mod_depth;
        float lfo_right = sinf(state->lfo_phase + M_PI) * state->mod_depth;
        state->lfo_phase += 2.0f * M_PI * 1.0f / state->sample_rate;
        if (state->lfo_phase >= 2.0f * M_PI)
            state->lfo_phase -= 2.0f * M_PI;

        // 4. Left tank half (shorter delays at high spread):
        //    AP1_L -> D1_L(mod) -> damp_L -> decay_L -> AP2_L -> D2_L -> DC_L
        // 5. Right tank half (longer delays at high spread):
        //    AP1_R -> D1_R(mod) -> damp_R -> decay_R -> AP2_R -> D2_R -> DC_R
        // 6. Output taps (clamped to current delay lengths)
        // 7. Width crossmix + dry/wet mix + clip

        output_left[i] = /* final_l */;
        output_right[i] = /* final_r */;
    }
}
"""
