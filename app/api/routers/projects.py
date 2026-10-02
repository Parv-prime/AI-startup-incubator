from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project, get_session
from app.api.schemas_project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from app.database.models import Project, User
from app.projects import store as project_store
from app.security.auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    projects = await project_store.list_projects(session, user_id=current_user.id)
    return [ProjectResponse.model_validate(p, from_attributes=True) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await project_store.create_project(
        session, user_id=current_user.id, fields=payload.model_dump()
    )
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project: Project = Depends(get_owned_project)) -> ProjectResponse:
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    payload: ProjectUpdateRequest,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    project = await project_store.update_project(session, project=project, fields=payload.model_dump())
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> None:
    await project_store.delete_project(session, project=project)
