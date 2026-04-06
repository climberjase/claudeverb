"""Tests for signal-flow DOT diagram generation (to_dot()) on all algorithms.

Validates that every registered algorithm produces valid Graphviz DOT strings
at both block and component detail levels, with correct node counts and
parameter values embedded in labels.
"""

from __future__ import annotations

import re

import pytest

from claudeverb.algorithms import ALGORITHM_REGISTRY


def _count_nodes(dot_str: str) -> int:
    """Count node definitions in a DOT string.

    Counts lines matching the pattern: identifier [label=...
    Excludes edge definitions (lines with ->).
    """
    count = 0
    for line in dot_str.splitlines():
        stripped = line.strip()
        # Skip edges, subgraph declarations, and closing braces
        if "->" in stripped:
            continue
        if stripped.startswith("subgraph"):
            continue
        if stripped in ("{", "}", ""):
            continue
        # Match node definitions: name [label="..."]
        if re.search(r'\[label="[^"]*"', stripped):
            count += 1
    return count


def _instantiate(name: str):
    """Instantiate an algorithm by registry name."""
    cls = ALGORITHM_REGISTRY[name]
    return cls()


class TestAllAlgorithmsHaveToDot:
    """Test that all registered algorithms have a working to_dot() method."""

    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    def test_to_dot_block_returns_string(self, algo_name: str) -> None:
        algo = _instantiate(algo_name)
        result = algo.to_dot("block")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    def test_to_dot_component_returns_string(self, algo_name: str) -> None:
        algo = _instantiate(algo_name)
        result = algo.to_dot("component")
        assert isinstance(result, str)
        assert len(result) > 0


class TestDotContainsDigraph:
    """Test that DOT output contains required digraph keyword."""

    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    def test_block_contains_digraph(self, algo_name: str) -> None:
        algo = _instantiate(algo_name)
        result = algo.to_dot("block")
        assert "digraph" in result

    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    def test_component_contains_digraph(self, algo_name: str) -> None:
        algo = _instantiate(algo_name)
        result = algo.to_dot("component")
        assert "digraph" in result


class TestDotBlockLevelNodeCount:
    """Test that block-level diagrams have 5-10 nodes."""

    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    def test_block_node_count(self, algo_name: str) -> None:
        algo = _instantiate(algo_name)
        dot = algo.to_dot("block")
        count = _count_nodes(dot)
        assert 5 <= count <= 10, (
            f"{algo_name} block level has {count} nodes (expected 5-10)"
        )


class TestDotComponentLevelNodeCount:
    """Test that component-level diagrams have 15-30 nodes."""

    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    def test_component_node_count(self, algo_name: str) -> None:
        algo = _instantiate(algo_name)
        dot = algo.to_dot("component")
        count = _count_nodes(dot)
        assert 15 <= count <= 30, (
            f"{algo_name} component level has {count} nodes (expected 15-30)"
        )


class TestDotContainsParamValues:
    """Test that DOT output contains parameter values from params dict."""

    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    def test_default_param_values_in_dot(self, algo_name: str) -> None:
        """Verify that at least some default param values appear in DOT labels."""
        algo = _instantiate(algo_name)
        specs = algo.param_specs
        # Get default values for knob-type params
        defaults = {
            k: v["default"] for k, v in specs.items()
            if v.get("type") == "knob"
        }
        dot = algo.to_dot("block", params=defaults)
        # At least one default value should appear as a string in the DOT
        found_any = False
        for val in defaults.values():
            if str(val) in dot:
                found_any = True
                break
        assert found_any, (
            f"{algo_name}: no default param values found in block DOT output"
        )

    def test_custom_param_values_in_dot(self) -> None:
        """Verify custom param values appear in DOT when passed explicitly."""
        # Use freeverb as a representative test
        algo = _instantiate("freeverb")
        custom_params = {"room_size": 42, "damping": 88}
        dot = algo.to_dot("block", params=custom_params)
        assert "42" in dot, "Custom room_size=42 not found in DOT"
        assert "88" in dot, "Custom damping=88 not found in DOT"
