# P4 — Dashboard, SLO & Alert (Trịnh Hải Đăng, 2A202601602)

Notes bàn giao cho Vũ (P5) gom vào `submission/REPORT.md`. Không sửa REPORT.md trực tiếp.

## Đã làm (code)

### 1. `config/dashboard.yaml` — 6 panel đúng contract

Panel: latency, traffic, errors, cost, tokens, quality.
Contract đã pass `python scripts/validate_dashboard.py` → `HỢP LỆ: 6/6 panel`.

### 2. `config/slo.yaml` — SLO targets

- `latency_p95_ms`: objective 3000ms, target 99.5%
- `error_rate_pct`: objective 2%, target 99.0%
- `daily_cost_usd`: objective 2.5 USD, target 100%
- `quality_score_avg`: objective 0.75, target 95.0%

### 3. `config/alert_rules.yaml` — 3 alert symptom-based

1. `tail-latency-increase` — warning — p95 > 2000ms trong 5 phút
2. `error-rate-spike` — critical — error rate > 2% trong 5 phút
3. `cost-spike` — warning — sum(cost_usd) by 1m > 0.25 USD trong 5 phút

### 4. `docs/alerts.md` — runbook cho 3 alert

Mỗi alert có: tên, severity, SLI/SLO, điều kiện, ảnh hưởng, 3 bước kiểm tra, mitigation, owner.

## Cần làm (nếu chưa xong)

- [ ] Deploy dashboard thật (Streamlit/Grafana) đọc từ `data/logs.jsonl`
- [ ] Chụp ảnh dashboard baseline (`submission/evidence/09-dashboard-baseline.png`)
- [ ] Chụp ảnh dashboard khi có incident (`submission/evidence/10-dashboard-incident.png`)
- [ ] Chụp ảnh alert rules (`submission/evidence/11-alert-rules.png`)
- [ ] Chụp ảnh 3 runbook (`submission/evidence/12-runbook-alert1.png`, `13-runbook-alert2.png`, `14-runbook-alert3.png`)
- [ ] Điền commit SHA vào `submission/REPORT.md` mục 7

## Phụ thuộc với người khác

- **Với P5**: cần P5 cung cấp `data/logs.jsonl` canonical để dashboard đọc đúng.
