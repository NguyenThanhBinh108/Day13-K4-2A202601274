import collections
import itertools
import json
import re
import uuid

from app.pii import hash_user_id, scrub_text, scrub_value

# 4 detector của scripts/validate_logs.py — chép nguyên văn để test khoá đúng thứ
# validator chấm, không phải khoá theo pattern nội bộ của app.
VALIDATOR_DETECTORS = {
    "email": re.compile(r"[\w.-]+@[\w.-]+\.\w+"),
    "phone_vn": re.compile(r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)"),
    "cccd": re.compile(r"\b\d{12}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
}


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    out = scrub_text("So CCCD: 012345678901")
    assert "012345678901" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card_16_digits() -> None:
    card_numbers = (
        "4111111111111111",
        "4111-1111-1111-1111",
        "4111 1111 1111 1111",
    )

    for card_number in card_numbers:
        out = scrub_text(f"Card number: {card_number}")
        assert card_number not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport() -> None:
    out = scrub_text("Passport: B1234567")
    assert "B1234567" not in out
    assert "REDACTED_PASSPORT" in out


def test_passport_pattern_does_not_eat_correlation_id() -> None:
    """Correlation ID `req-<8 hex>` phải đi qua scrub nguyên vẹn.

    `\\b[A-Za-z]\\d{7,8}\\b` khớp ngay sau dấu "-" nên nuốt đuôi ID: đo trên 200000
    ID sinh như app/middleware.py thì 1.4280% bị đổi thành `req-[REDACTED_PASSPORT]`.
    ID hỏng là đứt mắt xích Traces -> Logs (trace mang tag `cid:<correlation_id>`).
    """
    for correlation_id in ("req-b1234567", "req-a0000001", "req-f8647360"):
        assert scrub_text(correlation_id) == correlation_id


def test_correlation_id_shape_survives_scrub_for_every_hex_layout() -> None:
    """Quét toàn bộ không gian hình dạng thay vì tin vào vài mẫu may mắn.

    16 ký tự hex ở vị trí đầu × các đuôi rủi ro nhất (toàn chữ số) đủ phủ mọi
    biến thể mà passport/phone_vn/cccd có thể bắt nhầm.
    """
    risky_tails = ("0000000", "1234567", "9999999", "0123456", "8765432")
    for head in "0123456789abcdef":
        for tail in risky_tails:
            correlation_id = f"req-{head}{tail}"
            assert scrub_text(correlation_id) == correlation_id, correlation_id


def test_real_passport_is_still_redacted() -> None:
    """Nới passport để cứu correlation ID không được phép làm lọt hộ chiếu thật."""
    for text, secret in (
        ("Passport B1234567", "B1234567"),
        ("ho chieu C12345678", "C12345678"),
        ("Passport: B1234567", "B1234567"),
        ("So ho chieu la N7654321.", "N7654321"),
    ):
        out = scrub_text(text)
        assert secret not in out, text
        assert "REDACTED_PASSPORT" in out, text


def test_user_id_hash_survives_scrub_and_validator() -> None:
    """`user_id_hash` không được biến dạng, cũng không được làm validator báo leak.

    Hash 12 hex liền mạch khớp `phone_vn`/`cccd` ở tỷ lệ 0.4690% (đo trên 100000
    hash). Đó là false positive hai chiều: scrub che mất hash, còn validator lại
    coi chính giá trị đã băm là PII. `hash_user_id` chèn "_" để chặn cả hai.
    """
    for i in range(20_000):
        digest = hash_user_id(f"user-{i}")
        assert scrub_text(digest) == digest, digest
        hits = sorted(
            name for name, detector in VALIDATOR_DETECTORS.items() if detector.search(digest)
        )
        assert hits == [], f"{digest} -> {hits}"


def test_client_supplied_correlation_id_is_still_scrubbed() -> None:
    """Client tự đặt được `x-request-id` (app/middleware.py) nên field này vẫn phải scrub."""
    from app.logging_config import scrub_event

    out = scrub_event(
        None,
        "info",
        {"event": "request_received", "correlation_id": "0901234567"},
    )

    assert out["correlation_id"] != "0901234567"
    assert "REDACTED_PHONE_VN" in out["correlation_id"]


def test_scrub_vietnamese_address_keyword() -> None:
    out = scrub_text("Dia chi: 123 Nguyen Trai, Quan 1")
    assert "123 Nguyen Trai" not in out
    assert "REDACTED_ADDRESS_VN" in out


def test_scrub_event_covers_entire_record_not_only_payload() -> None:
    """scrub_event must sanitize the whole log record.

    validate_logs.py scans `json.dumps(rec)` end-to-end, so a leak in any
    field outside `payload`/`event` still costs 30 points.
    """
    from app.logging_config import scrub_event

    event_dict = {
        "event": "request_failed",
        "level": "error",
        "correlation_id": "req-abcdef01",
        "error_type": "ValueError",
        "payload": {"detail": "contact user at a@b.com about the error"},
        "extra_note": "callback number is 0901234567",
    }

    out = scrub_event(None, "error", event_dict)
    raw = json.dumps(out, ensure_ascii=False)

    assert "a@b.com" not in raw
    assert "0901234567" not in raw
    assert "REDACTED_EMAIL" in raw
    assert "REDACTED_PHONE_VN" in raw


def test_scrub_event_keeps_the_join_keys_of_one_real_record_intact() -> None:
    """Một record thật: PII bị che, còn khoá để join thì phải nguyên vẹn.

    Che được PII mà làm hỏng `correlation_id` hoặc `user_id_hash` thì vẫn hỏng:
    hết đường nối Traces -> Logs và hết đường gộp log theo người dùng.
    """
    from app.logging_config import scrub_event

    correlation_id = "req-b1234567"
    user_id_hash = hash_user_id("u05")

    out = scrub_event(
        None,
        "info",
        {
            "ts": "2026-08-11T09:15:04.123456Z",
            "level": "info",
            "service": "api",
            "event": "request_received",
            "correlation_id": correlation_id,
            "user_id_hash": user_id_hash,
            "session_id": "s05",
            "payload": {"message_preview": "Here is my phone 0987654321"},
        },
    )
    raw = json.dumps(out, ensure_ascii=False)

    assert out["correlation_id"] == correlation_id
    assert out["user_id_hash"] == user_id_hash
    assert out["ts"] == "2026-08-11T09:15:04.123456Z"
    assert "0987654321" not in raw
    assert "REDACTED_PHONE_VN" in raw
    detected = sorted(
        name for name, detector in VALIDATOR_DETECTORS.items() if detector.search(raw)
    )
    assert detected == []


def test_exception_traceback_is_scrubbed_before_reaching_the_file(tmp_path, monkeypatch) -> None:
    """`stack`/`exception` do structlog dựng ra cũng là text tự do.

    Hai processor sinh chúng chạy sau `scrub_event` trong chuỗi cũ, nên message của
    exception đi thẳng xuống `data/logs.jsonl` chưa được che — validator quét cả dòng.
    """
    import structlog

    from app import logging_config

    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    logging_config.configure_logging()
    try:
        log = structlog.get_logger()
        try:
            raise ValueError("khach hang a@b.com, so 0901234567")
        except ValueError:
            log.error("request_failed", service="api", exc_info=True)
    finally:
        # Trả structlog về cấu hình trỏ LOG_PATH gốc, tránh rò sang test khác.
        monkeypatch.undo()
        logging_config.configure_logging()

    raw = log_path.read_text(encoding="utf-8")

    assert "a@b.com" not in raw
    assert "0901234567" not in raw
    assert "REDACTED_EMAIL" in raw


def test_passport_with_hyphen_suffix_is_still_redacted() -> None:
    """Nới passport để cứu correlation ID không được kéo theo lọt hộ chiếu có đuôi "-".

    Chặn cả hai phía (`(?![\\w-])`) làm `B1234567-VN` thoát scrub, trong khi chặn một
    phía trái đã đủ cứu correlation ID — xem `test_passport_left_guard_alone_...`.
    """
    for text, secret in (
        ("Ho chieu so B1234567-VN het han", "B1234567-VN"),
        ("ho chieu B1234567-2020 het han", "B1234567-2020"),
        ("So HC: C12345678-A", "C12345678-A"),
    ):
        out = scrub_text(text)
        assert secret not in out, text
        assert "REDACTED_PASSPORT" in out, text


def test_passport_left_guard_alone_covers_every_correlation_id_shape() -> None:
    """Vét cạn thay vì lấy mẫu: chứng minh chặn một phía trái là đủ.

    Regex chỉ phân biệt 3 lớp ký tự trong `req-<8 hex>`: "0", chữ số 1-9, chữ cái a-f.
    3^8 = 6561 lớp hình dạng phủ hết mọi ID mà `app/middleware.py` sinh ra được.
    """
    representative = {"0": "0", "d": "7", "L": "b"}
    for combo in itertools.product("0dL", repeat=8):
        correlation_id = "req-" + "".join(representative[c] for c in combo)
        assert scrub_text(correlation_id) == correlation_id, correlation_id


def test_two_pii_stuck_together_are_both_redacted() -> None:
    """PII dính liền nhau: một lượt `re.sub` chỉ che được cái đầu.

    `(?<!\\d)` của `phone_vn` đọc trên chuỗi gốc nên số thứ hai bị bỏ qua, nhưng sau
    khi số đầu thành `[REDACTED_PHONE_VN]` thì nó lại hết đứng sau chữ số —
    `scripts/validate_logs.py` quét lại một lượt độc lập nên vẫn tính là leak.
    """
    for text in (
        "0901234567+84901234567",
        "012345678901+84901234567",
        "4111111111111111+84901234567",
        "0901234567+84901234567+84901234567+84901234567",
    ):
        out = scrub_text(text)
        detected = sorted(
            name for name, detector in VALIDATOR_DETECTORS.items() if detector.search(out)
        )
        assert detected == [], f"{text!r} -> {out!r} {detected}"


def test_client_supplied_session_id_leaves_no_leak_for_the_validator() -> None:
    """`session_id` là text tự do do client gửi và chỉ đi qua scrub_event đúng 1 lượt."""
    from app.logging_config import scrub_event

    out = scrub_event(
        None,
        "info",
        {
            "event": "request_received",
            "service": "api",
            "session_id": "0901234567+84901234567",
            "payload": {"message_preview": "Xin chao"},
        },
    )
    raw = json.dumps(out, ensure_ascii=False)
    detected = sorted(
        name for name, detector in VALIDATOR_DETECTORS.items() if detector.search(raw)
    )
    assert detected == [], raw


def test_correlation_id_generated_like_middleware_is_never_mangled() -> None:
    """Chốt lại bằng mẫu sinh đúng như `uuid.uuid4().hex[:8]` của middleware."""
    for _ in range(5_000):
        correlation_id = f"req-{uuid.uuid4().hex[:8]}"
        assert scrub_text(correlation_id) == correlation_id, correlation_id


def test_scrub_value_never_raises_on_exotic_containers() -> None:
    """scrub_value chạy trong processor của structlog nên không được phép ném.

    `type(value)(<generator>)` dựng lại namedtuple bằng một tham số vị trí duy nhất nên
    ném TypeError; khi đó một log call lỡ truyền namedtuple sẽ làm hỏng cả request thay
    vì chỉ hỏng dòng log.
    """
    Point = collections.namedtuple("Point", "x y")

    assert scrub_value(Point("a@b.com", "ok")) == ("[REDACTED_EMAIL]", "ok")
    assert scrub_value(("a@b.com",)) == ("[REDACTED_EMAIL]",)
    assert scrub_value(["a@b.com"]) == ["[REDACTED_EMAIL]"]
    assert scrub_value({"k": ["a@b.com"]}) == {"k": ["[REDACTED_EMAIL]"]}
    # Kiểu không phải chuỗi/container đi qua nguyên vẹn.
    assert scrub_value(None) is None
    assert scrub_value(0) == 0
