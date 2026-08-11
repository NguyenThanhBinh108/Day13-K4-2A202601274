# Kiến thức toàn bộ dự án Day 13 — Observability cho AI

Tài liệu gộp: giải thích **toàn bộ** dự án (không chỉ phần P4), mỗi mục có 3 lớp —
**(1) ví dụ đời thường** → **(2) trong dự án là gì** → **(3) số liệu/code thật** — để người mới học
hay không chuyên cũng hiểu được, đồng thời vẫn đủ chi tiết kỹ thuật để bắt tay làm việc và trả lời câu
hỏi khi demo (rubric A3/B1).

---

## 0. Cả dự án này giống cái gì?

Hãy tưởng tượng bạn vận hành một **quán ăn giao hàng qua app** (kiểu GrabFood/ShopeeFood). Khách bấm
đặt món → nhà bếp nấu → shipper giao. Bạn là quản lý ngồi văn phòng, không thấy tận mắt từng đơn, chỉ
có 3 nguồn để biết chuyện gì đang xảy ra:

1. **Bảng điện tử tổng quan**: "Hôm nay 500 đơn, thời gian giao trung bình 25 phút, 3% đơn bị huỷ."
   → đây là **Metrics**.
2. **Lịch sử di chuyển của 1 đơn cụ thể**: đặt 12:00 → bếp nhận 12:01 → bếp xong 12:15 → shipper lấy
   12:16 → giao xong 12:40. → đây là **Trace**.
3. **Biên bản chi tiết** ở từng bước: "12:15 — bếp báo hết nguyên liệu, phải đổi món." → đây là **Log**.

Ba cái này **không thay thế nhau được**: bảng điện tử cho biết "có gì bất thường" (đơn giao lâu hơn
thường ngày), lịch sử di chuyển cho biết "chậm ở khúc nào" (bếp hay shipper), biên bản chi tiết cho
biết "vì sao chậm" (hết nguyên liệu). Trong dự án: app giả lập chat AI = "quán ăn"; dashboard (P4) =
bảng điện tử tổng quan; trace trên Langfuse (P3) = lịch sử di chuyển 1 đơn; file log JSON = biên bản
chi tiết.

