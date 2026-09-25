"""API routes for orchestration workflow ingestion/inspection (T050)."""

from __future__ import annotations

import sqlite3
import threading

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.orchestration.engine import OrchestrationEngine
from src.orchestration.nodes.n1_ingestion import EmptyRequirementError, ingest_requirement
from src.persistence.orchestration_store import WorkflowInstanceRepository

router = APIRouter()


class CreateWorkflowRequest(BaseModel):
    raw_input: str


class WorkflowStateResponse(BaseModel):
    run_id: str
    requirement_id: str
    current_stage: str
    status: str
    created_at: str
    updated_at: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str


def register_workflow_routes(
    router: APIRouter,
    engine: OrchestrationEngine,
    workflow_repo: WorkflowInstanceRepository,
    conn: sqlite3.Connection,
    lock: threading.Lock,
) -> None:
    @router.post("/v1/workflows", status_code=201, response_model=None)
    def create_workflow(payload: CreateWorkflowRequest):
        try:
            result = ingest_requirement(engine, conn, lock, raw_input=payload.raw_input)
        except EmptyRequirementError as exc:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(error_code="EMPTY_REQUIREMENT", message=str(exc)).model_dump(),
            )

        instance = workflow_repo.get(result.run_id)
        return WorkflowStateResponse(
            run_id=instance.run_id,
            requirement_id=instance.requirement_id,
            current_stage=instance.current_stage,
            status=instance.status,
            created_at=instance.created_at.isoformat(),
            updated_at=instance.updated_at.isoformat(),
        )

    @router.get("/v1/workflows/{run_id}", response_model=None, responses={404: {"model": ErrorResponse}})
    def get_workflow(run_id: str):
        instance = workflow_repo.get(run_id)
        if instance is None:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(error_code="NOT_FOUND", message="No such workflow instance.").model_dump(),
            )
        return WorkflowStateResponse(
            run_id=instance.run_id,
            requirement_id=instance.requirement_id,
            current_stage=instance.current_stage,
            status=instance.status,
            created_at=instance.created_at.isoformat(),
            updated_at=instance.updated_at.isoformat(),
        )
