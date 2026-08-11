# Evidence: Log chứng minh root cause

Số liệu trong file này lấy từ run thật ngày 2026-08-11, nguồn `data/logs.jsonl`
(133 bản ghi, 67 correlation ID). Không có giá trị nào được điền tay.

## Challenge

- Challenge ID: `day13-k4-observability-v1` (cohort K4)
- Incident: `rag_slow`, seed `1304`
- Feature bị ảnh hưởng: `monitoring`
- `latency_threshold_ms` của challenge: **2000ms**

## Correlation ID dùng làm bằng chứng

Request chậm nhất trong 5 query chính thức: **`req-245d336c`** — `latency_ms = 2651`.

## Hai dòng log thật (copy nguyên văn từ `data/logs.jsonl`)

```json
{"service": "api", "payload": {"message_preview": "Describe how to prove a slow span is the root cause."}, "event": "request_received", "user_id_hash": "0c0433_5fe098", "feature": "monitoring", "correlation_id": "req-245d336c", "session_id": "k4-challenge-s05", "model": "claude-sonnet-4-5", "env": "dev", "level": "info", "ts": "2026-08-11T09:39:05.299835Z"}
{"service": "api", "latency_ms": 2651, "tokens_in": 35, "tokens_out": 92, "cost_usd": 0.001485, "quality_score": 0.8, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "user_id_hash": "0c0433_5fe098", "feature": "monitoring", "correlation_id": "req-245d336c", "session_id": "k4-challenge-s05", "model": "claude-sonnet-4-5", "env": "dev", "level": "info", "ts": "2026-08-11T09:39:07.951564Z"}
```

Lệnh tái hiện:

```bash
python -c "import json;[print(l.strip()) for l in open('data/logs.jsonl',encoding='utf-8') if 'req-245d336c' in l]"
```

## Log nói lên điều gì

| Quan sát | Giá trị thật | Ý nghĩa |
|---|---|---|
| Khoảng cách `ts` giữa hai dòng | 09:39:05.299835Z → 09:39:07.951564Z ≈ **2,652s** | Khớp `latency_ms = 2651`, xác nhận thời gian bị đốt **bên trong** một request, không phải do xếp hàng |
| `event` cuối | `response_sent` | Request **thành công**, không phải lỗi |
| `request_failed` cho ID này | không có | Không phải sự cố dạng lỗi |
| `tokens_in` / `tokens_out` | 35 / 92 | Nằm trong dải bình thường của baseline — LLM **không** làm gì khác thường |
| `cost_usd` | 0.001485 | Không tăng, loại trừ giả thuyết đổi model hay prompt phình to |
| `quality_score` | 0.8 | Không giảm — chất lượng trả lời không bị ảnh hưởng |

Kết luận rút ra **chỉ từ log**: request bị chậm nhưng vẫn thành công, số token và chi phí
không đổi. Nghĩa là độ trễ nằm ở một bước **không tiêu tốn token** — tức là trước hoặc sau
lời gọi LLM, chứ không phải ở chính lời gọi LLM.

## Đối chiếu baseline

| | Baseline (60 request, incident tắt) | Challenge (5 request, `rag_slow` bật) |
|---|---|---|
| p50 | 150ms | 2650ms |
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
