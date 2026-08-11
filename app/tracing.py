from __future__ import annotations

import atexit
import os
from typing import Any

try:
    from langfuse import get_client, observe

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

        def flush(self) -> None:
            return None

    def get_client():
        return _DummyClient()


def get_langfuse_client():
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def flush_tracing() -> None:
    """Đẩy nốt các span còn nằm trong buffer lên Langfuse.

    SDK v3 gửi span theo batch ở background thread. Khi tắt uvicorn bằng Ctrl+C ngay
    sau load test, batch cuối có thể chưa kịp gửi và evidence bị thiếu vài trace.
    Hàm này chạy qua `atexit` nên không cần sửa `app/main.py` (file của P1).
    """
    if not tracing_enabled():
        return
    try:
        get_langfuse_client().flush()
    except Exception:  # pragma: no cover - lỗi telemetry không được làm chết app
        pass


atexit.register(flush_tracing)
