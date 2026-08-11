# Kịch bản demo Day 13 — hướng dẫn chi tiết từng chặng

Tài liệu này viết **sau khi đã chạy thử trọn vẹn** ngày 2026-08-11. Mọi lệnh và mọi con số
dưới đây là output thật, không phải mô phỏng. Ai đọc xong file này là chạy được demo, kể cả
người chưa từng mở repo.

Tổng thời gian: **10–12 phút**. Năm người, mỗi người một chặng, mỗi người tự nói phần mình
làm — RUBRIC mục A3 (20đ) và B1 (20đ) chấm đúng chỗ đó, không ai nói hộ được.

---

## Phần 0 — Chuẩn bị trước buổi demo (làm trước 15 phút, KHÔNG làm trên sân khấu)

### 0.1 Kiểm tra port trống

Lỗi hay gặp nhất khi demo. Máy có thể đang chạy service khác ở port 8000:

```powershell
Get-NetTCPConnection -LocalPort 8000,8200 -State Listen -ErrorAction SilentlyContinue
```

- Không in ra gì → dùng port mặc định 8000.
- Có in ra → **đổi sang port khác** (ví dụ 8100) và thêm `--base-url http://127.0.0.1:8100`
  vào **mọi** lệnh gọi API bên dưới. Lúc chạy thử tôi gặp đúng tình huống này.

Cách kiểm chắc chắn nhất là gọi `/health`: nếu trả về JSON có `"tracing_enabled"` thì đúng app
của mình; trả về thứ khác là port bị service lạ chiếm.

### 0.2 Dựng môi trường

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Yêu cầu Python **3.11 trở lên**. Máy có nhiều bản Python thì chỉ định rõ: `py -3.13 -m venv .venv`.

### 0.3 Chạy trước một lượt để chắc chắn

```powershell
python -m pytest -q                    # phải: 46 passed
python scripts/validate_dashboard.py   # phải: HỢP LỆ: 6/6 panel
```

Hai lệnh này không cần server, chạy được ngay. Nếu fail thì dừng, đừng lên demo.

### 0.4 Mở sẵn 4 cửa sổ

| Cửa sổ | Dùng làm gì |
|---|---|
| Terminal 1 | Chạy API (để yên, không gõ gì thêm) |
| Terminal 2 | Gõ lệnh demo |
| Terminal 3 | Chạy dashboard (để yên) |
| Trình duyệt | Mở `http://127.0.0.1:8200` |

Chuẩn bị sẵn cỡ chữ terminal to (Ctrl + `+`) để người ngồi xa đọc được.

---

## Phần 1 — Khởi động (Terminal 1, để yên suốt buổi)

```powershell
$env:LOG_PATH = "data/logs.jsonl"
Remove-Item data/logs.jsonl -ErrorAction SilentlyContinue
python -m uvicorn app.main:app --port 8100 --log-level warning
```

Xoá log cũ để demo bắt đầu từ trạng thái sạch, người xem thấy log sinh ra trước mắt.

Từ đây trở đi mọi lệnh dùng Terminal 2 và đặt sẵn biến:

```powershell
$B = "http://127.0.0.1:8100"
```

---

## CHẶNG 0 — Sức khỏe hệ thống (30 giây, ai mở màn cũng được)

```powershell
curl.exe -s "$B/health"
```

Output thật:

```json
{"ok":true,"tracing_enabled":false,"incidents":{"rag_slow":false,"tool_fail":false,"cost_spike":false}}
```

**Nói gì:** "App sống, chưa bật incident nào, đây là trạng thái sạch. `tracing_enabled: false`
nghĩa là chưa cắm key Langfuse — em sẽ nói rõ ở chặng 3."

> Đừng giấu chỗ `tracing_enabled: false`. Giám khảo sẽ thấy. Nói thẳng ra và giải thích còn
> hơn để họ tự phát hiện.

---

