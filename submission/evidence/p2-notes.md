# Ghi chú đóng góp — P2 (Logging & PII / PII Redaction & Log Pipeline)

> File này không phải `submission/REPORT.md`. Theo [docs/TEAM_SPLIT.md](../../docs/TEAM_SPLIT.md) §1.2,
> chỉ P5 được ghi `REPORT.md`; P5 sẽ gộp nội dung dưới đây vào REPORT.md ở T+210.

## 1. Mục tiêu

Không một dòng log nào (trong toàn bộ record, không chỉ `payload`) chứa PII nguyên văn.

## 2. Việc đã làm

| # | File (exclusive của P2) | Thay đổi |
|---|---|---|
| 1 | `app/logging_config.py` | Đăng ký `scrub_event` vào chuỗi processor của `structlog`, đặt **trước** `JsonlFileProcessor()`. Mở rộng `scrub_event` quét đệ quy **toàn bộ** `event_dict` (mọi key, không chỉ `payload`/`event`). |
| 2 | `app/pii.py` | Thêm pattern `passport` (1 chữ + 7-8 số) và `address_vn` (từ khóa "địa chỉ"/"dia chi"). Thêm hàm `scrub_value()` đệ quy dùng chung cho `logging_config.py`. |
| 3 | `config/logging_schema.json` | Thêm rule `allOf/if-then`: log có `service == "api"` bắt buộc phải có đủ `user_id_hash / session_id / feature / model / env`, khớp `ENRICHMENT_FIELDS` mà `scripts/validate_logs.py` kiểm tra. |
| 4 | `tests/test_pii.py` | Thêm 5 test: `cccd`, `credit_card` (16 số, có/không dấu gạch), `passport`, `address_vn`, và 1 test chứng minh `scrub_event` che được field **ngoài** `payload` (mô phỏng đúng cách `validate_logs.py` chấm — quét `json.dumps(rec)` toàn bộ). |

## 3. Vì sao mở rộng phạm vi scrub

Bản gốc `scrub_event` chỉ quét `event_dict["payload"]` (dict phẳng) và `event_dict["event"]`. Nhưng
`scripts/validate_logs.py` chấm PII bằng cách `json.dumps(rec)` rồi regex trên **toàn bộ** dòng —
bất kỳ field nào khác lọt PII (ví dụ `payload={"detail": str(exc)}` khi exception message chứa dữ
liệu người dùng, hoặc field mới ai đó thêm sau này) cũng bị trừ 30 điểm dù `payload`/`event` sạch.
Giải pháp: `scrub_value()` đệ quy áp dụng cho **mọi** giá trị string trong `event_dict`, không quan
tâm nó nằm ở key nào hay lồng bao sâu.

## 4. Kết quả tự kiểm tra (Definition of Done)

```text
$ pytest tests/test_pii.py tests/test_validate_logs.py -v
8 passed

$ pytest -q                     # toàn repo, không phá vỡ phần của người khác
27 passed

$ python scripts/validate_logs.py     # chạy trên log thật (port 8002, LOG_PATH=data/dev/p2.jsonl)
Potential PII leaks detected: 0
+ [PASSED] PII scrubbing
```

Input test gửi vào `/chat`: email, số điện thoại VN, thẻ tín dụng 16 số, CCCD 12 số trong cùng một
message — tất cả đều bị thay bằng `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`,
`[REDACTED_CCCD]` trong `data/dev/p2.jsonl`.

*(Lưu ý: `correlation_id` lúc test là `"MISSING"` và enrichment fields còn thiếu — đó là phần việc
của P1, chưa hoàn thiện tại thời điểm P2 tự kiểm tra. Không ảnh hưởng tới `[PASSED] PII scrubbing`.)*

## 5. Evidence cần đính kèm (ảnh chụp — tự chụp, xem hướng dẫn bên dưới)

- [ ] `evidence/p2-01-pii-input.png` — request có PII gửi vào `/chat`.
- [ ] `evidence/p2-02-pii-redacted-log.png` — dòng log tương ứng trong `data/dev/p2.jsonl` đã `[REDACTED_*]`.
- [ ] `evidence/p2-03-pytest.png` — output `pytest tests/test_pii.py tests/test_validate_logs.py -v` (8 passed).
- [ ] `evidence/p2-04-validate-logs.png` — output `validate_logs.py` với `Potential PII leaks detected: 0` + `[PASSED] PII scrubbing`.

## 6. Rubric liên quan

- **A1 (10đ)** — phần "PII redaction đúng" trong logging kỹ thuật.
- **B1 (20đ cá nhân)** — có thể giải thích: vì sao `scrub_event` phải đặt trước `JsonlFileProcessor`,
  vì sao phải quét toàn bộ record thay vì chỉ `payload`, cách viết pattern `phone_vn`/`cccd`/`credit_card`
  tránh chồng lấn nhau (thứ tự trong `PII_PATTERNS` quan trọng vì `\b` word-boundary không cho cccd
  khớp nhầm vào giữa dãy 16 số của credit card).
- **B2 (20đ cá nhân)** — commit trên nhánh `feat/p2-pii`, xem mục 7.

## 7. Commit

Nhánh: `feat/p2-pii`
Commit: xem `git log feat/p2-pii` — điền SHA sau khi commit xong.
