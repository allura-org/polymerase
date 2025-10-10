from trio import Lock
from typing import Callable, Awaitable, Self
import copy

class AsyncKVStore[K, V]:
    def __init__(self, default_value: V, lock: Lock):
        self._store: dict[K, V] = {}
        self.default_value = default_value
        self.lock = lock

    async def get(self, key: K) -> V:
        return self._store.get(key, self.default_value)

    async def set(self, key: K, value: V) -> None:
        async with self.lock:
            self._store[key] = value

    async def delete(self, key: K) -> None:
        async with self.lock:
            del self._store[key]

    async def clear(self) -> None:
        async with self.lock:
            self._store.clear()

    async def closure(self, func: Callable[[Self], Awaitable[None]]) -> None:
        async with self.lock:
            await func(self)

class AsyncQueue[T]:
    def __init__(self, lock: Lock):
        self._queue: list[T] = []
        self.lock = lock

    @staticmethod
    def from_list(items: list[T], lock: Lock) -> Self:
        queue = AsyncQueue[T](lock)
        queue._queue = copy.deepcopy(items)
        return queue

    async def enqueue(self, item: T) -> None:
        async with self.lock:
            self._queue.append(item)

    async def dequeue(self) -> T:
        async with self.lock:
            if len(self._queue) == 0:
                raise IndexError("pop from empty list")
            return self._queue.pop(0)

    async def clear(self) -> None:
        async with self.lock:
            self._queue.clear()

    async def size(self) -> int:
        async with self.lock:
            return len(self._queue)