## CHẶNG A — Correlation ID (Đỗ Văn Linh, P1) · 2 phút

**Ý chính cần truyền đạt:** một request đi qua nhiều bước, mỗi bước ghi log riêng. Không có
sợi dây nối thì không biết dòng log nào thuộc request nào. Correlation ID là sợi dây đó.

### A1. Client tự đặt ID — hệ thống phải tôn trọng

```powershell
curl.exe -s -D - -o NUL -X POST "$B/chat" -H "Content-Type: application/json" `
  -H "x-request-id: req-demo0001" `
  -d '{\"user_id\":\"demo-user\",\"session_id\":\"demo-s1\",\"feature\":\"qa\",\"message\":\"What is your refund policy?\"}'
```

Output thật (phần header):

```
x-request-id: req-demo0001
x-response-time-ms: 155.50
```

**Nói gì:** "Client gửi ID nào thì hệ thống giữ nguyên ID đó. Đây là cách nối trace xuyên
nhiều service — service A gọi service B thì truyền tiếp header này, cả hai cùng một ID."

### A2. Không đặt header — hệ thống tự sinh

```powershell
curl.exe -s -D - -o NUL -X POST "$B/chat" -H "Content-Type: application/json" `
  -d '{\"user_id\":\"demo-user\",\"session_id\":\"demo-s2\",\"feature\":\"qa\",\"message\":\"How do I debug tail latency?\"}'
```

Output thật: `x-request-id: req-0e28d38f` — đúng định dạng `req-` + 8 ký tự hex.

### A3. Chứng minh trong log

```powershell
python -c "import json;[print(json.dumps(json.loads(l),ensure_ascii=False,indent=2)) for l in open('data/logs.jsonl',encoding='utf-8') if 'req-demo0001' in l]"
```

Output thật (rút gọn):

```json
{
  "service": "api",
  "event": "request_received",
  "correlation_id": "req-demo0001",
  "user_id_hash": "cebf29_2c038f",
  "session_id": "demo-s1",
  "feature": "qa",
  "model": "claude-sonnet-4-5",
  "env": "dev",
  "ts": "2026-08-11T10:10:56.971711Z"
}
{
  "service": "api",
  "event": "response_sent",
  "latency_ms": 150,
  "tokens_in": 28, "tokens_out": 170, "cost_usd": 0.002634, "quality_score": 0.9,
  "correlation_id": "req-demo0001",
  "user_id_hash": "cebf29_2c038f",
  "ts": "2026-08-11T10:10:57.124291Z"
}
```

**Chỉ vào ba thứ:**
1. **Cùng `correlation_id`** ở cả hai dòng — đây là sợi dây.
2. **Đủ 5 field enrichment**: `user_id_hash`, `session_id`, `feature`, `model`, `env`. Nhờ có
   chúng mới lọc được log theo người dùng / theo tính năng.
3. **`user_id_hash` chứ không phải `user_id`** — `demo-user` đã bị băm thành `cebf29_2c038f`.
   Định danh được người dùng mà không lộ danh tính.

**Câu hỏi hay bị hỏi — chuẩn bị sẵn:**

> *Làm sao đảm bảo request này không lẫn context của request trước?*
> Middleware gọi `clear_contextvars()` ở đầu **mỗi** request. Có test riêng cho việc này:
> `test_sequential_requests_get_distinct_ids_without_context_leakage`.

> *Vì sao `user_id_hash` có dấu gạch dưới ở giữa?*
> Đó là phần của Liễu, chặng sau sẽ giải thích.

---

## CHẶNG B — PII redaction (Đỗ Thu Liễu, P2) · 2 phút

**Ý chính:** log phải đủ chi tiết để điều tra, nhưng không được chứa dữ liệu cá nhân. Hai yêu
cầu này mâu thuẫn nhau, và đây là cách nhóm giải quyết.

### B1. Gửi một request chứa đủ loại PII

```powershell
curl.exe -s -o NUL -X POST "$B/chat" -H "Content-Type: application/json" `
  -d '{\"user_id\":\"demo-user\",\"session_id\":\"demo-s4\",\"feature\":\"qa\",\"message\":\"Ho chieu B1234567, dia chi: 123 Nguyen Trai\"}'
```

