# P4 — Dashboard, SLO & Alert — ghi chú cá nhân

File này dành cho P5 gom vào `submission/REPORT.md` (theo quy ước trong
[docs/TEAM_SPLIT.md](../../docs/TEAM_SPLIT.md) mục 1.2 — chỉ P5 được ghi REPORT.md).

## 1. Phạm vi đã hoàn thành

- [config/slo.yaml](../../config/slo.yaml): thay `note` bằng `rationale` cụ thể cho cả 4 SLI
  (latency_p95_ms, error_rate_pct, daily_cost_usd, quality_score_avg), số liệu khớp trực tiếp với
  threshold trong `config/dashboard.yaml`.
- [config/alert_rules.yaml](../../config/alert_rules.yaml): điền đủ 3 alert symptom-based
  (`high_latency_p95`, `high_error_rate`, `cost_budget_burn`), mỗi alert map 1:1 với một kịch bản
  practice (`rag_slow` / `tool_fail` / `cost_spike`).
- [docs/alerts.md](../../docs/alerts.md): runbook đầy đủ cho cả 3 alert (severity, SLI/SLO, điều
  kiện + thời gian duy trì, ảnh hưởng người dùng, 3 bước kiểm tra đầu, mitigation, owner).
- [docs/dashboard-ui-design.md](../../docs/dashboard-ui-design.md): khảo sát UI/UX Grafana, Datadog,
  Vercel/Linear (có nguồn), quyết định thiết kế áp dụng cho dashboard.
- `scripts/dashboard_app.py` + `scripts/dashboard_static/index.html`: dashboard thật (FastAPI +
  HTML/CSS/JS thuần, không Streamlit, không CDN/thư viện ngoài), đọc trực tiếp `data/logs.jsonl`
  (hoặc `--log-path` khác), tính đúng 6 panel theo `config/dashboard.yaml`, có threshold/SLO line,
  status pill tổng (HEALTHY/DEGRADED), incident banner, theme sáng/tối, auto-refresh theo
  `refresh_seconds` trong contract.
- `config/dashboard.yaml`: giữ nguyên (đã hợp lệ sẵn từ đầu, không cần sửa).

## 2. Cách chạy để chấm/demo

```bash
# 1 lần: cài dependency
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Dev: dashboard đọc data/dev/p4.jsonl (không đụng log của người khác)
python scripts/dashboard_app.py --log-path data/dev/p4.jsonl --port 8090

# Cuối buổi (sau khi P5 tạo data/logs.jsonl canonical): đổi đúng 1 flag
python scripts/dashboard_app.py --log-path data/logs.jsonl --port 8090
```

Mở `http://127.0.0.1:8090`. Panel tự refresh theo `refresh_seconds` trong `config/dashboard.yaml`
(30s); nút "↻ Refresh" để làm mới ngay; nút "◐ Theme" đổi sáng/tối; dropdown khung thời gian mặc định
đúng 60 phút theo contract, có thể đổi 15/30/120 phút để xem thêm (không phá contract vì mặc định vẫn
là 60).

## 3. Kết quả validator

```text
$ python scripts/validate_dashboard.py
HỢP LỆ: 6/6 panel có trong dashboard contract.
```

(Chạy lại và dán output thật của máy đang chấm vào đây nếu số liệu khác.)

## 4. SLO đã chọn và lý do (tóm tắt — chi tiết trong slo.yaml)

| SLI | Objective | Target/window | Lý do ngắn |
|---|---|---|---|
| latency_p95_ms | ≤ 3000ms | 99.5% / 28d | Khớp threshold dashboard + latency_threshold_ms của challenge; đủ nhạy để bắt `rag_slow` (+2.5s) |
| error_rate_pct | ≤ 2% | 99.0% / 28d | Đủ room cho lỗi hạ tầng thoáng qua, vẫn bắt được `tool_fail` (tăng vượt xa 2%) |
| daily_cost_usd | ≤ $2.5 | 100% / 28d | Khớp threshold cost; đủ nhạy bắt `cost_spike` (tokens_out x4) |
| quality_score_avg | ≥ 0.75 | 95% / 28d | Khớp mức "câu trả lời có RAG bình thường" (~0.8) theo heuristic trong agent.py |

## 5. Alert rules (tóm tắt — chi tiết trong alert_rules.yaml + alerts.md)

| Alert | Severity | Điều kiện | Map với incident |
|---|---|---|---|
| high_latency_p95 | critical | p95 > 3000ms, ≥5 phút | `rag_slow` |
| high_error_rate | critical | error_rate_pct > 2%, ≥5 phút | `tool_fail` |
| cost_budget_burn | warning | tổng cost/60m > $2.5, ≥10 phút | `cost_spike` |

## 6. Câu hỏi có thể bị hỏi khi demo (B1) — trả lời nhanh

- **Vì sao p95 mà không phải average?** Average bị outlier kéo lệch, che mất phần người dùng bị ảnh
  hưởng nặng; p95 lộ rõ vấn đề tail latency. Ví dụ số trong
  [docs/kien-thuc-du-an.md](../../docs/kien-thuc-du-an.md) mục 5.2.
- **error_rate_pct tính trên mẫu số nào?** `count(request_failed)/count(request_received)*100` —
  không dùng `response_sent` vì request lỗi không có `response_sent`.
- **SLO 99.5%/28 ngày cho phép vi phạm bao nhiêu?** ~201 phút (error budget).
- **Alert của tôi là symptom-based nghĩa là gì?** Dựa trên p95/error rate/cost — cái người dùng/đội
  vận hành cảm nhận được — không dựa vào tên flag nội bộ như `rag_slow`.
- **Vì sao dashboard không đọc `/metrics` hay Langfuse?** `/metrics` là snapshot in-memory của một
  process, không phải nguồn chuẩn theo contract; contract chốt cứng nguồn là `data/logs.jsonl`.

## 7. Evidence cần chụp thủ công (chưa tự động hoá được — cần chạy runtime thật)

- [ ] Ảnh dashboard baseline (traffic bình thường, không panel nào BREACH), thấy rõ tên panel + time
  range 60 phút + đơn vị + threshold line.
- [ ] Ảnh dashboard lúc bật `rag_slow` (P95 latency tăng rõ, banner DEGRADED xuất hiện).
- [ ] Output `python scripts/validate_dashboard.py` chạy thật trên máy chấm.
- [ ] Output `python -m pytest -q`.
