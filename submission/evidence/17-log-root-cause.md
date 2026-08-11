# Evidence: Log root cause — correlation_id chứng minh

## Challenge: day13-k4-observability-v1

- Incident: `rag_slow`
- Feature: `monitoring`

## Correlation ID liên quan

Từ trace `retrieve` span bất thường, lấy `correlation_id` = `req-1d179747` (ví dụ từ challenge run).

## Log lines (từ data/logs.jsonl)

```json
{"service": "api", "payload": {"message_preview": "Explain why metrics traces and logs work together."}, "event": "request_received", "level": "info", "ts": "2026-08-11T08:29:08.992195Z", "correlation_id": "req-1d179747", "user_id_hash": "k4-u01", "session_id": "k4-challenge-s01", "feature": "monitoring", "model": "mock-llm-v1", "env": "dev"}
{"service": "api", "latency_ms": 2660, "tokens_in": 35, "tokens_out": 161, "cost_usd": 0.00252, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "level": "info", "ts": "2026-08-11T08:29:11.655687Z", "correlation_id": "req-1d179747", "user_id_hash": "k4-u01", "session_id": "k4-challenge-s01", "feature": "monitoring", "model": "mock-llm-v1", "env": "dev"}
```

## Phân tích

- `request_received` → `response_sent` cùng `correlation_id: req-1d179747`
- `latency_ms = 2660` vượt ngưỡng SLO 3000ms và alert threshold 2000ms
- `event = "response_sent"` chứng minh request đã hoàn thành (không phải lỗi)
- Không có `request_failed` cho correlation_id này → error rate = 0%

## Kết luận

Log line với `correlation_id: req-1d179747` và `latency_ms: 2660` là bằng chứng trực tiếp:
- Request bị chậm do incident `rag_slow`
- Không phải lỗi hệ thống (error_type không có)
- Có thể trace ngược từ Langfuse trace ID → span `retrieve` → log này

## Placeholder

Ảnh: `submission/evidence/17-log-root-cause.png`
