from fastapi import APIRouter, Depends, Request

from app.api.schemas import ToolListResponse
from app.database.models import User
from app.security.auth import get_current_user

router = APIRouter(tags=["tools"])


@router.get("/api/v1/tools", response_model=ToolListResponse)
async def list_tools(
    request: Request,
    _current_user: User = Depends(get_current_user),
) -> ToolListResponse:
    return ToolListResponse(tools=request.app.state.tools.list_metadata())
