from __future__ import annotations

import threading
import time
from collections import defaultdict
from queue import Empty, Queue
from typing import Any, Dict, Optional

import redis

from backend.core.config import get_settings


settings = get_settings()


class MemoryPubSub:
    def __init__(self, parent: "MemoryRedis"):
        self.parent = parent
        self.channels: set[str] = set()
        self.queue: Queue = Queue()

    def subscribe(self, channel: str) -> None:
        self.channels.add(channel)
        self.parent._pubsub_channels[channel].append(self.queue)

    def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 0.5):
        try:
            message = self.queue.get(timeout=timeout)
        except Empty:
            return None
        return {"data": message}


class MemoryRedis:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expire: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._pubsub_channels: Dict[str, list[Queue]] = defaultdict(list)

    def _cleanup(self) -> None:
        now = time.time()
        expired = [key for key, ts in self._expire.items() if ts <= now]
        for key in expired:
            self._store.pop(key, None)
            self._expire.pop(key, None)

    def setex(self, key: str, ttl: int, value: Any) -> None:
        with self._lock:
            self._store[key] = value
            self._expire[key] = time.time() + ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            self._cleanup()
            return self._store.get(key)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)
            self._expire.pop(key, None)

    def incr(self, key: str) -> int:
        with self._lock:
            self._cleanup()
            value = int(self._store.get(key, 0)) + 1
            self._store[key] = value
            return value

    def expire(self, key: str, ttl: int) -> None:
        with self._lock:
            if key in self._store:
                self._expire[key] = time.time() + ttl

    def publish(self, channel: str, message: Any) -> int:
        subscribers = self._pubsub_channels.get(channel, [])
        for queue in subscribers:
            queue.put(message)
        return len(subscribers)

    def pubsub(self) -> MemoryPubSub:
        return MemoryPubSub(self)


def _create_redis_client():
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return MemoryRedis()


redis_client = _create_redis_client()


def get_redis():
    return redis_client
