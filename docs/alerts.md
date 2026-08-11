# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

Ba alert dưới đây khớp 1-1 với ba mục trong [config/alert_rules.yaml](../config/alert_rules.yaml) và canh ba
triệu chứng khác nhau mà người dùng cảm nhận được: **chậm**, **lỗi**, **trả lời kém**. Không alert nào canh
nguyên nhân kỹ thuật (cờ `rag_slow`, tên exception, số span RAG) — nguyên nhân là thứ tìm ra trong runbook,
không phải thứ để rung chuông.

**Thang severity** — chỉ hai mức, suy ra từ tốc độ đốt error budget trong [config/slo.yaml](../config/slo.yaml)
(cửa sổ 28 ngày = 40320 phút):

| Severity | Nghĩa | Quy tắc chọn |
|---|---|---|
| `critical` | Gọi người trực ngay, 24/7 | Vi phạm liên tục sẽ đốt hết error budget 28 ngày trong **dưới 24 giờ** |
| `warning` | Mở ticket, xử lý trong giờ làm việc | Cần **hơn 24 giờ** vi phạm liên tục mới hết budget |

Áp dụng: latency có 201.6 phút budget → cháy hết sau 3.4 giờ → `critical`. Error rate 403.2 phút → 6.7 giờ →
`critical`. Quality 2016 phút → 33.6 giờ → `warning`.

**Quy ước chung cho cả ba runbook**

- Lệnh viết cho PowerShell, chạy tại thư mục gốc repo, dùng `.venv\Scripts\python.exe` chứ không dùng `python` trần.
- Nguồn metrics là file JSONL app ghi ra theo biến `LOG_PATH`: `data/logs.jsonl` khi chấm, `data/dev/pN.jsonl` khi
  dev instance riêng. Đổi đường dẫn trong lệnh cho khớp instance đang điều tra.
- Bước Metrics của mỗi runbook đọc thẳng file JSONL đó bằng một lệnh Python độc lập, để vẫn điều tra được khi
  dashboard chưa mở hoặc đang hỏng. Nếu dashboard của nhóm đang chạy thì nhìn panel tương ứng trước cho nhanh;
  lệnh bên dưới là cách kiểm chứng lại con số trên dữ liệu gốc.
- Bước Metrics luôn in ra kèm `correlation_id` của các request tệ nhất. Đó là khoá để đi tiếp: trace trên Langfuse
  mang tag `cid:<correlation_id>` (xem [app/agent.py](../app/agent.py)), log có field `correlation_id`. Ba bước
  Metrics → Traces → Logs nối với nhau bằng đúng khoá này.
- **Giới hạn thật của trace trong repo này — đọc trước khi làm bước Traces.** Toàn bộ `app/` chỉ có đúng **một**
  observation được instrument: `@observe(as_type="generation")` trên `LabAgent.run`
  ([app/agent.py](../app/agent.py)). Không có span `retrieve` hay span LLM riêng, nên waterfall chỉ có một dòng
  `run` — không bóc tách được thời gian RAG với thời gian LLM ngay trên trace. Ngoài ra
  `update_current_trace(... tags=[..., "cid:<id>"])` nằm **sau** lời gọi `retrieve()`, nên **trace của request lỗi
  không hề có tag `cid:`, `user_id` hay `session_id`** — chỉ có `level=ERROR` và `status_message` do decorator ghi.
  Hệ quả: lọc theo tag `cid:` chỉ dùng được cho request **thành công**; với request lỗi phải lọc theo `Level = ERROR`
  và mốc thời gian, còn bằng chứng chính là dòng log ở bước 3.
