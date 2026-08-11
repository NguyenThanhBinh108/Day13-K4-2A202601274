# Evidence: Trace waterfall và span đáng chú ý

## Trạng thái

> **Chưa chụp được.** `.env` chưa có `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`, nên
> `/health` đang trả `"tracing_enabled": false` và **chưa có trace nào trên Langfuse**.
> Đây là việc của P3 (Bình). Không điền trace ID phỏng đoán vào file này.

Trace ID: *(P3 điền sau khi chạy thật)*

## Cách lấy

1. Điền ba biến vào `.env`:
   ```dotenv
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_SECRET_KEY=
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
2. Khởi động lại API, xác nhận `/health` trả `"tracing_enabled": true`
3. Sinh trace: `python scripts/load_test.py --concurrency 5 --base-url http://127.0.0.1:8000`
4. Mở Langfuse → Traces → chọn một trace có `feature: monitoring`
5. Mở waterfall view → chụp toàn bộ

## Span cần chỉ ra khi demo

`retrieve` — bước truy hồi tài liệu, chạy **trước** lời gọi LLM.

Dự kiến trên waterfall khi bật `rag_slow`: span `retrieve` chiếm ~2500ms trong tổng ~2650ms,
span sinh câu trả lời chỉ vài chục ms. Con số 2500ms không phải phỏng đoán — nó là
`time.sleep(2.5)` tại [`app/mock_rag.py:18`](../../app/mock_rag.py#L18), và đã được xác nhận
bằng đo đạc: baseline 150ms → challenge 2651ms (chênh đúng 2500ms).

## Nối trace về log

Mỗi trace mang tag `cid:<correlation_id>` do [`app/agent.py`](../../app/agent.py) gắn, và
`correlation_id` cũng nằm trong generation metadata. Từ trace chậm:

```bash
python -c "import json;[print(l.strip()) for l in open('data/logs.jsonl',encoding='utf-8') if '<correlation_id>' in l]"
```

Ví dụ đã chạy được với run thật: `req-ba5d3bd8` → hai dòng log `request_received` và
`response_sent`, cách nhau 2,652s. Chi tiết trong
[`17-log-root-cause.md`](17-log-root-cause.md).

## Luồng điều tra đầy đủ

```
Metrics  p50 latency 150ms -> 2650ms (×17,7), error rate và cost không đổi
   |
Traces   span `retrieve` chiếm ~2500ms trong waterfall        <- CHỜ KEY LANGFUSE
   |
Logs     req-ba5d3bd8: ts cách nhau 2,652s, tokens/cost bình thường, không có request_failed
   |
Root cause  time.sleep(2.5) trong retrieve() khi cờ rag_slow bật (app/mock_rag.py:18)
```

Ba trong bốn mắt xích đã có bằng chứng thật. Mắt xích Traces chờ key Langfuse.

## Ảnh

`submission/evidence/04-trace-waterfall.png` — *(chờ P3 chụp)*
