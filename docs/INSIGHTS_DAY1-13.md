# Insights quan trọng từ Day 1 → Day 13

> File này note những insight **đáng nhớ nhất** để áp dụng vào build sản phẩm thật.
> Mỗi ngày 1 section, mỗi insight là 1 pattern có thể dùng ngay.

---

## Day 11 — Controlled Agent Security

### 1. Source ≠ Instruction
- **Insight**: Email, RAG document, user input là **data**, không phải **instruction**.
- **Production**: Phân biệt rõ `system prompt` (instruction) vs `retrieved context` (data). Không bao giờ treat external content như command.

### 2. Defense in Depth — Không dựa vào 1 lớp
- **Insight**: Input guardrails → Output guardrails → LLM-as-Judge → Egress allowlist.
- **Production**: Mỗi lớp trả lời 1 câu hỏi khác:
  - Input: "Prompt này có độc hại không?"
  - Output: "Response này có lộ secret không?"
  - Judge: "Response này có an toàn không?"
  - Egress: "Hành động này có được phép không?"

### 3. Egress Allowlist — Chỉ allow exact destination
- **Insight**: `is_egress_allowed(destination, payload)` kiểm tra exact HTTPS endpoint, reject subdomain giả, external domain.
- **Production**: Agent không tự quyết policy — developer quyết trước. Allowlist cứng, không động.

### 4. HITL (Human-in-the-Loop) cho high-risk action
- **Insight**: Mọi `HIGH_RISK_ACTIONS` (transfer money, delete data) cần approve/reject/timeout + audit correlation ID.
- **Production**: Không bao giờ auto-execute high-risk action. Luôn có reviewer context + diff + timeout.

### 5. Red Team trước khi ship
- **Insight**: Tự viết attack prompts (jailbreak, indirect injection, obfuscation) rồi chạy lên agent.
- **Production**: Nếu bạn không thể break nó, attacker cũng không thể. Verifier replay xác nhận guardrails hoạt động.

### 6. Audit Log + Monitoring
- **Insight**: Request ID xuyên suốt input/output; alert theo block rate, rate-limit hits, judge failure rate.
- **Production**: Mọi action đều có trace. Alert khi guardrail block rate tăng đột biến → có thể đang bị tấn công.

---

## Day 12 — Cloud Infrastructure & Deployment

### 1. 12-Factor Config — Code không chứa secret
- **Insight**: `api_token` không có default → fail fast ngay lúc deploy.
- **Production**: Cùng 1 Docker image chạy dev/staging/production — chỉ khác biến môi trường. Không commit `.env`.

### 2. Bearer Token + Timing-safe comparison
- **Insight**: `secrets.compare_digest` thay vì `==` để chống timing attack.
- **Production**: Mọi API public đều dùng RFC 6750. 401 luôn kèm `WWW-Authenticate: Bearer`.

### 3. Token Bucket — Rate limit thông minh
- **Insight**: Token bucket cho phép "im lặng 5 phút rồi bấm 8 lần liên tiếp" mà vẫn chặn được kẻ gọi liên tục.
- **Production**: Không dùng "N request/phút" đơn thuần. Dùng token bucket với `min(capacity, tokens)` và `expire` key.

### 4. Cost Guard — Giới hạn chi phí theo ngày
- **Insight**: Rate limit ≠ Cost limit. Daily budget giới hạn thiệt hại tối đa của 1 sự cố xuống 1/30.
- **Production**: LLM API tính phí theo token. `incrbyfloat` + `expire` → tự reset mỗi ngày.

### 5. Stateless + Redis — Scale ngang
- **Insight**: Chat history trong Redis → mọi instance cùng nhìn thấy. `ltrim` giới hạn prompt length, `expire` tự dọn.
- **Production**: Không bao giờ giữ state trong process memory khi cần scale. Single source of truth.

### 6. Graceful Shutdown — Zero-downtime deploy
- **Insight**: SIGTERM → bật flag `draining` → `/healthz` trả 503 → LB ngừng traffic → xử lý nốt request → thoát.
- **Production**: Phải gọi lại handler cũ của uvicorn. Không gọi → app chạy mãi → SIGKILL → tệ hơn.

### 7. Health vs Readiness Probe
- **Insight**: `/healthz` không kiểm tra dependency (Redis chết không restart tất cả). `/readyz` kiểm tra dependency (LB ngừng traffic).
- **Production**: Gộp 2 endpoint = lỗi kinh điển. Liveness = process còn sống? Readiness = sẵn sàng nhận traffic?

### 8. Docker Multi-stage + Security
- **Insight**: Builder stage cài compiler → runtime stage chỉ copy kết quả. Chạy bằng user thường. `.dockerignore` loại `.env`.
- **Production**: Image dưới 400MB, non-root user, không lộ secret.

