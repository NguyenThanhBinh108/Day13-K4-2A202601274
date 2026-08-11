# Phân công 5 người — không chồng chéo, không chờ nhau

Tài liệu này chia việc của Day 13 cho **5 thành viên** dựa trên [README.md](../README.md),
[CHECKPOINTS.md](../CHECKPOINTS.md) và [RUBRIC.md](../RUBRIC.md).

> **Lưu ý về ràng buộc của đề bài:** README quy định *"tối đa 4 vai trò"* và *"không tách thêm vai trò
> chỉ để chia nhỏ đầu việc"*. Vì vậy 5 người ở đây **không tạo ra vai trò thứ 5**: vai trò
> `Logging & PII` có 2 người đồng sở hữu nhưng **tách theo file, không tách theo đầu việc**
> (P1 = ngữ cảnh request, P2 = đường ống log & PII). Khi điền `submission/REPORT.md` mục 1,
> vẫn khai đúng **4 vai trò** như bảng dưới.

| Người | Vai trò chính thức (theo README) | Câu một dòng |
|---|---|---|
| **P1** | Logging & PII | Correlation ID + request context |
| **P2** | Logging & PII | PII redaction + log pipeline/schema |
| **P3** | Tracing & Prompt Version | Traces, prompt v1/v2, label & rollback |
| **P4** | Dashboard, SLO & Alert | 6 panel, threshold, SLO, alert, runbook |
| **P5** | Incident, Report & Demo | Challenge, report, evidence, release, demo |

---

## 1. Nguyên tắc chống chồng chéo

### 1.1 Sở hữu file độc quyền — chỉ chủ sở hữu được ghi

Mọi file trong repo có **đúng một người được sửa**. Ai cần thay đổi file của người khác thì nhắn,
không tự sửa. Nhờ vậy 5 nhánh Git merge được theo thứ tự bất kỳ mà không xung đột.

| Người | File được ghi (exclusive) |
|---|---|
| **P1** | [app/middleware.py](../app/middleware.py), [app/main.py](../app/main.py), [tests/test_chat_observability.py](../tests/test_chat_observability.py) |
| **P2** | [app/pii.py](../app/pii.py), [app/logging_config.py](../app/logging_config.py), [config/logging_schema.json](../config/logging_schema.json), [tests/test_pii.py](../tests/test_pii.py), [tests/test_validate_logs.py](../tests/test_validate_logs.py) |
| **P3** | [app/tracing.py](../app/tracing.py), [app/agent.py](../app/agent.py), [app/prompt_management.py](../app/prompt_management.py), [tests/test_agent_prompt_trace.py](../tests/test_agent_prompt_trace.py), [tests/test_prompt_management.py](../tests/test_prompt_management.py), [tests/test_tracing_adapter.py](../tests/test_tracing_adapter.py) |
| **P4** | [config/dashboard.yaml](../config/dashboard.yaml), [config/slo.yaml](../config/slo.yaml), [config/alert_rules.yaml](../config/alert_rules.yaml), [docs/alerts.md](alerts.md), [docs/dashboard-spec.md](dashboard-spec.md), `scripts/dashboard_app.py` *(file mới)*, [tests/test_dashboard_validator.py](../tests/test_dashboard_validator.py) |
| **P5** | [scripts/load_test.py](../scripts/load_test.py), [scripts/inject_incident.py](../scripts/inject_incident.py), [scripts/validate_logs.py](../scripts/validate_logs.py), [scripts/validate_dashboard.py](../scripts/validate_dashboard.py), [submission/REPORT.md](../submission/REPORT.md), `submission/evidence/**`, [.gitignore](../.gitignore), [tests/test_challenge_config.py](../tests/test_challenge_config.py) |

**Read-only cho cả nhóm:** `config/challenge.json` (RULES cấm sửa), `app/mock_llm.py`, `app/mock_rag.py`,
`app/incidents.py`, `app/schemas.py`, `app/metrics.py`, `app/challenge.py`, `data/*`.

### 1.2 `submission/REPORT.md` chỉ có **một** người ghi

Đây là file dễ conflict nhất. **Chỉ P5 được ghi.** Bốn người còn lại viết phần của mình vào file riêng:

```text
submission/evidence/p1-notes.md
submission/evidence/p2-notes.md
submission/evidence/p3-notes.md
submission/evidence/p4-notes.md
```

P5 gom vào REPORT.md ở phút 210. Không ai phải chờ P5, và P5 không phải chờ ai để bắt đầu.