- Port mặc định trong lệnh là `8000` (instance canonical của P5); đổi sang port riêng nếu đang chạy instance của mình.
- **Ngưỡng latency hiện KHÔNG bắt được incident chính thức của K4 — đọc trước khi dùng Alert 1 để điều tra
  challenge.** `config/challenge.json` (Lab Coach phát hành, RULES cấm sửa) đặt `latency_threshold_ms: 2000`,
  trong khi panel `latency`, `latency_p95_ms` trong [config/slo.yaml](../config/slo.yaml) và Alert 1 đều dùng
  3000 ms. Incident chính thức là `rag_slow`, đo được **~2650 ms** (150 ms của `FakeLLM.generate` + 2.5 s
  `time.sleep`), tức nằm **giữa hai con số**. Hệ quả đã kiểm chứng: chạy `dashboard_app.py` trên log của
  challenge cho `p95 = 2651 ms → ĐẠT NGƯỠNG`, và Alert 1 (`> 3000`) **không bao giờ kêu** trong suốt sự cố.
  Nghĩa là bước Metrics của luồng Metrics → Traces → Logs hiện không có triệu chứng nào để chỉ vào cho đúng
  kịch bản mà đề bài dựng ra. Chừng nào nhóm chưa chốt lại con số, khi điều tra challenge phải so p95 với
  **2000 ms của `challenge.json`** chứ không phải với ngưỡng panel, và ghi rõ trong báo cáo là đang dùng
  thước đo nào. Cách sửa triệt để là hạ ngưỡng latency về 2000 ms **đồng thời ở cả bốn chỗ**
  (`config/dashboard.yaml` panel `latency`, `objective` trong `slo.yaml`, `condition` trong
  `alert_rules.yaml`, và mọi số 3000 trong tài liệu này) — đổi lẻ một chỗ sẽ làm dashboard, SLO và alert
  nói ba con số khác nhau. `error_budget_minutes` không đổi vì nó chỉ phụ thuộc `target` 99.5% và cửa sổ 28 ngày.

## Alert 1

- Tên: `user_facing_slow_response` — người dùng phải chờ quá lâu mới nhận được câu trả lời.
- Severity: `critical` (gọi ngay). 5 phút vi phạm liên tục đã tiêu 2.5% error budget latency; nếu để chạy tiếp thì
  chỉ 3.4 giờ là hết sạch budget 28 ngày, nên không thể để đến giờ hành chính.
- SLI/SLO liên quan: `latency_p95_ms` trong [config/slo.yaml](../config/slo.yaml) — objective 3000 ms, target 99.5%
  trên 28 ngày, error budget 201.6 phút. Cùng con số với panel `latency` (`threshold: p95 lte 3000`) trong
  [config/dashboard.yaml](../config/dashboard.yaml).
- Điều kiện và thời gian duy trì: `p95(latency_ms where event == "response_sent") > 3000 ms` duy trì liên tục
  **5 phút** (bucket 1 phút, tối thiểu 5 request trong cửa sổ). Cần cả ba ràng buộc: panel `traffic` chỉ bảo đảm
  ≥ 1 request/phút, nên một phút có thể chỉ có đúng 1 request — khi đó p95 chính là latency của đúng request lẻ đó,
  một mẫu chậm là alert kêu ngay và tắt ngay ở phút sau. Yêu cầu 5 bucket liên tiếp và đủ số mẫu để chặn nhấp nháy.
- Ảnh hưởng tới người dùng: `/chat` trả lời sau hơn 3 giây thay vì ~150 ms (baseline đo được trên fake LLM).
  Người dùng tưởng treo, bấm gửi lại →
  nhân đôi tải và nhân đôi cost, kéo theo panel `cost`/`tokens` cũng xấu theo.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics — xác nhận triệu chứng có thật và lấy khoá điều tra.** Tính p95 trên chính file log nguồn của
     dashboard, đồng thời in 3 request chậm nhất kèm `correlation_id`:

     ```powershell
     .venv\Scripts\python.exe -c "import json,math;r=[json.loads(l) for l in open('data/logs.jsonl',encoding='utf-8') if l.strip()];v=sorted((x for x in r if x.get('event')=='response_sent' and isinstance(x.get('latency_ms'),(int,float))),key=lambda x:x['latency_ms']);print('n=',len(v),'p95=',v[math.ceil(len(v)*0.95)-1]['latency_ms'] if v else 'khong co mau response_sent');print('cham nhat:',[(x.get('correlation_id','?'),x['latency_ms']) for x in v[-3:]])"
     ```

     `p95` > 3000 thì đi tiếp; nếu ≤ 3000 mà alert vẫn kêu thì vấn đề nằm ở cấu hình alert, không phải ở service.
     `n= 0` nghĩa là **không có request nào trả lời thành công** — đó là sự cố nặng hơn, chuyển sang Alert 2.
  2. **Traces — xác nhận trên trace và loại trừ tầng LLM.** Mở Langfuse → Tracing → lọc **Tags** bằng
     `cid:<correlation_id>` lấy ở bước 1 (đúng chuỗi đó, ví dụ `cid:req-1a2b3c4d`). Trace chỉ có một observation
     `run` (xem "Giới hạn thật của trace" ở trên), nên **không** so được span `retrieve` với span LLM; hai thứ đọc
     được là *Latency* của observation đó và *metadata*. Cách khoanh vùng thực tế: `FakeLLM.generate` luôn ngủ cố
     định 0.15 s ([app/mock_llm.py](../app/mock_llm.py)), nên latency ≈ 150 ms là bình thường, còn latency ≈ 2650 ms
     đúng bằng 150 ms + 2.5 s `time.sleep` của `rag_slow` ([app/mock_rag.py](../app/mock_rag.py)) → phần dôi ra nằm ở
     tầng RAG. Metadata `doc_count` **không** dùng để phán đoán ở đây: `retrieve` luôn trả ít nhất một document
     fallback nên `doc_count` luôn ≥ 1. Mở một trace nhanh cùng `feature` để so cạnh nhau và ghi lại trace ID.
  3. **Logs — chứng minh bằng dòng log của đúng request đó.** Đọc toàn bộ log của một `correlation_id` và kiểm tra
     xem đã có ai bật kịch bản inject chưa:

     ```powershell
     Select-String -Path data\logs.jsonl -Pattern 'req-1a2b3c4d'
     Select-String -Path data\logs.jsonl -Pattern 'incident_enabled'
     ```

     Đối chiếu `latency_ms` trong dòng `response_sent` với con số trên trace (phải khớp), và xem `feature`/`model`
     để biết chỉ một feature chậm hay tất cả cùng chậm.
