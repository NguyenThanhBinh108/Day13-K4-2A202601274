# Evidence: Log chứng minh root cause

Số liệu trong file này lấy từ run thật ngày 2026-08-11, nguồn `data/logs.jsonl`
(141 bản ghi, 71 correlation ID). Không có giá trị nào được điền tay.

## Challenge

- Challenge ID: `day13-k4-observability-v1` (cohort K4)
- Incident: `rag_slow`, seed `1304`
- Feature bị ảnh hưởng: `monitoring`
- `latency_threshold_ms` của challenge: **2000ms**

## Correlation ID dùng làm bằng chứng

Request chậm nhất trong 5 query chính thức: **`req-ba5d3bd8`** — `latency_ms = 2651`.

## Hai dòng log thật (copy nguyên văn từ `data/logs.jsonl`)

```json
{"service": "api", "payload": {"message_preview": "Which signal should be checked after latency increases?"}, "event": "request_received", "session_id": "k4-challenge-s04", "env": "dev", "feature": "monitoring", "user_id_hash": "6b83e7_4c0874", "correlation_id": "req-ba5d3bd8", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T10:12:25.980094Z"}
{"service": "api", "latency_ms": 2651, "tokens_in": 36, "tokens_out": 153, "cost_usd": 0.002403, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "session_id": "k4-challenge-s04", "env": "dev", "feature": "monitoring", "user_id_hash": "6b83e7_4c0874", "correlation_id": "req-ba5d3bd8", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T10:12:28.632025Z"}
```

Lệnh tái hiện:

```bash
python -c "import json;[print(l.strip()) for l in open('data/logs.jsonl',encoding='utf-8') if 'req-ba5d3bd8' in l]"
```

## Log nói lên điều gì

| Quan sát | Giá trị thật | Ý nghĩa |
|---|---|---|
| Khoảng cách `ts` giữa hai dòng | 10:12:25.980094Z → 10:12:28.632025Z ≈ **2,652s** | Khớp `latency_ms = 2651`, xác nhận thời gian bị đốt **bên trong** một request, không phải do xếp hàng |
| `event` cuối | `response_sent` | Request **thành công**, không phải lỗi |
| `request_failed` cho ID này | không có | Không phải sự cố dạng lỗi |
| `tokens_in` / `tokens_out` | 36 / 153 | Nằm trong dải bình thường của baseline — LLM **không** làm gì khác thường |
| `cost_usd` | 0.002403 | Không tăng, loại trừ giả thuyết đổi model hay prompt phình to |
| `quality_score` | 0.9 | Không giảm — chất lượng trả lời không bị ảnh hưởng |

Kết luận rút ra **chỉ từ log**: request bị chậm nhưng vẫn thành công, số token và chi phí
không đổi. Nghĩa là độ trễ nằm ở một bước **không tiêu tốn token** — tức là trước hoặc sau
lời gọi LLM, chứ không phải ở chính lời gọi LLM.

## Đối chiếu baseline

| | Baseline (64 request, incident tắt) | Challenge (5 request, `rag_slow` bật) |
|---|---|---|
| p50 | 150ms | 2651ms |
| p95 | 150ms | 2651ms |
| p99 | 151ms | 2651ms |
| error rate | 0% | 0% |

Chênh lệch **+2500ms gần như cố định** ở mọi request, không phải phân phối đuôi dài.
Độ trễ cộng thêm là hằng số, gợi ý một `sleep` cứng chứ không phải nghẽn tài nguyên.

## Đính chính một nhầm lẫn dễ mắc

`latency_ms = 2651` **vượt ngưỡng challenge 2000ms** nhưng **không vượt SLO p95 3000ms**
trong `config/slo.yaml`. Cả 5/5 request challenge đều vượt 2000ms, **0/5** vượt 3000ms.
Nói "vượt SLO" là sai; alert bắt được sự cố này là nhờ ngưỡng challenge, còn SLO thì chưa thủng.

## Ảnh

`submission/evidence/17-log-root-cause.png` — *(chụp màn hình terminal khi chạy lệnh tái hiện ở trên)*
