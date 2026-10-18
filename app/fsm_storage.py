"""
SQLite'dagi FSM saqlagichi: bot qayta ishga tushganda foydalanuvchining tugallanmagan
savol-javobi (holat va javoblari) yo'qolmaydi. Asosiy botdagi Redis saqlagich bilan bir xil
maqsad, lekin Redis kerak emas — buyurtmalar bazasi bilan bitta fayl.
"""

import json

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey


class SqliteStorage(BaseStorage):
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _key(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id or 0}:{key.destiny}"

    async def set_state(self, key: StorageKey, state: State | str | None = None) -> None:
        value = state.state if isinstance(state, State) else state
        await self.store.db.execute(
            "INSERT INTO fsm(key, state) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET state=excluded.state",
            (self._key(key), value))
        await self.store.db.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        row = await self.store._one("SELECT state FROM fsm WHERE key=?", (self._key(key),))
        return row["state"] if row else None

    async def set_data(self, key: StorageKey, data) -> None:
        await self.store.db.execute(
            "INSERT INTO fsm(key, data) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET data=excluded.data",
            (self._key(key), json.dumps(dict(data), ensure_ascii=False)))
        await self.store.db.commit()

    async def get_data(self, key: StorageKey) -> dict:
        row = await self.store._one("SELECT data FROM fsm WHERE key=?", (self._key(key),))
        return json.loads(row["data"]) if row else {}

    async def close(self) -> None:  # ulanishni `Store` yopadi
        pass
