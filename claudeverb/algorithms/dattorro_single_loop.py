"""Dattorro Single-Loop Tank reverb algorithm for claudeverb.

Implements a Griesinger-style single feedback ring with interleaved
allpass filters and delay sections. Unlike the standard Dattorro
figure-eight topology, this uses one continuous loop for denser,
less stereo-separated reverb with stereo derived from output tap spacing.

Mono input -> 4 input allpass diffusers -> single feedback ring
(4 allpass + 4 delay sections) -> stereo output from ring taps.

C struct equivalent:
    typedef struct {
        AllpassFilter input_diffusers[4];
        AllpassFilter loop_allpasses[4];
        DelayLine loop_delays[4];
        DelayLine pre_delay;
        OnePole damping_filters[2];
        DCBlocker dc_blocker;
        float decay, loop_length, damping, mod, mix, pre_delay_ms;
        int switch1, switch2;
        // Scaled internal parameters
        float feedback_gain, loop_scale;
        float damp_coeff, mod_depth, mod_rate;
        int pre_delay_samples;
        float lfo_phase;
        // Current delay lengths (scaled by loop_length)
        int loop_ap_lens[4];
        int loop_d_lens[4];
        // Output tap positions
        int tap_l[3], tap_r[3];
    } DattorroSingleLoop;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.base import ReverbAlgorithm
from claudeverb.algorithms.filters import AllpassFilter, DelayLine
from claudeverb.algorithms.dattorro_plate import OnePole, DCBlocker
from claudeverb.algorithms.fdn_reverb import rt60_to_gain
from claudeverb.config import SAMPLE_RATE


# ---------------------------------------------------------------------------
# Constants for single-loop topology at 48 kHz
# ---------------------------------------------------------------------------

# Input diffusion allpass delays (scaled from 29761 Hz to 48 kHz)
DATTORRO_SR = 29761
INPUT_AP_LENGTHS_29761 = [142, 107, 379, 277]
INPUT_AP_COEFFS = [0.75, 0.75, 0.625, 0.625]

# Loop allpass base delays in samples at 48 kHz
# ~5ms, ~8ms, ~11ms, ~7ms
LOOP_AP_BASE = [240, 384, 528, 336]
LOOP_AP_COEFF = 0.6

# Loop delay base delays in samples at 48 kHz
# ~15ms, ~22ms, ~18ms, ~25ms
LOOP_D_BASE = [720, 1056, 864, 1200]

# Total base loop delay (sum of all AP + delay sections)
TOTAL_BASE_LOOP = sum(LOOP_AP_BASE) + sum(LOOP_D_BASE)  # 5328 samples ~111ms

# Output tap positions as fractions of delay length
# Left: D1 at 30%, D2 at 60%, D4 at 45%
# Right: D1 at 70%, D3 at 40%, D4 at 80%
TAP_FRACS_L = [(0, 0.30), (1, 0.60), (3, 0.45)]  # (delay_index, fraction)
TAP_FRACS_R = [(0, 0.70), (2, 0.40), (3, 0.80)]

# Loop Length scaling: knob 0-100 -> scale 0.375 to 1.875
# At scale 1.0, total loop is ~111ms (base)
# At 0.375 -> ~42ms (tight), at 1.875 -> ~208ms (spacious)
LOOP_SCALE_MIN = 0.375
LOOP_SCALE_MAX = 1.875

# Max modulation excursion in samples
MAX_MOD_EXCURSION = 8

# LFO defaults
DEFAULT_MOD_RATE = 0.8  # Hz

# Shimmer blend
SHIMMER_BLEND = 0.15

# Output gain scaling
OUTPUT_GAIN = 1.2

# Max pre-delay: 100ms
MAX_PRE_DELAY_SAMPLES = int(0.1 * SAMPLE_RATE)


def _scale_29761(length: int) -> int:
    """Scale delay length from 29761 Hz to 48 kHz."""
    return round(length * SAMPLE_RATE / DATTORRO_SR)


# ---------------------------------------------------------------------------
# DattorroSingleLoop algorithm
# ---------------------------------------------------------------------------

class DattorroSingleLoop(ReverbAlgorithm):
    """Dattorro Single-Loop Tank reverb (Griesinger-style single feedback ring).

    6 knobs: decay, loop_length, damping, mod, mix, pre_delay
    2 switches: switch1 (Freeze/Normal/Shimmer), switch2 (Mono/Stereo/Wide)
    """

    __slots__ = (
        # DSP components
        "_input_diffusers",
        "_loop_allpasses",
        "_loop_delays",
        "_damping_filters",
        "_dc_blocker",
        "_pre_delay_line",
        # Parameters (0-100 knobs)
        "_decay", "_loop_length", "_damping", "_mod",
        "_mix", "_pre_delay",
        "_switch1", "_switch2",
        # Scaled internal parameters
        "_feedback_gain", "_loop_scale",
        "_damp_coeff", "_mod_depth", "_mod_rate",
        "_pre_delay_samples",
        # LFO state
        "_lfo_phase", "_lfo_phase_inc",
        # Current scaled delay lengths
        "_loop_ap_lens", "_loop_d_lens",
        # Output tap positions (in samples)
        "_taps_l", "_taps_r",
    )

    def __init__(self) -> None:
        # Default knob values
        self._decay = 60
        self._loop_length = 50
        self._damping = 40
        self._mod = 30
        self._mix = 50
        self._pre_delay = 10
        self._switch1 = 0   # Normal
        self._switch2 = 0   # Stereo

        # Scaled values
        self._feedback_gain = 0.0
        self._loop_scale = 1.0
        self._damp_coeff = 0.5
        self._mod_depth = 0.0
        self._mod_rate = DEFAULT_MOD_RATE
        self._pre_delay_samples = 0

        # LFO
        self._lfo_phase = 0.0
        self._lfo_phase_inc = 2.0 * math.pi * DEFAULT_MOD_RATE / SAMPLE_RATE

        # Current lengths (will be set by _scale_params)
        self._loop_ap_lens = list(LOOP_AP_BASE)
        self._loop_d_lens = list(LOOP_D_BASE)
        self._taps_l = [0, 0, 0]
        self._taps_r = [0, 0, 0]

        self._initialize()

    def _initialize(self) -> None:
        """Allocate all DSP components."""
        # 4 input allpass diffusers
        self._input_diffusers = [
            AllpassFilter(_scale_29761(length), feedback=coeff)
            for length, coeff in zip(INPUT_AP_LENGTHS_29761, INPUT_AP_COEFFS)
        ]

        # Max delay size accounts for Loop Length scaling to max
        max_scale = LOOP_SCALE_MAX + 0.1  # safety margin

        # 4 loop allpass filters
        self._loop_allpasses = [
            AllpassFilter(int(d * max_scale) + MAX_MOD_EXCURSION + 4, feedback=LOOP_AP_COEFF)
            for d in LOOP_AP_BASE
        ]

        # 4 loop delay lines
        self._loop_delays = [
            DelayLine(int(d * max_scale) + MAX_MOD_EXCURSION + 4)
            for d in LOOP_D_BASE
        ]

        # 2 damping filters (after D1 and D3)
        self._damping_filters = [OnePole(0.5), OnePole(0.5)]

        # DC blocker at loop junction
        self._dc_blocker = DCBlocker()

        # Pre-delay line
        self._pre_delay_line = DelayLine(MAX_PRE_DELAY_SAMPLES + 4)

        self._scale_params()

    def _scale_params(self) -> None:
        """Convert 0-100 knob values to internal parameters."""
        # Loop Length: 0-100 -> scale 0.375 to 1.875
        self._loop_scale = LOOP_SCALE_MIN + (self._loop_length / 100.0) * (LOOP_SCALE_MAX - LOOP_SCALE_MIN)

        # Scale all loop delay lengths
        self._loop_ap_lens = [max(1, int(d * self._loop_scale)) for d in LOOP_AP_BASE]
        self._loop_d_lens = [max(1, int(d * self._loop_scale)) for d in LOOP_D_BASE]

        # Compute total loop delay
        total_loop = sum(self._loop_ap_lens) + sum(self._loop_d_lens)

        # Decay: 0-100 -> 0.5s to 10.0s RT60
        rt60 = 0.5 + (self._decay / 100.0) ** 1.5 * 9.5

        # Feedback gain from RT60 and total loop length
        self._feedback_gain = rt60_to_gain(rt60, total_loop, SAMPLE_RATE)
        # Extra safety clamp
        self._feedback_gain = min(self._feedback_gain, 0.999)

        # Damping: 0-100 -> OnePole coeff 1.0 (bright) to 0.05 (dark)
        self._damp_coeff = 1.0 - (self._damping / 100.0) * 0.95
        for f in self._damping_filters:
            f._coeff = np.float32(self._damp_coeff)

        # Mod: 0-100 -> depth 0.0 to MAX_MOD_EXCURSION samples, rate 0.1 to 2.0 Hz
        self._mod_depth = (self._mod / 100.0) * MAX_MOD_EXCURSION
        self._mod_rate = 0.1 + (self._mod / 100.0) * 1.9
        self._lfo_phase_inc = 2.0 * math.pi * self._mod_rate / SAMPLE_RATE

        # Pre-delay: 0-100 -> 0 to 100ms
        self._pre_delay_samples = int((self._pre_delay / 100.0) * MAX_PRE_DELAY_SAMPLES)

        # Compute output tap positions
        for i, (d_idx, frac) in enumerate(TAP_FRACS_L):
            self._taps_l[i] = max(1, int(self._loop_d_lens[d_idx] * frac))
        for i, (d_idx, frac) in enumerate(TAP_FRACS_R):
            self._taps_r[i] = max(1, int(self._loop_d_lens[d_idx] * frac))

    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        """Process audio -- mono input produces stereo output."""
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

        feedback_gain = self._feedback_gain
        if freeze:
            feedback_gain = 1.0

        mod_depth = self._mod_depth if not freeze else 0.0

        # Width crossmix
        width = 1.0
        if wide_mode:
            width = 2.0
        wet1 = (1.0 + width) / 2.0
        wet2 = (1.0 - width) / 2.0

        # Mix
        mix_wet = self._mix / 100.0
        mix_dry = 1.0 - mix_wet

        # Freeze output gain (compensate for single-loop geometry)
        freeze_gain = 3.0 if freeze else 1.0

        # Cache delay lengths
        ap_lens = self._loop_ap_lens
        d_lens = self._loop_d_lens
        taps_l = self._taps_l
        taps_r = self._taps_r

        # Cache DSP objects
        input_diffs = self._input_diffusers
        loop_aps = self._loop_allpasses
        loop_ds = self._loop_delays
        damp1 = self._damping_filters[0]
        damp2 = self._damping_filters[1]
        dc_blocker = self._dc_blocker
        pre_delay = self._pre_delay_line
        pre_delay_samples = self._pre_delay_samples

        lfo_phase = self._lfo_phase
        lfo_inc = self._lfo_phase_inc

        for i in range(n_samples):
            dry_sample = float(mono_in[i])
            x = dry_sample

            # Freeze: zero input gain
            if freeze:
                x = 0.0

            # Pre-delay
            if pre_delay_samples > 0:
                delayed = pre_delay.read(pre_delay_samples)
                pre_delay.write(x)
                x = delayed
            else:
                pre_delay.write(x)

            # Input diffusion: 4 cascaded allpass filters
            for ap in input_diffs:
                x = ap.process_sample(x)

            tank_input = x

            # --- LFO ---
            lfo_val = math.sin(lfo_phase) * mod_depth
            lfo_phase += lfo_inc
            if lfo_phase >= 2.0 * math.pi:
                lfo_phase -= 2.0 * math.pi

            # --- Single feedback ring ---
            # Read from end of loop (D4 feedback)
            loop_fb = loop_ds[3].read(d_lens[3])
            if not freeze:
                loop_fb = dc_blocker.process_sample(loop_fb)
            loop_fb *= feedback_gain

            # Inject input + feedback
            x = tank_input + loop_fb

            # Section 1: AP1 -> D1 (modulated) -> damping1
            x = loop_aps[0].process_sample(x)
            loop_ds[0].write(x)
            read_d1 = max(1.0, float(d_lens[0]) + lfo_val)
            x = loop_ds[0].read(read_d1)

            # Shimmer: octave-up via half-delay read
            if shimmer:
                half_d1 = max(1.0, read_d1 * 0.5)
                x = x + SHIMMER_BLEND * loop_ds[0].read(half_d1)

            if not freeze:
                x = damp1.process_sample(x)

            # Section 2: AP2 -> D2
            x = loop_aps[1].process_sample(x)
            loop_ds[1].write(x)
            x = loop_ds[1].read(d_lens[1])

            # Section 3: AP3 -> D3 -> damping2
            x = loop_aps[2].process_sample(x)
            loop_ds[2].write(x)
            x = loop_ds[2].read(d_lens[2])
            if not freeze:
                x = damp2.process_sample(x)

            # Section 4: AP4 -> D4 (feeds back to start)
            x = loop_aps[3].process_sample(x)
            loop_ds[3].write(x)

            # --- Output taps ---
            out_l = (loop_ds[TAP_FRACS_L[0][0]].read(taps_l[0]) +
                     loop_ds[TAP_FRACS_L[1][0]].read(taps_l[1]) +
                     loop_ds[TAP_FRACS_L[2][0]].read(taps_l[2]))

            out_r = (loop_ds[TAP_FRACS_R[0][0]].read(taps_r[0]) +
                     loop_ds[TAP_FRACS_R[1][0]].read(taps_r[1]) +
                     loop_ds[TAP_FRACS_R[2][0]].read(taps_r[2]))

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

        # Store LFO phase
        self._lfo_phase = lfo_phase

        # Mono mode: copy left to right
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
        if "loop_length" in params:
            self._loop_length = params["loop_length"]
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
        for ap in self._loop_allpasses:
            ap.reset()
        for dl in self._loop_delays:
            dl.reset()
        for f in self._damping_filters:
            f.reset()
        self._dc_blocker.reset()
        self._pre_delay_line.reset()
        self._lfo_phase = 0.0
        # Re-apply current params (resets delay lengths to current scale)
        self._scale_params()

    @property
    def param_specs(self) -> dict:
        """Parameter specifications for UI/automation."""
        return {
            "decay": {
                "type": "knob", "min": 0, "max": 100, "default": 60,
                "label": "Decay",
            },
            "loop_length": {
                "type": "knob", "min": 0, "max": 100, "default": 50,
                "label": "Loop Length",
            },
            "damping": {
                "type": "knob", "min": 0, "max": 100, "default": 40,
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
        """Return C typedef struct for the Single-Loop Tank state."""
        # Compute max buffer sizes at max scale
        max_scale = LOOP_SCALE_MAX + 0.1
        ap_sizes = [int(d * max_scale) + MAX_MOD_EXCURSION + 4 for d in LOOP_AP_BASE]
        d_sizes = [int(d * max_scale) + MAX_MOD_EXCURSION + 4 for d in LOOP_D_BASE]
        input_ap_sizes = [_scale_29761(l) for l in INPUT_AP_LENGTHS_29761]

        return f"""\
