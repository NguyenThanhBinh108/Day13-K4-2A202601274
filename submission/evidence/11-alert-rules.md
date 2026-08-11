# Evidence: Alert rules từ config/alert_rules.yaml

## Nội dung

```yaml
alerts:
  - name: tail-latency-increase
    severity: warning
    condition: >-
      percentile(latency_ms, 95) > 2000 trong 5 phút
      (tương ứng dashboard panel latency threshold p95 <= 3000ms,
      dùng 2000ms để bắt sớm trước khi vượt SLO).
    type: symptom-based
    owner: Trịnh Hải Đăng
    runbook: docs/alerts.md#alert-1

  - name: error-rate-spike
    severity: critical
    condition: >-
      count(event == "request_failed") / count(event == "request_received") * 100 > 2
      trong 5 phút.
    type: symptom-based
    owner: Trịnh Hải Đăng
    runbook: docs/alerts.md#alert-2

  - name: cost-spike
    severity: warning
    condition: >-
      sum(cost_usd) by 1m > 0.25 trong 5 phút liên tiếp
      (tương ứng ~100 request/phút với chi phí trung bình).
    type: symptom-based
    owner: Trịnh Hải Đăng
    runbook: docs/alerts.md#alert-3
```

## Lưu ý

Tất cả alert đều là **symptom-based** (cảnh báo theo triệu chứng người dùng thấy, không theo nguyên nhân kỹ thuật).
Đây là yêu cầu của `docs/TEAM_SPLIT.md` mục P4.

## Placeholder

Ảnh: `submission/evidence/11-alert-rules.png`