### 9. CI/CD — Deploy an toàn
- **Insight**: Test trên máy sạc → build image → deploy chỉ khi xanh. Smoke test sau deploy.
- **Production**: Mọi deploy gắn với commit. Không push code hỏng lên production. Badge trên README cho biết main đang xanh hay đỏ.

---

## Day 13 — Observability & Incident Response

### 1. Correlation ID — Backbone của observability
- **Insight**: Middleware tạo ID → bind contextvars → ghi log → gửi trace (tag `cid:`) → trả header client.
- **Production**: Closed loop: Client → Middleware → Log → Trace → Client. Khi user complaint "request lúc 14:30 bị lỗi", hỏi `X-Request-ID` → trace ngược được.

### 2. Structured Logging — Log là data, không phải text
- **Insight**: JSONL + structlog + schema. Mỗi log là 1 dòng JSON → query, filter, alert.
- **Production**: Không dùng `print()`. `ts` ISO 8601 UTC. `service`, `event` để filter. Cloud log platform đọc được.

### 3. PII Scrubbing — Layered defense
- **Insight**: Scrub sau stack trace (exception có thể chứa PII), trước file write. `scrub_text` chạy iterative pass.
- **Production**: GDPR, PCI DSS, HIPAA yêu cầu. Multi-layer: processor level + hash user_id + never log raw PII.

### 4. Metrics cần percentile, không phải average
- **Insight**: p50/p95/p99 thấy tail latency. Average che giấu slow request.
- **Production**: 1 slow request không tăng average nhiều nhưng p99 tăng rõ. Alert trên p95, không phải average.

### 5. Trace → Log → Root cause — Playbook chuẩn
- **Insight**: Metrics (latency tăng) → Traces (filter span `retrieve` cao) → Logs (search correlation_id) → Root cause.
- **Production**: Incident response playbook. Mọi claim kèm evidence: trace ID, log line, metric value.

### 6. Prompt Versioning — Rollback không deploy
- **Insight**: Managed prompt trên Langfuse → version, label, rollback. `prompt_source` trace rõ.
- **Production**: A/B test prompt, gradual rollout, instant rollback khi prompt bị lỗi. Không cần deploy.

### 7. Symptom-based Alert — Dễ hiểu, dễ action
- **Insight**: "User thấy chậm" thay vì "Redis CPU cao". Mỗi alert có runbook.
- **Production**: Oncall không cần guess. Alert = symptom + threshold + runbook + owner.

### 8. Incident Injection — Chaos Engineering tối giản
- **Insight**: `/incidents/rag_slow/enable` → `time.sleep(2.5)` → test alert.
- **Production**: Deterministic chaos. Mỗi incident có symptom rõ, dễ reproduce. Production dùng Chaos Monkey, Gremlin.

### 9. Evidence-driven Development
- **Insight**: Mọi claim phải kèm trace ID / log line / screenshot.
- **Production**: Postmortem có bằng chứng, không phải opinion. Code không đủ — cần evidence.

---

## Combined: Kiến trúc Production-ready AI API

```
Day 12: Build RIGHT → deploy RIGHT → scale RIGHT
Day 13: See EVERYTHING → debug FAST → prevent RECURRENCE
```

### Checklist theo level

| Level | Pattern | Day |
|-------|---------|-----|
| **MVP** | 12-Factor config + Bearer token + Rate limit + Correlation ID + PII scrub | 12, 13 |
| **Production** | Docker + CI/CD + Redis state + Graceful shutdown + Langfuse traces + Prompt versioning + Dashboard + SLO + Alert | 12, 13 |
| **Enterprise** | Prometheus + Grafana + Jaeger/OTel + ELK/Loki + per-model budget + Chaos Engineering + PII SDK-level + Multi-region | 12, 13 |

### Mindset đáng nhớ

1. **Config ≠ Code** — Cùng image, nhiều môi trường
2. **Fail fast** — Thiếu secret → không khởi động
3. **Defense in depth** — 3 lớp bảo vệ, mỗi lớp trả lời 1 câu hỏi
4. **Statelessness** — State ngoài process, scale ngang không giới hạn
5. **Graceful degradation** — App chạy được cả khi dependency fail
6. **Correlation ID là backbone** — Trace ngược từ user complaint đến root cause
7. **Log là data** — JSON, queryable, alertable
8. **Percentile > Average** — Thấy tail latency
9. **Evidence > Opinion** — Mọi claim kèm trace ID/log line
10. **Automate everything** — Test, build, deploy, evidence — đều automated

---

## Ghi chú

- File này tổng hợp từ Day 11 (`Day11_2A202601044_TranChiVu`), Day 12 (`K4-Day12-2A202601044-TranChiVu`), Day 13 (`Day13-K4-2A202601274`).
- Các ngày khác (Day 1-10) cần bổ sung sau khi có đầy đủ repo.
- Mỗi insight đều có code example thật trong các repo tương ứng.
