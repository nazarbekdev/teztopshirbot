import pytest_asyncio

from app.db import Store


@pytest_asyncio.fixture
async def store(tmp_path):
    s = await Store(str(tmp_path / "t.db")).open()
    await s.touch_user(1, "Ali", "ali")
    yield s
    await s.close()
