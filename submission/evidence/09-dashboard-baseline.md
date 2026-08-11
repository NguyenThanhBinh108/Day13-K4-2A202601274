# Evidence: Dashboard baseline (trạng thái bình thường)

## Cách lấy

1. Chạy `python scripts/load_test.py --concurrency 5` **KHÔNG** bật incident
2. Mở dashboard (Streamlit/Grafana) đọc từ `data/logs.jsonl`
3. Đảm bảo time range = 60 phút
4. Chụp màn hình toàn bộ dashboard

## Yêu cầu ảnh

- Nhìn rõ 6 panel: latency, traffic, errors, cost, tokens, quality
- Mỗi panel có: tên, đơn vị, time range, threshold line
- Latency p50/p95/p99 đều < 1000ms (baseline ~150ms)

## Placeholder

Ảnh: `submission/evidence/09-dashboard-baseline.png`
