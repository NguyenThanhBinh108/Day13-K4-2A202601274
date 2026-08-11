# P1 — Correlation ID & Request Context

## Phần đã triển khai

- `CorrelationIdMiddleware` xóa context cũ ở đầu mỗi request.
- Ưu tiên dùng header `x-request-id`; khi header thiếu hoặc rỗng, sinh ID dạng `req-<8 hex>`.
- Bind `correlation_id` vào `structlog.contextvars` và lưu vào `request.state`.
- Response trả lại `x-request-id` và `x-response-time-ms`.
- Endpoint `/chat` bind `user_id_hash`, `session_id`, `feature`, `model` và `env` trước log `request_received`.
- Test bao phủ propagation, generated ID, enrichment và context isolation giữa hai request liên tiếp.

## Kết quả kiểm tra

```text
python -m pytest -q
24 passed, 2 warnings
```

Validator được chạy trên log tạm riêng của P1 với hai request:

```text
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 2
Potential PII leaks detected: 0
[PASSED] Correlation ID propagation
[PASSED] Log enrichment
Estimated Score: 100/100
```

Hai cảnh báo test là cảnh báo deprecation có sẵn của FastAPI `on_event`; không liên quan tới P1.
Các thông báo Langfuse disabled trong smoke test là do môi trường local chưa có public key và không ảnh
hưởng logging.

## Evidence cần chụp khi chạy canonical baseline

1. Response `/chat` hiển thị header `x-request-id` và `x-response-time-ms`.
2. Từ 3–5 dòng JSON có cùng `correlation_id`, hiển thị đủ `user_id_hash`, `session_id`, `feature`,
   `model`, `env` nhưng không chứa `user_id` thô.
3. Output `scripts/validate_logs.py` có `[PASSED] Correlation ID propagation` và
   `[PASSED] Log enrichment`.

P5 chèn tên ảnh canonical và commit SHA của P1 vào `submission/REPORT.md` khi merge.