```powershell
python -c "import json;[print(json.loads(l)['payload']['message_preview']) for l in open('data/logs.jsonl',encoding='utf-8') if 'demo-s4' in l and 'request_received' in l]"
```

Output thật:

```
Ho chieu [REDACTED_PASSPORT], [REDACTED_ADDRESS_VN]
```

> **Lưu ý khi demo:** `message_preview` bị cắt ở **80 ký tự**. Nếu gửi câu dài chứa 5–6 loại
> PII thì mấy loại cuối bị cắt mất, người xem tưởng không che được. Dùng **câu ngắn** như trên,
> hoặc gửi nhiều câu ngắn khác nhau.

Muốn khoe đủ 6 loại thì gửi từng câu ngắn: email, số điện thoại, CCCD 12 số, thẻ 16 số, hộ
chiếu, địa chỉ.

### B2. Chấm bằng chính validator của đề bài

```powershell
python scripts/validate_logs.py
```

Output thật ở cuối buổi demo (sau khi đã chạy hết các chặng):

```
--- Lab Verification Results ---
Total log records analyzed: 141
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 71
Potential PII leaks detected: 0

+ [PASSED] Basic JSON schema
+ [PASSED] Correlation ID propagation
+ [PASSED] Log enrichment
+ [PASSED] PII scrubbing

Estimated Score: 100/100
```

**Nói gì:** "Đây không phải script tự viết cho dễ đậu. Đây là validator của đề bài, có bộ
detector PII **riêng** quét toàn bộ dòng JSON, độc lập với code scrub của nhóm em."

### B3. Hai lỗi nhóm tự tìm ra và sửa — kể chuyện này, nó ghi điểm

Đây là phần đáng nói nhất của chặng B, vì nó cho thấy nhóm **đo** chứ không đoán.

**Lỗi 1 — pattern hộ chiếu ăn nhầm correlation ID.**
Pattern bắt hộ chiếu là "1 chữ cái + 7–8 chữ số". Correlation ID lại có dạng `req-` + 8 hex.
Khi 8 hex đó tình cờ là 1 chữ + 7 số, ví dụ `req-b1234567`, nó bị nuốt thành
`req-[REDACTED_PASSPORT]`. Đo trên 200.000 ID: **1,43% bị hỏng**. Hậu quả: trace không tìm
ngược về log được — đứt đúng mắt xích quan trọng nhất. Sửa bằng lookbehind chặn match bắt đầu
ngay sau dấu `-`. Đo lại: **0%**.

**Lỗi 2 — hàm scrub chỉ quét một lượt.**
Hai PII dính liền nhau, ví dụ `0901234567+84901234567`, chỉ cái đầu bị che. Cái thứ hai lọt
lưới và bị validator bắt → **70/100**. Sửa thành quét lặp đến khi không còn thay đổi. Sau khi
sửa: **100/100**.

**Câu hỏi hay bị hỏi:**

> *Vì sao `user_id_hash` là `cebf29_2c038f` mà không phải 12 hex liền?*
> Hash 12 hex liền mạch có **0,42%** khả năng tình cờ khớp regex số điện thoại hoặc CCCD của
> chính validator, và bị báo là PII leak dù nó chỉ là hash — mất 30 điểm oan. Chèn `_` vào
> giữa làm mỗi nửa chỉ còn 6 chữ số, dưới ngưỡng 10 của phone và 12 của CCCD. Đo lại trên
> 200.000 hash: 0 trường hợp.