typedef struct {{
    // Input diffusion allpass buffers
    float input_ap_buf_0[{input_ap_sizes[0]}];
    float input_ap_buf_1[{input_ap_sizes[1]}];
    float input_ap_buf_2[{input_ap_sizes[2]}];
    float input_ap_buf_3[{input_ap_sizes[3]}];
    int input_ap_write_idx[4];
    float input_ap_gain[4];  // {{0.75, 0.75, 0.625, 0.625}}

    // Loop allpass buffers
    float loop_ap_buf_0[{ap_sizes[0]}];
    float loop_ap_buf_1[{ap_sizes[1]}];
    float loop_ap_buf_2[{ap_sizes[2]}];
    float loop_ap_buf_3[{ap_sizes[3]}];
    int loop_ap_write_idx[4];
    float loop_ap_gain;       // 0.6

    // Loop delay buffers
    float loop_d_buf_0[{d_sizes[0]}];
    float loop_d_buf_1[{d_sizes[1]}];
    float loop_d_buf_2[{d_sizes[2]}];
    float loop_d_buf_3[{d_sizes[3]}];
    int loop_d_write_idx[4];

    // 2 one-pole damping filter states
    float damp_coeff;
    float damp_state[2];

    // DC blocker state
    float dc_r;
    float dc_x_prev;
    float dc_y_prev;

    // LFO state
    float lfo_phase;
    float lfo_phase_inc;
    float mod_depth;

    // Feedback and delay config
    float feedback_gain;
    int loop_ap_lens[4];
    int loop_d_lens[4];
    int tap_l[3];
    int tap_r[3];

    // Pre-delay line
    float pre_delay_buf[{MAX_PRE_DELAY_SAMPLES + 4}];
    int pre_delay_write_idx;
    int pre_delay_samples;

    // Config
    int sample_rate;
    int frozen;
    int shimmer;
    float width;
    float mix;
}} DattorroSingleLoopState;
"""

    def to_c_process_fn(self) -> str:
        """Return C process function template for Single-Loop Tank."""
        return """\
