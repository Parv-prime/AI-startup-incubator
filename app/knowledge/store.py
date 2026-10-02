from __future__ import annotations

from sqlalchemy import select

from app.database.engine import Database
from app.database.models import KnowledgeDoc


class KnowledgeStore:
    """Global reference documents, shared across all projects/users."""

    def __init__(self, db: Database):
        self.db = db

    async def add(self, title: str, content: str) -> dict:
        async with self.db.session() as session:
            row = KnowledgeDoc(title=title.strip(), content=content.strip())
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _serialize(row)

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        async with self.db.session() as session:
            like = f"%{query}%"
            stmt = (
                select(KnowledgeDoc)
                .where((KnowledgeDoc.title.ilike(like)) | (KnowledgeDoc.content.ilike(like)))
                .order_by(KnowledgeDoc.created_at.desc())
                .limit(limit)
            )
            rows = (await session.scalars(stmt)).all()
            return [_serialize(row) for row in rows]


def _serialize(row: KnowledgeDoc) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "content": row.content,
        "created_at": row.created_at.isoformat(),
    }
