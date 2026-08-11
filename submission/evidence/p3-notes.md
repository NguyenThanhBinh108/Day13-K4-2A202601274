# P3 — Tracing & Prompt Version (Nguyễn Thanh Bình, 2A202601274)

Notes bàn giao cho Vũ (P5) gom vào `submission/REPORT.md`. Không sửa REPORT.md trực tiếp.

## Đã làm (code)

Nhánh `feat/p3-binh-prompt-version`.

### 1. `app/agent.py` — nối Traces ↔ Logs bằng correlation ID

Trước đây trace chỉ có `user_id`, `session_id` và 4 field prompt. Không có cách nào từ một
trace chậm trên Langfuse tìm ngược ra dòng log tương ứng trong `data/logs.jsonl`, tức là
luồng **Metrics → Traces → Logs** mà rubric A2 yêu cầu bị đứt ở mắt xích cuối.

Bổ sung:

- `current_correlation_id()` đọc `correlation_id` từ structlog contextvars (do middleware của
  P1 bind vào), trả về `"unknown"` khi agent chạy ngoài HTTP request hoặc khi middleware còn
  để giá trị placeholder `"MISSING"`.
- Trace nhận thêm tag `cid:<correlation_id>` → search được trên Langfuse UI.
- Generation metadata nhận thêm `correlation_id`.

Correlation ID **cố ý không** đặt trong `metadata` của trace: public test
`test_agent_links_prompt_version_to_trace_and_generation` khẳng định metadata của trace chỉ
chứa đúng 4 field prompt. Dùng tag giữ nguyên được public test mà vẫn search được.

### 2. `app/tracing.py` — không mất trace khi tắt app

`flush_tracing()` + đăng ký `atexit`. SDK Langfuse v3 gửi span theo batch ở background thread;
tắt uvicorn bằng Ctrl+C ngay sau load test có thể mất batch cuối, tức là thiếu trace trong
evidence. Đặt ở `atexit` nên không phải sửa `app/main.py` (file của P1).

Hàm này nuốt mọi exception: lỗi telemetry không được phép làm chết app.

### 3. `scripts/seed_prompts.py` — prompt versioning bằng script

Thay cho thao tác tay trên UI, để lặp lại được và output in ra dùng thẳng làm evidence:

```bash
python scripts/seed_prompts.py init                 # v1 (baseline+production), v2 (candidate)
python scripts/seed_prompts.py list                 # version + label hiện tại
python scripts/seed_prompts.py promote --version 2  # production -> v2
python scripts/seed_prompts.py rollback             # production -> v1
```

`promote`/`rollback` in trạng thái **TRƯỚC và SAU** để chụp làm bằng chứng đổi label.
Script gọi API thật; thiếu key thì dừng với exit code 1 chứ không giả lập.

v2 giữ nguyên 3 biến bắt buộc `{{feature}}/{{docs}}/{{message}}`, chỉ thêm ràng buộc format
(tối đa 3 câu) — đúng yêu cầu "một thay đổi nhỏ" của `docs/PROMPT_VERSIONING.md`.

### 4. Tests

`python -m pytest -q` → **26 passed** (baseline 22, thêm 4). Không sửa assertion của public
test nào.

## Còn phải làm (cần key Langfuse — chỉ Bình làm được)

- [ ] Điền `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` vào `.env`
- [ ] `python scripts/seed_prompts.py init` → chụp ảnh 2 prompt version
- [ ] Chạy cùng 1 input với `LANGFUSE_PROMPT_LABEL=baseline` rồi `=candidate` → ghi 2 trace ID
- [ ] `promote --version 2` → chạy 1 request → `rollback` → lưu output trước/sau
- [ ] Bắn ≥10 trace trên port 8003, chụp danh sách trace + 1 trace waterfall

Kiểm tra nhanh cấu hình: `/health` phải trả `"tracing_enabled": true`. Nếu trace ghi
`prompt_source=local-fallback` thì host/key hoặc prompt name/label đang sai.

## Điền vào REPORT.md

| Mục | Nội dung |
|---|---|
| 2. Tổng số traces | *(điền sau khi chạy)* |
| 3. Evidence trace waterfall | *(đường dẫn ảnh)* |
| 3. Giải thích một span đáng chú ý | span `retrieve` là nơi incident `rag_slow` làm P95 tăng |
| 4. Prompt name | `day13-chat` |
| 4. Version/label baseline | v1 — `baseline`, `production` |
| 4. Version/label candidate | v2 — `candidate` |
| 4. Trace ID của mỗi version | *(điền sau khi chạy)* |
| 4. Bằng chứng đổi label/rollback | output `seed_prompts.py promote` + `rollback` |

## Phụ thuộc với người khác

- **Với P1 (Linh):** chỉ *đọc* `correlation_id` từ contextvars, không sửa file của Linh. Trước
  khi middleware xong, trace hiển thị `cid:unknown` — đúng như thiết kế, không phải bug. Sau khi
  nhánh của Linh merge, giá trị tự thành `req-xxxxxxxx`.
- **Với P5 (Vũ):** `scripts/seed_prompts.py` là file mới, không đụng script nào Vũ đang sở hữu.

## Lưu ý khi chạy

Chưa cấu hình key thì SDK in một dòng `Authentication error: Langfuse client initialized
without public_key`. Đây là hành vi có sẵn của SDK khi decorator `@observe` khởi tạo client,
không phải lỗi mới; điền key vào `.env` là hết.
