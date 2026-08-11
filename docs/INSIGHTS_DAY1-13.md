# Insights quan trọng từ Day 1 → Day 13

> File này note những insight **đáng nhớ nhất** để áp dụng vào build sản phẩm thật.
> Mỗi ngày 1 section, mỗi insight là 1 pattern có thể dùng ngay.

---

## Day 01 — LLM API Exploration

### 1. LLM là API bình thường — không có gì "ma thuật"
- **Insight**: OpenAI/Anthropic/Gemini đều là REST API. Bạn chỉ cần gọi đúng endpoint, parse JSON, handle timeout.
- **Production**: Tất cả LLM integration đều bắt đầu từ `requests.post()` + retry. Không cần wrapper phức tạp để bắt đầu.

### 2. Temperature & Top_p kiểm soát sáng tạo
- **Insight**: `temperature=0` → deterministic, `temperature=0.7` → creative. `top_p` ngăn tail distribution.
- **Production**: Chatbot hỏi-đáp → `temperature=0`. Creative writing → `temperature=0.7-0.9`. Không bao giờ để `temperature=1.0` trong production.

### 3. System prompt định hình persona
- **Insight**: System prompt không phải "câu giới thiệu". Nó là **behavior contract** của model.
- **Production**: Một system prompt tốt = role + constraints + output format + examples. Nên version control system prompt như code.

### 4. Token counting = cost control
- **Insight**: `tiktoken` đếm token trước khi gọi API. Biết trước chi phí, không bị shock hóa đơn.
- **Production**: Mọi LLM call cần log `prompt_tokens`, `completion_tokens`, `cost_usd`. Đây là metric cơ bản của observability.

### 5. Streaming + Retry = UX tốt
- **Insight**: Streaming cho user thấy response ngay. Retry với backoff cho resilience.
- **Production**: User chấp nhận delay nếu thấy progress. Retry phải có `max_retries`, `backoff_factor`, không retry mãi.

---

## Day 02 — Problem Definition

### 1. Problem trước, AI sau
- **Insight**: "Tìm đúng bài toán" quan trọng hơn "chọn đúng model". Workflow trước, AI sau.
- **Production**: Nếu workflow chưa rõ, AI sẽ làm đúng thứ mà không ai cần. Problem Statement có người gặp vấn đề, điểm nghẽn, tác động.

### 2. Metric phải đo trước/sau
- **Insight**: Metric cần baseline (hiện trạng) và target (mục tiêu). "Nhanh hơn" không phải metric.
- **Production**: Mọi thay đổi cần A/B test: trước = 5 phút, sau = 2 phút, cải thiện 60%. Con số thuyết phục hơn opinion.

### 3. Boundary rõ ràng — biết việc không làm
- **Insight**: AI được phép làm gì, phần nào cần người kiểm tra. Boundary không phải limitation, mà là **risk control**.
- **Production**: Nếu AI được phép gửi email, nó cũng cần được giới hạn: chỉ gửi template đã duyệt, không tự soạn nội dung mới.

### 4. Rule/Workflow/Agent — chọn đúng mức
- **Insight**: Rule đơn giản hơn Agent, Workflow ở giữa. Không phải lúc nào cũng cần Agent.
- **Production**: Nếu 3 if/else giải được bài toán → dùng Rule. Nếu cần gọi tool + suy luận → dùng Workflow/Agent.

---

## Day 03 — Chatbot vs ReAct Agent

### 1. 4 cấp độ AI hội thoại
- **Insight**: Rule-Based → LLM Chatbot → ReAct Agent → Autonomous Agent. Mỗi cấp thêm khả năng, thêm complexity.
- **Production**: Bắt đầu từ cấp thấp nhất giải được bài toán. Không leo cấp nếu chưa cần.

### 2. ReAct = Thought → Action → Observation
- **Insight**: Agent không trả lời ngay. Nó **suy luận** (thought), **hành động** (action), **quan sát** (observation), rồi mới trả lời.
- **Production**: Vòng lặp ReAct là pattern chuẩn cho tool-using agent. Prompt phải định hình rõ 3 bước này.

### 3. Tool description = interface với model
- **Insight**: Tên tool và mô tả quyết định routing. "Tên tool phản ánh đúng intent, mô tả nói rõ khi nào dùng/khi nào không".
- **Production**: Tool description cần có: purpose, input schema, output schema, confirmation boundary. Đây là API contract cho LLM.

### 4. Guardrail cho agent loop
- **Insight**: Agent có thể lặp vô hạn. Cần `max_iterations` + timeout + fallback.
- **Production**: Agent loop không bao giờ được chạy không giới hạn. Đặt `max_rounds=10` + `timeout=30s` + `fallback=human_escalation`.

### 5. Hybrid Decision Flowchart
- **Insight**: Không phải lúc nào cũng cần agent. Chatbot path cho câu hỏi đơn giản, ReAct path cho câu hỏi cần tool.
- **Production**: Router đơn giản: "Câu này cần tool không?" → Nếu không → chatbot, Nếu có → agent. Tiết kiệm latency và cost.

---

## Day 04 — Prompt Engineering & Tool Calling

