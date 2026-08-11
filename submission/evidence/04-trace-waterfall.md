# Evidence: Trace waterfall — span đáng chú ý

## Cách lấy

1. Mở Langfuse UI → chọn 1 trace có `feature: monitoring` từ challenge run
2. Click vào trace → xem waterfall view
3. Chụp màn hình toàn bộ waterfall

## Span đáng chú ý

- **span `retrieve`**: đây là nơi incident `rag_slow` làm P95 tăng
- Trong challenge run, span `retrieve` có duration ~2656ms (so với baseline ~150ms)
- Từ trace này, click vào span → xem `correlation_id` → search ngược trong `data/logs.jsonl`

## Luồng điều tra

```
Metrics (latency p95 = 2660ms) 
    → Traces (filter by time range, tìm span `retrieve` có duration cao)
        → Logs (search correlation_id = req-1d179747, tìm event response_sent có latency_ms = 2660)
```

## Placeholder

Ảnh: `submission/evidence/04-trace-waterfall.png`
Trace ID: `*(điền sau khi P3 chạy thật)*`
