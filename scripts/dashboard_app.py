from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio  # noqa: E402
from app.metrics import percentile  # noqa: E402  (reuse existing p50/p95/p99 logic, không viết lại)

STATIC_DIR = Path(__file__).resolve().parent / "dashboard_static"
DEFAULT_LOG_PATH = "data/logs.jsonl"

# Panel nào đọc trường nào để lấy "giá trị hiện tại" so với threshold trong
# config/dashboard.yaml. Khoá theo panel id (đã bị validate_dashboard.py chốt
# cứng 6 id), không hardcode lại số threshold ở đây — số threshold luôn đọc
# trực tiếp từ YAML để tránh hai nguồn sự thật lệch nhau.
PANEL_VALUE_RESOLVERS: dict[str, Callable[[dict[str, Any]], float]] = {
    "latency": lambda s: s["latency"]["p95"],
    "traffic": lambda s: s["traffic"]["rate_per_minute"],
    "errors": lambda s: s["errors"]["error_rate_pct"],
    "cost": lambda s: s["cost"]["total_usd"],
    # Contract ghi aggregation "sum_by_field" cho cả tokens_in và tokens_out;
    # diễn giải làm giá trị so ngưỡng là tổng cả hai chiều (token budget gộp).
    "tokens": lambda s: s["tokens"]["tokens_in_total"] + s["tokens"]["tokens_out_total"],
    "quality": lambda s: s["quality"]["mean"],
}

app = FastAPI(title="Day 13 Observability Dashboard")


def log_path() -> Path:
    return Path(os.environ.get("DASHBOARD_LOG_PATH", DEFAULT_LOG_PATH))


