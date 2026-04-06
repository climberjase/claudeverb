"""Shared DOT graph construction helpers for signal-flow diagrams.

Provides consistent node styling, edge creation, subgraph grouping,
and digraph wrapping for all reverb algorithm to_dot() methods.

Color scheme:
  - Input/Output nodes: light blue (#d0e8ff)
  - DSP blocks: light yellow (#ffffcc)
  - Feedback paths: dashed red edges
"""

from __future__ import annotations


def dsp_node(name: str, label: str, shape: str = "box",
             style: str = "rounded,filled") -> str:
    """Return a DOT node string for a DSP processing block.

    Args:
        name: Node identifier (no spaces).
        label: Display label (may contain special chars).
        shape: Graphviz shape (default: box).
        style: Graphviz style (default: rounded,filled).

    Returns:
        DOT node definition string.
    """
    escaped = label.replace('"', '\\"')
    return (
        f'    {name} [label="{escaped}", shape={shape}, '
        f'style="{style}", fillcolor="#ffffcc", fontname="Arial"];\n'
    )


def io_node(name: str, label: str) -> str:
    """Return a DOT node string for an input/output terminal.

    Args:
        name: Node identifier.
        label: Display label.

    Returns:
        DOT node definition string with ellipse shape and light blue fill.
    """
    escaped = label.replace('"', '\\"')
    return (
        f'    {name} [label="{escaped}", shape=ellipse, '
        f'style="filled", fillcolor="#d0e8ff", fontname="Arial"];\n'
    )


def edge(src: str, dst: str, label: str | None = None,
         style: str | None = None, color: str | None = None) -> str:
    """Return a DOT edge string.

    Args:
        src: Source node name.
        dst: Destination node name.
        label: Optional edge label.
        style: Optional edge style (e.g., "dashed").
        color: Optional edge color (e.g., "red").

    Returns:
        DOT edge definition string.
    """
    attrs = []
    if label:
        attrs.append(f'label="{label}"')
    if style:
        attrs.append(f'style="{style}"')
    if color:
        attrs.append(f'color="{color}"')
    if attrs:
        attrs.append('fontname="Arial"')
    attr_str = f' [{", ".join(attrs)}]' if attrs else ""
    return f"    {src} -> {dst}{attr_str};\n"


def feedback_edge(src: str, dst: str, label: str | None = None) -> str:
    """Return a DOT edge string styled as a feedback path (dashed red).

    Args:
        src: Source node name.
        dst: Destination node name.
        label: Optional edge label.

    Returns:
        DOT edge definition string with dashed red styling.
    """
    return edge(src, dst, label=label, style="dashed", color="red")


def subgraph(name: str, label: str, nodes_dot: str,
             color: str = "#cccccc") -> str:
    """Return a DOT cluster subgraph string for grouping DSP stages.

    Args:
        name: Subgraph identifier (will be prefixed with cluster_).
        label: Display label for the subgraph.
        nodes_dot: DOT string containing the nodes in this subgraph.
        color: Border color (default: light gray).

    Returns:
        DOT subgraph definition string.
    """
    return (
        f"    subgraph cluster_{name} {{\n"
        f'        label="{label}";\n'
        f'        style="rounded,dashed";\n'
        f'        color="{color}";\n'
        f'        fontname="Arial";\n'
        f"{nodes_dot}"
        f"    }}\n"
    )


def digraph_wrap(name: str, body: str, rankdir: str = "LR") -> str:
    """Wrap body content in a digraph declaration.

    Args:
        name: Graph name.
        body: DOT content (nodes, edges, subgraphs).
        rankdir: Layout direction (default: LR = left to right).

    Returns:
        Complete DOT digraph string.
    """
    return (
        f"digraph {name} {{\n"
        f'    rankdir={rankdir};\n'
        f'    fontname="Arial";\n'
        f'    node [fontsize=10];\n'
        f'    edge [fontsize=8];\n'
        f"{body}"
        f"}}\n"
    )
