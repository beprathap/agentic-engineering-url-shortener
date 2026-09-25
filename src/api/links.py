"""API routes for short-link creation (T016+)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.domain.short_link import generate_unique_short_code, utcnow
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


def register_links_routes(router: APIRouter, repo: ShortLinkRepository) -> None:
    @router.post("/v1/links", status_code=201, response_model=None, responses={400: {"model": ErrorResponse}})
    def create_short_link(payload: CreateShortLinkRequest):
        try:
            validate_url(payload.target_url)
        except InvalidUrlError as exc:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(error_code="INVALID_URL", message=str(exc)).model_dump(),
            )

        code = generate_unique_short_code(repo.is_active_code_taken)
        created_at = utcnow()
        link = ShortLink(
            short_code=code,
            target_url=payload.target_url,
            created_at=created_at,
            expires_at=None,
            status="active",
        )
        repo.create(link)

        return ShortLinkResponse(
            short_code=link.short_code,
            target_url=link.target_url,
            created_at=link.created_at.isoformat(),
            expires_at=None,
            status=link.status,
        )