> *Client gửi PII vào header `x-request-id` thì sao?*
> Vẫn bị scrub. Correlation ID cố ý **không** được miễn trừ khỏi lớp scrub, chỉ có `ts`,
> `level` và `user_id_hash` được miễn vì chúng không thể chứa PII theo cấu trúc.

---

## CHẶNG C — Tracing & prompt version (Nguyễn Thanh Bình, P3) · 2 phút

### C1. Nói thẳng trạng thái

```powershell
curl.exe -s "$B/health"
```

`"tracing_enabled": false` — chưa có key Langfuse.

**Nói gì:** "Phần code đã xong và có test. Phần cần chạy thật trên Langfuse thì chưa có key,
em không dựng trace giả để lấp chỗ trống — RULES cấm, và evidence giả thì cũng không được tính."

### C2. Chứng minh code sẵn sàng

```powershell
python scripts/seed_prompts.py list
```

Output thật:

```
Chưa cấu hình được Langfuse. Kiểm tra .env:
  - LANGFUSE_PUBLIC_KEY: THIẾU
  - LANGFUSE_SECRET_KEY: THIẾU
  - LANGFUSE_HOST: THIẾU
Không có key thì không tạo được prompt version thật, cũng không có evidence.
```

**Nói gì:** "Script dừng hẳn khi thiếu key thay vì âm thầm chạy tiếp bằng dữ liệu giả. Đây là
lựa chọn có chủ đích."

### C3. Mở code cho xem

Mở [`app/agent.py`](../app/agent.py), chỉ vào đoạn `update_current_trace`:

- Trace mang tag `cid:<correlation_id>` → từ Langfuse search ngược ra được đúng dòng log.
- Metadata có `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`.

Giải thích vì sao correlation ID nằm ở **tag** chứ không nằm trong `metadata`: public test
`test_agent_links_prompt_version_to_trace_and_generation` khẳng định metadata của trace chỉ
chứa đúng 4 field prompt. Đặt vào tag thì vừa search được vừa không phá test có sẵn.

### C4. Nếu KỊP có key trước buổi demo

```powershell
python scripts/seed_prompts.py init                 # tạo v1 (baseline+production), v2 (candidate)
python scripts/seed_prompts.py promote --version 2  # chuyển production sang v2
python scripts/seed_prompts.py rollback             # trả production về v1
```

`promote` và `rollback` in trạng thái **TRƯỚC và SAU**, chụp màn hình là có ngay bằng chứng
đổi label.

---

## CHẶNG D — Dashboard 6 panel (Trịnh Hải Đăng, P4) · 2 phút

### D1. Sinh baseline trước (làm ở phần chuẩn bị, đừng để khán giả ngồi chờ)

```powershell
1..6 | ForEach-Object { python scripts/load_test.py --concurrency 5 --base-url $B }
```

Sáu vòng × 10 query = **60 request**.

> **Vì sao phải 60?** Panel traffic có ngưỡng ≥ 1 request/phút tính trên cửa sổ 60 phút. Chạy
> ít hơn thì rate < 1 và panel báo vi phạm — không phải lỗi, chỉ là chưa đủ tải. Đây là bẫy
> dễ mắc nhất khi chụp ảnh dashboard.

### D2. Mở dashboard (Terminal 3)

```powershell
python scripts/dashboard_app.py --log-path data/logs.jsonl --port 8200
```

Mở trình duyệt `http://127.0.0.1:8200`. Số liệu thô ở `http://127.0.0.1:8200/api/summary`.

Output thật lúc baseline:

```
cửa sổ 60 phút | 129 bản ghi
[ĐẠT] latency  p50=150.0  p95=150.0  p99=151.0 ms   (sample 64)
[ĐẠT] traffic  count=64  rate_per_minute=1.07 requests_per_minute
[ĐẠT] errors   error_rate_pct=0.0  (0 failed / 64 received)
[ĐẠT] cost     total_usd=0.1361
[ĐẠT] tokens   in=2118  out=8647
[ĐẠT] quality  mean=0.8797  (sample 64)
```

