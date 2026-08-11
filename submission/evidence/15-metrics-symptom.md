# Evidence: Challenge metrics — triệu chứng từ metrics

## Challenge run summary

- Challenge ID: `day13-k4-observability-v1`
- Incident: `rag_slow`
- Thời gian chạy: 2026-08-11T08:29:08Z — 2026-08-11T08:29:22Z
- Số query: 5 (feature: `monitoring`)

## Metrics

| Metric | Giá trị | Ngưỡng SLO | Trạng thái |
|---|---|---|---|
| Request received | 5 | — | — |
| Response sent | 5 | — | — |
| Error rate | 0.0% | <= 2% | ✅ PASS |
| Latency min | 2654 ms | — | — |
| Latency max | 2660 ms | — | — |
| Latency p50 | 2657 ms | <= 3000 ms | ✅ PASS |
| Latency p95 | 2660 ms | <= 3000 ms | ✅ PASS |
| Latency p99 | 2660 ms | <= 3000 ms | ✅ PASS |

## Triệu chứng

- **Latency tăng đột biến**: p95 = 2660ms, vượt ngưỡng cảnh báo sớm 2000ms (alert `tail-latency-increase`)
- **Error rate không đổi**: 0%, cho thấy hệ thống không gặp lỗi nghiêm trọng, chỉ bị chậm
- **Tất cả request đều trả về 200**: không có exception, không có `request_failed` trong log
- **Cost và tokens**: không có dấu hiệu bất thường

## Kết luận

Triệu chứng chính là **latency tăng đột biến** do incident `rag_slow` được bật trước khi chạy challenge. Hệ thống vẫn hoạt động bình thường (không có lỗi), nhưng thời gian phản hồi tăng gấp ~17 lần so với baseline (~150ms).
