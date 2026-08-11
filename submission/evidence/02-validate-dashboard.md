# Evidence: validate_dashboard.py output

## Output

```
HỢP LỆ: 6/6 panel có trong dashboard contract.
```

## Dashboard panels (từ config/dashboard.yaml)

1. **latency** — Latency percentiles, source `data/logs.jsonl`, events `[response_sent]`, fields `[latency_ms]`, aggregations `[p50, p95, p99]`, unit `ms`, threshold p95 <= 3000
2. **traffic** — Request traffic, source `data/logs.jsonl`, events `[request_received]`, fields `[event]`, aggregations `[count, rate_per_minute]`, unit `requests_per_minute`, threshold rate_per_minute >= 1
3. **errors** — Error rate and breakdown, source `data/logs.jsonl`, events `[request_received, request_failed]`, fields `[error_type]`, aggregations `[error_rate_pct, count_by_value]`, unit `percent`, threshold error_rate_pct <= 2
4. **cost** — Cost over time, source `data/logs.jsonl`, events `[response_sent]`, fields `[cost_usd]`, aggregations `[sum_by_minute, total]`, unit `usd`, threshold total <= 2.5
5. **tokens** — Input and output tokens, source `data/logs.jsonl`, events `[response_sent]`, fields `[tokens_in, tokens_out]`, aggregations `[sum_by_field]`, unit `tokens`, threshold sum_by_field <= 50000
6. **quality** — Quality proxy, source `data/logs.jsonl`, events `[response_sent]`, fields `[quality_score]`, aggregations `[mean]`, unit `score_0_to_1`, threshold mean >= 0.75
