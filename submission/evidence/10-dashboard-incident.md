# Evidence: Dashboard khi có incident (P95 tăng rõ)

## Cách lấy

1. Chạy `python scripts/inject_incident.py --scenario rag_slow`
2. Chạy `python scripts/load_test.py --concurrency 5`
3. Mở dashboard đọc từ `data/logs.jsonl`
4. Chụp màn hình toàn bộ dashboard

## Yêu cầu ảnh

- Nhìn rõ 6 panel
- Panel **latency** có p95 tăng rõ (trong challenge: ~2660ms, vượt threshold 2000ms)
- Panel **errors** vẫn ở 0% (error rate không đổi)
- Time range = 60 phút

## Placeholder

Ảnh: `submission/evidence/10-dashboard-incident.png`