### 1. Evidence-driven prompt optimization
- **Insight**: Đổi prompt → chạy eval → đọc run JSON → sửa → chạy lại. Vòng lặp này quan trọng hơn prompt đẹp.
- **Production**: Mọi prompt cần có version log: `v0`, `v1`, `v2`... Mỗi version ghi: changed artifact, hypothesis, metric before/after.

### 2. Tool design là prompt engineering
- **Insight**: Tên tool, mô tả, argument schema — tất cả đều ảnh hưởng routing. "Thiết kế tool cũng là prompt engineering".
- **Production**: Tool bad naming → agent chọn sai tool. Tool description mơ hồ → agent nhầm args. Tool không có confirmation boundary → agent làm việc nguy hiểm.

### 3. Eval case thiết kế kỹ = bug report chất lượng
- **Insight**: Eval case cần có `failure_type`, `expect`, `metadata.what_it_tests`. Không phải "test xem agent có chạy không".
- **Production**: Eval case = bug report. Nó mô tả: scenario, expected behavior, actual behavior, failure category. Dùng eval để đo improvement, không chỉ để pass.

### 4. Versioning không chỉ là prompt
- **Insight**: `artifact_version` + `prompt_hash` + `tools_hash` → biết chính xác đang chạy cái gì.
- **Production**: Khi agent bị lỗi, bạn cần biết: prompt version nào? tools.yaml version nào? Chỉ có hash mới trả lời được.

### 5. UI là deliverable, không phải bonus
- **Insight**: "UI tốt không chỉ cần có chat. Cần thấy request/response, trace tool, transcript, artifact version".
- **Production**: Debug UI = observability cho developer. Production cần dashboard tương tự: xem được từng tool call, latency, cost, error.

---

## Day 07 — Data Foundations

### 1. Embedding chọn model phù hợp ngôn ngữ
- **Insight**: `BAAI/bge-m3` multilingual tốt cho tiếng Việt. `all-MiniLM-L6-v2` nhẹ, nhanh.
- **Production**: Model embedding là foundation của RAG. Chọn sai model → retrieval kém dù chunking tốt.

### 2. Chunking strategy ảnh hưởng retrieval
- **Insight**: `RecursiveCharacterTextSplitter` an toàn, `MarkdownHeaderTextSplitter` tốt cho heading rõ.
- **Production**: Chunk size cần match context window của LLM. Overhead 10-20% cho cross-chunk information. Chunk nhỏ → precision cao, recall thấp.

### 3. Vector store là single source of truth
- **Insight**: ChromaDB lưu vector + metadata + document. Không cần database phức tạp cho RAG cơ bản.
- **Production**: Vector store cần persist, backup, versioning. Metadata phải có `source`, `chunk_id`, `created_at` để debug.

---

## Day 08 — RAG Pipeline

### 1. Hybrid search > Dense-only
- **Insight**: Semantic search (dense) + BM25 (lexical) → merge → rerank. Mỗi loại bù weaknesses của loại kia.
- **Production**: Dense search bắt synonym, lexical search bắt exact match. Hybrid cho kết quả tốt nhất.

### 2. Reranking cải thiện precision
- **Insight**: Cross-encoder reranker (Jina, Qwen) chấm lại relevance. Top-k sau rerank chính xác hơn.
- **Production**: Rerank là lớp cuối trước LLM. Chi phí thấp, benefit cao. Luôn rerank top-20 → top-5.

### 3. Vectorless fallback cho edge case
- **Insight**: PageIndex (vectorless) làm fallback khi hybrid search không có kết quả đủ tốt.
- **Production**: Retrieval không bao giờ 100% confident. Fallback strategy = "không tìm thấy" → "tìm theo cách khác" → "hỏi lại user".

### 4. Citation = trust
- **Insight**: Trả lời có citation `[Nguồn, Năm]`. Nếu không có evidence → "I cannot verify".
- **Production**: Citation không phải optional. Nó là **trust mechanism** cho RAG. User cần biết câu trả lời dựa trên đâu.

### 5. Document reordering tránh "lost in the middle"
- **Insight**: LLM bỏ qua thông tin ở giữa context. Sắp xếp: quan trọng nhất ở đầu và cuối.
- **Production**: Reorder chunks theo relevance + freshness. Pattern: `[1, 3, 5, 4, 2]` thay vì `[1, 2, 3, 4, 5]`.

### 6. Evaluation pipeline bắt buộc
- **Insight**: Golden dataset 15+ Q&A, metrics: Faithfulness, Answer Relevance, Context Recall, Context Precision.
- **Production**: RAG không có eval = mù. Đo baseline → sau mỗi thay đổi → so sánh. A/B test reranking, chunking, embedding model.

---

## Day 09 — Multi-Agent (A2A)

### 1. Coordinator + Workers pattern
- **Insight**: Một agent điều phối, nhiều agent chuyên môn. Coordinator phân công, worker thực hiện, handoff bằng chứng.
- **Production**: Phân việc theo domain: Order Agent, Payment Agent, Delivery Agent, Policy Agent. Mỗi agent chỉ truy cập data của mình.

