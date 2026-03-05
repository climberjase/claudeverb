"""Freeverb algorithm implementation for claudeverb.

Jezar's Schroeder-Moorer reverb: 8 parallel lowpass-feedback comb filters
into 4 series allpass filters per channel. Delay line lengths scaled from
44.1 kHz reference to 48 kHz.

C struct equivalent:
    typedef struct {
        CombFilter combs_l[8];
        CombFilter combs_r[8];
        AllpassFilter allpasses_l[4];
        AllpassFilter allpasses_r[4];
        DelayLine pre_delay;
        float room_size, damping, mix, width, pre_delay_ms;
        float hf_damp;
        int switch1, switch2;
        // Scaled internal parameters
        float room_scaled, damp_scaled, mix_scaled, width_scaled;
        float hf_damp_scaled;
        int pre_delay_samples;
    } Freeverb;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.algorithms.filters import AllpassFilter, CombFilter, DelayLine
from claudeverb.config import SAMPLE_RATE


class Freeverb(ReverbAlgorithm):
    """Freeverb reverb algorithm (Jezar's public domain design).

    6 knobs: room_size, damping, mix, width, pre_delay, hf_damp
    2 switches: switch1 (freeze), switch2 (stereo mode)
    """

    __slots__ = (
        "_combs_l", "_combs_r",
        "_allpasses_l", "_allpasses_r",
        "_pre_delay_line",
        "_room_size", "_damping", "_mix", "_width",
        "_pre_delay", "_hf_damp",
        "_switch1", "_switch2",
        # Scaled internal parameters
        "_room_scaled", "_damp_scaled", "_mix_scaled", "_width_scaled",
        "_hf_damp_scaled", "_pre_delay_samples",
    )

    # Jezar's reference delay lengths at 44100 Hz
    COMB_LENGTHS_44100 = [1557, 1617, 1491, 1422, 1356, 1277, 1188, 1116]
    ALLPASS_LENGTHS_44100 = [225, 556, 441, 341]
    STEREO_SPREAD_44100 = 23

    # Scaling constants from Jezar's tuning.h
    FIXED_GAIN = 0.015
    SCALE_ROOM = 0.28
    OFFSET_ROOM = 0.7
    SCALE_DAMP = 0.4

    def __init__(self) -> None:
        # Default parameter values (0-100 integer knobs)
        self._room_size = 75
        self._damping = 25
        self._mix = 75
        self._width = 100
        self._pre_delay = 0
        self._hf_damp = 0
        self._switch1 = 0  # Freeze: -1=freeze, 0=normal, 1=bright
        self._switch2 = 0  # Stereo: -1=mono, 0=stereo, 1=wide

        # Initialize scaled values to defaults before _initialize
        self._room_scaled = 0.0
        self._damp_scaled = 0.0
        self._mix_scaled = 0.0
        self._width_scaled = 0.0
        self._hf_damp_scaled = 0.0
        self._pre_delay_samples = 0

        self._initialize()

    @staticmethod
    def _scale_length(length_44100: int) -> int:
        """Scale delay length from 44.1 kHz to 48 kHz."""
        return round(length_44100 * SAMPLE_RATE / 44100)

    def _initialize(self) -> None:
        """Allocate all comb filters, allpass filters, and pre-delay."""
        spread = self._scale_length(self.STEREO_SPREAD_44100)

        # 8 comb filters per channel
        self._combs_l = [
            CombFilter(self._scale_length(length))
            for length in self.COMB_LENGTHS_44100
        ]
        self._combs_r = [
            CombFilter(self._scale_length(length) + spread)
            for length in self.COMB_LENGTHS_44100
        ]

        # 4 allpass filters per channel
        self._allpasses_l = [
            AllpassFilter(self._scale_length(length))
            for length in self.ALLPASS_LENGTHS_44100
        ]
        self._allpasses_r = [
            AllpassFilter(self._scale_length(length) + spread)
            for length in self.ALLPASS_LENGTHS_44100
        ]

        # Pre-delay: max 100ms at 48 kHz = 4800 samples
        max_pre_delay = math.ceil(0.1 * SAMPLE_RATE)
        self._pre_delay_line = DelayLine(max_pre_delay)

        # Apply initial parameter scaling
        self._scale_params()

    def _scale_params(self) -> None:
        """Convert 0-100 integer knob values to internal float ranges."""
        # Room size: 0-100 -> 0.7 to 0.98
        self._room_scaled = (self._room_size / 100.0) * self.SCALE_ROOM + self.OFFSET_ROOM

        # Base damping: 0-100 -> 0.0 to 0.4
        base_damp = (self._damping / 100.0) * self.SCALE_DAMP

        # HF damp: 0-100 -> additional damping on top of base
        # effective_damp = base_damp + (hf_damp_scaled * (1.0 - base_damp))
        self._hf_damp_scaled = self._hf_damp / 100.0
        effective_damp = base_damp + (self._hf_damp_scaled * (1.0 - base_damp))
        self._damp_scaled = effective_damp

        # Mix: 0-100 -> 0.0 to 1.0
        self._mix_scaled = self._mix / 100.0

        # Width: 0-100 -> 0.0 to 1.0
        self._width_scaled = self._width / 100.0

        # Pre-delay: 0-100 -> 0 to 4800 samples (0 to 100ms)
        self._pre_delay_samples = int((self._pre_delay / 100.0) * 0.1 * SAMPLE_RATE)

        # Handle freeze mode (switch1 == -1)
        if self._switch1 == -1:
            room_feedback = 1.0
            damp_value = 0.0
        else:
            room_feedback = self._room_scaled
            damp_value = self._damp_scaled

        # Handle stereo mode width adjustment (switch2)
        if self._switch2 == 1:  # Wide
            self._width_scaled = min(self._width_scaled * 2.0, 1.0)

        # Apply to all comb filters
        for comb in self._combs_l + self._combs_r:
            comb.feedback = room_feedback
            comb.damp = damp_value

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        """Dispatch to mono or stereo processing."""
        if audio.ndim == 1:
            return self._process_mono(audio)
        else:
            return self._process_stereo(audio)

    def _process_mono(self, audio: np.ndarray) -> np.ndarray:
        """Process mono audio through Freeverb."""
        n_samples = len(audio)
        output = np.zeros(n_samples, dtype=np.float32)

        freeze = self._switch1 == -1

        for i in range(n_samples):
            x = float(audio[i]) * self.FIXED_GAIN

            # In freeze mode, zero input gain
            if freeze:
                x = 0.0

            # Pre-delay
            if self._pre_delay_samples > 0:
                delayed = self._pre_delay_line.read(self._pre_delay_samples)
                self._pre_delay_line.write(x)
                x = delayed

            # Sum of 8 parallel comb filters
            comb_sum = 0.0
            for comb in self._combs_l:
                comb_sum += comb.process_sample(x)

            # Series allpass filters
            out = comb_sum
            for ap in self._allpasses_l:
                out = ap.process_sample(out)

            # Mix: blend dry and wet
            dry_gain = 1.0 - self._mix_scaled
            wet_gain = self._mix_scaled
            output[i] = np.float32(float(audio[i]) * dry_gain + out * wet_gain)

        # Hard clip to [-1.0, 1.0]
        np.clip(output, -1.0, 1.0, out=output)
        return output

    def _process_stereo(self, audio: np.ndarray) -> np.ndarray:
        """Process stereo (2, N) audio through Freeverb."""
        left_in, right_in = audio[0], audio[1]
        n_samples = len(left_in)
        left_out = np.zeros(n_samples, dtype=np.float32)
        right_out = np.zeros(n_samples, dtype=np.float32)

        freeze = self._switch1 == -1
        mono_output = self._switch2 == -1

        # Width crossmix coefficients
        wet1 = self._mix_scaled * (1.0 + self._width_scaled) / 2.0
        wet2 = self._mix_scaled * (1.0 - self._width_scaled) / 2.0
        dry_gain = 1.0 - self._mix_scaled

        for i in range(n_samples):
            # Mono sum of input for reverb (standard Freeverb behavior)
            x = (float(left_in[i]) + float(right_in[i])) * self.FIXED_GAIN

            # In freeze mode, zero input gain
            if freeze:
                x = 0.0

            # Pre-delay
            if self._pre_delay_samples > 0:
                delayed = self._pre_delay_line.read(self._pre_delay_samples)
                self._pre_delay_line.write(x)
                x = delayed

            # Left channel: 8 combs -> 4 allpasses
            comb_l = 0.0
            for c in self._combs_l:
                comb_l += c.process_sample(x)
            out_l = comb_l
            for ap in self._allpasses_l:
                out_l = ap.process_sample(out_l)

            # Right channel: 8 combs -> 4 allpasses
            comb_r = 0.0
            for c in self._combs_r:
                comb_r += c.process_sample(x)
            out_r = comb_r
            for ap in self._allpasses_r:
                out_r = ap.process_sample(out_r)

            # Width crossmix and dry/wet blend
            left_out[i] = np.float32(
                float(left_in[i]) * dry_gain + out_l * wet1 + out_r * wet2
            )
            right_out[i] = np.float32(
                float(right_in[i]) * dry_gain + out_r * wet1 + out_l * wet2
            )

        # Mono mode: copy left to right
        if mono_output:
            right_out[:] = left_out

        # Hard clip to [-1.0, 1.0]
        np.clip(left_out, -1.0, 1.0, out=left_out)
        np.clip(right_out, -1.0, 1.0, out=right_out)

        return np.stack([left_out, right_out])

    def update_params(self, params: dict) -> None:
        """Update algorithm parameters from dict."""
        if "room_size" in params:
            self._room_size = params["room_size"]
        if "damping" in params:
            self._damping = params["damping"]
        if "mix" in params:
            self._mix = params["mix"]
        if "width" in params:
            self._width = params["width"]
        if "pre_delay" in params:
            self._pre_delay = params["pre_delay"]
        if "hf_damp" in params:
            self._hf_damp = params["hf_damp"]
        if "switch1" in params:
            self._switch1 = params["switch1"]
        if "switch2" in params:
            self._switch2 = params["switch2"]
        self._scale_params()

    def reset(self) -> None:
        """Reset all internal state to initial values."""
        for comb in self._combs_l + self._combs_r:
            comb.reset()
        for ap in self._allpasses_l + self._allpasses_r:
            ap.reset()
        self._pre_delay_line.reset()

    @property
    def param_specs(self) -> dict:
        """Parameter specifications for UI/automation."""
        return {
            "room_size": {
                "type": "knob", "min": 0, "max": 100, "default": 75,
                "label": "Room Size",
            },
            "damping": {
                "type": "knob", "min": 0, "max": 100, "default": 25,
                "label": "Damping",
            },
            "mix": {
                "type": "knob", "min": 0, "max": 100, "default": 75,
                "label": "Mix",
            },
            "width": {
                "type": "knob", "min": 0, "max": 100, "default": 100,
                "label": "Width",
            },
            "pre_delay": {
                "type": "knob", "min": 0, "max": 100, "default": 0,
                "label": "Pre-Delay",
            },
            "hf_damp": {
                "type": "knob", "min": 0, "max": 100, "default": 0,
                "label": "HF Damp",
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
