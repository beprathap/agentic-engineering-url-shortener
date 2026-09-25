"""Structured JSON logging to stdout, tagged with run_id (plan.md §Observability, ADR-010).

This is the secondary, human-readable operational view. The persisted
AuditEvent table (src/persistence/orchestration_store.py) remains the durable
source of truth (NFR-006) — evidence must not depend on log retention.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        # stderr, not stdout: keeps stdout clean for actual program output
        # (e.g. a CLI/script printing a result) - a real regression this file
        # caused once and fixed (see Phase 12 convergence task T118 commit).
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = True  # allow pytest's caplog to capture in tests
    return logger


def log_event(logger: logging.Logger, run_id: str, action: str, message: str = "") -> None:
    """Emit one structured JSON log line tagged with run_id, per NFR-005."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "action": action,
        "message": message,
    }
    logger.info(json.dumps(record))