**Chỉ vào từng thứ:** tên panel, đơn vị, đường threshold, time range 60 phút. Bốn thứ này
`docs/dashboard-spec.md` bắt buộc phải nhìn thấy trong ảnh chụp.

**Nói gì:** "Sáu panel này **không viết cứng trong code**. Dashboard đọc `config/dashboard.yaml`
lúc chạy. Sửa ngưỡng trong file contract thì dashboard đổi theo ngay, không bao giờ lệch khỏi
cái đang được chấm điểm."

### D3. Alert và runbook

Mở [`config/alert_rules.yaml`](../config/alert_rules.yaml) và [`docs/alerts.md`](alerts.md).

Ba alert đều là **symptom-based** — cảnh báo theo triệu chứng người dùng cảm nhận được (chậm,
lỗi, chi phí vọt), không cảnh báo theo nguyên nhân kỹ thuật nội bộ. Mỗi alert có ngưỡng, có
thời gian duy trì, và trỏ tới đúng một mục runbook.

---

## CHẶNG E — Incident và điều tra (Trần Chí Vũ, P5) · 3 phút

Đây là cao trào. Cả buổi demo dồn vào đây.

### E1. Bật incident chính thức

```powershell
python scripts/inject_incident.py --base-url $B
```

Không truyền `--scenario` thì script đọc `config/challenge.json` — file chính thức của Lab Coach.

Output thật:

```
200 {'ok': True, 'incidents': {'rag_slow': True, 'tool_fail': False, 'cost_spike': False}}
```

### E2. Chạy 5 query chính thức

```powershell
python scripts/load_test.py --challenge --concurrency 5 --base-url $B
```

Output thật:

```
Challenge: day13-k4-observability-v1 | Cohort: K4
[200] req-290fb48b | monitoring | 7963.0ms
[200] req-ba5d3bd8 | monitoring | 10615.1ms
[200] req-c4c848bf | monitoring | 10616.6ms
[200] req-cf2abb61 | monitoring | 10617.4ms
[200] req-15627ae6 | monitoring | 13269.6ms
```

> Con số ở đây (7963ms, 10615ms…) là thời gian **phía client**, đã cộng cả thời gian xếp hàng
> do chạy 5 request song song. Thời gian xử lý thật phía server là `latency_ms` trong log,
> khoảng 2651ms. Nói rõ chỗ này, nếu không giám khảo sẽ hỏi vì sao hai con số vênh nhau.

### E3. Metrics — bước 1: có gì đó bất thường

Bấm F5 dashboard. Output thật sau sự cố:

```
140 bản ghi
[ĐẠT] latency  p50=150.0  p95=2650.0  p99=2651.0 ms
[ĐẠT] traffic  count=69  rate_per_minute=1.15
[ĐẠT] errors   error_rate_pct=0.0  (0 failed / 69 received)
[ĐẠT] cost     total_usd=0.1462
[ĐẠT] tokens   in=2293  out=9289
[ĐẠT] quality  mean=0.8768
```

Tách riêng nhóm challenge:

| | Baseline (64 request) | Challenge (5 request) |
|---|---|---|
| p50 | 150 ms | **2651 ms** |
| p95 | 150 ms | **2651 ms** |
| error rate | 0% | 0% |

**Đọc metrics thành lời:**
1. Latency tăng **×17,7**.
2. Độ trễ cộng thêm **≈ +2500ms gần như cố định** ở mọi request — không phải đuôi phân phối.
   Hằng số thì gợi ý một khoảng chờ cứng, không phải nghẽn tài nguyên.
3. Error rate **không đổi** → không phải lỗi hệ thống.
4. Token và cost **không đổi** → không phải prompt phình to hay đổi model.
5. Quality **không giảm** → không phải suy giảm chất lượng.