def load_yaml(relative_path: str) -> dict[str, Any]:
    path = REPO_ROOT / relative_path
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dashboard_contract() -> dict[str, Any]:
    return load_yaml("config/dashboard.yaml")["dashboard"]


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_records(path: Path, window_minutes: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        ts = parse_ts(rec.get("ts"))
        if ts is None or ts < cutoff:
            continue
        rec["_ts"] = ts
        records.append(rec)
    records.sort(key=lambda r: r["_ts"])
    return records


def _numbers(records: list[dict[str, Any]], field: str) -> list[float]:
    return [r[field] for r in records if isinstance(r.get(field), (int, float))]


def compute_summary(records: list[dict[str, Any]], window_minutes: int) -> dict[str, Any]:
    responses = [r for r in records if r.get("event") == "response_sent"]
    received = [r for r in records if r.get("event") == "request_received"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    latencies = _numbers(responses, "latency_ms")
    costs = _numbers(responses, "cost_usd")
    tokens_in = _numbers(responses, "tokens_in")
    tokens_out = _numbers(responses, "tokens_out")
    quality = _numbers(responses, "quality_score")

    total_received = len(received)
    total_failed = len(failed)
    error_rate = (total_failed / total_received * 100) if total_received else 0.0
    error_breakdown = Counter(str(r.get("error_type") or "unknown") for r in failed)

    return {
        "latency": {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "sample_size": len(latencies),
            "unit": "ms",
        },
        "traffic": {
            "count": total_received,
            "rate_per_minute": round(total_received / window_minutes, 2) if window_minutes else 0.0,
            "unit": "requests_per_minute",
        },
        "errors": {
            "error_rate_pct": round(error_rate, 2),
            "breakdown": dict(error_breakdown),
            "total_failed": total_failed,
            "total_received": total_received,
            "unit": "percent",
        },
        "cost": {
            "total_usd": round(sum(costs), 4),
            "unit": "usd",
        },
        "tokens": {
            "tokens_in_total": int(sum(tokens_in)),
            "tokens_out_total": int(sum(tokens_out)),
            "unit": "tokens",
        },
        "quality": {
            "mean": round(sum(quality) / len(quality), 4) if quality else 0.0,
            "sample_size": len(quality),
            "unit": "score_0_to_1",
        },
    }


def compute_timeseries(
    records: list[dict[str, Any]], window_minutes: int, bucket_minutes: int
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=window_minutes)
    num_buckets = max(1, window_minutes // bucket_minutes)

    def bucket_index(ts: datetime) -> int:
        delta_buckets = (ts - start).total_seconds() / 60 / bucket_minutes
        return max(0, min(num_buckets - 1, int(delta_buckets)))

    latency_b: dict[int, list[float]] = defaultdict(list)
    cost_b: dict[int, list[float]] = defaultdict(list)
    tokens_in_b: dict[int, list[float]] = defaultdict(list)
    tokens_out_b: dict[int, list[float]] = defaultdict(list)
    quality_b: dict[int, list[float]] = defaultdict(list)
    received_b: Counter[int] = Counter()
    failed_b: Counter[int] = Counter()

    for r in records:
        idx = bucket_index(r["_ts"])
        event = r.get("event")
        if event == "response_sent":
            if isinstance(r.get("latency_ms"), (int, float)):
                latency_b[idx].append(r["latency_ms"])
            if isinstance(r.get("cost_usd"), (int, float)):
                cost_b[idx].append(r["cost_usd"])
            if isinstance(r.get("tokens_in"), (int, float)):
                tokens_in_b[idx].append(r["tokens_in"])
            if isinstance(r.get("tokens_out"), (int, float)):
                tokens_out_b[idx].append(r["tokens_out"])
            if isinstance(r.get("quality_score"), (int, float)):
                quality_b[idx].append(r["quality_score"])
        elif event == "request_received":
            received_b[idx] += 1
        elif event == "request_failed":
            failed_b[idx] += 1

    points = []
    for i in range(num_buckets):
        t = start + timedelta(minutes=i * bucket_minutes)
        lat = latency_b.get(i, [])
        qual = quality_b.get(i, [])
        recv = received_b.get(i, 0)
        fail = failed_b.get(i, 0)
        points.append(
            {
                "t": t.isoformat(),
                "latency_p50": percentile(lat, 50) if lat else None,
                "latency_p95": percentile(lat, 95) if lat else None,
                "latency_p99": percentile(lat, 99) if lat else None,
                "traffic": recv,
                "errors": fail,
                "error_rate_pct": round(fail / recv * 100, 2) if recv else 0.0,
                "cost_usd": round(sum(cost_b.get(i, [])), 4),
                "tokens_in": int(sum(tokens_in_b.get(i, []))),
                "tokens_out": int(sum(tokens_out_b.get(i, []))),
                "quality": round(sum(qual) / len(qual), 4) if qual else None,
            }
        )
    return points


def evaluate_threshold(value: float, threshold: dict[str, Any]) -> bool:
    target = threshold["value"]
    if threshold["operator"] == "lte":
        return value <= target
    return value >= target


@app.get("/api/meta")
def api_meta() -> JSONResponse:
    contract = dashboard_contract()
    slo = load_yaml("config/slo.yaml")
    alert_rules = load_yaml("config/alert_rules.yaml")
    return JSONResponse(
        {
            "title": contract["title"],
            "time_range_minutes": contract["time_range_minutes"],
            "refresh_seconds": contract["refresh_seconds"],
            "panels": contract["panels"],
            "slo": slo,
            "alerts": alert_rules.get("alerts", []),
            "log_path": str(log_path()),
        }
    )


@app.get("/api/summary")
def api_summary(window_minutes: int | None = Query(default=None, ge=1, le=1440)) -> JSONResponse:
    contract = dashboard_contract()
    window = window_minutes or contract["time_range_minutes"]
    records = load_records(log_path(), window)
    summary = compute_summary(records, window)

    panels_by_id = {p["id"]: p for p in contract["panels"]}
    evaluation: dict[str, Any] = {}
    for panel_id, resolver in PANEL_VALUE_RESOLVERS.items():
        panel = panels_by_id[panel_id]
        value = resolver(summary)
        evaluation[panel_id] = {
            "value": value,
            "threshold": panel["threshold"],
            "unit": panel["unit"],
            "title": panel["title"],
            "ok": evaluate_threshold(value, panel["threshold"]),
        }

    overall_ok = all(item["ok"] for item in evaluation.values())
    return JSONResponse(
        {
            "window_minutes": window,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(records),
            "summary": summary,
            "evaluation": evaluation,
            "overall_status": "healthy" if overall_ok else "degraded",
        }
    )


@app.get("/api/timeseries")
def api_timeseries(
    window_minutes: int | None = Query(default=None, ge=1, le=1440),
    bucket_minutes: int = Query(default=1, ge=1, le=60),
) -> JSONResponse:
    contract = dashboard_contract()
    window = window_minutes or contract["time_range_minutes"]
    records = load_records(log_path(), window)
    points = compute_timeseries(records, window, bucket_minutes)
    return JSONResponse({"window_minutes": window, "bucket_minutes": bucket_minutes, "points": points})


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Chạy dashboard Day 13 đọc trực tiếp từ file jsonl")
    parser.add_argument(
        "--log-path",
        default=os.environ.get("DASHBOARD_LOG_PATH", DEFAULT_LOG_PATH),
        help="Đường dẫn tới log jsonl (dev: data/dev/p4.jsonl; cuối buổi: data/logs.jsonl)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()

    os.environ["DASHBOARD_LOG_PATH"] = args.log_path

    import uvicorn

    print(f"Dashboard chạy tại http://{args.host}:{args.port}  (đọc log: {args.log_path})")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
