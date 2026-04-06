"""Abstract base class for reverb algorithms in claudeverb.

Provides float32/shape validation and defines the interface all reverb
algorithm implementations must satisfy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class ReverbAlgorithm(ABC):
    """Abstract base class for reverb algorithms.

    Subclasses implement the DSP logic; this base class enforces
    float32 dtype and valid audio shapes ((N,) mono or (2, N) stereo).

    Lifecycle:
        1. __init__() stores parameters
        2. _initialize() allocates delay lines / state (called once)
        3. process() validates then delegates to subclass
        4. update_params() allows real-time parameter changes
        5. reset() returns to initial state
    """

    @abstractmethod
    def _initialize(self) -> None:
        """Allocate internal DSP state (delay lines, filters, etc.).

        Called once after construction. Must use only fixed-size arrays
        and scalars (no dynamic allocation) for C portability.
        """

    @abstractmethod
    def _process_impl(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through the reverb algorithm.

        Args:
            audio: Validated float32 array, shape (N,) or (2, N).

        Returns:
            Processed audio, same shape and dtype as input.
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset all internal state to initial values."""

    @abstractmethod
    def update_params(self, params: dict) -> None:
        """Update algorithm parameters for real-time control.

        Args:
            params: Dictionary of parameter name -> value.
        """

    @property
    @abstractmethod
    def param_specs(self) -> dict:
        """Parameter specifications for UI/automation.

        Returns:
            Dictionary mapping parameter names to their specs
            (min, max, default, unit, etc.).
        """

    def to_dot(self, detail_level: str = "block",
               params: dict | None = None) -> str:
        """Generate a Graphviz DOT string representing the signal flow.

        Args:
            detail_level: Either "block" (5-10 nodes, major DSP stages)
                or "component" (15-30 nodes, individual elements).
            params: Parameter values to display in labels. If None,
                uses defaults from param_specs.

        Returns:
            DOT string suitable for rendering with Graphviz.
        """
        from claudeverb.export.dot_builder import (
            digraph_wrap, dsp_node, io_node, edge,
        )
        # Default placeholder for algorithms without custom to_dot()
        name = type(self).__name__
        body = io_node("input", "Input")
        body += dsp_node("algo", f"{name}\\n(no diagram yet)")
        body += io_node("output", "Output")
        body += edge("input", "algo")
        body += edge("algo", "output")
        return digraph_wrap(name, body)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Validate input and delegate to _process_impl.

        Args:
            audio: Input audio, must be float32 with shape (N,) or (2, N).

        Returns:
            Processed audio as float32 ndarray.

        Raises:
            TypeError: If audio is not float32.
            ValueError: If audio shape is not (N,) or (2, N).
        """
        if audio.dtype != np.float32:
            raise TypeError(
                f"ReverbAlgorithm.process() requires float32 input, got {audio.dtype}"
            )
        if audio.ndim == 1:
            pass  # (N,) mono -- valid
        elif audio.ndim == 2 and audio.shape[0] == 2:
            pass  # (2, N) stereo -- valid
        else:
            raise ValueError(
                f"Audio must be shape (N,) for mono or (2, N) for stereo, "
                f"got shape {audio.shape}"
            )
        return self._process_impl(audio)
