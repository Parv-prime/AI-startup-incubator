from fastapi import APIRouter, Depends, Request

from app.api.schemas_memory import KnowledgeCreateRequest
from app.database.models import User
from app.security.auth import get_current_user

router = APIRouter(tags=["knowledge"])


@router.post("/api/v1/knowledge")
async def create_knowledge(
    payload: KnowledgeCreateRequest,
    request: Request,
    _current_user: User = Depends(get_current_user),
):
    return await request.app.state.knowledge.add(payload.title, payload.content)
