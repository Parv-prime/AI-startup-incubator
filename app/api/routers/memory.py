from fastapi import APIRouter, Depends, Request

from app.api.deps import get_owned_project
from app.api.schemas_memory import MemoryCreateRequest, MemoryListResponse
from app.database.models import Project

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["memory"])


@router.post("/memory")
async def create_memory(
    payload: MemoryCreateRequest,
    request: Request,
    project: Project = Depends(get_owned_project),
):
    return await request.app.state.memory.add(project.id, payload.content, payload.category)


@router.get("/memory", response_model=MemoryListResponse)
async def list_memory(
    request: Request,
    project: Project = Depends(get_owned_project),
):
    items = await request.app.state.memory.list_recent(project.id)
    return MemoryListResponse(project_id=project.id, items=items)
