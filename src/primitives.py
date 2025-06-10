from trio import Lock
from result import Result
from typing import Callable, Awaitable, Self
import copy

class AsyncKVStore[K,V]:
    def __init__(self, default_value: V, lock: Lock):
        self._store: dict[K, V] = {}
        self.default_value = default_value
        self.lock = lock

    @Result.resultify_async
    async def get(self, key: K) -> V:
        return self._store.get(key, self.default_value)

    @Result.resultify_async
    async def set(self, key: K, value: V) -> None:
        async with self.lock:
            self._store[key] = value
            return None
    
    @Result.resultify_async
    async def delete(self, key: K) -> None:
        async with self.lock:
            del self._store[key]
            return None

    @Result.resultify_async
    async def clear(self) -> None:
        async with self.lock:
            self._store.clear()
            return None

    @Result.resultify_async
    async def closure(self, func: Callable[[Self], Awaitable[None]]) -> None:
        async with self.lock:
            await func(self)
            return None

class AsyncQueue[T]:
    def __init__(self, lock: Lock):
        self._queue: list[T] = []
        self.lock = lock

    @staticmethod
    def from_list(items: list[T], lock: Lock) -> Self:
        queue = AsyncQueue[T](lock)
        queue._queue = copy.deepcopy(items)
        return queue

    @Result.resultify_async
    async def enqueue(self, item: T) -> None:
        async with self.lock:
            self._queue.append(item)
            return None

    @Result.resultify_async
    async def dequeue(self) -> T:
        async with self.lock:
            return self._queue.pop(0)

    @Result.resultify_async
    async def clear(self) -> None:
        async with self.lock:
            self._queue.clear()
            return None

    @Result.resultify_async
    async def size(self) -> int:
        async with self.lock:
            return len(self._queue)