- Mitigation tạm thời:
  1. Xem cờ incident đang bật: `Invoke-RestMethod http://127.0.0.1:8000/health` → đọc map `incidents`.
  2. Nếu `rag_slow: true`, tắt ngay:
     `.venv\Scripts\python.exe scripts/inject_incident.py --scenario rag_slow --disable`
  3. Chạy lại lệnh ở bước 1 sau ~5 phút để xác nhận p95 tụt về dưới 3000 ms. Nếu cờ đã tắt mà vẫn chậm thì đây là
     chậm thật chứ không phải incident giả lập: dừng `scripts/load_test.py` để giảm tải, giữ nguyên log làm bằng
     chứng và escalate.
- Owner: **Trần Chí Vũ (P5)** — giữ `scripts/inject_incident.py` và `scripts/load_test.py`, tức là người duy nhất
  bật/tắt được nguyên nhân và điều tiết được tải. Escalate: **Trịnh Hải Đăng (P4)** (chủ dashboard và alert rules).

## Alert 2

- Tên: `user_facing_request_failure` — request thất bại, người dùng nhận HTTP 500 thay vì câu trả lời.
- Severity: `critical` (gọi ngay). Error budget 403.2 phút, vi phạm liên tục là cháy hết sau 6.7 giờ — vẫn dưới
  24 giờ nên phải xử lý ngoài giờ.
- SLI/SLO liên quan: `error_rate_pct` trong [config/slo.yaml](../config/slo.yaml) — objective 2%, target 99.0%
  trên 28 ngày, error budget 403.2 phút. Cùng con số với panel `errors` (`threshold: error_rate_pct lte 2`).
- Điều kiện và thời gian duy trì: `100 * count(request_failed) / count(request_received) > 2%` duy trì liên tục
  **5 phút** (bucket 1 phút, tối thiểu 5 request) — biểu thức đầy đủ kèm điều kiện `event` nằm trong
  [config/alert_rules.yaml](../config/alert_rules.yaml). Mẫu số bắt buộc là `request_received`: request lỗi không
  sinh `response_sent` nào cả, nên chia cho `response_sent` sẽ thổi phồng tỷ lệ lỗi.
