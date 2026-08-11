# Evidence: Rollback — TRƯỚC khi rollback (v2 đang là production)

## Cách lấy

```bash
python scripts/seed_prompts.py promote --version 2
python scripts/seed_prompts.py list
```

Output mẫu:

```
=== Promote ===
Trước: v1=baseline,production | v2=candidate
Sau: v1=baseline | v2=production,candidate
```

Chụp màn hình **output này** làm bằng chứng trước khi rollback.

## Trên Langfuse UI

1. Mở Langfuse → Prompts → `day13-chat`
2. Xác nhận version hiện tại đang là **v2** với label `production`

## Placeholder

Ảnh: `submission/evidence/07-rollback-before.png`
