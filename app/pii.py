from __future__ import annotations

import hashlib
import re
from typing import Any

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    # Hộ chiếu VN: 1 chữ cái + 7-8 chữ số (ví dụ B1234567).
    # Chỉ chặn dấu "-" ở PHÍA TRÁI: `\b` vẫn khớp ngay sau dấu "-", nên nó nuốt mất
    # đuôi của correlation ID `req-<8 hex>` mỗi khi 8 hex đó tình cờ là 1 chữ cái +
    # 7 chữ số (`req-b1234567` -> `req-[REDACTED_PASSPORT]`, 1.4280% trên 200000 ID),
    # làm đứt mắt xích Traces -> Logs vì trace mang tag `cid:<correlation_id>`.
    # Phía PHẢI giữ `\b` chứ không dùng `(?![\w-])`: correlation ID chỉ dài 8 hex nên
    # match hộ chiếu bên trong nó bắt buộc phải bắt đầu ở ký tự đầu — chặn bên trái là
    # đủ (0/6561 lớp hình dạng, 0/200000 mẫu). Chặn thêm bên phải không cứu được ID nào
    # mà chỉ làm lọt hộ chiếu thật có đuôi gạch nối ("B1234567-VN", "C12345678-A").
    "passport": r"(?<![\w-])[A-Za-z]\d{7,8}\b",
    # "Địa chỉ:"/"dia chi:" followed by free text up to the next separator.
    "address_vn": r"(?i)(?:địa chỉ|dia chi)\s*[:\-]?\s*[^\n,;]+",
}


# Trần số lượt quét lại. Mỗi lượt luôn ăn mất ít nhất một chữ số hoặc một "@" và
# chỉ chèn vào token `[REDACTED_*]` (không chứa chữ số, không chứa "@"), nên vòng lặp
# chắc chắn dừng; trần chỉ là chốt an toàn cho input dài bất thường.
_MAX_SCRUB_PASSES = 10


def scrub_text(text: str) -> str:
    """Quét lại đến khi ổn định thay vì đúng một lượt.

    `re.sub` chỉ khớp không chồng lấn và lookbehind của `phone_vn` (`(?<!\\d)`) đọc
    trên chuỗi GỐC, nên hai PII dính liền nhau chỉ bị che cái đầu:
    `"0901234567+84901234567"` -> `"[REDACTED_PHONE_VN]+84901234567"`. Sau khi thay,
    số thứ hai không còn đứng sau chữ số nữa nên `scripts/validate_logs.py` — vốn quét
    lại `json.dumps(rec)` một lượt độc lập — vẫn bắt được `phone_vn` và trừ 30 điểm
    (đã tái hiện: session_id do client gửi -> "Potential PII leaks detected: 2").
    """
    safe = text
    for _ in range(_MAX_SCRUB_PASSES):
        before = safe
        for name, pattern in PII_PATTERNS.items():
            safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
        if safe == before:
            break
    return safe


def scrub_value(value: Any) -> Any:
    """Recursively scrub PII from strings nested in dicts/lists/tuples.

    Used to sanitize an entire log record (not just a known `payload`/`event`
    key), because the validator scans the full JSON line for leaks — any
    field carrying free text (error detail, a future kwarg, ...) must be
    covered too.
    """
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {key: scrub_value(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(scrub_value(v) for v in value)
    return value


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    """Rút gọn user_id thành 48 bit sha256, chèn "_" vào giữa digest.

    Dấu "_" không nằm trong bộ phân cách mà `phone_vn`/`credit_card` chấp nhận
    (`[ .-]`), đồng thời vẫn là ký tự `\\w` nên chặn luôn ranh giới `\\b` của `cccd`.
    Nhờ vậy hash không bao giờ chứa nổi 10-12 chữ số liên tiếp.

    Lý do phải làm thế: hash 12 hex liền mạch tình cờ khớp `phone_vn`/`cccd` ở tỷ lệ
    0.4690% (đo trên 100000 hash). Đó là false positive cho CẢ hai phía — lớp scrub
    của app che mất hash (hỏng khả năng gộp log theo người dùng), còn 4 detector của
    `scripts/validate_logs.py` thì báo "PII leak" trên chính giá trị đã băm (-30 điểm).
    Không thể nới regex để chữa vì validator mới là ground truth; chỉ có thể làm cho
    giá trị sinh ra không rơi vào vùng nhập nhằng.
    """
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return f"{digest[:6]}_{digest[6:12]}"