- Ảnh hưởng tới người dùng: nhận HTTP 500 với body `detail: <error_type>`, không có câu trả lời nào và không có
  gợi ý phải làm gì; người dùng phải tự thử lại. Đây là triệu chứng nặng nhất trong ba alert vì tính năng đứt hẳn.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics — đo tỷ lệ lỗi đúng công thức và xem lỗi thuộc loại nào.**

     ```powershell
     .venv\Scripts\python.exe -c "import json,collections;r=[json.loads(l) for l in open('data/logs.jsonl',encoding='utf-8') if l.strip()];rec=sum(x.get('event')=='request_received' for x in r);bad=[x for x in r if x.get('event')=='request_failed'];print('received=',rec,'failed=',len(bad),'error_rate_pct=',round(100*len(bad)/rec,2) if rec else 'khong co request_received');print(collections.Counter(x.get('error_type') for x in bad));print('cid loi:',[x.get('correlation_id','?') for x in bad[:3]])"
     ```

     Breakdown theo `error_type` cho biết ngay là một loại lỗi duy nhất (thường là hỏng một dependency) hay nhiều
     loại rải rác (thường là hỏng ở tầng vào).
  2. **Traces — xác nhận lỗi có tới được tầng agent hay không.** Request lỗi **không tìm được bằng tag `cid:`**:
     `update_current_trace(...)` chạy sau `retrieve()` nên exception thoát ra trước khi tag/`user_id`/`session_id`
     kịp gắn (xem "Giới hạn thật của trace" ở trên). Cách lọc đúng: Langfuse → Tracing → lọc **Level = ERROR**, lấy
     trace ở đúng mốc thời gian của `correlation_id` bước 1, đọc `status_message` mà `@observe` ghi lại — với
     `tool_fail` chuỗi này là `Vector store timeout`, khớp `error_type: RuntimeError` trong log. Nếu **không** có
     trace ERROR nào trong khi log đầy `request_failed`, nghĩa là lỗi xảy ra ngoài `LabAgent.run` (tầng
     validate/middleware) — chuyển thẳng sang bước 3. Mở một trace thành công cùng `feature` để đối chiếu.
  3. **Logs — lấy thông điệp lỗi gốc.**

     ```powershell
     Select-String -Path data\logs.jsonl -Pattern 'request_failed' | Select-Object -First 5
     Select-String -Path data\logs.jsonl -Pattern 'req-1a2b3c4d'
     ```

     Trong cặp `request_received` → `request_failed` của cùng một `correlation_id`, đọc `error_type` và
     `payload.detail`. Ví dụ `RuntimeError` + `Vector store timeout` chỉ thẳng vào `retrieve` trong
     [app/mock_rag.py](../app/mock_rag.py).
- Mitigation tạm thời:
  1. `Invoke-RestMethod http://127.0.0.1:8000/health` → đọc map `incidents`.
  2. Nếu `tool_fail: true`: `.venv\Scripts\python.exe scripts/inject_incident.py --scenario tool_fail --disable`,
     rồi bắn lại vài request và chạy lại lệnh ở bước 1 để xác nhận `error_rate_pct` về 0.
  3. Nếu `error_type` không phải lỗi của vector store (không tắt được bằng cờ incident), giữ nguyên log và trace
     làm bằng chứng, escalate cho chủ sở hữu đường lỗi thay vì restart mù — restart sẽ xoá mất ngữ cảnh in-memory
     của `/metrics`.
- Owner: **Đỗ Văn Linh (P1)** — giữ [app/main.py](../app/main.py) và [app/middleware.py](../app/middleware.py),
  nơi exception bị bắt và ghi ra event `request_failed`. Escalate: **Trần Chí Vũ (P5)** nếu cần tắt incident hoặc
  chạy lại load test.

## Alert 3

- Tên: `user_facing_answer_quality_drop` — API vẫn nhanh, vẫn trả 200, nhưng nội dung trả lời kém đi.
- Severity: `warning` (ticket trong giờ làm việc). Error budget 2016 phút, phải vi phạm liên tục 33.6 giờ mới
  cháy hết — trên 24 giờ nên theo thang severity là `warning`, không gọi người lúc nửa đêm cho một chỉ số proxy.
- SLI/SLO liên quan: `quality_score_avg` trong [config/slo.yaml](../config/slo.yaml) — objective 0.75, target
  95.0% trên 28 ngày, error budget 2016 phút. Cùng con số với panel `quality` (`threshold: mean gte 0.75`).
- Điều kiện và thời gian duy trì: `mean(quality_score where event == "response_sent") < 0.75` duy trì liên tục
  **10 phút** (bucket 1 phút, tối thiểu 10 request). Dài gấp đôi hai alert kia vì `quality_score` là điểm rời rạc
  do `_heuristic_quality` chấm (bước nhảy 0.1), chỉ vài request lệch là mean đã qua ngưỡng trong cửa sổ ngắn;
  10 phút và 10 mẫu là mức tối thiểu để phân biệt xu hướng thật với nhiễu.
