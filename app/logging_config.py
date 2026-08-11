from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars

from .pii import scrub_value

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


class JsonlFileProcessor:
    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        rendered = structlog.processors.JSONRenderer()(logger, method_name, event_dict)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(rendered + "\n")
        return event_dict



# Field do chính pipeline log sinh ra, không đường nào nhận được text người dùng
# nhập: `ts`/`level` là của structlog, `user_id_hash` là output của `hash_user_id`.
# Quét chúng không chặn thêm được PII nào mà chỉ có thể làm hỏng giá trị khi regex
# bắt nhầm. `correlation_id` CỐ Ý không nằm ở đây: client gửi được nó qua header
# `x-request-id` (app/middleware.py) nên vẫn phải scrub.
NON_USER_TEXT_KEYS = frozenset({"ts", "level", "user_id_hash"})


def scrub_event(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    # Scrub the whole record, not just `payload`/`event`: validate_logs.py
    # checks `json.dumps(rec)` end-to-end, so any field that can carry free
    # text (error detail, a preview added later, ...) must be sanitized here
    # too, otherwise a single leaked field costs 30 points.
    for key, value in list(event_dict.items()):
        if key in NON_USER_TEXT_KEYS:
            continue
        event_dict[key] = scrub_value(value)
    return event_dict



def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            # `scrub_event` phải đứng SAU hai processor dựng traceback: chúng sinh ra
            # field `stack`/`exception` là text tự do (message của exception có thể
            # chứa PII). Nếu scrub chạy trước, hai field đó đi thẳng xuống file chưa
            # được che. Vẫn phải đứng TRƯỚC `JsonlFileProcessor` vì đó là chỗ ghi file.
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            scrub_event,
            JsonlFileProcessor(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )



def get_logger() -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger()
