# Evidence: Prompt v2 — label `candidate`

## Cách lấy

```bash
python scripts/seed_prompts.py init
python scripts/seed_prompts.py list
```

Output mẫu:

```
=== Prompt Versions ===
v1 | label: baseline, production | created: 2026-08-11
v2 | label: candidate | created: 2026-08-11
```

## Thay đổi so với v1

v2 chỉ thêm ràng buộc format (tối đa 3 câu), giữ nguyên 3 biến bắt buộc:
- `{{feature}}`
- `{{docs}}`
- `{{message}}`

Đúng yêu cầu "một thay đổi nhỏ" của `docs/PROMPT_VERSIONING.md`.

## Trên Langfuse UI

1. Mở Langfuse → Prompts → `day13-chat`
2. Chọn version v2
3. Chụp màn hình hiển thị: label `candidate`, content prompt

## Placeholder

Ảnh: `submission/evidence/06-prompt-v2.png`
