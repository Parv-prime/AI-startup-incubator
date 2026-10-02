from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config.settings import Settings
from app.database.engine import Database
from app.projects import store as project_store
from app.startup.profile import ProfileUpdate


def test_profile_update_is_empty():
    assert ProfileUpdate().is_empty()
    assert not ProfileUpdate(industry="EdTech").is_empty()


def test_profile_update_to_project_fields_maps_renamed_columns():
    update = ProfileUpdate(startup_name="SafePlate", startup_stage="MVP", industry="FoodTech")
    fields = update.to_project_fields()
    assert fields == {"name": "SafePlate", "stage": "MVP", "industry": "FoodTech"}


def test_profile_update_to_project_fields_drops_blanks():
    update = ProfileUpdate(industry="FoodTech")
    fields = update.to_project_fields()
    assert "name" not in fields
    assert "stage" not in fields
    assert fields == {"industry": "FoodTech"}


@pytest.fixture
async def db(tmp_path: Path) -> Database:
    db_path = tmp_path / "test.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    database = Database(settings)
    await database.create_all()
    yield database
    await database.dispose()


async def test_project_belongs_to_creating_user(db: Database):
    async with db.session() as session:
        user = await project_store.create_user(
            session, name="Ada", email="ada@example.com", password_hash="hash"
        )
        project = await project_store.create_project(
            session, user_id=user.id, fields={"name": "SafePlate", "industry": "FoodTech"}
        )
        fetched = await project_store.get_owned_project(session, project_id=project.id, user_id=user.id)
        assert fetched.name == "SafePlate"


async def test_user_cannot_access_another_users_project(db: Database):
    async with db.session() as session:
        user_a = await project_store.create_user(
            session, name="Ada", email="ada@example.com", password_hash="hash"
        )
        user_b = await project_store.create_user(
            session, name="Bo", email="bo@example.com", password_hash="hash"
        )
        project_a = await project_store.create_project(
            session, user_id=user_a.id, fields={"name": "SafePlate"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await project_store.get_owned_project(session, project_id=project_a.id, user_id=user_b.id)
        assert exc_info.value.status_code == 403


async def test_conversation_isolated_by_project_owner(db: Database):
    async with db.session() as session:
        user_a = await project_store.create_user(
            session, name="Ada", email="ada@example.com", password_hash="hash"
        )
        user_b = await project_store.create_user(
            session, name="Bo", email="bo@example.com", password_hash="hash"
        )
        project_a = await project_store.create_project(
            session, user_id=user_a.id, fields={"name": "SafePlate"}
        )
        conversation = await project_store.create_conversation(session, project_id=project_a.id)

        owned = await project_store.get_conversation_for_user(
            session, conversation_id=conversation.id, user_id=user_a.id
        )
        assert owned.id == conversation.id

        with pytest.raises(HTTPException) as exc_info:
            await project_store.get_conversation_for_user(
                session, conversation_id=conversation.id, user_id=user_b.id
            )
        assert exc_info.value.status_code == 403


async def test_merge_profile_fields_never_overwrites_with_blank(db: Database):
    async with db.session() as session:
        user = await project_store.create_user(
            session, name="Ada", email="ada@example.com", password_hash="hash"
        )
        project = await project_store.create_project(
            session, user_id=user.id, fields={"name": "SafePlate", "industry": "FoodTech"}
        )
        await project_store.merge_profile_fields(
            session, project=project, fields={"industry": None, "geography": "India"}
        )
        assert project.industry == "FoodTech"
        assert project.geography == "India"
