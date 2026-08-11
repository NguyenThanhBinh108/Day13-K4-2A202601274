# Báo cáo Day 13 Observability — K4

## 1. Thông tin nhóm

- Tên nhóm: K4-2A202601274
- Repository URL: https://github.com/NguyenThanhBinh108/Day13-K4-2A202601274
- Commit SHA cuối: *(điền SHA cuối cùng ngay trước khi nộp — xem `git log -1 --format=%H`)*
- Thành viên và vai trò:

| Thành viên | MSSV | Vai trò | Phạm vi | File sở hữu |
|---|---|---|---|---|
| Đỗ Văn Linh | 2A202601190 | Logging & PII | Correlation ID, request context, log enrichment | `app/middleware.py`, `app/main.py` |
| Đỗ Thu Liễu | 2A202601898 | Logging & PII | PII redaction, log pipeline, logging schema | `app/pii.py`, `app/logging_config.py`, `config/logging_schema.json` |
| Nguyễn Thanh Bình (lead) | 2A202601274 | Tracing & Prompt Version | Traces, prompt v1/v2, label & rollback | `app/tracing.py`, `app/agent.py`, `app/prompt_management.py` |
| Trịnh Hải Đăng | 2A202601602 | Dashboard, SLO & Alert | 6 panel, threshold, SLO, alert rules, runbook | `config/dashboard.yaml`, `config/slo.yaml`, `config/alert_rules.yaml` |
| Trần Chí Vũ | 2A202601044 | Incident, Report & Demo | Challenge, evidence, release, demo | `scripts/`, `submission/`, `.gitignore` |

Nhóm có 5 thành viên trên 4 vai trò: vai trò `Logging & PII` do Linh và Liễu đồng đảm nhiệm,
tách theo file sở hữu chứ không tách thêm vai trò mới.

---

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — canonical run 2026-08-11, 141 bản ghi, **71 correlation ID**, 0 PII leak
- Tổng số traces: **0** — `.env` chưa có key Langfuse nên `/health` trả `tracing_enabled: false`.
  Đây là hạng mục còn thiếu, do P3 (Bình) hoàn thành sau khi có key.
