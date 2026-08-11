# Evidence: Runbook Alert 2 — error-rate-spike

## Nội dung runbook (từ docs/alerts.md)

### Alert 2: Lỗi API tăng bất thường

- **Tên**: Lỗi API tăng bất thường
- **Severity**: critical
- **SLI/SLO liên quan**: error_rate_pct <= 2%, target 99.0%
- **Điều kiện và thời gian duy trì**: error rate > 2% trong 5 phút
- **Ảnh hưởng tới người dùng**: Request thất bại, mất kết quả, giảm trust vào hệ thống
- **Ba bước kiểm tra đầu tiên**:
  1. Mở dashboard panel errors, xem breakdown theo `error_type`
  2. Mở log, lọc `event == "request_failed"`, đọc `error_type` và `payload.detail`
  3. Kiểm tra `/metrics` endpoint, đọc snapshot hiện tại
- **Mitigation tạm thời**: Khởi động lại service nếu error_type là Exception chung; nếu do external dependency, chuyển sang fallback
- **Owner**: Trịnh Hải Đăng

## Placeholder

Ảnh: `submission/evidence/13-runbook-alert2.png`
