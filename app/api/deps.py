from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation, Project, User
from app.projects import store as project_store
from app.security.auth import get_current_user


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    db = request.app.state.db
    async with db.session() as session:
        yield session


async def get_owned_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    return await project_store.get_owned_project(session, project_id=project_id, user_id=current_user.id)


async def get_owned_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Conversation:
    return await project_store.get_conversation_for_user(
        session, conversation_id=conversation_id, user_id=current_user.id
    )
