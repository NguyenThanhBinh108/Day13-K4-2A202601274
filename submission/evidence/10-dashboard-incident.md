# Evidence: Dashboard khi có incident

Số liệu lấy từ `GET /api/summary` của [`scripts/dashboard_app.py`](../../scripts/dashboard_app.py)
chạy trên `data/logs.jsonl` thật (141 bản ghi), ngày 2026-08-11.

## Cách tái hiện

```bash
python scripts/inject_incident.py                              # đọc config/challenge.json
python scripts/load_test.py --challenge --concurrency 5
python scripts/dashboard_app.py --log-path data/logs.jsonl     # mở http://127.0.0.1:8000
python scripts/inject_incident.py --scenario rag_slow --disable
```

## Giá trị thật của 6 panel

| Panel | Giá trị đo được | Ngưỡng contract | Kết quả |
|---|---|---|---|
| latency | p50 **150ms** · p95 **2650ms** · p99 **2651ms** | p95 ≤ 3000ms | ĐẠT |
| traffic | **1,15** request/phút (69 request) | ≥ 1/phút | ĐẠT |
| errors | **0,00%** (0 failed / 69 received) | ≤ 2% | ĐẠT |
| cost | **0,1462 usd** | ≤ 2,5 usd | ĐẠT |
| tokens | in **2 293** · out **9 289** | ≤ 50 000 | ĐẠT |
| quality | **0,8768** | ≥ 0,75 | ĐẠT |

## Điều đáng chú ý — và đây mới là phần đáng nói khi demo

Incident **có** hiện rõ trên panel latency: p50 nhảy từ 150ms (baseline 64 request) lên
2650ms. Nhưng **không panel nào vi phạm ngưỡng**, kể cả latency.

Lý do: cửa sổ 60 phút chứa cả 64 request baseline lẫn 5 request challenge, nên p95 bị 64
mẫu nhanh kéo xuống còn 2650ms — vẫn dưới SLO 3000ms. Nếu chỉ nhìn 5 request challenge thì
p95 = 2651ms, và cả 5/5 đều vượt **ngưỡng challenge 2000ms**.

Bài học rút ra: **ngưỡng SLO 3000ms quá lỏng để bắt sự cố này**. Alert cứu được là nhờ
ngưỡng challenge 2000ms chặt hơn. Đây là một preventive measure đáng đề xuất trong report —
siết ngưỡng cảnh báo xuống dưới mức SLO để bắt sớm, thay vì đợi thủng SLO mới báo.

## Yêu cầu ảnh chụp

- Nhìn rõ đủ 6 panel với tên panel
- Panel latency thấy p95 tăng rõ so với baseline
- Time range 60 phút và đơn vị của từng panel
- Đường threshold/SLO hiện trên biểu đồ

## Ảnh

- `submission/evidence/09-dashboard-baseline.png` — trước khi bật incident
- `submission/evidence/10-dashboard-incident.png` — sau khi bật incident
