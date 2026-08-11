# Evidence: Runbook Alert 1 — tail-latency-increase

## Nội dung runbook (từ docs/alerts.md)

### Alert 1: Tail latency tăng đột biến

- **Tên**: Tail latency tăng đột biến
- **Severity**: warning
- **SLI/SLO liên quan**: latency_p95_ms <= 3000ms (SLO), target 99.5%
- **Điều kiện và thời gian duy trì**: percentile(latency_ms, 95) > 2000ms trong 5 phút
- **Ảnh hưởng tới người dùng**: Trải nghiệm trả lời chậm, có thể timeout ở client
- **Ba bước kiểm tra đầu tiên**:
  1. Mở dashboard panel latency, kiểm tra p50/p95/p99 có tăng đột biến không
  2. Mở trace list, lọc theo time range, tìm span có duration cao nhất
  3. Mở log theo correlation_id của span đó, tìm event `response_sent` có latency_ms cao
- **Mitigation tạm thời**: Nếu do incident `rag_slow` đang bật, cân nhắc disable tạm; nếu không, kiểm tra LLM provider status page
- **Owner**: Trịnh Hải Đăng

## Placeholder

Ảnh: `submission/evidence/12-runbook-alert1.png`
