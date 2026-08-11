"""Dashboard 6 panel của Day 13 — đọc log JSONL, sinh một file HTML tự chứa.

Vì sao là HTML tĩnh chứ không phải Streamlit/Grafana: requirements.txt của lab chỉ có
fastapi/uvicorn/pydantic/structlog/python-dotenv/httpx/langfuse/PyYAML/pytest, không có
pandas/matplotlib/streamlit. docs/DASHBOARD_SETUP.md cho phép "Streamlit, notebook, Grafana
hoặc công cụ tương đương", nên ở đây dùng stdlib + PyYAML để vẽ biểu đồ bằng SVG inline.
File sinh ra mở bằng trình duyệt là chụp màn hình được ngay, không cần cài thêm gì.

Toàn bộ panel (tên, đơn vị, event, field, phép tổng hợp, threshold) được đọc từ
config/dashboard.yaml lúc chạy. Không panel nào được viết cứng trong file này, nhờ vậy
dashboard không bao giờ lệch khỏi contract chấm điểm.

Ví dụ:
    python scripts/dashboard_app.py --source data/dev/p4.jsonl --out build/dashboard.html
    python scripts/dashboard_app.py --source data/logs.jsonl --now latest --open
    python scripts/dashboard_app.py --watch          # sinh lại theo nhịp refresh của contract
"""

from __future__ import annotations

import argparse
import html
import json
import math
import statistics
import sys
import time
import webbrowser
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from scripts.validate_dashboard import DashboardConfigError, load_dashboard_config

DEFAULT_CONFIG = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_SOURCE = Path("data/logs.jsonl")
DEFAULT_OUT = Path("build/dashboard.html")

# Số chữ số thập phân theo `unit` của contract, cộng hai đơn vị nội bộ cho phép đếm
# ("request" và ""); unit lạ thì rơi về mặc định.
UNIT_DECIMALS = {
    "ms": 0,
    "requests_per_minute": 2,
    "percent": 2,
    "usd": 4,
    "tokens": 0,
    "score_0_to_1": 3,
    "request": 0,
    "": 0,
}
UNIT_DECIMALS_DEFAULT = 2

OPERATOR_SIGN = {"lte": "≤", "gte": "≥"}

STATUS_OK = "ok"
STATUS_VIOLATED = "violated"
STATUS_UNKNOWN = "unknown"
STATUS_LABEL = {
    STATUS_OK: "ĐẠT NGƯỠNG",
    STATUS_VIOLATED: "VI PHẠM NGƯỠNG",
    STATUS_UNKNOWN: "THIẾU DỮ LIỆU",
}


# --------------------------------------------------------------------------- #
# Đọc log
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LogRecord:
    ts: datetime
    event: str
    raw: dict[str, Any]


@dataclass
class SourceStats:
    """Thống kê chất lượng nguồn log, để hiển thị thay vì im lặng bỏ qua dòng hỏng."""

    path: Path
    exists: bool = True
    readable: bool = True
    read_error: str = ""
    total_lines: int = 0
    blank_lines: int = 0
    bad_json: int = 0
    not_object: int = 0
    bad_ts: int = 0
    parsed: int = 0
    oldest: datetime | None = None
    newest: datetime | None = None


