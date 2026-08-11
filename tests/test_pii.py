import json

from app.pii import scrub_text


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
