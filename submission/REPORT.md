# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

| Thành viên | MSSV | Vai trò | Phạm vi |
|---|---|---|---|
| Đỗ Văn Linh | 2A202601190 | Logging & PII | Correlation ID, request context, log enrichment |
| Đỗ Thu Liễu | 2A202601898 | Logging & PII | PII redaction, log pipeline, logging schema |
| Nguyễn Thanh Bình (lead) | 2A202601274 | Tracing & Prompt Version | Traces, prompt v1/v2, label & rollback |
| Trịnh Hải Đăng | 2A202601602 | Dashboard, SLO & Alert | 6 panel, threshold, SLO, alert rules, runbook |
| Trần Chí Vũ | 2A202601044 | Incident, Report & Demo | Challenge, evidence, release, demo |

Nhóm có 5 thành viên trên 4 vai trò: vai trò `Logging & PII` do Linh và Liễu đồng đảm nhiệm,
tách theo file sở hữu chứ không tách thêm vai trò mới.

Chi tiết phân công và quy ước sở hữu file: [docs/TEAM_SPLIT.md](../docs/TEAM_SPLIT.md).

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

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