→ Thời gian bị đốt ở một bước **không tiêu tốn token**, tức là ngoài lời gọi LLM. Metrics đã
thu hẹp phạm vi đến đây, nhưng chưa chỉ được đúng bước nào.

### E4. Điểm quan trọng nhất — SLO không bắt được sự cố này

**5/5** request vượt ngưỡng challenge **2000ms**, nhưng **0/5** vượt SLO **3000ms**.

**Nói gì:** "Latency tăng gần 18 lần mà SLO vẫn báo xanh. Nếu nhóm em chỉ cảnh báo khi thủng
SLO thì sự cố này lọt lưới hoàn toàn. Đó là lý do preventive measure đầu tiên của nhóm là đặt
ngưỡng cảnh báo **thấp hơn** SLO để bắt sớm."

Đây là nhận xét ghi điểm — nó cho thấy nhóm hiểu **khác biệt giữa SLO và ngưỡng cảnh báo**,
không chỉ chép số vào file.

### E5. Traces — bước 2

**Trạng thái thật:** chưa có trace vì chưa có key Langfuse. Nói thẳng.

Giải thích trace **sẽ** cho thấy gì và vì sao: mỗi trace mang tag `cid:<correlation_id>`, mở
waterfall ra thì span `retrieve` chiếm phần lớn thời gian. Ba trong bốn mắt xích đã có bằng
chứng thật; mắt xích này còn thiếu và nhóm ghi rõ trong report chứ không lấp bằng số bịa.

### E6. Logs — bước 3: chứng minh

```powershell
python -c "import json;[print(l.strip()) for l in open('data/logs.jsonl',encoding='utf-8') if 'req-ba5d3bd8' in l]"
```

Output thật:

```json
{"service": "api", "payload": {"message_preview": "Which signal should be checked after latency increases?"}, "event": "request_received", "session_id": "k4-challenge-s04", "env": "dev", "feature": "monitoring", "user_id_hash": "6b83e7_4c0874", "correlation_id": "req-ba5d3bd8", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T10:12:25.980094Z"}
{"service": "api", "latency_ms": 2651, "tokens_in": 36, "tokens_out": 153, "cost_usd": 0.002403, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer..."}, "event": "response_sent", "session_id": "k4-challenge-s04", "env": "dev", "feature": "monitoring", "user_id_hash": "6b83e7_4c0874", "correlation_id": "req-ba5d3bd8", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T10:12:28.632025Z"}
```

**Chỉ vào bốn thứ:**
1. Hai `ts` cách nhau **2,652s**, khớp `latency_ms: 2651` → thời gian bị đốt **bên trong** một
   request, không phải do xếp hàng.
2. Kết thúc bằng `response_sent`, **không có** `request_failed` → thành công, chỉ chậm.
3. `tokens_in: 36`, `tokens_out: 153` — bình thường như baseline.
4. `cost_usd: 0.002403` — không tăng.

### E7. Root cause — bước 4

Mở [`app/mock_rag.py`](../app/mock_rag.py), dòng 17–18:

```python
if STATE["rag_slow"]:
    time.sleep(2.5)
```

**Kết luận:** cờ incident `rag_slow` bật một `time.sleep(2.5)` **chặn luồng** trong bước truy
hồi tài liệu `retrieve()`, chạy **trước** lời gọi LLM.

**Phép kiểm khớp:** 150ms baseline + 2500ms = **2650ms**, đúng bằng con số đo được. Và vì độ
trễ nằm ngoài đường đi của token nên token, cost, quality đều đứng yên — khớp chính xác những
gì metrics và log cho thấy.

### E8. Fix và phòng ngừa

**Fix ngay:**

```powershell
python scripts/inject_incident.py --scenario rag_slow --disable --base-url $B
```

**Fix cho hệ thống thật:** đặt timeout cho bước retrieval và trả câu trả lời fallback khi quá
hạn, thay vì để một lời gọi chậm chặn cả request.