def parse_ts(value: Any) -> datetime | None:
    """Ép ts về UTC. Trả None nếu không đọc được — người gọi tự đếm, không raise."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text[-1] in "Zz":
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    # config/logging_schema.json quy định ts là ISO UTC, nên bản ghi thiếu offset
    # được hiểu là UTC thay vì theo giờ máy đang chạy dashboard.
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_records(path: Path) -> tuple[list[LogRecord], SourceStats]:
    stats = SourceStats(path=path)
    if not path.exists():
        stats.exists = False
        return [], stats

    records: list[LogRecord] = []
    try:
        # errors="replace" để một vài byte hỏng không giết cả dashboard.
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stats.total_lines += 1
                text = line.strip()
                if not text:
                    stats.blank_lines += 1
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    stats.bad_json += 1
                    continue
                if not isinstance(payload, dict):
                    stats.not_object += 1
                    continue
                ts = parse_ts(payload.get("ts"))
                if ts is None:
                    stats.bad_ts += 1
                    continue
                event = payload.get("event")
                records.append(
                    LogRecord(ts=ts, event=event if isinstance(event, str) else "", raw=payload)
                )
    except OSError as exc:
        stats.readable = False
        stats.read_error = str(exc)
        return [], stats

    stats.parsed = len(records)
    if records:
        stats.oldest = min(record.ts for record in records)
        stats.newest = max(record.ts for record in records)
    return records, stats


# --------------------------------------------------------------------------- #
# Cửa sổ thời gian
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Window:
    start: datetime  # bao gồm
    end: datetime  # loại trừ
    minutes: int

    def buckets(self) -> list[datetime]:
        return [self.start + timedelta(minutes=i) for i in range(self.minutes)]

    def index_of(self, ts: datetime) -> int | None:
        if not self.start <= ts < self.end:
            return None
        return int((ts - self.start).total_seconds() // 60)

    def label(self) -> str:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        return f"{self.start.strftime(fmt)} → {self.end.strftime(fmt)}"


def floor_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def build_window(now: datetime, minutes: int) -> Window:
    # Cắt theo mốc phút tròn để số bucket đúng bằng time_range_minutes của contract
    # (nếu neo vào giây lẻ sẽ ra 61 cột cho cửa sổ 60 phút).
    end = floor_minute(now) + timedelta(minutes=1)
    return Window(start=end - timedelta(minutes=minutes), end=end, minutes=minutes)


# --------------------------------------------------------------------------- #
# Phép tổng hợp
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Point:
    label: str
    value: float | None  # None = không có mẫu nào, khác hẳn với 0


@dataclass
class Metric:
    aggregation: str
    description: str
    kind: str  # scalar | multi | series | breakdown | unsupported
    value: float | None = None
    points: tuple[Point, ...] = ()
    group: str = ""  # các scalar cùng group được vẽ chung một trục
    note: str = ""
    unit: str | None = None  # đặt khi phép đo không cùng đơn vị với panel (vd: count)

    def unit_or(self, panel_unit: str) -> str:
        return panel_unit if self.unit is None else self.unit

    def threshold_samples(self) -> list[float]:
        """Những con số threshold sẽ soi vào (multi: mọi field đều phải đạt)."""
        if self.kind == "multi":
            return [point.value for point in self.points if point.value is not None]
        return [] if self.value is None else [self.value]

    def display(self, panel_unit: str) -> str:
        """Chuỗi hiển thị của phép đo; multi có nhiều số nên phải liệt kê từng field."""
        unit = self.unit_or(panel_unit)
        if self.kind == "multi":
            if not self.points:
                return "—"
            return " · ".join(
                f"{point.label}={format_value(point.value, unit)}" for point in self.points
            )
        return format_value(self.value, unit)


@dataclass
class PanelContext:
    panel: dict[str, Any]
    records: list[LogRecord]  # đã lọc theo events của panel và theo cửa sổ
    window: Window
    notes: list[str]

    @property
    def events(self) -> list[str]:
        return [str(event) for event in self.panel.get("events", [])]

    @property
    def fields(self) -> list[str]:
        return [str(name) for name in self.panel.get("fields", [])]

    def records_of(self, event: str) -> list[LogRecord]:
        return [record for record in self.records if record.event == event]

    def numbers(self, field_name: str) -> list[float]:
        """Giá trị số của một field; bản ghi thiếu/sai kiểu bị bỏ và được ghi chú."""
        values: list[float] = []
        missing = 0
        for record in self.records:
            raw = record.raw.get(field_name)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                missing += 1
                continue
            if math.isnan(raw) or math.isinf(raw):
                missing += 1
                continue
            values.append(float(raw))
        if missing:
            self.notes.append(
                f"{missing} bản ghi khớp event nhưng thiếu hoặc sai kiểu field `{field_name}`."
            )
        return values

    def first_field(self) -> str | None:
        fields = self.fields
        if not fields:
            self.notes.append("Panel không khai báo `fields` trong contract.")
            return None
        return fields[0]


def nearest_rank_percentile(values: list[float], percent: float) -> float | None:
    """Percentile theo nearest-rank (không nội suy).

    Chọn nearest-rank vì kết quả luôn là một giá trị latency có thật trong log, nên khi
    điều tra incident có thể mở đúng trace/log của mẫu đó. Công thức: sắp xếp tăng dần,
    rank = ceil(p/100 * n), lấy phần tử thứ rank (1-based).
    - n = 0 -> None (không bịa số khi không có mẫu).
    - n = 1 -> mọi percentile đều bằng mẫu duy nhất.
    - n = 2, p50 -> rank = 1 -> lấy mẫu nhỏ hơn (nearest-rank không lấy trung bình).
    """
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil(percent / 100 * len(ordered))
    index = min(max(rank, 1), len(ordered)) - 1
    return ordered[index]


def _percentile_metric(ctx: PanelContext, percent: int) -> Metric:
    field_name = ctx.first_field()
    values = ctx.numbers(field_name) if field_name else []
    return Metric(
        aggregation=f"p{percent}",
        description=f"p{percent} của {field_name or '?'} ({len(values)} mẫu, nearest-rank)",
        kind="scalar",
        value=nearest_rank_percentile(values, percent),
        group="percentiles",
    )


def _minute_series(ctx: PanelContext, values_of: Callable[[LogRecord], float | None]) -> list[float]:
    series = [0.0] * ctx.window.minutes
    for record in ctx.records:
        index = ctx.window.index_of(record.ts)
        if index is None:
            continue
        value = values_of(record)
        if value is not None:
            series[index] += value
    return series


def _series_points(ctx: PanelContext, series: list[float]) -> tuple[Point, ...]:
    return tuple(
        Point(label=bucket.strftime("%H:%M"), value=value)
        for bucket, value in zip(ctx.window.buckets(), series)
    )


def _observed_minutes(series: list[float]) -> int:
    """Số phút từ bucket đầu tới bucket cuối có dữ liệu (span thực tế của traffic)."""
    active = [index for index, value in enumerate(series) if value > 0]
    if not active:
        return 0
    return active[-1] - active[0] + 1


def agg_count(ctx: PanelContext) -> Metric:
    return Metric(
        aggregation="count",
        description=f"Số bản ghi {', '.join(ctx.events) or '?'} trong cửa sổ",
        kind="scalar",
        value=float(len(ctx.records)),
        group="",
        unit="request",  # count là số đếm, không mang đơn vị requests_per_minute của panel
    )


def agg_rate_per_minute(ctx: PanelContext) -> Metric:
    series = _minute_series(ctx, lambda _: 1.0)
    total = sum(series)
    observed = _observed_minutes(series)
    # Quy ước: chia cho số phút QUAN SÁT ĐƯỢC (từ phút đầu tới phút cuối có request),
    # không chia cứng cho 60. Load test dồn trong 1-2 phút mà chia cho cả cửa sổ sẽ ra
    # rate giả thấp và làm sai lệch ngưỡng "có traffic hay không".
    rate = total / observed if observed else None
    window_rate = total / ctx.window.minutes if ctx.window.minutes else 0.0
    note = (
        f"rate = {total:.0f} request / {observed} phút quan sát được; "
        f"trung bình trên cả cửa sổ {ctx.window.minutes} phút là {window_rate:.2f}/phút."
        if observed
        else "Không có request nào trong cửa sổ."
    )
    return Metric(
        aggregation="rate_per_minute",
        description="Request mỗi phút",
        kind="series",
        value=rate,
        points=_series_points(ctx, series),
        note=note,
    )


def agg_error_rate_pct(ctx: PanelContext) -> Metric:
    events = ctx.events
    if len(events) != 2:
        return Metric(
            aggregation="error_rate_pct",
            description="Tỷ lệ lỗi",
            kind="unsupported",
            note="Cần đúng 2 event trong contract: [mẫu số, tử số].",
        )
    # Thứ tự lấy từ contract (events[0] = tổng request, events[1] = request lỗi),
    # không viết cứng tên event trong code.
    total_event, failed_event = events
    total = len(ctx.records_of(total_event))
    failed = len(ctx.records_of(failed_event))
    if total == 0:
        return Metric(
            aggregation="error_rate_pct",
            description=f"{failed_event} / {total_event} × 100",
            kind="scalar",
            value=None,
            note=f"Không có bản ghi `{total_event}` nên không tính được tỷ lệ (không chia cho 0).",
        )
    return Metric(
        aggregation="error_rate_pct",
        description=f"{failed} lỗi / {total} request × 100",
        kind="scalar",
        value=failed / total * 100,
    )


def agg_count_by_value(ctx: PanelContext) -> Metric:
    field_name = ctx.first_field()
    counter: Counter[str] = Counter()
    without_field = 0
    for record in ctx.records:
        raw = record.raw.get(field_name) if field_name else None
        if raw is None or raw == "":
            without_field += 1
            continue
        counter[str(raw)] += 1
    points = tuple(
        Point(label=label, value=float(count)) for label, count in counter.most_common()
    )
    return Metric(
        aggregation="count_by_value",
        description=f"Breakdown theo `{field_name or '?'}`",
        kind="breakdown",
        value=float(sum(counter.values())) if counter else 0.0,
        points=points,
        unit="",  # breakdown đếm số lần, không mang đơn vị của panel
        note=(
            f"{without_field} bản ghi không có `{field_name}` (bình thường với event thành công)."
            if without_field
            else ""
        ),
    )


def agg_sum_by_minute(ctx: PanelContext) -> Metric:
    field_name = ctx.first_field()
    if field_name is None:
        return Metric("sum_by_minute", "Tổng theo phút", "unsupported", note="Thiếu `fields`.")
    ctx.numbers(field_name)  # gọi để ghi chú bản ghi thiếu field, kết quả dùng ở dưới
    series = _minute_series(ctx, lambda record: _as_number(record.raw.get(field_name)))
    return Metric(
        aggregation="sum_by_minute",
        description=f"Tổng `{field_name}` theo từng phút",
        kind="series",
        value=None,
        points=_series_points(ctx, series),
    )


def agg_total(ctx: PanelContext) -> Metric:
    field_name = ctx.first_field()
    values = ctx.numbers(field_name) if field_name else []
    # Không mẫu nào thì trả None chứ không trả 0: tổng 0 trên dashboard trống trông
    # như "chi phí đang rất tốt", trong khi thực tế là chưa có dữ liệu để kết luận.
    return Metric(
        aggregation="total",
        description=f"Tổng `{field_name or '?'}` toàn cửa sổ ({len(values)} mẫu)",
        kind="scalar",
        value=sum(values) if values else None,
    )


def agg_sum_by_field(ctx: PanelContext) -> Metric:
    points: list[Point] = []
    for field_name in ctx.fields:
        values = ctx.numbers(field_name)
        points.append(Point(label=field_name, value=float(sum(values)) if values else None))
    return Metric(
        aggregation="sum_by_field",
        description="Tổng theo từng field",
        kind="multi" if points else "unsupported",
        points=tuple(points),
        note="" if points else "Panel không khai báo `fields`.",
    )


def agg_mean(ctx: PanelContext) -> Metric:
    field_name = ctx.first_field()
    values = ctx.numbers(field_name) if field_name else []
    return Metric(
        aggregation="mean",
        description=f"Trung bình `{field_name or '?'}` ({len(values)} mẫu)",
        kind="scalar",
        value=statistics.fmean(values) if values else None,
    )


def _as_number(raw: Any) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    if math.isnan(raw) or math.isinf(raw):
        return None
    return float(raw)


AGGREGATIONS: dict[str, Callable[[PanelContext], Metric]] = {
    "p50": lambda ctx: _percentile_metric(ctx, 50),
    "p95": lambda ctx: _percentile_metric(ctx, 95),
    "p99": lambda ctx: _percentile_metric(ctx, 99),
    "count": agg_count,
    "rate_per_minute": agg_rate_per_minute,
    "error_rate_pct": agg_error_rate_pct,
    "count_by_value": agg_count_by_value,
    "sum_by_minute": agg_sum_by_minute,
    "total": agg_total,
    "sum_by_field": agg_sum_by_field,
    "mean": agg_mean,
}


# --------------------------------------------------------------------------- #
# Tính panel
# --------------------------------------------------------------------------- #


@dataclass
class PanelResult:
    panel_id: str
    title: str
    unit: str
    events: list[str]
    metrics: list[Metric]
    threshold: dict[str, Any]
    status: str
    matched_records: int
    notes: list[str]

    @property
    def threshold_aggregation(self) -> str:
        return str(self.threshold.get("aggregation", ""))

    def threshold_text(self) -> str:
        operator = str(self.threshold.get("operator", ""))
        sign = OPERATOR_SIGN.get(operator, operator)
        value = self.threshold.get("value")
        return f"{self.threshold_aggregation} {sign} {format_value(value, self.unit)} {self.unit}"

    def headline(self) -> Metric | None:
        for metric in self.metrics:
            if metric.aggregation == self.threshold_aggregation:
                return metric
        return None


def evaluate_threshold(metric: Metric | None, threshold: dict[str, Any]) -> str:
    if metric is None:
        return STATUS_UNKNOWN
    samples = metric.threshold_samples()
    if not samples:
        return STATUS_UNKNOWN
    limit = threshold.get("value")
    operator = threshold.get("operator")
    if not isinstance(limit, (int, float)) or operator not in OPERATOR_SIGN:
        return STATUS_UNKNOWN
    if operator == "lte":
        ok = all(sample <= limit for sample in samples)
    else:
        ok = all(sample >= limit for sample in samples)
    return STATUS_OK if ok else STATUS_VIOLATED


def compute_panel(panel: dict[str, Any], records: list[LogRecord], window: Window) -> PanelResult:
    events = [str(event) for event in panel.get("events", [])]
    matched = [
        record
        for record in records
        if record.event in events and window.index_of(record.ts) is not None
    ]
    notes: list[str] = []
    ctx = PanelContext(panel=panel, records=matched, window=window, notes=notes)

    metrics: list[Metric] = []
    for name in panel.get("aggregations", []):
        aggregation = AGGREGATIONS.get(str(name))
        if aggregation is None:
            metrics.append(
                Metric(
                    aggregation=str(name),
                    description="Chưa hỗ trợ",
                    kind="unsupported",
                    note=f"Aggregation `{name}` có trong contract nhưng script chưa cài đặt.",
                )
            )
            continue
        metrics.append(aggregation(ctx))

    result = PanelResult(
        panel_id=str(panel.get("id", "")),
        title=str(panel.get("title", panel.get("id", ""))),
        unit=str(panel.get("unit", "")),
        events=events,
        metrics=metrics,
        threshold=panel.get("threshold") or {},
        status=STATUS_UNKNOWN,
        matched_records=len(matched),
        notes=_dedupe(notes),
    )
    result.status = evaluate_threshold(result.headline(), result.threshold)
    return result


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        if value:
            seen.setdefault(value, None)
    return list(seen)


# --------------------------------------------------------------------------- #
# Định dạng số
# --------------------------------------------------------------------------- #


def format_value(value: Any, unit: str) -> str:
    if value is None:
        return "—"
    if not isinstance(value, (int, float)):
        return str(value)
    decimals = UNIT_DECIMALS.get(unit, UNIT_DECIMALS_DEFAULT)
    return f"{value:,.{decimals}f}"


def format_axis(value: float, unit: str) -> str:
    decimals = UNIT_DECIMALS.get(unit, UNIT_DECIMALS_DEFAULT)
    if abs(value) >= 1000 and decimals == 0:
        return f"{value / 1000:,.1f}k"
    return f"{value:,.{decimals}f}"


# --------------------------------------------------------------------------- #
# Vẽ SVG
# --------------------------------------------------------------------------- #

CHART_WIDTH = 560
BAR_LABEL_WIDTH = 104
BAR_PLOT_LEFT = BAR_LABEL_WIDTH
BAR_PLOT_RIGHT = 452
BAR_HEIGHT = 22
BAR_ROW = 36
BAR_TOP = 26


def _scale_max(values: Iterable[float], threshold: float | None) -> float:
    candidates = [abs(value) for value in values]
    if threshold is not None:
        candidates.append(abs(threshold))
    peak = max(candidates) if candidates else 0.0
    return peak * 1.15 if peak > 0 else 1.0


def svg_bars(
    bars: list[tuple[str, float | None]],
    unit: str,
    threshold: float | None,
    operator: str,
    highlight: set[str],
) -> str:
    """Bar chart ngang; đường threshold là đường đứt dọc có nhãn."""
    height = BAR_TOP + BAR_ROW * len(bars) + 6
    plot_width = BAR_PLOT_RIGHT - BAR_PLOT_LEFT
    scale = _scale_max([value for _, value in bars if value is not None], threshold)
    parts = [
        f'<svg viewBox="0 0 {CHART_WIDTH} {height}" role="img" '
        f'preserveAspectRatio="xMidYMid meet" class="chart">'
    ]
    for index, (label, value) in enumerate(bars):
        top = BAR_TOP + index * BAR_ROW
        parts.append(
            f'<text class="bar-label" x="{BAR_PLOT_LEFT - 8}" y="{top + 15}" '
            f'text-anchor="end">{esc(label)}</text>'
        )
        parts.append(
            f'<rect class="track" x="{BAR_PLOT_LEFT}" y="{top}" width="{plot_width}" '
            f'height="{BAR_HEIGHT}" rx="3"/>'
        )
        if value is None:
            parts.append(
                f'<text class="bar-value muted" x="{BAR_PLOT_LEFT + 8}" y="{top + 15}">'
                f"không có mẫu</text>"
            )
            continue
        width = max(2.0, min(plot_width, abs(value) / scale * plot_width))
        breached = _breaches(value, threshold, operator) if label in highlight else False
        css = "bar bad" if breached else "bar"
        parts.append(
            f'<rect class="{css}" x="{BAR_PLOT_LEFT}" y="{top}" width="{width:.2f}" '
            f'height="{BAR_HEIGHT}" rx="3"/>'
        )
        parts.append(
            f'<text class="bar-value" x="{BAR_PLOT_RIGHT + 8}" y="{top + 15}">'
            f"{esc(format_value(value, unit))}</text>"
        )
    parts.append(
        f'<line class="axis" x1="{BAR_PLOT_LEFT}" y1="{height - 6}" '
        f'x2="{BAR_PLOT_RIGHT}" y2="{height - 6}"/>'
    )
    parts.append(f'<text class="tick" x="{BAR_PLOT_LEFT}" y="{height - 12}">0</text>')
    parts.append(
        f'<text class="tick" x="{BAR_PLOT_RIGHT}" y="{height - 12}" text-anchor="end">'
        f"{esc(format_axis(scale, unit))}</text>"
    )
    if threshold is not None:
        x = BAR_PLOT_LEFT + min(1.0, abs(threshold) / scale) * plot_width
        parts.append(
            f'<line class="slo" x1="{x:.2f}" y1="14" x2="{x:.2f}" y2="{height - 6}"/>'
        )
        anchor = "end" if x > CHART_WIDTH * 0.7 else "start"
        offset = -6 if anchor == "end" else 6
        parts.append(
            f'<text class="slo-label" x="{x + offset:.2f}" y="11" text-anchor="{anchor}">'
            f"SLO {esc(format_value(threshold, unit))}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


COL_TOP = 18
COL_BOTTOM = 132
COL_LEFT = 46
COL_RIGHT = 552


def svg_columns(
    points: tuple[Point, ...],
    unit: str,
    threshold: float | None,
    operator: str,
) -> str:
    """Column chart theo phút cho cả cửa sổ, kèm đường threshold ngang."""
    height = 158
    if not points:
        return svg_empty("không có bucket nào")
    scale = _scale_max([point.value for point in points if point.value is not None], threshold)
    slot = (COL_RIGHT - COL_LEFT) / len(points)
    bar_width = max(1.5, slot - 1.4)
    parts = [
        f'<svg viewBox="0 0 {CHART_WIDTH} {height}" role="img" '
        f'preserveAspectRatio="xMidYMid meet" class="chart">'
    ]
    parts.append(
        f'<line class="axis" x1="{COL_LEFT}" y1="{COL_BOTTOM}" x2="{COL_RIGHT}" y2="{COL_BOTTOM}"/>'
    )
    parts.append(f'<line class="grid" x1="{COL_LEFT}" y1="{COL_TOP}" x2="{COL_RIGHT}" y2="{COL_TOP}"/>')
    parts.append(
        f'<text class="tick" x="{COL_LEFT - 6}" y="{COL_TOP + 4}" text-anchor="end">'
        f"{esc(format_axis(scale, unit))}</text>"
    )
    parts.append(f'<text class="tick" x="{COL_LEFT - 6}" y="{COL_BOTTOM}" text-anchor="end">0</text>')
    plot_height = COL_BOTTOM - COL_TOP
    for index, point in enumerate(points):
        if point.value is None or point.value <= 0:
            continue
        bar_height = max(1.0, min(plot_height, point.value / scale * plot_height))
        x = COL_LEFT + index * slot
        y = COL_BOTTOM - bar_height
        breached = _breaches(point.value, threshold, operator)
        css = "bar bad" if breached else "bar"
        parts.append(
            f'<rect class="{css}" x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" '
            f'height="{bar_height:.2f}"><title>{esc(point.label)} — '
            f"{esc(format_value(point.value, unit))} {esc(unit)}</title></rect>"
        )
    step = max(1, len(points) // 6)
    for index in range(0, len(points), step):
        x = COL_LEFT + index * slot + bar_width / 2
        parts.append(
            f'<text class="tick" x="{x:.2f}" y="{COL_BOTTOM + 14}" text-anchor="middle">'
            f"{esc(points[index].label)}</text>"
        )
    if threshold is not None:
        y = COL_BOTTOM - min(1.0, abs(threshold) / scale) * plot_height
        parts.append(f'<line class="slo" x1="{COL_LEFT}" y1="{y:.2f}" x2="{COL_RIGHT}" y2="{y:.2f}"/>')
        # Nhãn đặt ở mép trái: log mới nhất nằm bên phải nên nhãn bên phải hay đè lên cột.
        label_y = y - 4 if y - 4 > COL_TOP + 2 else y + 11
        parts.append(
            f'<text class="slo-label" x="{COL_LEFT + 3}" y="{label_y:.2f}">'
            f"SLO {esc(format_value(threshold, unit))}</text>"
        )
    parts.append(
        f'<text class="tick" x="{COL_LEFT}" y="{height - 4}">mỗi cột = 1 phút '
        f"({len(points)} phút)</text>"
    )
    parts.append("</svg>")
    return "".join(parts)


def svg_empty(message: str) -> str:
    return (
        f'<svg viewBox="0 0 {CHART_WIDTH} 70" role="img" class="chart">'
        f'<rect class="track" x="0" y="12" width="{CHART_WIDTH}" height="46" rx="4"/>'
        f'<text class="muted" x="{CHART_WIDTH / 2}" y="40" text-anchor="middle">'
        f"{esc(message)}</text></svg>"
    )


def _breaches(value: float, threshold: float | None, operator: str) -> bool:
    if threshold is None or operator not in OPERATOR_SIGN:
        return False
    return value > threshold if operator == "lte" else value < threshold


# --------------------------------------------------------------------------- #
# Dựng HTML
# --------------------------------------------------------------------------- #


def esc(value: Any) -> str:
    """Escape mọi giá trị đi vào HTML/SVG — error_type là dữ liệu từ log, không tin được."""
    return html.escape(str(value), quote=True)


CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; padding: 24px; background: #f1f5f9; color: #0f172a;
  font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 14px; }
header { background: #0f172a; color: #e2e8f0; border-radius: 10px; padding: 18px 22px; }
header h1 { margin: 0 0 10px; font-size: 21px; letter-spacing: .2px; }
.meta { display: flex; flex-wrap: wrap; gap: 8px 18px; font-size: 13px; color: #cbd5f5; }
.meta b { color: #f8fafc; font-weight: 600; }
.scoreline { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.pill { border-radius: 999px; padding: 3px 11px; font-size: 12px; font-weight: 600; }
.pill.ok { background: #16a34a; color: #f0fdf4; }
.pill.violated { background: #dc2626; color: #fef2f2; }
.pill.unknown { background: #64748b; color: #f8fafc; }
.banner { margin-top: 16px; border-radius: 8px; padding: 12px 16px; font-size: 13px;
  background: #fef3c7; border: 1px solid #f59e0b; color: #78350f; }
.banner.error { background: #fee2e2; border-color: #dc2626; color: #7f1d1d; }
.banner ul { margin: 6px 0 0; padding-left: 20px; }
.grid { display: grid; gap: 16px; margin-top: 16px;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); }
.panel { background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #64748b;
  border-radius: 10px; padding: 14px 16px 16px; }
.panel.ok { border-top-color: #16a34a; }
.panel.violated { border-top-color: #dc2626; }
.panel h2 { margin: 0; font-size: 16px; display: flex; align-items: center;
  justify-content: space-between; gap: 10px; }
.unit { font-size: 12px; font-weight: 600; color: #475569; background: #e2e8f0;
  border-radius: 4px; padding: 2px 8px; }
.subhead { margin: 4px 0 10px; font-size: 12px; color: #64748b; }
.stats { display: flex; flex-wrap: wrap; gap: 8px 20px; margin-bottom: 8px; }
.stat { min-width: 96px; }
.stat .k { font-size: 11px; text-transform: uppercase; letter-spacing: .4px; color: #64748b; }
.stat .v { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat .v small { font-size: 11px; font-weight: 600; color: #64748b; margin-left: 3px; }
.chart { width: 100%; height: auto; display: block; margin: 2px 0 6px; }
.chart .bar { fill: #2563eb; }
.chart .bar.bad { fill: #dc2626; }
.chart .track { fill: #f1f5f9; }
.chart .axis { stroke: #cbd5e1; stroke-width: 1; }
.chart .grid { stroke: #e2e8f0; stroke-width: 1; stroke-dasharray: 3 3; }
.chart .slo { stroke: #b91c1c; stroke-width: 1.6; stroke-dasharray: 6 4; }
.chart .slo-label { fill: #b91c1c; font-size: 10px; font-weight: 700; }
.chart .bar-label { fill: #334155; font-size: 12px; }
.chart .bar-value { fill: #0f172a; font-size: 12px; font-weight: 600; }
.chart .tick { fill: #64748b; font-size: 10px; }
.chart .muted { fill: #94a3b8; font-size: 12px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 4px 0 6px; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid #e2e8f0; }
th { font-size: 11px; text-transform: uppercase; letter-spacing: .4px; color: #64748b; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.share { background: #e2e8f0; border-radius: 3px; height: 8px; }
.share span { display: block; height: 8px; border-radius: 3px; background: #2563eb; }
.slo-text { margin: 8px 0 0; font-size: 12px; font-weight: 600; color: #b91c1c; }
.notes { margin: 6px 0 0; padding-left: 18px; font-size: 12px; color: #64748b; }
footer { margin-top: 18px; font-size: 12px; color: #64748b; line-height: 1.6; }
code { background: #e2e8f0; border-radius: 3px; padding: 1px 5px; font-size: 12px; }
"""


