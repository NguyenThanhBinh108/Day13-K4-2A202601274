# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1: tail-latency-increase

- Tên: Tail latency tăng đột biến
- Severity: warning
- SLI/SLO liên quan: latency_p95_ms <= 3000ms (SLO), target 99.5%
- Điều kiện và thời gian duy trì: percentile(latency_ms, 95) > 2000ms trong 5 phút
- Ảnh hưởng tới người dùng: Trải nghiệm trả lời chậm, có thể timeout ở client
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel latency, kiểm tra p50/p95/p99 có tăng đột biến không
  2. Mở trace list, lọc theo time range, tìm span có duration cao nhất
  3. Mở log theo correlation_id của span đó, tìm event `response_sent` có latency_ms cao
- Mitigation tạm thời: Nếu do incident `rag_slow` đang bật, cân nhắc disable tạm; nếu không, kiểm tra LLM provider status page
- Owner: Trịnh Hải Đăng

## Alert 2: error-rate-spike

- Tên: Lỗi API tăng bất thường
- Severity: critical
- SLI/SLO liên quan: error_rate_pct <= 2%, target 99.0%
- Điều kiện và thời gian duy trì: error rate > 2% trong 5 phút
- Ảnh hưởng tới người dùng: Request thất bại, mất kết quả, giảm trust vào hệ thống
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel errors, xem breakdown theo `error_type`
  2. Mở log, lọc `event == "request_failed"`, đọc `error_type` và `payload.detail`
  3. Kiểm tra `/metrics` endpoint, đọc snapshot hiện tại
- Mitigation tạm thời: Khởi động lại service nếu error_type là Exception chung; nếu do external dependency, chuyển sang fallback
- Owner: Trịnh Hải Đăng

## Alert 3: cost-spike

- Tên: Chi phí API tăng đột biến
- Severity: warning
- SLI/SLO liên quan: daily_cost_usd <= 2.5 USD, target 100%
- Điều kiện và thời gian duy trì: sum(cost_usd) by 1m > 0.25 USD trong 5 phút liên tiếp
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp nhưng vượt ngân sách, có thể bị giới hạn quota
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel cost, kiểm tra trend cost theo thời gian
  2. Mở log, lọc `event == "response_sent"`, tính trung bình `cost_usd` mỗi request
  3. Kiểm tra `tokens_in`/`tokens_out` có tăng bất thường không (token cao = cost cao)
- Mitigation tạm thời: Giảm `max_tokens` trong prompt, hoặc chuyển sang model rẻ hơn nếu có
- Owner: Trịnh Hải Đăng
