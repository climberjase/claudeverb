"""Tests for C export functionality: to_c_struct/to_c_process_fn on all algorithms,
and the centralized c_export.py module (generate_header, generate_source,
estimate_ram, generate_audio_callback, export_to_files).
"""

from __future__ import annotations

import re

import pytest

from claudeverb.algorithms import ALGORITHM_REGISTRY


# ---------------------------------------------------------------------------
# Task 1 tests: to_c_struct() and to_c_process_fn() on all algorithms
# ---------------------------------------------------------------------------


class TestFreeverbCExport:
    """Freeverb-specific C struct and process function tests."""

    @pytest.fixture
    def algo(self):
        from claudeverb.algorithms.freeverb import Freeverb
        return Freeverb()

    def test_to_c_struct_contains_typedef(self, algo):
        c_struct = algo.to_c_struct()
        assert "typedef struct" in c_struct

    def test_to_c_struct_contains_state_name(self, algo):
        c_struct = algo.to_c_struct()
        assert "FreeverbState" in c_struct

    def test_to_c_process_fn_contains_function(self, algo):
        c_fn = algo.to_c_process_fn()
        assert "void freeverb_process" in c_fn

    def test_to_c_struct_has_comb_buffers(self, algo):
        """Freeverb must have 8 comb filter delay buffers per channel."""
        c_struct = algo.to_c_struct()
        # Should have comb buffer declarations
        comb_bufs = re.findall(r"float\s+comb_buf_\w+\[\d+\]", c_struct)
        assert len(comb_bufs) >= 8, f"Expected >= 8 comb buffers, found {len(comb_bufs)}"

    def test_to_c_struct_has_allpass_buffers(self, algo):
        """Freeverb must have 4 allpass filter delay buffers per channel."""
        c_struct = algo.to_c_struct()
        allpass_bufs = re.findall(r"float\s+allpass_buf_\w+\[\d+\]", c_struct)
        assert len(allpass_bufs) >= 4, f"Expected >= 4 allpass buffers, found {len(allpass_bufs)}"


class TestDattorroPlateCExport:
    """DattorroPlate-specific C struct and process function tests."""

    @pytest.fixture
    def algo(self):
        from claudeverb.algorithms.dattorro_plate import DattorroPlate
        return DattorroPlate()

    def test_to_c_struct_contains_typedef(self, algo):
        c_struct = algo.to_c_struct()
        assert "typedef struct" in c_struct

    def test_to_c_struct_contains_state_name(self, algo):
        c_struct = algo.to_c_struct()
        assert "DattorroPlateState" in c_struct

    def test_to_c_process_fn_contains_function(self, algo):
        c_fn = algo.to_c_process_fn()
        assert "void dattorro_plate_process" in c_fn

    def test_to_c_struct_has_input_diffuser_buffers(self, algo):
        """DattorroPlate must have 4 input diffuser allpass buffers."""
        c_struct = algo.to_c_struct()
        input_ap_bufs = re.findall(r"float\s+input_ap_buf_\d\[\d+\]", c_struct)
        assert len(input_ap_bufs) == 4, f"Expected 4 input AP buffers, found {len(input_ap_bufs)}"

    def test_to_c_struct_has_tank_delay_buffers(self, algo):
        """DattorroPlate must have 4 tank delay buffers."""
        c_struct = algo.to_c_struct()
        tank_bufs = re.findall(r"float\s+tank_delay_buf_\d\[\d+\]", c_struct)
        assert len(tank_bufs) == 4, f"Expected 4 tank delay buffers, found {len(tank_bufs)}"


