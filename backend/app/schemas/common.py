from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.pagination import PageMeta


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseModel):
    items: list[Any]
    meta: PaginationMeta


def meta_from_page(meta: PageMeta) -> PaginationMeta:
    return PaginationMeta(page=meta.page, page_size=meta.page_size, total=meta.total, total_pages=meta.total_pages)