### 1.3 Không tranh chấp runtime

App ghi log ra đường dẫn lấy từ biến `LOG_PATH`, nên mỗi người chạy instance riêng, ghi log riêng.
Không ai làm hỏng log của ai.

| Người | Port | `LOG_PATH` riêng khi dev |
|---|---|---|
| P1 | 8001 | `data/dev/p1.jsonl` |
| P2 | 8002 | `data/dev/p2.jsonl` |
| P3 | 8003 | `data/dev/p3.jsonl` |
| P4 | 8004 | `data/dev/p4.jsonl` |
| P5 | **8000** | `data/logs.jsonl` ← **canonical** |

Mỗi người tạo `.env.local` của mình (đã bị `.gitignore` chặn qua `.env`? **chưa** — P5 thêm
`.env.local` và `data/dev/` vào `.gitignore` ngay ở phút đầu):

```powershell
# ví dụ cho P3
$env:LOG_PATH = "data/dev/p3.jsonl"
uvicorn app.main:app --reload --port 8003 --env-file .env
```

**`data/logs.jsonl` là artifact phát hành, không phải file làm việc.** Chỉ P5 sinh ra nó, đúng 2 lần
(baseline ở T+90, challenge ở T+150). Nhờ vậy không ai phải "xin phép ngừng chạy app" để người khác
lấy evidence.

> Lưu ý kỹ thuật: `scripts/load_test.py` đang hard-code `BASE_URL = http://127.0.0.1:8000`.
> Việc đầu tiên của P5 là thêm cờ `--base-url` (hoặc đọc env `BASE_URL`) để 4 người kia bắn tải vào
> port của mình. RULES cho phép "thêm test, script và dashboard của nhóm". Trước khi P5 làm xong,
> 4 người kia dùng `curl`/`httpx` trực tiếp vào port riêng để smoke test.

### 1.4 Nhánh Git riêng, commit riêng

`feat/p1-correlation`, `feat/p2-pii`, `feat/p3-prompt-version`, `feat/p4-dashboard`, `feat/p5-incident-report`.

Đây không chỉ là chống conflict: RUBRIC mục **B2 (20 điểm cá nhân)** yêu cầu *"commit/PR cụ thể và có
thể kiểm tra"*, khớp với phần khai trong report. Ai commit chung vào một nhánh sẽ mất điểm này.

---

## 2. Chi tiết từng người

### P1 — Correlation ID & Request Context *(vai trò: Logging & PII)*

**Mục tiêu:** mọi log của một request đều truy ngược được về một ID duy nhất.

**Việc:**
1. [app/middleware.py](../app/middleware.py) — 4 khối TODO: `clear_contextvars()`, đọc header
   `x-request-id` hoặc sinh mới dạng `req-<8 hex>`, `bind_contextvars(correlation_id=...)`,
   trả `x-request-id` + `x-response-time-ms` trong response header.
