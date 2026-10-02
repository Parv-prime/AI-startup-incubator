import pytest

from app.config.settings import Settings
from app.database.engine import Database
from app.memory.store import MemoryStore


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "agent.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    database = Database(settings)
    await database.create_all()
    yield database
    await database.dispose()


async def test_memory_is_isolated_by_project(db: Database):
    store = MemoryStore(db)
    await store.add("proj_safeplate", "max salt is 2 grams")
    await store.add("proj_vibevault", "favorite genre is jazz")

    safeplate = await store.search("proj_safeplate", "salt")
    vibe = await store.search("proj_vibevault", "salt")
    jazz = await store.search("proj_vibevault", "jazz")

    assert safeplate[0]["content"] == "max salt is 2 grams"
    assert vibe == []
    assert jazz[0]["content"] == "favorite genre is jazz"
