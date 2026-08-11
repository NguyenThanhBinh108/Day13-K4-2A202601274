# Evidence: Khoanh vùng span bất thường

## Challenge

- Challenge ID: `day13-k4-observability-v1` (cohort K4)
- Incident: `rag_slow` · Feature: `monitoring` · Ngưỡng challenge: 2000ms
- Thời điểm run: 2026-08-11T09:39:05Z – 09:39:19Z

## Trạng thái phần trace

> **Chưa chụp được.** App đang chạy với `tracing_enabled: false` vì `.env` chưa có
> `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`. Không có trace nào được gửi lên Langfuse,
> nên **không có trace ID thật để dẫn**. P3 (Bình) phải điền key rồi chạy lại mục "Cách lấy"
> bên dưới. Không điền trace ID phỏng đoán vào đây — RULES cấm làm giả trace.

Trace ID sau khi chạy thật: *(P3 điền)*

## Phần đã chứng minh được bằng số thật

Chưa có trace, nhưng luồng **Metrics → Logs** đã đủ khoanh vùng, và trace chỉ còn nhiệm vụ
xác nhận trực quan span nào ăn thời gian.

| | Baseline (60 request) | Challenge (5 request) | Chênh |
|---|---|---|---|
| p50 latency | 150ms | 2650ms | **×17,7** |
| p95 latency | 150ms | 2651ms | ×17,7 |
| tokens_in / out | 2155 / 8336 toàn cửa sổ | 35 / 92 mỗi request | không đổi |
| cost mỗi request | ~0.0022 usd | 0.001485 usd | không tăng |
| error rate | 0% | 0% | không đổi |

Độ trễ cộng thêm **≈ +2500ms cố định** ở mọi request, không phải đuôi phân phối.

## Suy luận: span nào

Token, chi phí và chất lượng đều không đổi → thời gian **không** bị đốt trong lời gọi LLM.
Trong `LabAgent.run()` chỉ còn ba bước có thể tốn thời gian:

```
LabAgent.run()  ->  retrieve()  ->  resolve_prompt()  ->  FakeLLM.generate()
                    ^^^^^^^^^^
```

`resolve_prompt()` bị loại vì tracing đang tắt nên nó dùng template local, không gọi mạng.
Còn lại `retrieve()`.

## Xác nhận bằng mã nguồn

[`app/mock_rag.py:17-18`](../../app/mock_rag.py#L17-L18):

```python
if STATE["rag_slow"]:
    time.sleep(2.5)
```

Đúng bằng 2500ms cộng thêm đo được: 150ms baseline + 2500ms = 2650ms. Khớp tuyệt đối.

## Root cause

Cờ incident `rag_slow` bật một `time.sleep(2.5)` **chặn luồng** trong bước truy hồi tài liệu
`retrieve()`, chạy **trước** lời gọi LLM. Vì nó nằm ngoài đường đi của token nên chỉ latency
đổi, còn token/cost/quality/error đều giữ nguyên — đúng như số liệu quan sát được.

## Cách lấy ảnh trace (sau khi có key Langfuse)

1. Điền `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` vào `.env`
2. Khởi động lại API, xác nhận `/health` trả `"tracing_enabled": true`
3. `python scripts/inject_incident.py` rồi `python scripts/load_test.py --challenge --concurrency 5`
4. Mở Langfuse → Traces → lọc `feature: monitoring`, sắp xếp theo duration giảm dần
5. Mở trace chậm nhất → xem waterfall → span `retrieve` sẽ chiếm phần lớn thời gian
6. Trace mang tag `cid:<correlation_id>` (xem [`app/agent.py`](../../app/agent.py)) — dùng tag đó
   để nhảy ngược về đúng dòng log trong `data/logs.jsonl`

## Ảnh

`submission/evidence/16-trace-root-cause.png` — *(chờ P3 chụp sau khi có key)*
