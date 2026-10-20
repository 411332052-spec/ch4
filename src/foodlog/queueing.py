"""排隊區：先進先出，一個工人一次只處理一張，不會同時開很多個 claude -p。"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

REJECT_FULL = "full"  # 排隊區滿了
REJECT_USER_LIMIT = "user_limit"  # 這個人排太多張了


@dataclass(frozen=True)
class Job:
    author_id: int
    message: Any
    attachment: Any
    tag: str = ""  # log 用的標籤，例如 [訊息ID 第1/2張]


class JobQueue:
    def __init__(
        self,
        handler: Callable[[Job], Awaitable[None]],
        max_size: int,
        per_user_max: int,
    ) -> None:
        self._handler = handler
        self._max_size = max_size
        self._per_user_max = per_user_max
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._by_user: Counter[int] = Counter()  # 每個人「排隊中＋處理中」的張數
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @property
    def size(self) -> int:
        """排隊中加上處理中，一共幾張。"""
        return sum(self._by_user.values())

    def put(self, job: Job) -> str | None:
        """放進排隊區。成功回傳 None，被拒絕回傳原因。"""
        if self._queue.qsize() >= self._max_size:
            return REJECT_FULL
        if self._by_user[job.author_id] >= self._per_user_max:
            return REJECT_USER_LIMIT
        self._by_user[job.author_id] += 1
        self._queue.put_nowait(job)
        return None

    async def _run(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._handler(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                # 一張出錯只影響這一張，工人要繼續做下一張
                log.exception("處理照片時發生未預期的錯誤")
            finally:
                self._by_user[job.author_id] -= 1
                if self._by_user[job.author_id] <= 0:
                    del self._by_user[job.author_id]
                self._queue.task_done()