def render_stats(panel: PanelResult) -> str:
    cells: list[str] = []
    for metric in panel.metrics:
        unit = metric.unit_or(panel.unit)
        if metric.kind == "multi":
            for point in metric.points:
                cells.append(_stat_cell(point.label, point.value, unit))
        elif metric.kind == "breakdown":
            cells.append(_stat_cell(f"{metric.aggregation} (số nhóm)", len(metric.points), ""))
        elif metric.kind == "series" and metric.value is None:
            # Series thuần (vd sum_by_minute) không có số tổng hợp riêng; hiện đỉnh/phút
            # để hàng stat không có ô trống khó hiểu. Series toàn 0 nghĩa là không có
            # dữ liệu, hiện "—" thay vì 0 để không trông như một phép đo thật.
            positives = [point.value for point in metric.points if point.value]
            cells.append(
                _stat_cell(f"{metric.aggregation} (đỉnh/phút)", max(positives, default=None), unit)
            )
        elif metric.kind == "unsupported":
            cells.append(_stat_cell(metric.aggregation, None, ""))
        else:
            cells.append(_stat_cell(metric.aggregation, metric.value, unit))
    return f'<div class="stats">{"".join(cells)}</div>'


def _stat_cell(key: str, value: Any, unit: str) -> str:
    unit_html = f"<small>{esc(unit)}</small>" if unit and value is not None else ""
    return (
        f'<div class="stat"><div class="k">{esc(key)}</div>'
        f'<div class="v">{esc(format_value(value, unit))}{unit_html}</div></div>'
    )


