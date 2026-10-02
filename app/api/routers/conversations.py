from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_owned_conversation, get_owned_project, get_session
from app.api.schemas_conversation import (
    ConversationCreateRequest,
    ConversationRenameRequest,
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.database.models import Conversation, Project, User
from app.projects import store as project_store
from app.security.auth import get_current_user

router = APIRouter(tags=["conversations"])


def _auto_title(user_input: str) -> str:
    words = user_input.strip().split()
    title = " ".join(words[:8])
    if len(words) > 8:
        title += "..."
    return title[:200] or "New Conversation"


@router.get("/api/v1/projects/{project_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> list[ConversationResponse]:
    conversations = await project_store.list_conversations(session, project_id=project.id)
    return [ConversationResponse.model_validate(c, from_attributes=True) for c in conversations]


@router.post(
    "/api/v1/projects/{project_id}/conversations",
    response_model=ConversationResponse,
    status_code=201,
)
async def create_conversation(
    payload: ConversationCreateRequest,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    conversation = await project_store.create_conversation(
        session, project_id=project.id, title=payload.title
    )
    return ConversationResponse.model_validate(conversation, from_attributes=True)


@router.get("/api/v1/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation: Conversation = Depends(get_owned_conversation)) -> ConversationResponse:
    return ConversationResponse.model_validate(conversation, from_attributes=True)


@router.put("/api/v1/conversations/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(
    payload: ConversationRenameRequest,
    conversation: Conversation = Depends(get_owned_conversation),
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    conversation = await project_store.rename_conversation(session, conversation=conversation, title=payload.title)
    return ConversationResponse.model_validate(conversation, from_attributes=True)


@router.delete("/api/v1/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation: Conversation = Depends(get_owned_conversation),
    session: AsyncSession = Depends(get_session),
) -> None:
    await project_store.delete_conversation(session, conversation=conversation)


@router.get("/api/v1/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation: Conversation = Depends(get_owned_conversation),
    session: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    messages = await project_store.list_messages(session, conversation_id=conversation.id)
    return [MessageResponse.model_validate(m, from_attributes=True) for m in messages]


async def _maybe_autotitle(session: AsyncSession, conversation: Conversation, user_input: str) -> None:
    if conversation.title == "New Conversation":
        await project_store.rename_conversation(
            session, conversation=conversation, title=_auto_title(user_input)
        )


@router.post("/api/v1/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    payload: SendMessageRequest,
    request: Request,
    conversation: Conversation = Depends(get_owned_conversation),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SendMessageResponse:
    project = await session.get(Project, conversation.project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")

    await _maybe_autotitle(session, conversation, payload.content)

    orchestrator = request.app.state.orchestrator
    final: dict = {}
    async for event in orchestrator.run_stream(
        project=project,
        user_id=current_user.id,
        conversation_id=conversation.id,
        user_input=payload.content,
    ):
        if event["type"] == "done":
            final = event
    return SendMessageResponse(**{k: v for k, v in final.items() if k != "type"})


@router.post("/api/v1/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    payload: SendMessageRequest,
    request: Request,
    conversation: Conversation = Depends(get_owned_conversation),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    project = await session.get(Project, conversation.project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")

    await _maybe_autotitle(session, conversation, payload.content)

    orchestrator = request.app.state.orchestrator

    async def event_generator():
        async for event in orchestrator.run_stream(
            project=project,
            user_id=current_user.id,
            conversation_id=conversation.id,
            user_input=payload.content,
        ):
            yield {"event": event["type"], "data": json.dumps(event)}

    return EventSourceResponse(event_generator())
