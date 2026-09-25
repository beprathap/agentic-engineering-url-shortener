"""API routes for short-link creation (T016+)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from src.domain.short_link import compute_default_expiration, generate_unique_short_code, utcnow
from src.domain.validation import InvalidUrlError, validate_url
from src.persistence.short_links import ShortLink, ShortLinkRepository

router = APIRouter()


class CreateShortLinkRequest(BaseModel):
    target_url: str
    expires_at: str | None = None


class ShortLinkResponse(BaseModel):
    short_code: str
    target_url: str
    created_at: str
    expires_at: str | None
    status: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class ShortLinkDetailResponse(ShortLinkResponse):
    redirect_count: int
    last_accessed_at: str | None


def register_links_routes(router: APIRouter, repo: ShortLinkRepository) -> None:
    @router.post("/v1/links", status_code=201, response_model=None, responses={400: {"model": ErrorResponse}})
    def create_short_link(payload: CreateShortLinkRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        try:
            if idempotency_key is not None:
                existing = repo.find_by_idempotency_key(idempotency_key)
                if existing is not None:
                    return ShortLinkResponse(
                        short_code=existing.short_code,
                        target_url=existing.target_url,
                        created_at=existing.created_at.isoformat(),
                        expires_at=existing.expires_at.isoformat() if existing.expires_at else None,
                        status=existing.status,
                    )

            try:
                validate_url(payload.target_url)
            except InvalidUrlError as exc:
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(error_code="INVALID_URL", message=str(exc)).model_dump(),
                )

            code = generate_unique_short_code(repo.is_active_code_taken)
            created_at = utcnow()
            if payload.expires_at is not None:
                expires_at = datetime.fromisoformat(payload.expires_at)
            else:
                expires_at = compute_default_expiration(created_at)
            link = ShortLink(
                short_code=code,
                target_url=payload.target_url,
                created_at=created_at,
                expires_at=expires_at,
                status="active",
                idempotency_key=idempotency_key,
            )
            repo.create(link)

            return ShortLinkResponse(
                short_code=link.short_code,
                target_url=link.target_url,
                created_at=link.created_at.isoformat(),
                expires_at=link.expires_at.isoformat() if link.expires_at else None,
                status=link.status,
            )
        except sqlite3.Error:
            # FR-SVC-010: fail safely, no internal implementation detail in the response.
            return JSONResponse(
                status_code=503,
                content=ErrorResponse(
                    error_code="STORE_UNAVAILABLE",
                    message="Unable to persist the short link at this time.",
                ).model_dump(),
            )

    @router.get("/v1/links/{short_code}", response_model=None, responses={404: {"model": ErrorResponse}})
    def get_short_link_detail(short_code: str):
        link = repo.get(short_code)
        if link is None:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(error_code="NOT_FOUND", message="No such short link.").model_dump(),
            )
        count, last_accessed = repo.get_analytics(short_code)
        return ShortLinkDetailResponse(
            short_code=link.short_code,
            target_url=link.target_url,
            created_at=link.created_at.isoformat(),
            expires_at=link.expires_at.isoformat() if link.expires_at else None,
            status=link.status,
            redirect_count=count,
            last_accessed_at=last_accessed.isoformat() if last_accessed else None,
        )

    @router.get("/{short_code}", response_model=None, responses={404: {"model": ErrorResponse}, 410: {"model": ErrorResponse}})
    def resolve_redirect(short_code: str):
        link = repo.get(short_code)
        now = utcnow()

        if link is None:
            repo.record_redirect_event(short_code, now, "not_found")
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(error_code="NOT_FOUND", message="No such short link.").model_dump(),
            )

        if link.expires_at is not None and link.expires_at < now:
            repo.record_redirect_event(short_code, now, "expired")
            return JSONResponse(
                status_code=410,
                content=ErrorResponse(error_code="EXPIRED", message="This short link has expired.").model_dump(),
            )

        repo.record_redirect_event(short_code, now, "redirected")
        return RedirectResponse(url=link.target_url, status_code=302)