void dattorro_single_loop_process(DattorroSingleLoopState* state,
                                  const float* input,
                                  float* output_left, float* output_right,
                                  int num_samples) {
    float wet1 = (1.0f + state->width) / 2.0f;
    float wet2 = (1.0f - state->width) / 2.0f;
    float mix_wet = state->mix / 100.0f;
    float mix_dry = 1.0f - mix_wet;
    float freeze_gain = state->frozen ? 3.0f : 1.0f;

    for (int i = 0; i < num_samples; i++) {
        float dry = input[i];
        float x = state->frozen ? 0.0f : dry;

        // 1. Pre-delay (circular buffer)
        if (state->pre_delay_samples > 0) {
            // read then write
        }

        // 2. Input diffusion (4 cascaded allpass filters)
        for (int d = 0; d < 4; d++) {
            // allpass: v = x + g * buf[read]; y = buf[read] - g * v; buf[write] = v
        }
        float tank_input = x;

        // 3. LFO
        float lfo_val = sinf(state->lfo_phase) * state->mod_depth;
        state->lfo_phase += state->lfo_phase_inc;
        if (state->lfo_phase >= 2.0f * M_PI)
            state->lfo_phase -= 2.0f * M_PI;

        // 4. Read feedback from D4
        float loop_fb = /* delay_read(loop_d_3, d_lens[3]) */;
        if (!state->frozen) {
            // DC blocker: y = x - x_prev + R * y_prev
            float dc_y = loop_fb - state->dc_x_prev + state->dc_r * state->dc_y_prev;
            state->dc_x_prev = loop_fb;
            state->dc_y_prev = dc_y;
            loop_fb = dc_y;
        }
        loop_fb *= state->feedback_gain;

        x = tank_input + loop_fb;

        // 5. Section 1: AP1 -> D1 (modulated) -> damping1
        // x = allpass(loop_ap_0, x);
        // delay_write(loop_d_0, x);
        // x = delay_read(loop_d_0, d_lens[0] + lfo_val);
        // if (!frozen) x = one_pole(damp_0, x);

        // 6. Section 2: AP2 -> D2
        // 7. Section 3: AP3 -> D3 -> damping2
        // 8. Section 4: AP4 -> D4

        // 9. Output taps
        float out_l = /* tap reads */ * 1.2f * freeze_gain;
        float out_r = /* tap reads */ * 1.2f * freeze_gain;

        // 10. Width crossmix + dry/wet mix + clip
        float final_l = dry * mix_dry + (out_l * wet1 + out_r * wet2) * mix_wet;
        float final_r = dry * mix_dry + (out_r * wet1 + out_l * wet2) * mix_wet;
        if (final_l > 1.0f) final_l = 1.0f;
        if (final_l < -1.0f) final_l = -1.0f;
        if (final_r > 1.0f) final_r = 1.0f;
        if (final_r < -1.0f) final_r = -1.0f;

        output_left[i] = final_l;
        output_right[i] = final_r;
    }
}
"""
