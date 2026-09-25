"""Repositories for orchestration governance entities (data-model.md, ADR-003).

AuditEvent exposes no update/delete method by design (NFR-006, ADR-010's
append-only consequence) — do not add one without a governed change.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime


def _to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _from_iso(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s is not None else None


@dataclass
class WorkflowInstance:
    run_id: str
    requirement_id: str
    current_stage: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Decision:
    decision_id: str
    run_id: str
    decision_type: str
    actor_role_capacity: str
    rationale: str
    created_at: datetime
    conditions: str | None = None


@dataclass
class AuditEvent:
    event_id: str
    run_id: str
    actor_type: str
    action: str
    occurred_at: datetime
    result: str
    affected_artifact: str | None = None
    reason: str | None = None


@dataclass
class PolicyCheckResult:
    result_id: str
    run_id: str
    policy_id: str
    policy_version: str
    outcome: str
    evaluated_at: datetime
    exception_id: str | None = None


@dataclass
class PolicyException:
    exception_id: str
    applicable_policy: str
    reason: str
    scope: str
    approving_authority: str
    compensating_control: str
    approved_at: datetime
    expires_at: datetime


class WorkflowInstanceRepository:
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self._conn = conn
        self._lock = lock

    def create(self, instance: WorkflowInstance) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workflow_instances (run_id, requirement_id, current_stage, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    instance.run_id,
                    instance.requirement_id,
                    instance.current_stage,
                    instance.status,
                    _to_iso(instance.created_at),
                    _to_iso(instance.updated_at),
                ),
            )
            self._conn.commit()

    def get(self, run_id: str) -> WorkflowInstance | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workflow_instances WHERE run_id = ?", (run_id,)
            ).fetchone()
            return self._row_to_instance(row) if row else None

    def update_stage(self, run_id: str, current_stage: str, status: str, updated_at: datetime) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE workflow_instances SET current_stage = ?, status = ?, updated_at = ? WHERE run_id = ?",
                (current_stage, status, _to_iso(updated_at), run_id),
            )
            self._conn.commit()

    @staticmethod
    def _row_to_instance(row: sqlite3.Row) -> WorkflowInstance:
        return WorkflowInstance(
            run_id=row["run_id"],
            requirement_id=row["requirement_id"],
            current_stage=row["current_stage"],
            status=row["status"],
            created_at=_from_iso(row["created_at"]),
            updated_at=_from_iso(row["updated_at"]),
        )


class DecisionRepository:
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self._conn = conn
        self._lock = lock

    def create(self, decision: Decision) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO decisions (decision_id, run_id, decision_type, actor_role_capacity, rationale, conditions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.run_id,
                    decision.decision_type,
                    decision.actor_role_capacity,
                    decision.rationale,
                    decision.conditions,
                    _to_iso(decision.created_at),
                ),
            )
            self._conn.commit()

    def list_for_run(self, run_id: str) -> list[Decision]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM decisions WHERE run_id = ? ORDER BY created_at", (run_id,)
            ).fetchall()
            return [
                Decision(
                    decision_id=r["decision_id"],
                    run_id=r["run_id"],
                    decision_type=r["decision_type"],
                    actor_role_capacity=r["actor_role_capacity"],
                    rationale=r["rationale"],
                    conditions=r["conditions"],
                    created_at=_from_iso(r["created_at"]),
                )
                for r in rows
            ]


class AuditEventRepository:
    """Append-only by design: no update()/delete() method exists (NFR-006, ADR-010)."""

    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self._conn = conn
        self._lock = lock

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO audit_events (event_id, run_id, actor_type, action, occurred_at, affected_artifact, result, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.run_id,
                    event.actor_type,
                    event.action,
                    _to_iso(event.occurred_at),
                    event.affected_artifact,
                    event.result,
                    event.reason,
                ),
            )
            self._conn.commit()

    def list_for_run(self, run_id: str) -> list[AuditEvent]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit_events WHERE run_id = ? ORDER BY occurred_at", (run_id,)
            ).fetchall()
            return [
                AuditEvent(
                    event_id=r["event_id"],
                    run_id=r["run_id"],
                    actor_type=r["actor_type"],
                    action=r["action"],
                    occurred_at=_from_iso(r["occurred_at"]),
                    affected_artifact=r["affected_artifact"],
                    result=r["result"],
                    reason=r["reason"],
                )
                for r in rows
            ]


class PolicyCheckResultRepository:
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self._conn = conn
        self._lock = lock

    def create(self, result: PolicyCheckResult) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO policy_check_results (result_id, run_id, policy_id, policy_version, outcome, evaluated_at, exception_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.result_id,
                    result.run_id,
                    result.policy_id,
                    result.policy_version,
                    result.outcome,
                    _to_iso(result.evaluated_at),
                    result.exception_id,
                ),
            )
            self._conn.commit()

    def list_for_run(self, run_id: str) -> list[PolicyCheckResult]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM policy_check_results WHERE run_id = ?", (run_id,)
            ).fetchall()
            return [
                PolicyCheckResult(
                    result_id=r["result_id"],
                    run_id=r["run_id"],
                    policy_id=r["policy_id"],
                    policy_version=r["policy_version"],
                    outcome=r["outcome"],
                    evaluated_at=_from_iso(r["evaluated_at"]),
                    exception_id=r["exception_id"],
                )
                for r in rows
            ]


class PolicyExceptionRepository:
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self._conn = conn
        self._lock = lock

    def create(self, exception: PolicyException) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO policy_exceptions
                    (exception_id, applicable_policy, reason, scope, approving_authority, compensating_control, approved_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exception.exception_id,
                    exception.applicable_policy,
                    exception.reason,
                    exception.scope,
                    exception.approving_authority,
                    exception.compensating_control,
                    _to_iso(exception.approved_at),
                    _to_iso(exception.expires_at),
                ),
            )
            self._conn.commit()

    def get(self, exception_id: str) -> PolicyException | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM policy_exceptions WHERE exception_id = ?", (exception_id,)
            ).fetchone()
            if not row:
                return None
            return PolicyException(
                exception_id=row["exception_id"],
                applicable_policy=row["applicable_policy"],
                reason=row["reason"],
                scope=row["scope"],
                approving_authority=row["approving_authority"],
                compensating_control=row["compensating_control"],
                approved_at=_from_iso(row["approved_at"]),
                expires_at=_from_iso(row["expires_at"]),
            )


def new_id() -> str:
    return str(uuid.uuid4())