- Ảnh hưởng tới người dùng: đây là hỏng **âm thầm** — không ai báo lỗi vì HTTP vẫn 200 và vẫn nhanh, nhưng câu
  trả lời ngắn cụt, lạc đề hoặc lộ chuỗi `[REDACTED_*]` ra mặt người dùng. Không có alert này thì chỉ phát hiện
  khi có người khiếu nại, tức là muộn hàng ngày.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics — xác nhận mean tụt và lấy request kém nhất.**

     ```powershell
     .venv\Scripts\python.exe -c "import json,statistics;r=[json.loads(l) for l in open('data/logs.jsonl',encoding='utf-8') if l.strip()];v=[x for x in r if x.get('event')=='response_sent' and isinstance(x.get('quality_score'),(int,float))];print('n=',len(v),'mean_quality=',round(statistics.fmean(x['quality_score'] for x in v),3) if v else 'khong co mau response_sent');print('kem nhat:',sorted((x['quality_score'],x.get('correlation_id','?')) for x in v)[:3])"
     ```

     Dùng `statistics.fmean` cho khớp đúng phép `mean` mà panel `quality` đang tính trong
     `scripts/dashboard_app.py`; `n= 0` nghĩa là chưa có câu trả lời nào để chấm, không phải chất lượng bằng 0.

  2. **Traces — kiểm tra phiên bản prompt, vì log không mang thông tin này.** Lọc Tags `cid:<correlation_id>` của
     request kém nhất, mở generation và đọc metadata `prompt_name` / `prompt_label` / `prompt_version` /
     `prompt_source`. Hai dấu hiệu cần tìm: (a) `prompt_version` vừa đổi ngay trước lúc mean tụt → có người
     promote phiên bản mới; (b) `prompt_source = local-fallback` → gọi Langfuse hỏng nên app đang chạy template
     local chứ không phải bản đang giữ label `production`, kèm theo `prompt_fetch_error` cho biết lý do.
  3. **Logs — đối chiếu nội dung thật của câu trả lời.**

     ```powershell
     Select-String -Path data\logs.jsonl -Pattern 'req-1a2b3c4d'
     Select-String -Path data\logs.jsonl -Pattern 'REDACTED'
     ```

     Xem `payload.answer_preview` của các dòng `response_sent`: điều kiện cộng điểm là `len(answer) > 40`, nên câu
     trả lời dài **≤ 40 ký tự** là mất 0.1 điểm trong `_heuristic_quality` ([app/agent.py](../app/agent.py)). Preview
     chỉ là ước lượng của độ dài đó — `summarize_text` cắt ở 80 ký tự và đã thay PII bằng `[REDACTED_*]` (dài hơn
     chuỗi gốc), nên chỉ tin preview khi nó ngắn hơn hẳn 40. Nếu preview chứa `[REDACTED_`, câu trả
     lời đang lặp lại PII của người dùng — phải xử lý ngay cả khi điểm chưa bị trừ, vì `_heuristic_quality` chấm
     trên answer gốc chưa qua scrub còn preview thì đã được che.
- Mitigation tạm thời:
  1. Xem version nào đang giữ label `production`: `.venv\Scripts\python.exe scripts/seed_prompts.py list`.
  2. Nếu vừa promote một version mới: `.venv\Scripts\python.exe scripts/seed_prompts.py rollback` (trả label
     `production` về v1), bắn lại một request rồi mở trace mới để xác nhận metadata `prompt_version` đã về 1 và
     `quality_score` phục hồi.
  3. Nếu `prompt_source = local-fallback` thì rollback không giải quyết được gì: kiểm tra `LANGFUSE_*` trong `.env`
     và `Invoke-RestMethod http://127.0.0.1:8000/health` → `tracing_enabled`. Trong lúc chờ, service vẫn phục vụ
     được bằng template local nên chỉ cần ghi nhận và theo dõi, không rollback mù.
- Owner: **Nguyễn Thanh Bình (P3)** — giữ [app/prompt_management.py](../app/prompt_management.py) và
  `scripts/seed_prompts.py`, người duy nhất promote/rollback được label `production`. Escalate:
  **Trịnh Hải Đăng (P4)** nếu cần chỉnh lại ngưỡng hoặc cửa sổ của alert.