2. [app/main.py](../app/main.py#L47) — TODO enrich: `bind_contextvars` với `user_id_hash`
   (dùng `hash_user_id` sẵn có), `session_id`, `feature`, `model`, `env`.
3. Bổ sung test trong [tests/test_chat_observability.py](../tests/test_chat_observability.py):
   hai request → hai correlation ID khác nhau, không rò rỉ context giữa các request.

**Bắt đầu ngay ở T+0, không phụ thuộc ai.** Đây là đường găng (critical path) của cả nhóm — xong sớm
thì P4 và P5 có dữ liệu thật sớm hơn, nên P1 nên là người khỏe nhất về FastAPI.

**Definition of done:** `validate_logs.py` in `[PASSED] Correlation ID propagation` và
`[PASSED] Log enrichment` (script kiểm hai mục này độc lập với phần PII của P2).

**Evidence bàn giao:** ảnh 3–5 dòng log JSON cùng một `correlation_id`, có đủ
`user_id_hash / session_id / feature / model / env`; ảnh response header có `x-request-id`.

**Rubric:** A1 (10đ logging) · B1/B2 cá nhân.

---

### P2 — PII Redaction & Log Pipeline *(vai trò: Logging & PII)*

**Mục tiêu:** không một dòng log nào chứa PII nguyên văn.

**Việc:**
1. [app/logging_config.py](../app/logging_config.py#L45) — TODO: đăng ký `scrub_event` vào chuỗi
   processor. **Đặt trước `JsonlFileProcessor()`**, nếu không PII vẫn được ghi xuống file trước khi bị che.
2. [app/pii.py](../app/pii.py#L11) — thêm pattern (passport, từ khóa địa chỉ VN…). Kiểm chéo với
   `PII_DETECTORS` trong [scripts/validate_logs.py](../scripts/validate_logs.py#L9): 4 loại
   `email / phone_vn / cccd / credit_card` là mức tối thiểu phải chặn.
3. Mở rộng phạm vi scrub: `scrub_event` hiện chỉ quét `payload` và `event`. Validator quét
   **toàn bộ record** (`json.dumps(rec)`), nên field nào lọt PII cũng bị trừ 30 điểm.
4. [config/logging_schema.json](../config/logging_schema.json) — chốt schema field bắt buộc.
5. Test trong [tests/test_pii.py](../tests/test_pii.py): email, `+84`/`0` 10 số, CCCD 12 số, thẻ 16 số.

**Bắt đầu ngay ở T+0.** Không đụng file nào của P1. Test được bằng unit test thuần
(`scrub_text("a@b.com")`) mà không cần app chạy, nên **không chờ P1**.

**Definition of done:** `validate_logs.py` in `Potential PII leaks detected: 0` +
`[PASSED] PII scrubbing`.

**Evidence bàn giao:** ảnh input có PII → dòng log tương ứng đã `[REDACTED_*]`; kết quả `pytest tests/test_pii.py`.

**Rubric:** A1 (10đ logging/PII) · B1/B2 cá nhân.

> **Giao diện giữa P1 và P2 — chốt 5 phút ở T+0, sau đó không cần nói chuyện nữa:**
> tên key là `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, và mọi text
> tự do đi trong `payload={...}`. P1 chỉ *bind* key; P2 chỉ *làm sạch* value.

---

### P3 — Tracing & Prompt Version *(vai trò: Tracing & Prompt Version)*

**Mục tiêu:** ≥10 trace có metadata, 2 phiên bản prompt, chứng minh được rollback.

**Việc:**
1. Cấu hình Langfuse (`LANGFUSE_*` trong `.env`) và xác minh `/health` trả `tracing_enabled: true`.
2. Tạo prompt `day13-chat` trên Langfuse theo [docs/PROMPT_VERSIONING.md](PROMPT_VERSIONING.md):
   v1 gắn label `baseline` + `production`; v2 (đổi nhỏ về format) gắn label `candidate`.
3. Chạy cùng một input với `LANGFUSE_PROMPT_LABEL=baseline` rồi `candidate` → lấy 2 trace ID.
4. Chuyển `production` sang v2, chạy 1 request, rồi **rollback** về v1 → chụp trước/sau.
5. Kiểm tra `app/agent.py` đã gửi đủ `prompt_name / prompt_label / prompt_version / prompt_source`
   (code hiện đã có — nhiệm vụ là *xác minh và sửa nếu lệch*, đồng thời bảo đảm
   `prompt_source` không phải `local-fallback` khi có key).
6. Bắn đủ ≥10 trace bằng chính port 8003 của mình.

**Bắt đầu ngay ở T+0.** Toàn bộ phần này chạy trên Langfuse UI + instance riêng, **không đụng
correlation ID hay PII**, nên độc lập hoàn toàn với P1/P2. Nếu key Langfuse chậm được cấp, P3 làm
phần Docker local trong [SETUP.md](../SETUP.md#3-tùy-chọn-chạy-langfuse-local-bằng-docker-compose)
song song thay vì ngồi chờ.

**Definition of done:** Langfuse có ≥10 trace; 2 trace ID chứng minh 2 version khác nhau; có ảnh rollback.

**Evidence bàn giao:** ảnh list ≥10 trace · 1 trace waterfall · ảnh 2 prompt version · 2 trace ID
kèm label/version · ảnh trước/sau rollback.

**Rubric:** A1 (10đ traces/prompt) · B1/B2 cá nhân.

---

### P4 — Dashboard, SLO & Alert *(vai trò: Dashboard, SLO & Alert)*

**Mục tiêu:** 6 panel đúng contract + SLO + 3 alert có runbook.

**Việc:**
1. Chạy `python scripts/validate_dashboard.py` ngay để hiểu contract; giữ nguyên
   [config/dashboard.yaml](../config/dashboard.yaml) trừ khi có lý do — mục tiêu là `HỢP LỆ: 6/6 panel`.
2. Dựng dashboard thật (Streamlit/notebook/Grafana) đọc từ một file jsonl. **Nhận đường dẫn qua
   tham số**, dev bằng `data/dev/p4.jsonl`, cuối buổi trỏ sang `data/logs.jsonl` — đổi một dòng,
   không phải sửa lại dashboard.
3. Panel phải khớp bảng mapping trong [docs/DASHBOARD_SETUP.md](DASHBOARD_SETUP.md): latency p50/p95/p99,
   traffic/phút, error rate + breakdown theo `error_type`, cost theo phút + tổng, tokens in/out, quality mean.
   Ảnh phải nhìn rõ **tên panel, time range 60 phút, đơn vị và đường threshold**.
4. [config/slo.yaml](../config/slo.yaml) — thay `note: Replace with your group's target` bằng
   target thật của nhóm, kèm lý do.
5. [config/alert_rules.yaml](../config/alert_rules.yaml) — 3 alert đang là `TODO` hết:
   điền `name / severity / condition / owner`, giữ `type: symptom-based`
   (cảnh báo theo triệu chứng người dùng thấy, không theo nguyên nhân kỹ thuật).
6. [docs/alerts.md](alerts.md) — viết runbook cho `#alert-1/2/3` đúng anchor đã trỏ trong YAML.

**Bắt đầu ngay ở T+0.** Contract, SLO, alert, runbook **không cần dữ liệu**. Phần cần dữ liệu thật
chỉ là ảnh chụp cuối, và P4 tự sinh được dữ liệu dev của mình. Không chờ P1/P2.

**Definition of done:** `validate_dashboard.py` báo `6/6 panel`; không còn chữ `TODO` trong `config/`.

**Evidence bàn giao:** output validator · ảnh dashboard baseline · ảnh dashboard lúc có incident
(P95 tăng rõ) · alert rules + runbook.

**Rubric:** A1 (10đ dashboard/SLO/alert) · B1/B2 cá nhân.

---

### P5 — Incident, Report, Demo & Release *(vai trò: Incident, Report & Demo)*

**Mục tiêu:** nối được Metrics → Traces → Logs thành một câu chuyện có bằng chứng, và nộp bài sạch.

**Việc theo thứ tự thời gian:**
1. **T+0 (không chờ ai):** thêm `data/dev/` và `.env.local` vào [.gitignore](../.gitignore);
   thêm `--base-url` cho [scripts/load_test.py](../scripts/load_test.py) để 4 người kia dùng port riêng;
   tạo khung thư mục `submission/evidence/` và đặt quy ước tên file
   (`01-validate-logs.png`, `02-traces-list.png`, …); dựng sườn [submission/REPORT.md](../submission/REPORT.md).
2. **T+20:** chạy **practice** incident để tập luồng điều tra — luôn dùng được, không cần chờ code ai:
   ```bash
   python scripts/inject_incident.py --scenario rag_slow
   python scripts/load_test.py --concurrency 5
   python scripts/inject_incident.py --scenario rag_slow --disable
   ```
3. **T+90 (Gate 1):** merge nhánh P1 + P2 → chạy **canonical baseline run** trên port 8000 ghi vào
   `data/logs.jsonl` → `validate_logs.py` phải ≥ 80/100 → báo số cho cả nhóm.
4. **T+150 (Gate 2):** chạy challenge chính thức. `config/challenge.json` **đã được release**
   (`day13-k4-observability-v1`, incident `rag_slow`, `latency_threshold_ms: 2000`, 5 query feature
   `monitoring`). Tuyệt đối không sửa file này:
   ```bash
   python scripts/inject_incident.py
   python scripts/load_test.py --challenge --concurrency 5
   ```
5. Điều tra theo đúng 5 bước của [CHECKPOINTS.md](../CHECKPOINTS.md) Checkpoint 3: triệu chứng từ
   metrics → khoanh vùng span bất thường trong trace → chứng minh bằng log cùng `correlation_id` →
   root cause → fix + preventive measure.
6. **T+210:** gom `p1..p4-notes.md` vào REPORT.md, chạy `pytest -q`, `git status --short`, soát
   không lộ `.env`/key/PII, commit và lấy SHA cuối.
7. Chuẩn bị demo 5 phút theo luồng **Metrics → Traces → Logs → Root cause**.

**Definition of done:** REPORT.md không còn mục trống; mọi nhận định incident đều có trace ID hoặc
log line kèm theo (RULES: *"Evidence không thể kiểm chứng sẽ không được tính"*).

**Rubric:** A2 (10đ incident) · A3 (20đ demo) · B1/B2 cá nhân.

---

## 3. Timeline 4 giờ — chỉ 3 điểm đồng bộ

```text
T+0    ── KICKOFF 10 phút ─────────────────────────────────────────────
        Chốt: tên key log · port · LOG_PATH · tên nhánh · ai giữ file nào
          ↓            ↓            ↓            ↓            ↓
T+10   P1 middleware  P2 pii+      P3 Langfuse  P4 contract  P5 gitignore
       +main          logging_cfg  +prompt v1   +SLO+alert   +base-url
          │            │            │            │            +practice
T+60      │            │           P3 prompt v2  P4 dashboard  P5 report
          │            │           +2 trace ID   code (dev)    skeleton
          ▼            ▼            │            │            │
T+90   ── GATE 1: merge P1+P2 → P5 chạy canonical baseline ───────────
        validate_logs ≥ 80/100.  P4 trỏ dashboard sang data/logs.jsonl.
          ↓            ↓            ↓            ↓            ↓
T+100  P1 test edge   P2 test PII  P3 rollback  P4 ảnh        P5 tập
       case           mở rộng      +≥10 trace   baseline      luồng điều tra
          ▼            ▼            ▼            ▼            ▼
T+150  ── GATE 2: P5 chạy challenge chính thức ────────────────────────
        P3 nộp trace ID chậm · P4 nộp ảnh dashboard lúc incident (async)
          ↓
T+210  ── GATE 3: freeze report + chạy pytest + demo thử ──────────────
T+240  Nộp: repo URL + commit SHA
```

Ba gate đều là **hẹn giờ cố định**, không phải "chờ người khác xong". Giữa hai gate, không ai bị chặn.

---

## 4. Ma trận phụ thuộc — và cách đã gỡ

| Phụ thuộc tự nhiên | Nguy cơ | Cách gỡ trong bản phân công này |
|---|---|---|
| Log cần correlation ID (P1) trước khi validate được | P2/P4/P5 ngồi chờ P1 | P2 test bằng unit test thuần; P4 dev trên dữ liệu riêng; P5 chạy practice incident bằng code baseline |
| Dashboard cần `data/logs.jsonl` đầy đủ | P4 chờ đến cuối buổi | Dashboard nhận **đường dẫn tham số**; dev trên `data/dev/p4.jsonl`, cuối buổi đổi 1 dòng |
| Ai cũng chạy app → ghi đè log của nhau | Evidence bị nhiễu, phải chạy lại | Mỗi người 1 port + 1 `LOG_PATH`; `data/logs.jsonl` chỉ P5 ghi |
| Cả nhóm cùng sửa REPORT.md | Merge conflict lúc gấp nhất | P5 là người ghi duy nhất; người khác nộp `pN-notes.md` |
| Challenge cần cả logging + tracing + dashboard | Kẹt cứng ở phút 150 | Gate 1 ở T+90 bảo đảm baseline sẵn sàng trước 60 phút |
| Langfuse key cấp chậm | P3 mất cả buổi | P3 có phương án Docker local trong SETUP.md; phần log/dashboard vẫn chạy không cần key |

---

## 5. Checklist trước khi nộp *(P5 chủ trì, mỗi người tự xác nhận dòng của mình)*

- [ ] **P1** — `validate_logs.py`: PASSED correlation ID + PASSED enrichment
- [ ] **P2** — `validate_logs.py`: `Potential PII leaks detected: 0`
- [ ] **P1+P2** — điểm tổng `validate_logs.py` ≥ 80/100
- [ ] **P3** — ≥10 trace, 2 prompt version, 1 bằng chứng rollback
- [ ] **P4** — `validate_dashboard.py` báo `6/6 panel`, không còn `TODO` trong `config/`
- [ ] **P5** — challenge đã chạy, root cause có trace ID **và** log line làm bằng chứng
- [ ] **P5** — `python -m pytest -q` xanh
- [ ] **P5** — `git status --short` sạch, không có `.env`, key, `.venv/`, log chứa PII
- [ ] **P5** — REPORT.md mục 7 khai đúng commit/PR của từng người (RUBRIC B2 = 20 điểm cá nhân)
- [ ] **Cả nhóm** — mỗi người giải thích được phần mình làm (RUBRIC A3 + B1)
