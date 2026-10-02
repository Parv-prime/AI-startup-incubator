from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation, Message, Project, User

PROFILE_FIELDS = (
    "name",
    "description",
    "industry",
    "stage",
    "target_customer",
    "geography",
    "business_model",
    "problem",
    "solution",
    "budget",
    "goals",
)


# ---------------------------------------------------------------- users ----

async def create_user(session: AsyncSession, *, name: str, email: str, password_hash: str) -> User:
    existing = await session.scalar(select(User).where(User.email == email.lower()))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(name=name.strip(), email=email.lower().strip(), password_hash=password_hash)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.lower().strip()))


# ------------------------------------------------------------- projects ----

async def create_project(session: AsyncSession, *, user_id: str, fields: dict) -> Project:
    project = Project(user_id=user_id, **{k: v for k, v in fields.items() if k in PROFILE_FIELDS})
    if not project.name:
        project.name = "Untitled Startup"
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def list_projects(session: AsyncSession, *, user_id: str, include_archived: bool = False) -> list[Project]:
    stmt = select(Project).where(Project.user_id == user_id)
    if not include_archived:
        stmt = stmt.where(Project.archived.is_(False))
    stmt = stmt.order_by(Project.last_active_at.desc())
    result = await session.scalars(stmt)
    return list(result.all())


async def get_project(session: AsyncSession, *, project_id: str) -> Project | None:
    return await session.get(Project, project_id)


async def get_owned_project(session: AsyncSession, *, project_id: str, user_id: str) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
    if project.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this project.")
    return project


async def update_project(session: AsyncSession, *, project: Project, fields: dict) -> Project:
    for key, value in fields.items():
        if key in PROFILE_FIELDS and value is not None:
            setattr(project, key, value)
    if "status" in fields and fields["status"]:
        project.status = fields["status"]
    if "archived" in fields and fields["archived"] is not None:
        project.archived = bool(fields["archived"])
    project.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(project)
    return project


async def touch_project(session: AsyncSession, *, project: Project) -> None:
    project.last_active_at = datetime.now(timezone.utc)
    await session.commit()


async def merge_profile_fields(session: AsyncSession, *, project: Project, fields: dict) -> Project:
    """Only fill in fields the AI has explicitly extracted; never overwrite with blanks."""
    # `project` may have been loaded in a different session (the orchestrator opens a fresh
    # session per call), so re-fetch it here rather than mutating/refreshing a detached instance.
    current = await session.get(Project, project.id)
    if current is None:
        return project
    changed = False
    for key, value in fields.items():
        if key in PROFILE_FIELDS and value:
            setattr(current, key, value)
            changed = True
    if changed:
        current.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(current)
    return current


async def delete_project(session: AsyncSession, *, project: Project) -> None:
    await session.delete(project)
    await session.commit()


# --------------------------------------------------------- conversations ----

async def create_conversation(
    session: AsyncSession, *, project_id: str, title: str = "New Conversation"
) -> Conversation:
    conversation = Conversation(project_id=project_id, title=title)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def list_conversations(session: AsyncSession, *, project_id: str) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def get_owned_conversation(
    session: AsyncSession, *, conversation_id: str, project_id: str
) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    return conversation


async def get_conversation_for_user(
    session: AsyncSession, *, conversation_id: str, user_id: str
) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    project = await session.get(Project, conversation.project_id)
    if project is None or project.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this conversation.")
    return conversation


async def rename_conversation(session: AsyncSession, *, conversation: Conversation, title: str) -> Conversation:
    conversation.title = title.strip() or conversation.title
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def delete_conversation(session: AsyncSession, *, conversation: Conversation) -> None:
    await session.delete(conversation)
    await session.commit()


async def touch_conversation(session: AsyncSession, *, conversation_id: str) -> None:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is not None:
        conversation.updated_at = datetime.now(timezone.utc)
        await session.commit()


# -------------------------------------------------------------- messages ----

async def add_message(
    session: AsyncSession,
    *,
    conversation_id: str,
    role: str,
    content: str,
    tool_name: str | None = None,
    model: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id, role=role, content=content, tool_name=tool_name, model=model
    )
    session.add(message)
    await touch_conversation(session, conversation_id=conversation_id)
    await session.commit()
    await session.refresh(message)
    return message


async def list_messages(session: AsyncSession, *, conversation_id: str) -> list[Message]:
    stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    result = await session.scalars(stmt)
    return list(result.all())


async def recent_messages(session: AsyncSession, *, conversation_id: str, limit: int = 20) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await session.scalars(stmt)
    return list(reversed(result.all()))
