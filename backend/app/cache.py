"""线程安全的 TTL 缓存工具"""
import threading
from cachetools import TTLCache


class ThreadSafeTTLCache:
    """线程安全的 TTL 缓存封装。"""

    def __init__(self, maxsize: int = 100, ttl: int = 3600):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value):
        with self._lock:
            self._cache[key] = value

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()


# 全局缓存实例：用于学院、类别、校区等不常变化的数据
reference_data_cache = ThreadSafeTTLCache(maxsize=100, ttl=3600)
