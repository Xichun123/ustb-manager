"""基于内存的滑动窗口频率限制器"""
import time
from fastapi import HTTPException


class InMemoryRateLimiter:
    """简单的内存频率限制器，使用滑动窗口算法。"""

    def __init__(self, window_seconds: int = 60, max_requests: int = 1):
        self._window = window_seconds
        self._max = max_requests
        self._requests: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        """检查是否超出频率限制。

        Raises:
            HTTPException 429: 超出频率限制
        """
        now = time.time()
        cutoff = now - self._window

        # 清理过期记录
        timestamps = self._requests.get(key, [])
        timestamps = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= self._max:
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请{self._window}秒后重试",
            )

        timestamps.append(now)
        self._requests[key] = timestamps


# SMS 频率限制：每手机号 60 秒 1 次
sms_rate_limiter = InMemoryRateLimiter(window_seconds=60, max_requests=1)
