# Evidence: Runbook Alert 3 — cost-spike

## Nội dung runbook (từ docs/alerts.md)

### Alert 3: Chi phí API tăng đột biến

- **Tên**: Chi phí API tăng đột biến
- **Severity**: warning
- **SLI/SLO liên quan**: daily_cost_usd <= 2.5 USD, target 100%
- **Điều kiện và thời gian duy trì**: sum(cost_usd) by 1m > 0.25 USD trong 5 phút liên tiếp
- **Ảnh hưởng tới người dùng**: Không ảnh hưởng trực tiếp nhưng vượt ngân sách, có thể bị giới hạn quota
- **Ba bước kiểm tra đầu tiên**:
  1. Mở dashboard panel cost, kiểm tra trend cost theo thời gian
  2. Mở log, lọc `event == "response_sent"`, tính trung bình `cost_usd` mỗi request
  3. Kiểm tra `tokens_in`/`tokens_out` có tăng bất thường không (token cao = cost cao)
- **Mitigation tạm thời**: Giảm `max_tokens` trong prompt, hoặc chuyển sang model rẻ hơn nếu có
- **Owner**: Trịnh Hải Đăng

## Placeholder

Ảnh: `submission/evidence/14-runbook-alert3.png`