@pytest.mark.parametrize("name,cls", list(ALGORITHM_REGISTRY.items()))
class TestAllAlgorithmsCExport:
    """Parametrized tests for all 9 algorithms in the registry."""

    def test_has_to_c_struct(self, name, cls):
        """Every algorithm must implement to_c_struct()."""
        algo = cls()
        assert hasattr(algo, "to_c_struct"), f"{name} missing to_c_struct()"
        result = algo.to_c_struct()
        assert isinstance(result, str)
        assert len(result) > 50, f"{name}.to_c_struct() too short"

    def test_has_to_c_process_fn(self, name, cls):
        """Every algorithm must implement to_c_process_fn()."""
        algo = cls()
        assert hasattr(algo, "to_c_process_fn"), f"{name} missing to_c_process_fn()"
        result = algo.to_c_process_fn()
        assert isinstance(result, str)
        assert len(result) > 50, f"{name}.to_c_process_fn() too short"

    def test_no_malloc_in_struct(self, name, cls):
        """No generated C code should contain malloc, calloc, or realloc."""
        algo = cls()
        c_struct = algo.to_c_struct()
        for forbidden in ("malloc", "calloc", "realloc"):
            assert forbidden not in c_struct, (
                f"{name}.to_c_struct() contains '{forbidden}'"
            )

    def test_no_malloc_in_process(self, name, cls):
        """No generated C process function should contain malloc, calloc, or realloc."""
        algo = cls()
        c_fn = algo.to_c_process_fn()
        for forbidden in ("malloc", "calloc", "realloc"):
            assert forbidden not in c_fn, (
                f"{name}.to_c_process_fn() contains '{forbidden}'"
            )

    def test_fixed_size_arrays(self, name, cls):
        """All delay buffers must be fixed-size arrays with compile-time constant sizes."""
        algo = cls()
        c_struct = algo.to_c_struct()
        # Find all array declarations: type name[size]
        arrays = re.findall(r"(?:float|int)\s+\w+\[([^\]]+)\]", c_struct)
        for size_expr in arrays:
            # Size must be a positive integer literal (compile-time constant)
            stripped = size_expr.strip()
            # Allow simple integer constants and expressions like N + M
            assert re.match(r"^[\d\s+\-*/]+$", stripped), (
                f"{name}.to_c_struct() has non-constant array size: [{stripped}]"
            )

    def test_struct_has_typedef(self, name, cls):
        """Every struct must have typedef struct."""
        algo = cls()
        c_struct = algo.to_c_struct()
        assert "typedef struct" in c_struct

    def test_process_fn_signature(self, name, cls):
        """Every process function must accept standard signature."""
        algo = cls()
        c_fn = algo.to_c_process_fn()
        assert "const float* input" in c_fn
        assert "float* output_left" in c_fn
        assert "float* output_right" in c_fn
        assert "int num_samples" in c_fn


# ---------------------------------------------------------------------------
# Task 2 tests: c_export.py module functions
# ---------------------------------------------------------------------------


from claudeverb.export.c_export import (
    generate_header,
    generate_source,
    generate_audio_callback,
    estimate_ram,
    export_to_files,
    _snake_case,
)


class TestSnakeCase:
    """Test the _snake_case helper."""

    def test_simple(self):
        assert _snake_case("Freeverb") == "freeverb"

    def test_two_words(self):
        assert _snake_case("DattorroPlate") == "dattorro_plate"

    def test_acronym(self):
        assert _snake_case("FDNReverb") == "fdn_reverb"

    def test_triple(self):
        assert _snake_case("DattorroSingleLoop") == "dattorro_single_loop"


class TestGenerateHeader:
    """Tests for generate_header()."""

    @pytest.fixture
    def freeverb(self):
        from claudeverb.algorithms.freeverb import Freeverb
        return Freeverb()

    @pytest.fixture
    def default_params(self):
        return {"room_size": 75, "damping": 25, "mix": 75}

    def test_include_guard(self, freeverb, default_params):
        header = generate_header(freeverb, default_params)
        assert "#ifndef FREEVERB_H" in header
        assert "#define FREEVERB_H" in header
        assert "#endif" in header

    def test_struct_typedef(self, freeverb, default_params):
        header = generate_header(freeverb, default_params)
        assert "typedef struct" in header
        assert "FreeverbState" in header

    def test_init_prototype(self, freeverb, default_params):
        header = generate_header(freeverb, default_params)
        assert "void freeverb_init(FreeverbState* state)" in header

    def test_process_prototype(self, freeverb, default_params):
        header = generate_header(freeverb, default_params)
        assert "void freeverb_process(FreeverbState* state" in header

    def test_param_comments(self, freeverb, default_params):
        header = generate_header(freeverb, default_params)
        assert "Room Size: 75" in header
        assert "Damping: 25" in header

    def test_timestamp_comment(self, freeverb, default_params):
        header = generate_header(freeverb, default_params)
        assert "Timestamp:" in header


class TestGenerateSource:
    """Tests for generate_source()."""

    @pytest.fixture
    def freeverb(self):
        from claudeverb.algorithms.freeverb import Freeverb
        return Freeverb()

    @pytest.fixture
    def default_params(self):
        return {"room_size": 75, "damping": 25, "mix": 75, "width": 100}

    def test_include_header(self, freeverb, default_params):
        source = generate_source(freeverb, default_params)
        assert '#include "Freeverb.h"' in source

    def test_init_function(self, freeverb, default_params):
        source = generate_source(freeverb, default_params)
        assert "void freeverb_init(FreeverbState* state)" in source

    def test_memset_zero(self, freeverb, default_params):
        source = generate_source(freeverb, default_params)
        assert "memset(state, 0" in source

    def test_param_defaults(self, freeverb, default_params):
        source = generate_source(freeverb, default_params)
        assert "state->room_size = 75" in source
        assert "state->damping = 25" in source

    def test_process_function(self, freeverb, default_params):
        source = generate_source(freeverb, default_params)
        assert "void freeverb_process" in source

    def test_param_values_in_comments(self, freeverb, default_params):
        source = generate_source(freeverb, default_params)
        # Parameter labels should appear as comments
        assert "Room Size" in source


