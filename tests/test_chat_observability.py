from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.main import app
from app.pii import hash_user_id


def _chat_payload(*, user_id: str = "student-01", session_id: str = "session-01") -> dict:
    return {
        "user_id": user_id,
        "session_id": session_id,
        "feature": "qa",
        "message": "Explain observability",
    }


def _read_events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.post("/chat", json=_chat_payload())

    assert response.status_code == 200
    events = _read_events(log_path)
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]


def test_chat_propagates_supplied_request_id_and_enriches_all_api_logs(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    monkeypatch.setenv("APP_ENV", "test")

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "req-from-client"},
            json=_chat_payload(),
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-from-client"
    assert response.json()["correlation_id"] == "req-from-client"
    assert float(response.headers["x-response-time-ms"]) >= 0

    api_events = [event for event in _read_events(log_path) if event.get("service") == "api"]
    assert {event["event"] for event in api_events} == {"request_received", "response_sent"}
    for event in api_events:
        assert event["correlation_id"] == "req-from-client"
        assert event["user_id_hash"] == hash_user_id("student-01")
        assert event["session_id"] == "session-01"
        assert event["feature"] == "qa"
        assert event["model"] == "claude-sonnet-4-5"
        assert event["env"] == "test"


def test_sequential_requests_get_distinct_ids_without_context_leakage(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        first = client.post(
            "/chat",
            json=_chat_payload(user_id="first-user", session_id="first-session"),
        )
        second = client.post(
            "/chat",
            json=_chat_payload(user_id="second-user", session_id="second-session"),
        )

    first_id = first.headers["x-request-id"]
    second_id = second.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", first_id)
    assert re.fullmatch(r"req-[0-9a-f]{8}", second_id)
    assert second_id != first_id

    api_events = [event for event in _read_events(log_path) if event.get("service") == "api"]
    second_events = [event for event in api_events if event["correlation_id"] == second_id]
    assert len(second_events) == 2
    assert all(event["session_id"] == "second-session" for event in second_events)
    assert all(event["user_id_hash"] == hash_user_id("second-user") for event in second_events)
