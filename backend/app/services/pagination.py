from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass(slots=True)
class PageMeta:
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


def paginate(db: Session, stmt: Select, *, page: int = 1, page_size: int = 20):
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)

    total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(total_stmt) or 0)

    items = (
        db.execute(
            stmt.offset((safe_page - 1) * safe_page_size).limit(safe_page_size)
        )
        .scalars()
        .all()
    )

    return items, PageMeta(page=safe_page, page_size=safe_page_size, total=total)