class TestEstimateRam:
    """Tests for estimate_ram()."""

    @pytest.fixture
    def freeverb(self):
        from claudeverb.algorithms.freeverb import Freeverb
        return Freeverb()

    @pytest.fixture
    def fdn(self):
        from claudeverb.algorithms.fdn_reverb import FDNReverb
        return FDNReverb()

    def test_returns_required_keys(self, freeverb):
        ram = estimate_ram(freeverb)
        required_keys = {
            "delay_lines_kb", "filters_kb", "total_kb",
            "fits_sram", "fits_sdram",
        }
        assert required_keys.issubset(ram.keys())

    def test_total_kb_positive(self, freeverb):
        ram = estimate_ram(freeverb)
        assert ram["total_kb"] > 0

    def test_fits_sram_boolean(self, freeverb):
        ram = estimate_ram(freeverb)
        assert isinstance(ram["fits_sram"], bool)

    def test_fits_sdram_boolean(self, freeverb):
        ram = estimate_ram(freeverb)
        assert isinstance(ram["fits_sdram"], bool)

    def test_sdram_candidates_list(self, freeverb):
        ram = estimate_ram(freeverb)
        assert isinstance(ram["sdram_candidates"], list)

    def test_counts_float_arrays(self, freeverb):
        """RAM estimate should count float arrays from struct definition."""
        ram = estimate_ram(freeverb)
        # Freeverb has 16 comb buffers + 8 allpass buffers + pre-delay
        # Should be significantly more than 0
        assert ram["delay_lines_kb"] > 10, (
            f"Expected > 10 KB for Freeverb delays, got {ram['delay_lines_kb']}"
        )

    def test_breakdown_dict(self, freeverb):
        ram = estimate_ram(freeverb)
        assert "breakdown" in ram
        assert isinstance(ram["breakdown"], dict)
        assert len(ram["breakdown"]) > 0

    def test_reasonable_total_for_fdn(self, fdn):
        """FDN reverb should use reasonable RAM (< 100 KB)."""
        ram = estimate_ram(fdn)
        assert ram["total_kb"] < 100, f"FDN RAM too high: {ram['total_kb']} KB"
        assert ram["fits_sram"] is True


class TestGenerateAudioCallback:
    """Tests for generate_audio_callback()."""

    @pytest.fixture
    def freeverb(self):
        from claudeverb.algorithms.freeverb import Freeverb
        return Freeverb()

    @pytest.fixture
    def knob_mapping(self):
        return {
            "room_size": "KNOB_1",
            "damping": "KNOB_2",
            "mix": "KNOB_3",
        }

    def test_hothouse_include(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert '#include "hothouse.h"' in cb

    def test_daisysp_include(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert '#include "daisysp.h"' in cb

    def test_algo_include(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert '#include "Freeverb.h"' in cb

    def test_hothouse_namespace(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "using clevelandmusicco::Hothouse" in cb

    def test_audio_callback_function(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "void AudioCallback(" in cb

    def test_main_function(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "int main(void)" in cb

    def test_block_size_48(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "SetAudioBlockSize(48)" in cb

    def test_sample_rate_48k(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "SAI_48KHZ" in cb

    def test_knob_reads(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "KNOB_1" in cb
        assert "KNOB_2" in cb
        assert "room_size" in cb

    def test_init_call(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "freeverb_init(&state)" in cb

    def test_process_call(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "freeverb_process(&state" in cb

    def test_bypass_logic(self, freeverb, knob_mapping):
        cb = generate_audio_callback(freeverb, knob_mapping)
        assert "bypass" in cb

    def test_knob_mapping_uses_param_specs_range(self, freeverb, knob_mapping):
        """Knob init should use min/max from param_specs."""
        cb = generate_audio_callback(freeverb, knob_mapping)
        # room_size has min=0, max=100
        assert "0.0f, 100.0f" in cb


@pytest.mark.parametrize("name,cls", list(ALGORITHM_REGISTRY.items()))
class TestExportAllAlgorithms:
    """Test that c_export functions work for every registered algorithm."""

    def test_generate_header_works(self, name, cls):
        algo = cls()
        params = {k: v.get("default", 0) for k, v in algo.param_specs.items()
                  if v.get("type") == "knob"}
        header = generate_header(algo, params)
        assert "#ifndef" in header
        assert "typedef struct" in header

    def test_generate_source_works(self, name, cls):
        algo = cls()
        params = {k: v.get("default", 0) for k, v in algo.param_specs.items()
                  if v.get("type") == "knob"}
        source = generate_source(algo, params)
        assert "#include" in source
        assert "_init(" in source

    def test_estimate_ram_works(self, name, cls):
        algo = cls()
        ram = estimate_ram(algo)
        assert ram["total_kb"] > 0
        assert isinstance(ram["fits_sram"], bool)
