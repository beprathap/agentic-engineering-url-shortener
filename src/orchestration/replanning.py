"""Dynamic replanning on material upstream artifact change (ADR-009, FR-ORC-012/013)."""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass

from src.orchestration.engine import OrchestrationEngine

_VERSIONS_TABLE = "design_versions"


@dataclass
class DesignVersion:
    run_id: str
    version: int
    contract_shape: dict


def _ensure_versions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_VERSIONS_TABLE} (
            run_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            contract_shape TEXT NOT NULL,
            PRIMARY KEY (run_id, version)
        )
        """
    )
    conn.commit()


def register_design_version(
    conn: sqlite3.Connection,
    lock: threading.Lock,
    run_id: str,
    contract_shape: dict,
) -> DesignVersion:
    with lock:
        _ensure_versions_table(conn)
        conn.execute(
            f"INSERT INTO {_VERSIONS_TABLE} (run_id, version, contract_shape) VALUES (?, ?, ?)",
            (run_id, 1, json.dumps(contract_shape)),
        )
        conn.commit()
    return DesignVersion(run_id=run_id, version=1, contract_shape=contract_shape)


def revise_design(
    engine: OrchestrationEngine,
    conn: sqlite3.Connection,
    lock: threading.Lock,
    run_id: str,
    new_contract_shape: dict,
    built_against_version: int,
) -> DesignVersion:
    """Revise a run's design artifact. If the contract *shape* changes (material,
    per Plan §2's "every API or schema change must identify version impact"),
    bump the version, suspend downstream work back to N7, and require it to
    pass N8 again (ADR-009) — governance is never bypassed for replanned work.
    If the shape is unchanged (cosmetic), no version bump and no replanning.
    """
    with lock:
        _ensure_versions_table(conn)
        row = conn.execute(
            f"SELECT contract_shape FROM {_VERSIONS_TABLE} WHERE run_id = ? AND version = ?",
            (run_id, built_against_version),
        ).fetchone()
    previous_shape = json.loads(row["contract_shape"])

    if new_contract_shape == previous_shape:
        return DesignVersion(run_id=run_id, version=built_against_version, contract_shape=previous_shape)

    new_version = built_against_version + 1
    with lock:
        conn.execute(
            f"INSERT INTO {_VERSIONS_TABLE} (run_id, version, contract_shape) VALUES (?, ?, ?)",
            (run_id, new_version, json.dumps(new_contract_shape)),
        )
        conn.commit()

    engine.emit(
        run_id,
        actor_type="system",
        action="dependency_staleness_detected",
        result="success",
        affected_artifact=f"design_v{built_against_version}",
        reason=f"contract shape changed: {previous_shape} -> {new_contract_shape}",
    )
    engine.transition(run_id, to_stage="N7", status="running", action="replanning_triggered")

    return DesignVersion(run_id=run_id, version=new_version, contract_shape=new_contract_shape)
