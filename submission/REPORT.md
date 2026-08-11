# Báo cáo Day 13 Observability — K4

## 1. Thông tin nhóm

- Tên nhóm: K4-2A202601274
- Repository URL: https://github.com/NguyenThanhBinh108/Day13-K4-2A202601274
- Commit SHA cuối: `e5af6ea` (cập nhật sau khi merge P1, P2, P3)
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

- Điểm `validate_logs.py`: **100/100** (baseline canonical run trên port 8000)
- Tổng số traces: **≥10** (do P3 tạo, evidence trong `submission/evidence/03-traces-list.png`)
- Số PII leak còn lại: **0**
- Link/đường dẫn dashboard: **<điền sau khi P4 deploy>**

---

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/01-validate-logs.png`
- Evidence PII redaction: `submission/evidence/p2-notes.md` + `submission/evidence/p2-04-validate-logs.png`
- Evidence trace waterfall: `submission/evidence/04-trace-waterfall.png`
- Giải thích một span đáng chú ý: **<điền khi có trace thật>**

---

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: v1 — label `baseline` + `production`
- Version/label candidate: v2 — label `candidate`
- Trace ID của mỗi version: **<điền 2 trace ID từ P3>**
- Bằng chứng đổi label hoặc rollback: `submission/evidence/07-rollback-before.png`, `08-rollback-after.png`

---

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel**
- Evidence dashboard: `submission/evidence/09-dashboard-baseline.png`, `10-dashboard-incident.png`
- SLO đã chọn và lý do: **<điền theo config/slo.yaml>**
- Alert rules và runbook: `submission/evidence/11-alert-rules.png`, `12-runbook-alert1.png`, `13-runbook-alert2.png`, `14-runbook-alert3.png`

---

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1`
- Triệu chứng từ metrics: `submission/evidence/15-metrics-symptom.png` — latency p95 tăng vượt ngưỡng 2000ms (chứng kiến ~2660ms), error rate vẫn 0%
- Trace ID liên quan: `submission/evidence/16-trace-root-cause.png`
- Log line/correlation ID liên quan: `submission/evidence/17-log-root-cause.png`
- Root cause: **rag_slow incident** — RAG pipeline được cấu hình chậm cố định (~2656ms mỗi request), kéo theo latency p95 = 2660ms vượt SLO 3000ms
- Fix action: Tối ưu retrieval pipeline (vector index, chunk size, reranker), hoặc tăng ngưỡng SLO tạm thời
- Preventive measure: Thiết lập alert latency p95 > 2000ms, giám sát RAG span duration, circuit breaker cho slow RAG

---

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Đỗ Văn Linh | `app/middleware.py`, `app/main.py` — correlation ID `req-<8hex>`, contextvars, enrichment `user_id_hash`/`session_id`/`feature`/`model`/`env`, response header `x-request-id` | `feat/p1-linh-correlation` — | |
| Đỗ Thu Liễu | `app/pii.py`, `app/logging_config.py`, `config/logging_schema.json` — đăng ký `scrub_event` trước `JsonlFileProcessor`, mở rộng PII pattern, test redaction | `feat/p2-lieu-pii` — | |
| Nguyễn Thanh Bình (lead) | `app/tracing.py`, `app/agent.py`, `app/prompt_management.py` — prompt `day13-chat` v1/v2, label `baseline`/`candidate`/`production`, rollback, ≥10 trace có metadata | `feat/p3-binh-prompt-version` — | |
| Trịnh Hải Đăng | `config/dashboard.yaml`, `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md` — 6 panel đúng contract, SLO target, 3 alert symptom-based + runbook | `feat/p4-dang-dashboard` — | |
| Trần Chí Vũ | `scripts/`, `submission/` — challenge run, điều tra Metrics → Traces → Logs, gom evidence, release và demo | `feat/p5-vu-incident-report` — | |

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
