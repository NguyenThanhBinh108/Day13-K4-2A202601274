# Evidence: Triệu chứng từ metrics

Bước đầu tiên của luồng điều tra: metrics cho biết **có gì bất thường**, chưa cho biết ở đâu.
Số liệu đo thật từ `data/logs.jsonl`, run 2026-08-11.

## Challenge

- Challenge ID: `day13-k4-observability-v1` · cohort K4 · seed 1304
- Incident: `rag_slow` · Feature: `monitoring` · Ngưỡng challenge: **2000ms**
- Thời gian: 2026-08-11T10:12:25Z — 10:12:39Z · 5 query chính thức

## So sánh baseline và challenge

| Metric | Baseline (64 req, incident tắt) | Challenge (5 req, `rag_slow` bật) | SLO | Trạng thái |
|---|---|---|---|---|
| Request received | 64 | 5 | — | — |
| Response sent | 64 | 5 | — | — |
| Request failed | 0 | 0 | — | — |
| Error rate | 0,00% | 0,00% | ≤ 2% | ĐẠT |
| Latency p50 | **150 ms** | **2651 ms** | — | — |
| Latency p95 | **150 ms** | **2651 ms** | ≤ 3000 ms | ĐẠT |
| Latency p99 | 151 ms | 2651 ms | ≤ 3000 ms | ĐẠT |
| Latency max | 151 ms | 2651 ms | — | — |
| Cost mỗi request | ~0,0022 usd | 0,002403 usd | — | không tăng |
| Quality mean | ~0,88 | 0,90 | ≥ 0,75 | ĐẠT |

## Triệu chứng đọc được

1. **Latency tăng ×17,7** — p50 từ 150ms lên 2650ms. Đây là tín hiệu duy nhất động.
2. **Độ trễ cộng thêm gần như hằng số ≈ +2500ms** ở mọi request, không phải phân phối đuôi dài.
   Hằng số gợi ý một khoảng chờ cứng, không phải nghẽn tài nguyên hay tranh chấp.
3. **Error rate không đổi (0%)** — tất cả 5 request đều trả 200, không có `request_failed`.
   Loại trừ giả thuyết lỗi hệ thống.
4. **Token và cost không tăng** — loại trừ giả thuyết prompt phình to hoặc đổi model.
5. **Quality không giảm** — loại trừ giả thuyết chất lượng suy giảm do đổi prompt.

Kết hợp 3+4+5: thời gian bị đốt ở một bước **không tiêu tốn token**, tức là ngoài lời gọi LLM.
Metrics đã thu hẹp được phạm vi tới đây, bước tiếp theo cần trace/log để chỉ đúng bước nào.

## Điểm quan trọng — SLO không bắt được sự cố này

Cả 5/5 request đều vượt **ngưỡng challenge 2000ms**, nhưng **0/5** vượt **SLO 3000ms**.
Nếu chỉ cảnh báo khi thủng SLO thì sự cố này lọt lưới hoàn toàn dù latency đã tăng gần 18 lần.

Đây là lập luận cho preventive measure số 1 trong REPORT mục 6: đặt ngưỡng cảnh báo **thấp hơn**
SLO để bắt sớm, thay vì đợi thủng SLO.

## Lệnh tái hiện

```bash
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
python scripts/dashboard_app.py --log-path data/logs.jsonl   # /api/summary
python scripts/inject_incident.py --scenario rag_slow --disable
```

## Bước tiếp theo

→ [`16-trace-root-cause.md`](16-trace-root-cause.md) khoanh vùng span
→ [`17-log-root-cause.md`](17-log-root-cause.md) chứng minh bằng log

## Ảnh

`submission/evidence/15-metrics-symptom.png`