def render_charts(panel: PanelResult) -> str:
    threshold_agg = panel.threshold_aggregation
    threshold_value = panel.threshold.get("value")
    operator = str(panel.threshold.get("operator", ""))
    blocks: list[str] = []
    grouped: dict[str, list[Metric]] = {}
    order: list[tuple[str, str]] = []  # (loại, khóa) giữ đúng thứ tự aggregations trong contract

    for metric in panel.metrics:
        if metric.kind == "scalar" and metric.group:
            if metric.group not in grouped:
                grouped[metric.group] = []
                order.append(("group", metric.group))
            grouped[metric.group].append(metric)
        else:
            order.append(("metric", metric.aggregation))

    by_aggregation = {metric.aggregation: metric for metric in panel.metrics}
    for kind, key in order:
        if kind == "group":
            metrics = grouped[key]
            bars = [(metric.aggregation, metric.value) for metric in metrics]
            has_threshold = any(metric.aggregation == threshold_agg for metric in metrics)
            blocks.append(
                svg_bars(
                    bars,
                    panel.unit,
                    threshold_value if has_threshold else None,
                    operator,
                    {threshold_agg} if has_threshold else set(),
                )
            )
            continue

        metric = by_aggregation[key]
        applies = metric.aggregation == threshold_agg
        limit = threshold_value if applies else None
        unit = metric.unit_or(panel.unit)
        if metric.kind == "series":
            blocks.append(svg_columns(metric.points, unit, limit, operator))
        elif metric.kind == "multi":
            bars = [(point.label, point.value) for point in metric.points]
            highlight = {point.label for point in metric.points} if applies else set()
            blocks.append(svg_bars(bars, unit, limit, operator, highlight))
        elif metric.kind == "breakdown":
            blocks.append(render_breakdown(metric))
        elif metric.kind == "unsupported":
            blocks.append(svg_empty(metric.note or "aggregation chưa hỗ trợ"))
        elif applies:
            blocks.append(
                svg_bars(
                    [(metric.aggregation, metric.value)],
                    unit,
                    limit,
                    operator,
                    {metric.aggregation},
                )
            )
        # Scalar lẻ không gắn threshold (vd `count`) không cần biểu đồ: một thanh bar
        # không có mốc so sánh chỉ làm rối ảnh chụp, số đã nằm ở hàng stat phía trên.
    return "".join(blocks)