### 2. Handoff bằng evidence, không phải tin lời
- **Insight**: Agent không gửi "kết luận" cho agent khác. Nó gửi **evidence IDs**: `order:123`, `payment:456`, `policy:SELLER_HANDOFF`.
- **Production**: Evidence ID = stable reference. Không bị misinterpret khi agent đọc lại. Có thể verify từ source data.

### 3. Policy-driven decision
- **Insight**: `EC_POLICY_V2` là single source of truth. Agent áp dụng policy, không tự quyết.
- **Production**: Business logic nên nằm ở policy layer, không phải trong agent prompt. Prompt chỉ định hướng, policy quyết chi tiết.

### 4. Verifier agent trước khi output
- **Insight**: Verifier kiểm tra ID, số tiền, null handling, array limit, schema trước khi ghi file.
- **Production**: Output không được tin ngay. Verifier = unit test cho agent output. Schema validation + business rule validation.

### 5. Trace chạy thật, không tự tạo
- **Insight**: `trace.jsonl` ghi lại từng case thực tế. Không append, chỉ cần lượt chạy mới nhất.
- **Production**: Agent trace cần có: input, thought, action, observation, output, latency, cost. Đây bằng chứng cho audit và improvement.

---

## Day 10 — Data Pipeline & Data Observability

### 1. Raw artifact phải persist
- **Insight**: Lưu raw response từ Crossref trước khi clean. Nếu clean sai, có thể rollback về raw.
- **Production**: Data lineage: raw → clean → embedding → index. Mỗi stage đều có artifact. Không bao giờ overwrite raw data.

### 2. Corruption flow = controlled failure
- **Insight**: Tạo lỗi chủ đích (thiếu record, summary rỗng, duplicate, ngày cũ) để đo ảnh hưởng.
- **Production**: Chaos engineering cho data. Nếu bạn không biết data corruption làm hỏng agent như thế nào, bạn chưa sẵn sàng production.

### 3. Data quality metrics
- **Insight**: `missing_rate`, `duplicate_rate`, `freshness_hours`, `null_summary_rate`. Đo baseline → corrupt → repair.
- **Production**: Data quality report phải có: threshold, current value, trend, alert. Giống metrics cho application.

### 4. Repair từ raw, không từ corrupted
- **Insight**: Khi data lỗi, repair từ raw artifact, không cố patch corrupted data.
- **Production**: Immutable raw data + idempotent pipeline = reproducible results. Nếu pipeline chạy 2 lần cho kết quả khác nhau → bug.

### 5. So sánh 3 trạng thái
- **Insight**: Baseline (sạch) vs Corrupted (lỗi) vs Repaired (sửa). Cùng eval set, cùng metric.
- **Production**: Trước khi claim "pipeline improved", chạy eval trên baseline. Sau khi claim "bug fixed", chạy lại baseline để confirm.

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
Day 1-4:  Understand LLM → Design problem → Build agent → Optimize prompt
Day 7-10: Data foundations → RAG pipeline → Multi-agent coordination → Data quality
Day 11-13: Security → Deployment → Observability
```

### Checklist theo level

| Level | Pattern | Day |
|-------|---------|-----|
| **MVP** | LLM API + System prompt + Token counting + ReAct + Eval-driven + 12-Factor + Bearer + Correlation ID | 1, 3, 4, 12, 13 |
| **Production** | Streaming + Retry + Problem statement + Tool design + RAG hybrid + Multi-agent + Docker + CI/CD + Structured logging + PII scrub + Metrics + Traces + Prompt versioning | 1-13 |
| **Enterprise** | A/B testing + Guardrails + Egress allowlist + HITL + Cost guard + Graceful shutdown + SLO + Alert + Chaos Engineering + Data quality pipeline + Evidence-driven | 10-13 |

### Mindset đáng nhớ

1. **Problem trước, AI sau** — Đừng giải bài toán không có
2. **Config ≠ Code** — Cùng image, nhiều môi trường
3. **Fail fast** — Thiếu secret → không khởi động
4. **Defense in depth** — 3 lớp bảo vệ, mỗi lớp trả lời 1 câu hỏi
5. **Evidence > Opinion** — Mọi claim kèm data
6. **Statelessness** — State ngoài process, scale ngang
7. **Trace ngược được** — Correlation ID từ user complaint đến root cause
8. **Log là data** — JSON, queryable, alertable
9. **Percentile > Average** — Thấy tail latency
10. **Automate everything** — Test, build, deploy, evidence — đều automated
11. **Tool description = interface** — Thiết kế tool cũng là prompt engineering
12. **RAG cần eval** — Golden dataset + metrics + A/B test
13. **Multi-agent cần handoff** — Evidence-based, không tin lời
14. **Data quality > Model quality** — Garbage in, garbage out
15. **Red team trước khi ship** — Tự break nó trước khi attacker break nó

---

## Ghi chú

- File này tổng hợp từ tất cả repo Day 1-13 trên GitHub của bạn.
- Mỗi insight đều có code example thật trong các repo tương ứng.
- Dùng file này làm cheat sheet khi build sản phẩm thật.
