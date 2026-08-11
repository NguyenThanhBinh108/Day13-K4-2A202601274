# Quy ước đặt tên file evidence

Mọi file trong `submission/evidence/` phải tuân theo quy ước này để P5 gom vào `REPORT.md` không bị thiếu.

## Cấu trúc

```
submission/evidence/
├── README.md                  ← file này
├── 01-validate-logs.png       ← kết quả chạy validate_logs.py (baseline + challenge)
├── 02-validate-dashboard.png  ← output validate_dashboard.py (HỢP LỆ: 6/6 panel)
├── 03-traces-list.png         ← danh sách trace từ Langfuse (≥10 trace)
├── 04-trace-waterfall.png     ← waterfall của 1 trace chọn lọc
├── 05-prompt-v1.png           ← prompt v1 trên Langfuse (label baseline)
├── 06-prompt-v2.png           ← prompt v2 trên Langfuse (label candidate)
├── 07-rollback-before.png     ← trước khi rollback (v2 đang là production)
├── 08-rollback-after.png      ← sau khi rollback (v1 trở lại production)
├── 09-dashboard-baseline.png  ← dashboard ở trạng thái bình thường
├── 10-dashboard-incident.png  ← dashboard khi có incident (P95 tăng rõ)
├── 11-alert-rules.png         ← alert rules từ config/alert_rules.yaml
├── 12-runbook-alert1.png      ← runbook alert 1 (docs/alerts.md#alert-1)
├── 13-runbook-alert2.png      ← runbook alert 2 (docs/alerts.md#alert-2)
├── 14-runbook-alert3.png      ← runbook alert 3 (docs/alerts.md#alert-3)
├── 15-metrics-symptom.png     ← metrics cho thấy triệu chứng (latency/error tăng)
├── 16-trace-root-cause.png    ← trace khoanh vùng span bất thường
├── 17-log-root-cause.png      ← log có correlation_id chứng minh root cause
└── p1-notes.md                ← ghi chú cá nhân P1 (do P1 viết, P5 chỉ gom)
    p2-notes.md                ← ghi chú cá nhân P2
    p3-notes.md                ← ghi chú cá nhân P3
    p4-notes.md                ← ghi chú cá nhân P4
```

## Quy tắc chung

1. **Đuôi file**: dùng `.png` cho ảnh chụp màn hình, `.md` cho ghi chú văn bản.
2. **Tên không dấu, dùng gạch ngang**, bắt đầu bằng số thứ tự 2 chữ số để đúng thứ tự khi gom vào REPORT.md.
3. **Ảnh phải rõ**: nhìn thấy được tên panel, time range, đơn vị, threshold.
4. **Chỉ nộp evidence thật**: không hard-code output, không xóa log lỗi, không làm giả trace/screenshot.
5. **Không commit secret/PII**: kiểm tra `.gitignore` đã chặn `.env`, `.env.local`, `data/dev/`, `.venv/`.

## Trách nhiệm

- P5 chịu trách nhiệm tạo thư mục này và quy ước.
- P1–P4 đưa ảnh/evidence vào đúng vị trí theo quy ước.
- P5 gom vào `REPORT.md` ở phút 210, không ai khác chỉnh `REPORT.md`.
