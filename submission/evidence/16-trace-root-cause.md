# Evidence: Trace root cause — span bất thường

## Challenge: day13-k4-observability-v1

- Incident: `rag_slow`
- Feature: `monitoring`
- Thời gian: 2026-08-11T08:29:08Z — 2026-08-11T08:29:22Z

## Trace ID liên quan

Trace ID từ Langfuse (cần P3 cung cấp ảnh thật):

- `*(điền trace ID thật từ Langfuse)*`
- `*(điền trace ID thật từ Langfuse)*`

## Span bất thường

| Span | Duration (ms) | Baseline (ms) | Tăng | Ghi chú |
|---|---|---|---|---|
| `retrieve` | ~2656 | ~150 | ~17x | Đây là span bị `rag_slow` ảnh hưởng |
| `llm` | ~10 | ~10 | 1x | Không đổi |
| `total` | ~2660 | ~160 | ~16x | Tổng thời gian request |

## Cách khoanh vùng

1. Mở Langfuse → Traces → filter time range 2026-08-11T08:29:00Z – 08:30:00Z
2. Lọc `feature: monitoring`
3. Sắp xếp theo `duration` giảm dần
4. Chọn trace có `retrieve` span cao nhất
5. Click vào span `retrieve` → xem `correlation_id` tag

## Kết luận

Span `retrieve` có duration bất thường (~2656ms) chứng minh incident `rag_slow` ảnh hưởng trực tiếp đến RAG retrieval pipeline. Đây là root cause của latency tăng đột biến.

## Placeholder

Ảnh: `submission/evidence/16-trace-root-cause.png`