Mọi nhận định về sự cố trong bài lab đều phải đi theo đúng thứ tự này: **Metrics → Traces → Logs →
Root cause**, không được nhảy cóc kết luận mà thiếu bằng chứng cụ thể (RULES.md: "Evidence không thể
kiểm chứng sẽ không được tính").

---

## 1. Kiến trúc — một request đi qua những gì

```text
Client → CorrelationIdMiddleware → /chat handler → LabAgent.run()
           (P1)                      (P1 log)         (P3: retrieve → resolve_prompt → FakeLLM)
                                                              │
                                                     metrics.record_request()
                                                              │
                                            log "response_sent" (P1 bind + P2 scrub)
                                                              │
                                              Langfuse trace/generation (P3)
                                                              │
                                        data/logs.jsonl (nguồn chuẩn của dashboard — P4)
```

1. Request tới `/chat`, [app/middleware.py](../app/middleware.py) chạy trước tiên: sinh
   `correlation_id` dạng `req-<8 hex>` — giống **mã vận đơn** khi bạn đặt hàng Shopee: dù đơn đi qua
   nhiều trạm trung chuyển, mỗi trạm đều ghi lại "mã vận đơn XYZ tới đây lúc mấy giờ", nhờ đó tra được
   toàn bộ hành trình của đúng đơn đó, không lẫn đơn người khác.
2. [app/main.py:47](../app/main.py#L47) enrich thêm `user_id_hash`, `session_id`, `feature`, `model`,
   `env` vào cùng context — mọi log sau đó trong request tự động có các field này.
3. Log `request_received` được ghi.
4. [app/agent.py](../app/agent.py) (`LabAgent.run`) chạy: `retrieve()` tài liệu → `resolve_prompt()`
   lấy prompt theo version/label → `FakeLLM.generate()` sinh câu trả lời + token usage → tính
   `cost_usd`, `quality_score`.
5. `metrics.record_request(...)` cập nhật state in-memory dùng cho `/metrics` (**chỉ là tiện ích debug
   nhanh, KHÔNG phải nguồn dữ liệu dashboard chấm điểm**).
6. Log `response_sent` được ghi đầy đủ `latency_ms/tokens_in/tokens_out/cost_usd/quality_score`.
7. [app/logging_config.py](../app/logging_config.py) ghi dòng log ra file — và đây cũng là nơi PII bị
   che **trước khi** ghi (thứ tự quan trọng, xem mục 3).
8. Nếu lỗi (RAG timeout, tool fail...), log `request_failed` với `error_type`, **không có**
   `response_sent` cho request đó.

Tất cả dồn vào **một file** `data/logs.jsonl` — nguồn sự thật duy nhất mà dashboard P4 đọc.

---

## 2. Correlation ID & Structured Logging *(P1 — app/middleware.py, app/main.py)*

**Đời thường**: mã vận đơn (ví dụ ở trên). Còn log có cấu trúc giống **bệnh án theo mẫu cố định** —
bác sĩ không ghi tự do "bệnh nhân hơi mệt mệt gì đó" mà điền vào mẫu: họ tên, triệu chứng, chẩn đoán.
Nhờ mẫu cố định, bệnh viện tổng hợp được hàng ngàn bệnh án (VD: "có bao nhiêu ca sốt tháng 8").

**Kỹ thuật**: dùng `structlog.contextvars` — giống thread-local. `bind_contextvars(correlation_id=...)`
gọi 1 lần ở middleware, mọi `log.info(...)` gọi sau đó trong request **tự động** có field này, không
cần truyền tay. Cuối request phải `clear_contextvars()` để tránh **context leak** — nếu quên, request
B (chạy sau, cùng worker) có thể vô tình "kế thừa" correlation_id của request A.

**Ví dụ 2 request liên tiếp (đúng khi hoàn thiện)**:

```json
{"event": "request_received", "correlation_id": "req-a1b2c3d4"}
{"event": "response_sent",   "correlation_id": "req-a1b2c3d4"}
{"event": "request_received", "correlation_id": "req-e5f6a7b8"}
{"event": "response_sent",   "correlation_id": "req-e5f6a7b8"}
```

Header response `x-request-id` + `x-response-time-ms` trả cho client — để hệ thống hỗ trợ khách hàng
báo lại đúng ID mà không cần đọc log server.

---

## 3. PII Redaction *(P2 — app/pii.py, app/logging_config.py)*

**Đời thường**: giống việc **làm mờ số CMND** trước khi đăng ảnh công khai, hoặc che email/số điện
thoại trong ảnh chụp màn hình trước khi gửi cho người lạ — vẫn giữ đủ thông tin để biết "đây là câu
hỏi liên quan gì" mà không lộ danh tính thật.

**Kỹ thuật**: regex-based scrubbing, 4 loại bắt buộc trong [app/pii.py](../app/pii.py):

| Loại | Ví dụ input → output |
|---|---|
| `email` | `student@vinuni.edu.vn` → `[REDACTED_EMAIL]` |
| `phone_vn` | `0912345678` → `[REDACTED_PHONE_VN]` |
| `cccd` | `012345678901` → `[REDACTED_CCCD]` |
| `credit_card` | `4111 1111 1111 1111` → `[REDACTED_CREDIT_CARD]` |

**Hai điểm dễ sai**:
- `scrub_event()` trong `logging_config.py` chỉ quét `payload`/`event`, nhưng
  [scripts/validate_logs.py:54](../scripts/validate_logs.py#L54) chấm điểm bằng
  `json.dumps(rec)` — quét **toàn bộ record**. PII lọt field khác vẫn bị trừ 30 điểm.
- Thứ tự processor: `scrub_event` phải nằm **trước** `JsonlFileProcessor()` trong
  `configure_logging()`. Ghi file trước, che sau thì dữ liệu đã lưu PII thô rồi.

---

## 4. Tracing & Prompt Versioning *(P3 — app/tracing.py, app/agent.py, app/prompt_management.py)*

**Đời thường (trace)**: giống app giao hàng cho bạn xem "Bếp nhận đơn 12:01 → Bếp nấu xong 12:15
(14 phút) → Shipper lấy 12:16 → Giao tới 12:40 (24 phút)" — nhìn ngay được **chặng nào chiếm nhiều thời
gian nhất**.

**Đời thường (prompt version/label)**: giống **bảng "Menu hôm nay"** treo ngoài cửa nhà hàng — tấm
bảng luôn trỏ tới bản in menu mới nhất treo trong quán. Đổi món chỉ cần thay bản in, không cần sơn lại
chữ trên bảng. Món mới bị phàn nàn → treo lại bản in cũ (rollback), không cần làm lại bảng ngoài cửa.

**Kỹ thuật**: [app/tracing.py](../app/tracing.py) bọc Langfuse SDK — có đủ `LANGFUSE_PUBLIC_KEY` +
`LANGFUSE_SECRET_KEY` thì `tracing_enabled()=true`, decorator `@observe(as_type="generation")` trên
`LabAgent.run()` tự tạo 1 trace + 1 generation span mỗi request.

[app/prompt_management.py](../app/prompt_management.py) (`resolve_prompt`) đọc 2 biến env:
`LANGFUSE_PROMPT_NAME` (mặc định `day13-chat`), `LANGFUSE_PROMPT_LABEL` (mặc định `production`,
tương đương "bảng Menu hôm nay"). `production` trỏ tới version cụ thể (bản in menu). Đổi label = đổi
món đang phục vụ mà không cần deploy lại code. Rollback = trỏ label về version cũ.

**3 giá trị `prompt_source`**:

| `prompt_source` | Ý nghĩa | Khi nào xảy ra |
|---|---|---|
| `langfuse` | Lấy đúng prompt managed theo label | Bình thường, key đúng |
| `local-fallback` | Có key nhưng Langfuse lỗi/timeout | Key sai, prompt/label không tồn tại, mạng lỗi |
| `local` | Tracing tắt hoàn toàn | Chưa cấu hình `.env` |

---

## 5. Dashboard, SLO & Alert *(P4 — bạn)*

Đây là tầng **Metrics** — bảng điện tử tổng quan, giống **đồng hồ trên xe hơi**: bảng điều khiển ô tô
chỉ hiện vài đồng hồ quan trọng nhất (tốc độ, nhiên liệu, nhiệt độ máy) — không hiện 500 thông số kỹ
thuật, chỉ hiện những gì người lái cần biết ngay để quyết định có nên dừng xe.

### 5.1 6 panel — "đồng hồ" quan trọng nhất

| Panel | Giống đồng hồ nào trên xe | Event/field | Aggregation | Unit | Threshold |
|---|---|---|---|---|---|
| Latency | Đồng hồ tốc độ | `response_sent.latency_ms` | p50/p95/p99 | ms | p95 ≤ 3000 |
| Traffic | Đồng hồ vòng tua máy | `request_received` | count, req/phút | requests_per_minute | rate ≥ 1 |
| Errors | Đèn báo lỗi động cơ | `request_received`+`request_failed`, `error_type` | error_rate%, breakdown | percent | rate ≤ 2% |
| Cost | Đồng hồ nhiên liệu | `response_sent.cost_usd` | sum/phút + tổng | usd | total ≤ 2.5 |
| Tokens | Chỉ số tiêu thụ chi tiết | `response_sent.tokens_in/out` | sum mỗi field | tokens | ≤ 50000 |
| Quality | Đồng hồ nhiệt độ máy | `response_sent.quality_score` | mean | score 0–1 | mean ≥ 0.75 |

Yêu cầu trình bày: time range 60 phút, refresh 15–30s, có threshold/SLO line vẽ trên chart, ghi rõ đơn
vị, tên panel nhìn rõ trong screenshot. Nguồn dữ liệu duy nhất là `data/logs.jsonl` — dashboard
**không đọc** `/metrics` endpoint (đó chỉ là snapshot in-memory 1 process) và **không đọc** Langfuse
(Langfuse chỉ dùng mở trace khi điều tra sâu).

**Công thức `errors` — điểm dễ sai nhất**: `request_received` log ở đầu mọi request, `request_failed`
chỉ log khi có exception (request lỗi thì **không có** `response_sent`). Vậy:

```text
error_rate_pct = count(event == "request_failed") / count(event == "request_received") * 100
```

Không phải chia cho `response_sent` — mẫu số đó nhỏ hơn, error rate sẽ bị thổi phồng sai.

### 5.2 Percentile (p50/p95/p99) — vì sao không dùng average

**Đời thường**: app giao đồ ăn quảng cáo "90% đơn giao trong 30 phút" — không nói "trung bình 30
phút", vì trung bình dễ bị 1 đơn kẹt xe 3 giờ kéo lệch, trong khi 95% đơn khác vẫn nhanh.

**Ví dụ số cụ thể** với 10 latency (ms): `150, 160, 155, 170, 180, 165, 3200, 158, 172, 168` (9 request
bình thường, 1 request bị `rag_slow`):

- **Average** = 468ms → nhìn "có vẻ ổn", che mất vấn đề.
- **p50 (median)** ≈ 165ms → đúng cảm nhận "người dùng điển hình".
- **p95** ≈ 3200ms → **lộ rõ** vấn đề mà average giấu đi.

Đây là lý do threshold đặt trên p95, không đặt trên average.

### 5.3 SLI, SLO, Error Budget

**Đời thường**: công ty điện lực cam kết "cung cấp điện ổn định 99.5% thời gian trong năm" — được
phép mất điện tối đa ~1.8 ngày/năm do sự cố trước khi bị coi là vi phạm cam kết. Đây là **error
budget** (ngân sách lỗi được phép).

**Kỹ thuật**: [config/slo.yaml](../config/slo.yaml):

```yaml
latency_p95_ms:
  objective: 3000      # SLI này phải ≤ 3000ms
  target: 99.5         # ...trong ít nhất 99.5% thời gian
window: 28d             # cửa sổ đánh giá 28 ngày
```

Tính ra: 28 ngày = 40320 phút, error budget = 0.5% × 40320 ≈ **201 phút** vi phạm được phép trong 28
ngày. Việc bạn cần làm: xoá dòng `note: Replace with your group's target`, đặt target thật (giữ
`3000/99.5` là hợp lý để khớp threshold dashboard) và **ghi lý do chọn số đó**.

### 5.4 Symptom-based alert — khác gì cause-based

**Đời thường**: chuông báo khói kêu khi **phát hiện khói** (triệu chứng người trong nhà cảm nhận
được) — không cần biết "dây điện nào bị chập" (nguyên nhân kỹ thuật). Nghe chuông là chạy ra ngoài
trước, tìm nguyên nhân sau.

| Sai (cause-based) | Đúng (symptom-based) |
|---|---|
| "Alert khi `rag_slow` flag = true" | "Alert khi p95 latency > 3000ms, duy trì ≥ 5 phút" |
| "Alert khi `RuntimeError` xuất hiện trong log" | "Alert khi error rate > 2%, duy trì ≥ 5 phút" |
| "Alert khi cost_spike=true" | "Alert khi tổng cost/phút vượt ngưỡng dự kiến, duy trì ≥ 10 phút" |

**Vì sao cần "duy trì X phút"**: giống chuông khói không nên kêu chỉ vì bạn hút 1 hơi thuốc gần cảm
biến — cần khói liên tục đủ lâu để chắc là cháy thật, tránh **alert flapping** (báo động giả).

3 alert cần điền trong [config/alert_rules.yaml](../config/alert_rules.yaml), khớp 3 threshold đã có
sẵn trong `dashboard.yaml`:
1. **High Latency** — p95 > 3000ms, ≥5 phút, severity warning/critical.
2. **High Error Rate** — error_rate_pct > 2%, ≥5 phút, severity critical.
3. **Cost hoặc Quality** — cost > $2.5/window, hoặc quality mean < 0.75 trong ≥10 phút.

Mỗi alert cần mục tương ứng trong [docs/alerts.md](alerts.md) (anchor `#alert-1/2/3`): tên, severity,
SLI/SLO liên quan, điều kiện + thời gian duy trì, ảnh hưởng người dùng, 3 bước kiểm tra đầu, mitigation
tạm thời, owner.

### 5.5 Cost & Token — công thức tính tiền thật

[app/agent.py:93](../app/agent.py#L93):

```python
input_cost  = (tokens_in  / 1_000_000) * 3   # $3 / 1M input tokens
output_cost = (tokens_out / 1_000_000) * 15  # $15 / 1M output tokens
```

**Ví dụ**: `tokens_in=42, tokens_out=134` → `cost_usd = 42/1e6*3 + 134/1e6*15 = 0.002136`.

**Kịch bản `cost_spike`** ([app/mock_llm.py:31](../app/mock_llm.py#L31)) nhân `output_tokens *= 4`:
`tokens_out` 134 → 536, cost/request tăng ~4 lần → cost/phút có thể vượt threshold $2.5 rất nhanh nếu
incident chạy liên tục — đây là triệu chứng alert cost cần bắt được.

### 5.6 Checklist tự kiểm tra trước demo

- [ ] Vì sao dùng p95 thay vì average cho latency?
- [ ] `error_rate_pct` tính trên mẫu số nào, vì sao không dùng `response_sent`?
- [ ] SLO 99.5%/28 ngày cho phép "đốt" bao nhiêu phút vi phạm?
- [ ] Alert symptom-based nghĩa là gì, cho 1 ví dụ sai để đối chiếu?
- [ ] Cost tăng thế nào khi `cost_spike` bật, bằng số cụ thể?
- [ ] Dashboard đọc dữ liệu từ đâu, vì sao không đọc `/metrics` endpoint?

---

## 6. Incident Injection, Challenge & Report *(P5)*

**Đời thường (điều tra sự cố)**: giống bác sĩ chẩn đoán — (1) đo huyết áp, nhiệt độ (triệu chứng =
Metrics), (2) hỏi bệnh sử, khi nào bắt đầu mệt (khoanh vùng = Trace), (3) xét nghiệm máu cụ thể để xác
nhận (bằng chứng = Log), rồi mới kết luận nguyên nhân và kê thuốc (fix) + dặn phòng bệnh (preventive
measure). Không được kết luận mà thiếu "kết quả xét nghiệm" cụ thể.

**Kỹ thuật — 3 practice incident** ([app/incidents.py](../app/incidents.py), dict `STATE`, bật/tắt qua
`/incidents/{name}/enable|disable`):

| Scenario | Code gây ra gì | Panel bị ảnh hưởng |
|---|---|---|
| `rag_slow` | [mock_rag.py:18](../app/mock_rag.py#L18) `time.sleep(2.5)` | `latency`: p95 tăng vượt threshold |
| `tool_fail` | [mock_rag.py:16](../app/mock_rag.py#L16) raise `RuntimeError` | `errors`: error_rate tăng |
| `cost_spike` | [mock_llm.py:31](../app/mock_llm.py#L31) `output_tokens *=4` | `cost`+`tokens` tăng ~4x |

**Challenge chính thức**: cấu hình từ `config/challenge.json` (release bởi Lab Coach,
[app/challenge.py](../app/challenge.py) validate `cohort/challenge_id/incident/seed/latency_threshold_ms/queries`).
Trước khi file tồn tại, script raise `FileNotFoundError` — chặn cứng không cho ai tự chạy trước giờ.

**Ví dụ luồng điều tra đầy đủ với `rag_slow`**: metric latency p95 tăng từ 210ms → 2680ms → mở trace
thấy span `retrieve` chiếm 2.5s trên tổng ~2.7s → log dòng `response_sent` cùng `correlation_id` xác
nhận `latency_ms≈2687` → root cause: "vector store bị chậm/giả lập timeout" → fix: cache kết quả
retrieve hoặc thêm timeout+fallback → phòng ngừa: alert High Latency + circuit breaker cho RAG call.

**`scripts/validate_logs.py`** chấm 4 mục độc lập (mỗi mục -20/-30 nếu fail): schema cơ bản,
correlation ID propagation, log enrichment, PII scrubbing — kiểm PII **độc lập với cách P2 code**
(tự quét regex riêng trên toàn bộ record).

---

## 7. Quy định & cách chấm — vì sao chia việc như vậy

- **RULES.md**: không copy bài nhóm khác, không tự sửa `config/challenge.json`, không hard-code để
  qua validator, mọi nhận định phải có evidence kiểm chứng được.
- **RUBRIC.md** (100 điểm): 60 điểm nhóm (30 kỹ thuật + 10 điều tra + 20 demo) + 40 điểm cá nhân
  (20 hiểu bài + 20 evidence commit) + tối đa 10 bonus. Điểm cuối = `min(100, nhóm + cá nhân + bonus)`.
- **Sở hữu file riêng** (xem [docs/TEAM_SPLIT.md](TEAM_SPLIT.md)): tránh git conflict khi 5 người code
  song song 4 giờ; khớp yêu cầu B2 "commit/PR cụ thể và có thể kiểm tra".
- **Port + `LOG_PATH` riêng khi dev**: tránh ghi đè `data/logs.jsonl` của nhau — file này chỉ là
  **artifact phát hành cuối cùng**, do P5 sinh đúng 2 lần (baseline T+90, challenge T+150).
- **3 "Gate" thời gian cố định** (T+90, T+150, T+210) thay cho "chờ người khác xong" — mỗi người chỉ
  cần có sẵn phần của mình đúng hạn gate.

---

## 8. Bảng thuật ngữ nhanh — đối chiếu đời thường ↔ dự án

| Thuật ngữ dự án | Ví dụ đời thường | Nằm ở đâu trong repo |
|---|---|---|
| Metrics | Bảng điện tử tổng quan / đồng hồ trên xe | Dashboard P4 |
| Trace / Span | Lịch sử di chuyển 1 đơn hàng theo từng chặng | `app/tracing.py`, `app/agent.py` |
| Log | Biên bản/bệnh án chi tiết từng bước | `app/logging_config.py` |
| Correlation ID | Mã vận đơn | `app/middleware.py` |
| Structured log | Form khai báo có mẫu cố định | `app/logging_config.py` |
| PII redaction | Làm mờ số CMND trước khi đăng công khai | `app/pii.py` |
| Percentile p95 | "90% đơn giao trong 30 phút" (không phải trung bình) | `app/metrics.py` |
| SLI | Chỉ số đo được | `config/slo.yaml` |
| SLO | Cam kết dịch vụ (điện, mạng) — "ổn định 99.5% thời gian" | `config/slo.yaml` |
| Error budget | Số phút được phép "trục trặc" trước khi vi phạm cam kết | Suy ra từ `target` trong `slo.yaml` |
| Symptom-based alert | Chuông báo khói (phát hiện khói, không cần biết dây nào cháy) | `config/alert_rules.yaml` |
| Prompt version/label | Bản in menu cụ thể / bảng "menu hôm nay" trỏ tới bản in đó | `app/prompt_management.py` |
| Root cause investigation | Bác sĩ: triệu chứng → khoanh vùng → xét nghiệm → kết luận | Checkpoint 3 |

---

## 9. Vì sao việc của bạn (P4) quan trọng trong câu chuyện lớn hơn

Nếu ví cả hệ thống là quán ăn giao hàng, bạn đang dựng **cái bảng điện tử tổng quan treo ở văn phòng
quản lý**. Nếu bảng sai số hoặc thiếu đồng hồ, không ai biết **lúc nào** cần lo lắng — không ai biết
để mở "lịch sử di chuyển đơn hàng" (trace) ra xem, vì bảng chưa báo động gì. Dù bạn không code phần
"nấu ăn" (LLM) hay "ghi biên bản" (log), bảng điện tử đúng là điều kiện để cả nhóm biết **khi nào** và
**ở đâu** cần điều tra sâu hơn.

## 10. Cách trả lời khi demo phần không phải của mình

Trả lời theo cấu trúc: **"tầng nào chịu trách nhiệm gì → ví dụ cụ thể từ code → liên hệ tới dashboard
của tôi"**. Ví dụ mẫu:

> "Correlation ID do P1 sinh trong middleware dạng `req-<8hex>`, giống mã vận đơn, bind vào mọi log
> qua contextvars. Dashboard của tôi không cần correlation_id để vẽ panel — panel chỉ tổng hợp theo
> `event` — nhưng khi điều tra incident, correlation_id là cầu nối để tôi trỏ từ panel bất thường
> sang đúng dòng log chứng minh."
