"""The 14-node orchestration DAG (FR-ORC-001, CON-003, ADR-005).

Declares node identity and structural metadata as data, matching
contracts/orchestration-state-machine.md exactly. Node *behavior* lives in
src/orchestration/nodes/; this module is the graph's shape, not its execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NodeDef:
    node_id: str
    purpose: str
    responsible_actor: str  # "system" | "agent" | "human"
    allowed_transitions: tuple[str, ...]
    conditional: bool = False  # True for N4/N4b, which are only entered on certain classifications


NODES: dict[str, NodeDef] = {
    "N1": NodeDef("N1", "Requirement Ingestion", "system", ("N2",)),
    "N2": NodeDef("N2", "Requirement Normalization", "agent", ("N3",)),
    "N3": NodeDef("N3", "Ambiguity Detection & Classification", "system", ("N4", "N4b", "N5")),
    "N4": NodeDef("N4", "Human Clarification", "human", ("N2", "SAFE_STOP"), conditional=True),
    "N4b": NodeDef("N4b", "Impact Analysis", "agent", ("N5",), conditional=True),
    "N5": NodeDef("N5", "Human Approval Gate: Requirements", "human", ("N6", "SAFE_STOP")),
    "N6": NodeDef("N6", "Task Decomposition", "agent", ("N7",)),
    "N7": NodeDef("N7", "Architecture & Design", "agent", ("N8",)),
    "N8": NodeDef("N8", "Human Approval Gate: Architecture", "human", ("N9", "SAFE_STOP")),
    "N9": NodeDef("N9", "Implementation (TDD)", "agent", ("N10", "N11", "N12")),
    "N10": NodeDef("N10", "Testing", "system", ("N13",)),
    "N11": NodeDef("N11", "Documentation", "agent", ("N13",)),
    "N12": NodeDef("N12", "Security & Risk Validation", "system", ("N13",)),
    "N13": NodeDef("N13", "Release-Readiness Determination", "human", ("N14",)),
    "N14": NodeDef("N14", "Final Engineering Summary", "system", ()),  # terminal
}

# The synchronization join: N9 fans out to these three, which must all
# complete before N13 proceeds (FR-ORC-015).
JOIN_BEFORE_N13 = ("N10", "N11", "N12")

ENTRY_NODE = "N1"
TERMINAL_NODES = ("N14", "SAFE_STOP")
