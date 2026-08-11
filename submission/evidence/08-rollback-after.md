# Evidence: Rollback — SAU khi rollback (v1 trở lại production)

## Cách lấy

```bash
python scripts/seed_prompts.py rollback
python scripts/seed_prompts.py list
```

Output mẫu:

```
=== Rollback ===
Trước: v1=baseline | v2=production,candidate
Sau: v1=baseline,production | v2=candidate
```

Chụp màn hình **output này** làm bằng chứng sau khi rollback.

## Trên Langfuse UI

1. Mở Langfuse → Prompts → `day13-chat`
2. Xác nhận version hiện tại đang là **v1** với label `production`

## Placeholder

Ảnh: `submission/evidence/08-rollback-after.png`
