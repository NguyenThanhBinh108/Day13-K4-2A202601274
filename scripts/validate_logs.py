import argparse
import json
import os
import re
import sys
from pathlib import Path

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
REQUIRED_FIELDS = {"ts", "level", "service", "event", "correlation_id"}
ENRICHMENT_FIELDS = {"user_id_hash", "session_id", "feature", "model"}
PII_DETECTORS = {
    "email": re.compile(r"[\w.-]+@[\w.-]+\.\w+"),
    "phone_vn": re.compile(r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)"),
    "cccd": re.compile(r"\b\d{12}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Kiểm tra log schema và PII của Day 13")
    parser.add_argument(
        "--log-path",
        type=Path,
        default=LOG_PATH,
        help="Đường dẫn file log (mặc định đọc env LOG_PATH hoặc data/logs.jsonl)",
    )
    args = parser.parse_args(argv)
    log_path = args.log_path

    if not log_path.exists():
        print(f"Error: {log_path} not found. Run the app and send some requests first.")
        sys.exit(1)

    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not records:
        print("Error: No valid JSON logs found in data/logs.jsonl")
        sys.exit(1)

    total = len(records)
    missing_required = 0
    missing_enrichment = 0
    pii_hits = []
    correlation_ids = set()

    for rec in records:
        # Check required fields (global)
        if not {"ts", "level", "event"}.issubset(rec.keys()):
            missing_required += 1
            
        # Context-specific checks for API requests
        if rec.get("service") == "api":
            if "correlation_id" not in rec or rec.get("correlation_id") == "MISSING":
                missing_required += 1
            
            if not ENRICHMENT_FIELDS.issubset(rec.keys()):
                missing_enrichment += 1

        # Check raw PII independently from the student's scrubbing implementation.
        raw = json.dumps(rec, ensure_ascii=False)
        detected_types = sorted(
            name for name, detector in PII_DETECTORS.items() if detector.search(raw)
        )
        if detected_types:
            pii_hits.append(
                {"event": rec.get("event", "unknown"), "types": detected_types}
            )

        # Collect correlation IDs
        cid = rec.get("correlation_id")
        if cid and cid != "MISSING":
            correlation_ids.add(cid)

    print("--- Lab Verification Results ---")
    print(f"Total log records analyzed: {total}")
    print(f"Records with missing required fields: {missing_required}")
    print(f"Records with missing enrichment (context): {missing_enrichment}")
    print(f"Unique correlation IDs found: {len(correlation_ids)}")
    print(f"Potential PII leaks detected: {len(pii_hits)}")
    if pii_hits:
        events = sorted({hit["event"] for hit in pii_hits})
        types = sorted({pii_type for hit in pii_hits for pii_type in hit["types"]})
        print(f"  Events with leaks: {events}")
        print(f"  PII types detected: {types}")
    
    print("\n--- Grading Scorecard (Estimates) ---")
    score = 100
    if missing_required > 0:
        score -= 30
        print("- [FAILED] Missing required fields (ts, level, etc.)")
    else:
        print("+ [PASSED] Basic JSON schema")

    if len(correlation_ids) < 2:
        score -= 20
        print("- [FAILED] Correlation ID propagation (less than 2 unique IDs)")
    else:
        print("+ [PASSED] Correlation ID propagation")

    if missing_enrichment > 0:
        score -= 20
        print("- [FAILED] Log enrichment (missing user_id_hash, etc.)")
    else:
        print("+ [PASSED] Log enrichment")

    if pii_hits:
        score -= 30
        print("- [FAILED] PII scrubbing (raw PII remains in logs)")
    else:
        print("+ [PASSED] PII scrubbing")

    print(f"\nEstimated Score: {max(0, score)}/100")

if __name__ == "__main__":
    main()
