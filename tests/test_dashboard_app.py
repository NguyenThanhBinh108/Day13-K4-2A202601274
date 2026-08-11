"""Test cho scripts/dashboard_app.py — số liệu 6 panel và các trường hợp dữ liệu hỏng.

Mọi số kỳ vọng ở đây được tính tay từ FIXTURE_* bên dưới, không lấy từ output của script.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.dashboard_app import (
    build_dashboard,
    load_records,
    main,
    nearest_rank_percentile,
    parse_ts,
)

CONFIG = REPO_ROOT / "config" / "dashboard.yaml"
ANCHOR = "2026-01-01T12:00:30Z"  # mốc cuối cửa sổ dùng cho mọi test, để kết quả tất định

# 10 response_sent: latency 100..900 và một mẫu 5000 làm p95/p99 vượt ngưỡng 3000.
LATENCIES = [100, 200, 300, 400, 500, 600, 700, 800, 900, 5000]
QUALITY = [0.8] * 9 + [0.5]  # mean = (0.8*9 + 0.5) / 10 = 0.77


def write_log(path: Path) -> Path:
    lines: list[str] = []
    base = {"level": "info", "service": "api", "correlation_id": "req-0"}
    first_minute = datetime(2026, 1, 1, 11, 58, tzinfo=timezone.utc)

    def ts(minute_offset: int, second: int) -> str:
        moment = first_minute + timedelta(minutes=minute_offset, seconds=second)
        return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # 12 request_received rải trên đúng 3 phút (11:58, 11:59, 12:00) -> 4 request/phút.
    for index in range(12):
        lines.append(
            json.dumps(
                {"ts": ts(index // 4, index * 4), "event": "request_received", **base}
            )
        )
    for index, (latency, score) in enumerate(zip(LATENCIES, QUALITY)):
        lines.append(
            json.dumps(
                {
                    "ts": ts(index // 4, index * 4 + 1),
                    "event": "response_sent",
                    "latency_ms": latency,
                    "tokens_in": 100,
                    "tokens_out": 50,
                    "cost_usd": 0.01,
                    "quality_score": score,
                    **base,
                }
            )
        )
    # 2 request_failed; một error_type chứa ký tự HTML để kiểm tra escape.
    lines.append(
        json.dumps({"ts": ts(2, 50), "event": "request_failed", "error_type": "TimeoutError", **base})
    )
    lines.append(
        json.dumps(
            {"ts": ts(2, 52), "event": "request_failed", "error_type": "<b>&Retry</b>", **base}
        )
    )
    # Dữ liệu bẩn: sai kiểu field, thiếu ts, ts hỏng, JSON hỏng, không phải object, dòng trống.
    lines.append(json.dumps({"ts": ts(2, 55), "event": "response_sent", "latency_ms": "chậm", **base}))
    lines.append(json.dumps({"event": "response_sent", "latency_ms": 1, **base}))
    lines.append(json.dumps({"ts": "hôm qua", "event": "response_sent", "latency_ms": 1, **base}))
    lines.append("{không phải json}")
    lines.append("[1, 2, 3]")
    lines.append("")
    # Ngoài cửa sổ 60 phút -> phải bị loại hoàn toàn.
    lines.append(json.dumps({"ts": "2026-01-01T09:00:00.000Z", "event": "request_received", **base}))
    lines.append(
        json.dumps(
            {
                "ts": "2026-01-01T09:00:01.000Z",
                "event": "response_sent",
                "latency_ms": 99999,
                "tokens_in": 99999,
                "tokens_out": 99999,
                "cost_usd": 99.0,
                "quality_score": 0.01,
                **base,
            }
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def dashboard(tmp_path: Path):
    source = write_log(tmp_path / "p4.jsonl")
    html_text, panels, stats, in_window = build_dashboard(CONFIG, source, ANCHOR)
    return html_text, {panel.panel_id: panel for panel in panels}, stats, in_window


# --------------------------------------------------------------------------- #
# Percentile
# --------------------------------------------------------------------------- #


def test_percentile_nearest_rank_no_sample_returns_none() -> None:
    assert nearest_rank_percentile([], 95) is None


def test_percentile_nearest_rank_single_sample() -> None:
    assert nearest_rank_percentile([42.0], 50) == 42.0
    assert nearest_rank_percentile([42.0], 99) == 42.0


def test_percentile_nearest_rank_two_samples() -> None:
    # rank = ceil(0.5 * 2) = 1 -> mẫu nhỏ hơn; nearest-rank không nội suy trung bình.
    assert nearest_rank_percentile([10.0, 20.0], 50) == 10.0
    assert nearest_rank_percentile([10.0, 20.0], 95) == 20.0


def test_percentile_nearest_rank_always_returns_observed_value() -> None:
    assert nearest_rank_percentile(LATENCIES, 50) == 500  # rank ceil(5) = 5
    assert nearest_rank_percentile(LATENCIES, 95) == 5000  # rank ceil(9.5) = 10
    assert nearest_rank_percentile(LATENCIES, 99) == 5000


# --------------------------------------------------------------------------- #
# Đọc log
# --------------------------------------------------------------------------- #


def test_parse_ts_accepts_iso_utc_with_z_suffix() -> None:
    parsed = parse_ts("2026-01-01T12:00:30.123456Z")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.hour == 12 and parsed.minute == 0


@pytest.mark.parametrize("value", [None, "", "hôm qua", 12345, "2026-13-45T99:99:99Z"])
def test_parse_ts_rejects_rubbish(value: object) -> None:
    assert parse_ts(value) is None


def test_load_records_counts_broken_lines_instead_of_crashing(tmp_path: Path) -> None:
    source = write_log(tmp_path / "p4.jsonl")
    records, stats = load_records(source)

    assert stats.bad_json == 1
    assert stats.not_object == 1
    assert stats.bad_ts == 2  # một bản ghi thiếu ts, một bản ghi ts sai định dạng
    assert stats.blank_lines == 1
    assert len(records) == stats.parsed == 27


def test_load_records_ignores_utf8_bom_written_by_powershell(tmp_path: Path) -> None:
    source = tmp_path / "bom.jsonl"
    source.write_text(
        json.dumps({"ts": "2026-01-01T12:00:00.000Z", "event": "request_received"}) + "\n",
        encoding="utf-8-sig",
    )

    records, stats = load_records(source)

    assert stats.bad_json == 0
    assert [record.event for record in records] == ["request_received"]


def test_load_records_on_missing_file_reports_instead_of_raising(tmp_path: Path) -> None:
    records, stats = load_records(tmp_path / "không-có.jsonl")

    assert records == []
    assert stats.exists is False


# --------------------------------------------------------------------------- #
# Panel sinh từ contract
# --------------------------------------------------------------------------- #


def test_panels_come_from_contract_not_from_code(dashboard) -> None:
    _, panels, _, _ = dashboard
    contract = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["dashboard"]["panels"]

    assert [panel["id"] for panel in contract] == list(panels)
    for spec in contract:
        panel = panels[spec["id"]]
        assert panel.title == spec["title"]
        assert panel.unit == spec["unit"]
        assert [metric.aggregation for metric in panel.metrics] == spec["aggregations"]
        assert panel.threshold == spec["threshold"]


def test_window_keeps_only_last_60_minutes(dashboard) -> None:
    _, _, _, in_window = dashboard

    # 27 bản ghi đọc được, 2 bản ghi lúc 09:00 nằm ngoài cửa sổ 11:01 -> 12:01.
    assert in_window == 25


def test_latency_panel_percentiles(dashboard) -> None:
    _, panels, _, _ = dashboard
    values = {metric.aggregation: metric.value for metric in panels["latency"].metrics}

    assert values == {"p50": 500, "p95": 5000, "p99": 5000}
    assert panels["latency"].status == "violated"  # p95 = 5000 > 3000


def test_traffic_panel_rate_uses_contract_window_length(dashboard) -> None:
    _, panels, _, _ = dashboard
    metrics = {metric.aggregation: metric for metric in panels["traffic"].metrics}

    assert metrics["count"].value == 12
    # 12 request trên cửa sổ 60 phút của contract = 0.2 request/phút, dưới ngưỡng >= 1.
    assert metrics["rate_per_minute"].value == pytest.approx(12 / 60)
    assert sum(point.value for point in metrics["rate_per_minute"].points) == 12
    assert len(metrics["rate_per_minute"].points) == 60  # đúng một cột mỗi phút
    assert panels["traffic"].status == "violated"


def test_traffic_rate_never_falls_when_traffic_is_added(tmp_path: Path) -> None:
    """Thêm request không bao giờ được làm rate tụt xuống.

    Mẫu số "số phút quan sát được" từng vi phạm tính chất này: 1 request lẻ ra đúng
    1.00/phút (ĐẠT NGƯỠNG) còn 2 request cách nhau 59 phút chỉ còn 0.03/phút (VI PHẠM).
    """
    stamps = [f"2026-01-01T11:{minute:02d}:00.000Z" for minute in range(2, 60)]

    rates: list[float] = []
    for count in range(1, len(stamps) + 1):
        source = tmp_path / f"traffic-{count}.jsonl"
        source.write_text(
            "\n".join(
                json.dumps({"ts": stamp, "event": "request_received"})
                for stamp in stamps[:count]
            )
            + "\n",
            encoding="utf-8",
        )
        _, panels, _, _ = build_dashboard(CONFIG, source, ANCHOR)
        traffic = {panel.panel_id: panel for panel in panels}["traffic"]
        rates.append(traffic.headline().value)

    assert rates == sorted(rates)
    assert rates[0] == pytest.approx(1 / 60)  # 1 request lẻ không được coi là đủ traffic


def test_traffic_panel_needs_a_full_window_of_requests_to_pass(tmp_path: Path) -> None:
    source = tmp_path / "one-per-minute.jsonl"
    source.write_text(
        "\n".join(
            json.dumps({"ts": f"2026-01-01T{11 + (minute + 1) // 60:02d}:"
                              f"{(minute + 1) % 60:02d}:00.000Z", "event": "request_received"})
            for minute in range(60)
        )
        + "\n",
        encoding="utf-8",
    )

    _, panels, _, _ = build_dashboard(CONFIG, source, ANCHOR)
    traffic = {panel.panel_id: panel for panel in panels}["traffic"]

    assert traffic.headline().value == pytest.approx(1.0)
    assert traffic.status == "ok"


def test_errors_panel_rate_and_breakdown(dashboard) -> None:
    _, panels, _, _ = dashboard
    metrics = {metric.aggregation: metric for metric in panels["errors"].metrics}

    assert metrics["error_rate_pct"].value == pytest.approx(2 / 12 * 100)
    assert {point.label: point.value for point in metrics["count_by_value"].points} == {
        "TimeoutError": 1,
        "<b>&Retry</b>": 1,
    }
    assert panels["errors"].status == "violated"  # 16.67% > 2%


def test_cost_panel_total_and_minute_series(dashboard) -> None:
    _, panels, _, _ = dashboard
    metrics = {metric.aggregation: metric for metric in panels["cost"].metrics}

    assert metrics["total"].value == pytest.approx(0.10)  # 10 response × 0.01
    assert max(point.value for point in metrics["sum_by_minute"].points) == pytest.approx(0.04)
    assert panels["cost"].status == "ok"


def test_tokens_panel_sums_each_field(dashboard) -> None:
    _, panels, _, _ = dashboard
    metric = panels["tokens"].metrics[0]

    assert {point.label: point.value for point in metric.points} == {
        "tokens_in": 1000,
        "tokens_out": 500,
    }
    assert panels["tokens"].status == "ok"


def test_quality_panel_mean(dashboard) -> None:
    _, panels, _, _ = dashboard

    assert panels["quality"].metrics[0].value == pytest.approx(0.77)
    assert panels["quality"].status == "ok"


def test_error_rate_never_divides_by_zero(tmp_path: Path) -> None:
    source = tmp_path / "only-failed.jsonl"
    source.write_text(
        json.dumps({"ts": "2026-01-01T12:00:00.000Z", "event": "request_failed", "error_type": "X"})
        + "\n",
        encoding="utf-8",
    )

    _, panels, _, _ = build_dashboard(CONFIG, source, ANCHOR)
    errors = {panel.panel_id: panel for panel in panels}["errors"]

    assert errors.headline().value is None
    assert errors.status == "unknown"


def test_empty_source_reports_missing_data_instead_of_green_zero(tmp_path: Path) -> None:
    source = tmp_path / "empty.jsonl"
    source.write_text("", encoding="utf-8")

    _, panels, _, in_window = build_dashboard(CONFIG, source, ANCHOR)

    assert in_window == 0
    # Tổng của tập rỗng không được hiển thị là 0 "đạt ngưỡng" — phải là thiếu dữ liệu.
    assert {panel.status for panel in panels} == {"unknown"}


# --------------------------------------------------------------------------- #
# HTML sinh ra
# --------------------------------------------------------------------------- #


def test_html_shows_every_panel_title_unit_and_threshold_line(dashboard) -> None:
    html_text, panels, _, _ = dashboard

    assert html_text.count('<section class="panel') == 6
    assert html_text.count('class="slo"') == 6  # mỗi panel một đường threshold trên biểu đồ
    for panel in panels.values():
        assert panel.title in html_text
        assert f'class="unit">{panel.unit}</span>' in html_text
        assert panel.threshold_text() in html_text


def test_html_shows_time_range_and_refresh(dashboard) -> None:
    html_text, _, _, _ = dashboard
    refresh = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["dashboard"]["refresh_seconds"]

    assert "2026-01-01T11:01:00Z → 2026-01-01T12:01:00Z" in html_text
    assert "60 phút gần nhất" in html_text
    assert f'<meta http-equiv="refresh" content="{refresh}">' in html_text


def test_html_starts_with_doctype_then_charset(dashboard) -> None:
    """Thiếu doctype là trình duyệt chuyển sang quirks mode, ảnh evidence sẽ lệch layout."""
    html_text, _, _, _ = dashboard

    assert html_text.startswith('<!doctype html>\n<meta charset="utf-8">\n<title>')


def test_html_escapes_values_taken_from_the_log(dashboard) -> None:
    html_text, _, _, _ = dashboard

    assert "&lt;b&gt;&amp;Retry&lt;/b&gt;" in html_text
    assert "<b>&Retry</b>" not in html_text


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "cp1258"  # terminal Windows không phải UTF-8
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "dashboard_app.py"), *args],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        check=False,
    )


def test_cli_survives_missing_source(tmp_path: Path) -> None:
    out = tmp_path / "dash.html"

    result = run_cli("--source", str(tmp_path / "không-có.jsonl"), "--out", str(out))

    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert out.exists()


def test_cli_survives_empty_source(tmp_path: Path) -> None:
    source = tmp_path / "empty.jsonl"
    source.write_text("", encoding="utf-8")
    out = tmp_path / "dash.html"

    result = run_cli("--source", str(source), "--out", str(out))

    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert out.exists()


def test_cli_rejects_unreadable_now_argument(tmp_path: Path) -> None:
    result = run_cli("--source", str(write_log(tmp_path / "p4.jsonl")), "--now", "hôm qua")

    assert result.returncode == 1


def test_cli_writes_file_and_creates_parent_directory(tmp_path: Path) -> None:
    source = write_log(tmp_path / "p4.jsonl")
    out = tmp_path / "build" / "nested" / "dashboard.html"

    assert main(["--source", str(source), "--out", str(out), "--now", ANCHOR]) == 0
    assert "Day 13 AI Observability" in out.read_text(encoding="utf-8")
