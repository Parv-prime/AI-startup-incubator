from __future__ import annotations

from sqlalchemy import select

from app.database.engine import Database
from app.database.models import ProjectMemory

VALID_CATEGORIES = {"fact", "decision", "assumption", "open_question", "risk", "note"}


class MemoryStore:
    """Project-scoped durable memory (facts/decisions/assumptions/open questions/risks).

    Isolated by project_id — never returns another project's rows.
    """

    def __init__(self, db: Database):
        self.db = db

    async def add(self, project_id: str, content: str, category: str = "fact") -> dict:
        category = category if category in VALID_CATEGORIES else "fact"
        async with self.db.session() as session:
            row = ProjectMemory(project_id=project_id, content=content.strip(), category=category)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _serialize(row)

    async def search(self, project_id: str, query: str, limit: int = 5) -> list[dict]:
        async with self.db.session() as session:
            stmt = (
                select(ProjectMemory)
                .where(ProjectMemory.project_id == project_id)
                .where(ProjectMemory.content.ilike(f"%{query}%"))
                .order_by(ProjectMemory.created_at.desc())
                .limit(limit)
            )
            rows = (await session.scalars(stmt)).all()
            return [_serialize(row) for row in rows]

    async def list_recent(self, project_id: str, limit: int = 20) -> list[dict]:
        async with self.db.session() as session:
            stmt = (
                select(ProjectMemory)
                .where(ProjectMemory.project_id == project_id)
                .order_by(ProjectMemory.created_at.desc())
                .limit(limit)
            )
            rows = (await session.scalars(stmt)).all()
            return [_serialize(row) for row in rows]


def _serialize(row: ProjectMemory) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "category": row.category,
        "content": row.content,
        "created_at": row.created_at.isoformat(),
    }