**Phòng ngừa:**
1. Siết ngưỡng cảnh báo xuống dưới SLO — lý do đã nói ở E4.
2. Tách span riêng cho `retrieve` để dashboard thấy thời gian từng bước, không chỉ tổng.
3. Cảnh báo khi latency tăng mà token/cost **không** tăng — dấu hiệu đặc trưng của nghẽn ở
   bước không dùng LLM, khoanh vùng được ngay từ metrics.

---

## Phần cuối — Dọn dẹp (30 giây)

```powershell
python scripts/inject_incident.py --scenario rag_slow --disable --base-url $B
curl.exe -s "$B/health"      # xác nhận mọi incident đã tắt
```

Tắt Terminal 1 và 3 bằng Ctrl+C.

---

## Bảng phân vai và thời lượng

| Chặng | Người | Phút | Nội dung |
|---|---|---|---|
| 0 | ai cũng được | 0,5 | health check |
| A | Đỗ Văn Linh | 2 | correlation ID, enrichment |
| B | Đỗ Thu Liễu | 2 | PII redaction, 2 lỗi tự tìm ra |
| C | Nguyễn Thanh Bình | 2 | tracing, prompt version |
| D | Trịnh Hải Đăng | 2 | dashboard 6 panel, alert, runbook |
| E | Trần Chí Vũ | 3 | incident, điều tra 4 bước |
| Dọn | Vũ | 0,5 | tắt incident |

---

## Sự cố hay gặp khi demo và cách xử

| Triệu chứng | Nguyên nhân | Cách xử tại chỗ |
|---|---|---|
| `/health` trả JSON lạ, không có `tracing_enabled` | Port bị service khác chiếm | Đổi port, thêm `--base-url` vào mọi lệnh |
| `[Errno 10048] bind` | Port đang bận | Đổi port khác |
| Mọi `/chat` timeout | Server chạy trong pipe không ai đọc | Chạy uvicorn ở terminal riêng, đừng redirect stdout vào pipe |
| `validate_logs.py` báo not found | Chưa sinh log | Chạy `load_test.py` trước |
| Panel traffic báo vi phạm | Chưa đủ 60 request trong cửa sổ 60 phút | Chạy thêm vòng load test |
| PII loại cuối không thấy bị che | `message_preview` cắt ở 80 ký tự | Gửi câu ngắn hơn |
| Log dính BOM, dòng đầu báo JSON hỏng | PowerShell ghi BOM khi redirect | Dashboard đã đọc `utf-8-sig`, không sao |
| Terminal hiện tiếng Việt thành `?` | Console dùng cp1252 | `chcp 65001` trước khi chạy |

---

## Ba câu hỏi khó nhất và cách trả lời

**"Nhóm dùng AI để làm bài đúng không?"**
Trả lời thẳng, đừng vòng vo. Nói rõ phần nào tự làm, phần nào có hỗ trợ, và quan trọng nhất là
**giải thích được** từng quyết định kỹ thuật. Ai cũng phải nói được vì sao code của mình như
vậy — chỗ đó mới là điểm.

**"Vì sao trace chưa có mà vẫn nộp?"**
Vì thiếu key Langfuse, và nhóm chọn ghi rõ thiếu thay vì dựng trace giả. RULES cấm làm giả
trace. Ba trong bốn mắt xích Metrics → Traces → Logs → Root cause đã có bằng chứng kiểm chứng
được, mắt xích còn lại được ghi thiếu một cách minh bạch.

**"Con số trong report lấy ở đâu ra?"**
Mọi con số đều tái hiện được bằng lệnh ghi kèm trong từng file evidence. Chạy lại `load_test`
và `validate_logs` là ra đúng những con số đó — trừ cost và token, vì mock LLM sinh độ dài
ngẫu nhiên nên hai giá trị này lệch giữa các lần chạy. Latency, error rate, số correlation ID
và quality thì tái hiện chính xác.
