# Evidence: Danh sách traces từ Langfuse (≥10 trace)

## Cách lấy

1. Cấu hình `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` trong `.env`
2. Chạy `python scripts/load_test.py --concurrency 5` trên port 8003 (của P3)
3. Mở Langfuse UI → Traces → filter by `session_id` hoặc `feature: monitoring`
4. Chụp màn hình danh sách trace

## Yêu cầu

- Tối thiểu **10 traces** có metadata
- Mỗi trace có đủ: `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`
- Trace ID được liên kết với log qua `cid:<correlation_id>` tag

## Lưu ý

P3 đã bổ sung tag `cid:<correlation_id>` vào trace, giúp search ngược từ Langfuse về `data/logs.jsonl`.
Public test `test_agent_links_prompt_version_to_trace_and_generation` xác nhận metadata chỉ chứa 4 field prompt,
không có `correlation_id` trong metadata (dùng tag thay thế).

## Placeholder

Ảnh: `submission/evidence/03-traces-list.png`
Trace ID mẫu: `*(điền sau khi P3 chạy thật)*`
