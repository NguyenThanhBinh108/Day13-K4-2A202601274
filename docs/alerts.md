# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

3 alert dưới đây được thiết kế để mỗi kịch bản incident practice trong [data/incidents.json](../data/incidents.json)
đều có đúng một alert bắt được: `rag_slow` → Alert 1, `tool_fail` → Alert 2, `cost_spike` → Alert 3. Số liệu
threshold khớp trực tiếp với [config/dashboard.yaml](../config/dashboard.yaml) và [config/slo.yaml](../config/slo.yaml)
— xem lý do chọn số ở phần `rationale` của từng SLI trong `slo.yaml`.

## Alert 1

- Tên: High Latency (P95 SLO Breach)
- Severity: Critical
- SLI/SLO liên quan: `latency_p95_ms` trong `config/slo.yaml` (objective 3000ms, target 99.5%/28 ngày) — khớp threshold p95 của panel `latency`.
- Điều kiện và thời gian duy trì: `p95(latency_ms)` tính trên rolling window 5 phút > 3000ms, duy trì liên tục ≥ 5 phút. Yêu cầu duy trì 5 phút để không alert vì một request đơn lẻ chậm ngẫu nhiên (network jitter, GC pause).
- Ảnh hưởng tới người dùng: người dùng chờ câu trả lời hơn 3 giây, cảm giác app bị "treo"; nếu kéo dài, tỉ lệ người dùng bỏ dở request tăng.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `latency` trên dashboard, xác nhận p95 tăng từ thời điểm nào và có trùng với panel `traffic` tăng đột biến không (loại trừ nguyên nhân quá tải thông thường).
  2. Mở Langfuse, lọc trace trong đúng khoảng thời gian panel báo bất thường, tìm span/generation chiếm thời lượng lớn nhất (thường là span `retrieve` khi nguyên nhân là RAG).
  3. Lấy `correlation_id` của trace nghi vấn, grep trong `data/logs.jsonl` để xác nhận `latency_ms` thực tế và `feature` bị ảnh hưởng nhiều nhất.
- Mitigation tạm thời: nếu nguyên nhân là RAG chậm, tạm tắt bước retrieve hoặc trả fallback answer không cần tài liệu; nếu do tải, giảm concurrency phía client hoặc bật rate limit tạm thời. Nếu đang chạy incident practice, tắt bằng `python scripts/inject_incident.py --scenario rag_slow --disable`.
- Owner: P5 (on-call điều tra) — escalate sang P3 nếu root cause nằm ở RAG/LLM (`app/agent.py`, `app/mock_rag.py`).

## Alert 2

- Tên: High Error Rate
- Severity: Critical
- SLI/SLO liên quan: `error_rate_pct` trong `config/slo.yaml` (objective 2%, target 99.0%/28 ngày) — khớp threshold của panel `errors`.
- Điều kiện và thời gian duy trì: `error_rate_pct = count(event=="request_failed") / count(event=="request_received") * 100` tính trên rolling window 5 phút > 2%, duy trì liên tục ≥ 5 phút.
- Ảnh hưởng tới người dùng: người dùng nhận lỗi (HTTP 500) hoặc không có câu trả lời; tính năng chat coi như gián đoạn với nhóm người dùng bị ảnh hưởng trong khoảng thời gian đó.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `errors`, xem breakdown theo `error_type` để biết loại lỗi nào chiếm đa số (ví dụ `RuntimeError`).
  2. Lọc log theo `event == "request_failed"` trong đúng khoảng thời gian, đọc `payload.detail` để lấy thông tin exception thật.
  3. Gọi `GET /health` xem field `incidents` — kiểm tra `tool_fail` có đang bật không (kịch bản giả lập "Vector store timeout").
- Mitigation tạm thời: nếu do `tool_fail`, tạm fallback trả câu trả lời chung không cần tool RAG; thêm timeout ngắn hơn hoặc retry có giới hạn cho lời gọi retrieve; thông báo cho nhóm người dùng dùng đúng `feature` bị ảnh hưởng.
- Owner: P5 (on-call điều tra) — escalate sang P3 nếu lỗi xuất phát từ agent/RAG, sang P1 nếu lỗi xuất phát từ tầng middleware/request.

## Alert 3

- Tên: Cost Budget Burn
- Severity: Warning
- SLI/SLO liên quan: `daily_cost_usd` trong `config/slo.yaml` (objective $2.5, target 100%/28 ngày) — khớp threshold `total` của panel `cost`.
- Điều kiện và thời gian duy trì: tổng `cost_usd` tính trên rolling window 60 phút > $2.5, duy trì liên tục ≥ 10 phút. Yêu cầu duy trì 10 phút để phân biệt với một request đắt bất thường đơn lẻ.
- Ảnh hưởng tới người dùng: không ảnh hưởng trực tiếp trải nghiệm ngay lúc alert bắn, nhưng nếu không xử lý sẽ vượt budget vận hành và có thể dẫn tới việc phải giới hạn hoặc tắt tính năng cho toàn bộ người dùng.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `cost` và `tokens`, xác nhận mức tăng do số lượng request (traffic) hay do mỗi request tốn nhiều token hơn bình thường.
  2. Nếu do token/request tăng, mở Langfuse xem `usage_details` (`prompt_tokens`/`completion_tokens`) của vài generation gần nhất, so với baseline (~40 input / ~130 output token).
  3. Gọi `GET /health` xem field `incidents` — kiểm tra `cost_spike` có đang bật không (kịch bản nhân `tokens_out` lên 4 lần).
- Mitigation tạm thời: giới hạn `max_tokens` output tạm thời; tắt incident practice `cost_spike` nếu đang test; tạm hạ concurrency traffic để tránh đốt budget nhanh trong lúc điều tra.
- Owner: P5 (on-call điều tra) — escalate sang P3 nếu nguyên nhân ở prompt/model config, sang cả nhóm nếu cần quyết định giới hạn tính năng.
