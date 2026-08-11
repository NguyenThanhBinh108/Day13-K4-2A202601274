# Evidence: validate_logs.py baseline (canonical run)

## Output

```
--- Lab Verification Results ---
Total log records analyzed: 20
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 10
Potential PII leaks detected: 0

--- Grading Scorecard (Estimates) ---
+ [PASSED] Basic JSON schema
+ [PASSED] Correlation ID propagation
+ [PASSED] Log enrichment
+ [PASSED] PII scrubbing

Estimated Score: 100/100
```

## Log mẫu (1 correlation_id)

```json
{"service": "api", "payload": {"message_preview": "What is your refund policy? My email is student@vinuni.edu.vn"}, "event": "request_received", "level": "info", "ts": "2026-08-11T08:16:03.107350Z", "correlation_id": "req-ea83f02b", "user_id_hash": "u01", "session_id": "s01", "feature": "qa", "model": "mock-llm-v1", "env": "dev"}
{"service": "api", "latency_ms": 155, "tokens_in": 35, "tokens_out": 161, "cost_usd": 0.00252, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "level": "info", "ts": "2026-08-11T08:16:03.106456Z", "correlation_id": "req-ea83f02b", "user_id_hash": "u01", "session_id": "s01", "feature": "qa", "model": "mock-llm-v1", "env": "dev"}
```