- Số PII leak còn lại: **0** (quét bằng chính 4 detector của `scripts/validate_logs.py`)
- Link/đường dẫn dashboard: chạy cục bộ `python scripts/dashboard_app.py --log-path data/logs.jsonl`
  → `http://127.0.0.1:8000`, API số liệu ở `/api/summary`

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/p1-notes.md` + `submission/evidence/01-validate-logs.png`
- Evidence PII redaction: `submission/evidence/p2-notes.md` + `submission/evidence/p2-04-validate-logs.png`
- Evidence trace waterfall: `submission/evidence/04-trace-waterfall.png`
- Giải thích một span đáng chú ý: **<điền khi có trace thật>**

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: v1 — label `baseline` + `production`
- Version/label candidate: v2 — label `candidate`
- Trace ID của mỗi version: **<điền 2 trace ID từ P3>**
- Bằng chứng đổi label hoặc rollback: `submission/evidence/07-rollback-before.png`, `08-rollback-after.png`

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel**
- Evidence dashboard: `submission/evidence/09-dashboard-baseline.png`, `10-dashboard-incident.png`
- SLO đã chọn và lý do:
  - `latency_p95_ms`: target 99.5%, objective 3000ms — đo thật: baseline p95 **150ms**, challenge p95
    **2651ms**. Lưu ý 2651ms **chưa** thủng SLO 3000ms, nên riêng SLO này không đủ bắt sự cố —
    xem preventive measure ở mục 6.
  - `error_rate_pct`: target 99.0%, objective 2% — challenge run cho thấy 0% error, target 2% có buffer nhạy
  - `daily_cost_usd`: target 100%, objective 2.5 USD — ~0.0025 USD/request, 1000 request/ngày = ~2.5 USD
  - `quality_score_avg`: target 95.0%, objective 0.75 — mock trả ~0.9, target 0.75 đảm bảo output chất lượng
- Alert rules và runbook: `submission/evidence/11-alert-rules.png`, `12-runbook-alert1.png`, `13-runbook-alert2.png`, `14-runbook-alert3.png`

---

## 6. Điều tra challenge

Run thật ngày 2026-08-11, mọi con số dưới đây đo từ `data/logs.jsonl` (141 bản ghi).

- Challenge ID: `day13-k4-observability-v1` (cohort K4, incident `rag_slow`, seed 1304, feature `monitoring`)
- Triệu chứng từ metrics: latency **p50 150ms → 2651ms (×17,7)** giữa baseline (64 request,
  incident tắt) và challenge (5 request, incident bật). Error rate giữ **0%**, cost và token
  **không đổi** — chỉ mỗi latency động. Chi tiết: [`10-dashboard-incident.md`](evidence/10-dashboard-incident.md)
- Trace ID liên quan: **chưa có** — `.env` thiếu key Langfuse nên chưa sinh được trace nào.
  Ba trong bốn mắt xích (Metrics → Logs → Root cause) đã có bằng chứng thật; mắt xích Traces
  chờ P3. Xem [`16-trace-root-cause.md`](evidence/16-trace-root-cause.md)
- Log line/correlation ID liên quan: **`req-ba5d3bd8`**, `latency_ms = 2651`,
  session `k4-challenge-s04`. Hai dòng log nguyên văn cách nhau **2,652s** trong
  [`17-log-root-cause.md`](evidence/17-log-root-cause.md)
- Root cause: cờ incident `rag_slow` bật một **`time.sleep(2.5)` chặn luồng** trong bước truy hồi
  tài liệu `retrieve()` tại [`app/mock_rag.py:18`](../app/mock_rag.py#L18), chạy **trước** lời gọi LLM.
  Bằng chứng: 150ms baseline + 2500ms = 2650ms đo được, khớp tuyệt đối; và vì độ trễ nằm ngoài
  đường đi của token nên `tokens_in/out`, `cost_usd`, `quality_score` đều không đổi — đúng như số liệu.
- Fix action: gỡ `sleep` khỏi đường xử lý request (`python scripts/inject_incident.py --scenario rag_slow --disable`).
  Với hệ thống thật: đặt timeout cho bước retrieval và trả câu trả lời fallback khi quá hạn,
  thay vì để một lời gọi chậm chặn cả request.
- Preventive measure:
  1. **Siết ngưỡng alert xuống dưới SLO.** Sự cố này làm p95 lên 2650ms nhưng **không** thủng
     SLO 3000ms — nếu chỉ cảnh báo khi thủng SLO thì đã bỏ lọt. Ngưỡng challenge 2000ms mới bắt được.
  2. Tách span riêng cho `retrieve` để dashboard thấy được thời gian từng bước, không chỉ tổng.
  3. Alert khi latency tăng mà token/cost **không** tăng — dấu hiệu đặc trưng của nghẽn ở bước
     không dùng LLM, giúp khoanh vùng ngay từ metrics.

---

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Đỗ Văn Linh | `app/middleware.py`, `app/main.py` — correlation ID `req-<8hex>`, contextvars, enrichment `user_id_hash`/`session_id`/`feature`/`model`/`env`, response header `x-request-id` | `feat/p1-linh-correlation` · `863fc37` | |
| Đỗ Thu Liễu | `app/pii.py`, `app/logging_config.py`, `config/logging_schema.json` — đăng ký `scrub_event` trước `JsonlFileProcessor`, mở rộng PII pattern, test redaction | `feat/p2-pii` · `a734f7a`, `8de6d59`, `7f408a4` | |
| Nguyễn Thanh Bình (lead) | `app/tracing.py`, `app/agent.py`, `app/prompt_management.py` — prompt `day13-chat` v1/v2, label `baseline`/`candidate`/`production`, rollback, ≥10 trace có metadata | `feat/p3-binh-prompt-version` · `70c3d44`, `a0b8fd9`, `4bb24f6` | |
| Trịnh Hải Đăng | `config/dashboard.yaml`, `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md` — 6 panel đúng contract, SLO target, 3 alert symptom-based + runbook | `haidang2425` · `e459a03`, `7e67634` | |
| Trần Chí Vũ | `scripts/`, `submission/` — challenge run, điều tra Metrics → Traces → Logs, gom evidence, release và demo | `feat/p5-incident-report` · `e5af6ea`, `5bbd5a4`, `3d1d248` | |

> Điền commit SHA hoặc link PR cụ thể vào cột thứ ba trước khi nộp. RUBRIC mục B2 (20 điểm cá nhân)
> yêu cầu phần khai ở đây phải khớp với thay đổi thật trong Git.

---

## 8. Checklist nộp bài

- [ ] `python -m pytest -q` xanh
- [ ] `git status --short` sạch, không có `.env`, key, `.venv/`, log chứa PII
- [ ] `python scripts/validate_logs.py` đạt ≥ 80/100
- [ ] `python scripts/validate_dashboard.py` báo `HỢP LỆ: 6/6 panel`
- [ ] Không còn chữ `TODO` trong `config/`
- [ ] REPORT.md mục 7 khai đúng commit/PR của từng người
- [ ] Cả nhóm giải thích được phần mình triển khai