def render_breakdown(metric: Metric) -> str:
    points = [point for point in metric.points if point.value is not None]
    if not points:
        return svg_empty("chưa có giá trị nào để breakdown")
    total = sum(point.value for point in points) or 1.0
    rows = []
    for point in points:
        share = point.value / total * 100
        rows.append(
            "<tr>"
            f"<td>{esc(point.label)}</td>"
            f'<td class="num">{point.value:,.0f}</td>'
            f'<td class="num">{share:.1f}%</td>'
            f'<td style="width:38%"><div class="share">'
            f'<span style="width:{share:.1f}%"></span></div></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Giá trị</th><th class='num'>Số lần</th>"
        f"<th class='num'>Tỷ trọng</th><th>{esc(metric.description)}</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_panel(panel: PanelResult) -> str:
    headline = panel.headline()
    notes = list(panel.notes)
    for metric in panel.metrics:
        if metric.note:
            notes.append(f"{metric.aggregation}: {metric.note}")
    notes_html = (
        f'<ul class="notes">{"".join(f"<li>{esc(note)}</li>" for note in _dedupe(notes))}</ul>'
        if notes
        else ""
    )
    descriptions = " · ".join(
        f"{metric.aggregation} = {metric.description}" for metric in panel.metrics
    )
    return (
        f'<section class="panel {panel.status}">'
        f"<h2><span>{esc(panel.title)}</span>"
        f'<span><span class="unit">{esc(panel.unit)}</span> '
        f'<span class="pill {panel.status}">{esc(STATUS_LABEL[panel.status])}</span></span></h2>'
        f'<p class="subhead">id <code>{esc(panel.panel_id)}</code> · event '
        f"{esc(', '.join(panel.events))} · {panel.matched_records} bản ghi khớp · {esc(descriptions)}</p>"
        f"{render_stats(panel)}"
        f"{render_charts(panel)}"
        f'<p class="slo-text">Threshold contract: {esc(panel.threshold_text())} — '
        f"giá trị đang xét: {esc(headline.display(panel.unit) if headline else '—')}</p>"
        f"{notes_html}"
        "</section>"
    )


def render_html(
    dashboard: dict[str, Any],
    panels: list[PanelResult],
    window: Window,
    stats: SourceStats,
    generated_at: datetime,
    in_window: int,
) -> str:
    refresh = int(dashboard.get("refresh_seconds", 30))
    title = str(dashboard.get("title", "Dashboard"))
    counts = Counter(panel.status for panel in panels)
    banners = "".join(render_banners(stats, in_window, window))
    body_panels = "".join(render_panel(panel) for panel in panels)
    return f"""<title>{esc(title)} — {esc(window.label())}</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{refresh}">
<style>{CSS}</style>
<header>
  <h1>{esc(title)}</h1>
  <div class="meta">
    <span>Time range: <b>{esc(window.label())}</b> ({window.minutes} phút gần nhất, UTC)</span>
    <span>Auto refresh: <b>{refresh}s</b></span>
    <span>Nguồn: <b>{esc(stats.path)}</b></span>
    <span>Sinh lúc: <b>{esc(generated_at.strftime('%Y-%m-%dT%H:%M:%SZ'))}</b></span>
  </div>
  <div class="scoreline">
    <span class="pill ok">{counts[STATUS_OK]} đạt</span>
    <span class="pill violated">{counts[STATUS_VIOLATED]} vi phạm</span>
    <span class="pill unknown">{counts[STATUS_UNKNOWN]} thiếu dữ liệu</span>
    <span class="pill unknown">{len(panels)} panel · {in_window} bản ghi trong cửa sổ</span>
  </div>
</header>
{banners}
<main class="grid">{body_panels}</main>
<footer>
  Panel, đơn vị và threshold được đọc trực tiếp từ <code>config/dashboard.yaml</code> lúc sinh trang;
  không có số nào viết cứng trong <code>scripts/dashboard_app.py</code>.
  Percentile dùng nearest-rank (giá trị có thật trong log, không nội suy).
  Trang tự tải lại sau {refresh}s — chạy script với <code>--watch</code> để số liệu cũng được tính lại.
</footer>
"""


def render_banners(stats: SourceStats, in_window: int, window: Window) -> list[str]:
    banners: list[str] = []
    if not stats.exists:
        banners.append(
            f'<div class="banner error">Không tìm thấy file log <code>{esc(stats.path)}</code>. '
            "Dashboard đang rỗng — chạy load test hoặc trỏ <code>--source</code> sang file khác.</div>"
        )
        return banners
    if not stats.readable:
        banners.append(
            f'<div class="banner error">Không đọc được <code>{esc(stats.path)}</code>: '
            f"{esc(stats.read_error)}</div>"
        )
        return banners

    problems: list[str] = []
    if stats.bad_json:
        problems.append(f"{stats.bad_json} dòng JSON hỏng đã bỏ qua")
    if stats.not_object:
        problems.append(f"{stats.not_object} dòng JSON không phải object đã bỏ qua")
    if stats.bad_ts:
        problems.append(f"{stats.bad_ts} bản ghi thiếu hoặc sai định dạng `ts` đã bỏ qua")
    if problems:
        banners.append(
            '<div class="banner">Chất lượng nguồn log: '
            + "; ".join(esc(problem) for problem in problems)
            + f" (tổng {stats.total_lines} dòng, {stats.parsed} bản ghi đọc được).</div>"
        )
    if in_window == 0:
        detail = "File log rỗng." if stats.parsed == 0 else (
            f"{stats.parsed} bản ghi nằm ngoài cửa sổ (cũ nhất "
            f"{stats.oldest.strftime('%Y-%m-%dT%H:%M:%SZ') if stats.oldest else '?'}, mới nhất "
            f"{stats.newest.strftime('%Y-%m-%dT%H:%M:%SZ') if stats.newest else '?'}). "
            "Dùng `--now latest` để neo cửa sổ vào bản ghi mới nhất."
        )
        banners.append(
            f'<div class="banner error">Không có bản ghi nào trong {window.minutes} phút gần nhất. '
            f"{esc(detail)}</div>"
        )
    return banners


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def resolve_now(raw: str | None, records: list[LogRecord]) -> datetime:
    if raw is None or raw.lower() == "now":
        return datetime.now(timezone.utc)
    if raw.lower() == "latest":
        # Neo vào bản ghi mới nhất để xem lại một file log cũ mà không phải đổi giờ máy.
        return max((record.ts for record in records), default=datetime.now(timezone.utc))
    parsed = parse_ts(raw)
    if parsed is None:
        raise ValueError(f"--now không đọc được: {raw!r} (dùng ISO UTC, 'now' hoặc 'latest')")
    return parsed


def build_dashboard(
    config_path: Path, source: Path, now_arg: str | None
) -> tuple[str, list[PanelResult], SourceStats, int]:
    payload = load_dashboard_config(config_path)
    dashboard = payload["dashboard"]
    minutes = int(dashboard["time_range_minutes"])

    records, stats = load_records(source)
    now = resolve_now(now_arg, records)
    window = build_window(now, minutes)
    in_window = sum(1 for record in records if window.index_of(record.ts) is not None)

    panels = [compute_panel(panel, records, window) for panel in dashboard["panels"]]
    html_text = render_html(
        dashboard=dashboard,
        panels=panels,
        window=window,
        stats=stats,
        generated_at=datetime.now(timezone.utc),
        in_window=in_window,
    )
    return html_text, panels, stats, in_window


def print_summary(panels: list[PanelResult], stats: SourceStats, in_window: int, out: Path) -> None:
    print(f"Nguồn: {stats.path}")
    if not stats.exists:
        print("CẢNH BÁO: file log không tồn tại — dashboard được sinh ở trạng thái rỗng.")
    elif not stats.readable:
        print(f"CẢNH BÁO: không đọc được file log: {stats.read_error}")
    else:
        print(
            f"Đọc {stats.parsed}/{stats.total_lines} dòng "
            f"(JSON hỏng: {stats.bad_json}, không phải object: {stats.not_object}, "
            f"ts hỏng: {stats.bad_ts}) · trong cửa sổ: {in_window}"
        )
        if in_window == 0 and stats.parsed:
            print("CẢNH BÁO: mọi bản ghi đều nằm ngoài cửa sổ — thử thêm `--now latest`.")
        elif in_window == 0:
            print("CẢNH BÁO: không có bản ghi hợp lệ nào.")
    for panel in panels:
        headline = panel.headline()
        value = headline.display(panel.unit) if headline else "—"
        print(
            f"  [{STATUS_LABEL[panel.status]:>15}] {panel.panel_id:<8} {panel.title} — "
            f"{panel.threshold_aggregation} = {value} {panel.unit} "
            f"(threshold {panel.threshold_text()})"
        )
    counts = Counter(panel.status for panel in panels)
    print(
        f"Tổng: {len(panels)} panel · {counts[STATUS_OK]} đạt · "
        f"{counts[STATUS_VIOLATED]} vi phạm · {counts[STATUS_UNKNOWN]} thiếu dữ liệu"
    )
    print(f"Đã ghi: {out}")


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Sinh dashboard HTML 6 panel từ log JSONL theo config/dashboard.yaml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit code: 0 = đã sinh file (kể cả khi log rỗng, chỉ in CẢNH BÁO), "
            "1 = contract sai hoặc không ghi được file."
        ),
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="dashboard contract YAML")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="file log JSONL")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="file HTML sẽ sinh ra")
    parser.add_argument(
        "--now",
        default=None,
        help="mốc cuối cửa sổ: 'now' (mặc định), 'latest' (bản ghi mới nhất) hoặc ISO UTC",
    )
    parser.add_argument("--open", action="store_true", help="mở file HTML bằng trình duyệt")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="sinh lại liên tục theo refresh_seconds của contract (Ctrl+C để dừng)",
    )
    args = parser.parse_args(argv)

    try:
        payload = load_dashboard_config(args.config)
    except DashboardConfigError as exc:
        print(f"KHÔNG HỢP LỆ: {exc}")
        return 1
    refresh = int(payload["dashboard"].get("refresh_seconds", 30))

    while True:
        try:
            html_text, panels, stats, in_window = build_dashboard(args.config, args.source, args.now)
        except (DashboardConfigError, ValueError) as exc:
            print(f"LỖI: {exc}")
            return 1
        try:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(html_text, encoding="utf-8")
        except OSError as exc:
            print(f"LỖI: không ghi được {args.out}: {exc}")
            return 1

        print_summary(panels, stats, in_window, args.out)
        if args.open:
            webbrowser.open(args.out.resolve().as_uri())
            args.open = False  # chỉ mở tab một lần dù đang chạy --watch
        if not args.watch:
            return 0
        try:
            print(f"--watch: sinh lại sau {refresh}s (Ctrl+C để dừng)\n")
            time.sleep(refresh)
        except KeyboardInterrupt:
            print("Đã dừng --watch.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
