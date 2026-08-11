# Báo cáo Day 13 Observability — K4

## 1. Thông tin nhóm

- Tên nhóm: K4-2A202601274
- Repository URL: https://github.com/<org>/Day13-K4-2A202601274
- Commit SHA cuối: `git rev-parse HEAD` (chạy ở phút 210)
- Thành viên và vai trò:

| Thành viên | Vai trò | Phạm vi chính | File sở hữu |
|---|---|---|---|
| P1 | Logging & PII | Correlation ID + request context | `app/middleware.py`, `app/main.py` |
| P2 | Logging & PII | PII redaction + log pipeline/schema | `app/pii.py`, `app/logging_config.py`, `config/logging_schema.json` |
| P3 | Tracing & Prompt Version | Traces, prompt v1/v2, label & rollback | `app/tracing.py`, `app/agent.py`, `app/prompt_management.py` |
| P4 | Dashboard, SLO & Alert | 6 panel, threshold, SLO, alert, runbook | `config/dashboard.yaml`, `config/slo.yaml`, `config/alert_rules.yaml` |
| P5 | Incident, Report, Demo & Release | Challenge, report, evidence, release, demo | `scripts/`, `submission/`, `.gitignore` |

---

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **<điền sau khi chạy baseline>**
- Tổng số traces: **<điền sau khi P3 chạy xong>**
- Số PII leak còn lại: **0** (mục tiêu)
- Link/đường dẫn dashboard: **<điền sau khi P4 deploy>**

---

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/01-validate-logs.png`
- Evidence PII redaction: `submission/evidence/01-validate-logs.png` + `submission/evidence/p2-notes.md`
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
- Triệu chứng từ metrics: `submission/evidence/15-metrics-symptom.png` — **<mô tả: latency p95 tăng, error rate tăng>**
- Trace ID liên quan: `submission/evidence/16-trace-root-cause.png`
- Log line/correlation ID liên quan: `submission/evidence/17-log-root-cause.png`
- Root cause: **<điền sau khi chạy challenge>**
- Fix action: **<điền sau khi chạy challenge>**
- Preventive measure: **<điền sau khi chạy challenge>**

---

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| P1 | Correlation ID + request context | `<commit SHA>` | ... |
| P2 | PII redaction + log pipeline/schema | `<commit SHA>` | ... |
| P3 | Traces, prompt v1/v2, label & rollback | `<commit SHA>` | ... |
| P4 | Dashboard, SLO & Alert | `<commit SHA>` | ... |
| P5 | Incident, report, demo, release | `<commit SHA>` | ... |

---

## 8. Checklist nộp bài

- [ ] `python -m pytest -q` xanh
- [ ] `git status --short` sạch, không có `.env`, key, `.venv/`, log chứa PII
- [ ] `python scripts/validate_logs.py` đạt ≥ 80/100
- [ ] `python scripts/validate_dashboard.py` báo `HỢP LỆ: 6/6 panel`
- [ ] Không còn chữ `TODO` trong `config/`
- [ ] REPORT.md mục 7 khai đúng commit/PR của từng người
- [ ] Cả nhóm giải thích được phần mình triển khai
