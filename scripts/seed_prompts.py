"""Quản lý prompt version trên Langfuse cho Checkpoint 2 (vai trò P3).

Làm đúng các bước trong docs/PROMPT_VERSIONING.md bằng SDK thay vì click tay, để
thao tác lặp lại được và output in ra dùng thẳng làm evidence.

    python scripts/seed_prompts.py init                 # tạo v1 (baseline+production) và v2 (candidate)
    python scripts/seed_prompts.py list                 # in version + label hiện tại
    python scripts/seed_prompts.py promote --version 2  # chuyển label production sang v2
    python scripts/seed_prompts.py rollback             # trả production về v1

Script chỉ gọi API thật; không có key Langfuse thì dừng và báo lỗi, không giả lập.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE
from app.tracing import get_langfuse_client, tracing_enabled

# v2 giữ nguyên ba biến bắt buộc, chỉ đổi format/độ dài câu trả lời như đề bài yêu cầu.
CANDIDATE_PROMPT_TEMPLATE = (
    f"{DEFAULT_PROMPT_TEMPLATE}\n\n"
    "Trả lời trong tối đa 3 câu. Nêu rõ tín hiệu cần kiểm tra trước khi kết luận."
)


def _require_langfuse() -> None:
    if tracing_enabled():
        return
    print("Chưa cấu hình được Langfuse. Kiểm tra .env:")
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        state = "đã đặt" if os.getenv(key) else "THIẾU"
        print(f"  - {key}: {state}")
    print("Không có key thì không tạo được prompt version thật, cũng không có evidence.")
    sys.exit(1)


def _prompt_name() -> str:
    return os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")


def _print_versions(client, name: str, header: str) -> None:
    print(f"\n{header}")
    try:
        listing = client.api.prompts.list(name=name)
    except Exception as exc:
        print(f"  Không đọc được danh sách prompt: {type(exc).__name__}: {exc}")
        return

    entries = getattr(listing, "data", None) or []
    if not entries:
        print(f"  Chưa có prompt nào tên '{name}'.")
        return

    for entry in entries:
        versions = getattr(entry, "versions", None) or []
        labels = getattr(entry, "labels", None) or []
        print(f"  {getattr(entry, 'name', name)}: versions={list(versions)} labels={list(labels)}")

    # Label nằm trên từng version, nên đọc lại từng version để biết ai đang giữ label nào.
    for version in sorted({v for e in entries for v in (getattr(e, "versions", None) or [])}):
        try:
            detail = client.api.prompts.get(prompt_name=name, version=int(version))
        except Exception as exc:
            print(f"  v{version}: không đọc được ({type(exc).__name__})")
            continue
        detail_labels = getattr(detail, "labels", None) or []
        print(f"  v{version}: labels={list(detail_labels)}")


def cmd_init(client, name: str) -> int:
    baseline = client.create_prompt(
        name=name,
        prompt=DEFAULT_PROMPT_TEMPLATE,
        type="text",
        labels=["baseline", "production"],
        commit_message="v1 baseline - template goc cua lab",
    )
    print(f"Đã tạo v{baseline.version} với label baseline + production")

    candidate = client.create_prompt(
        name=name,
        prompt=CANDIDATE_PROMPT_TEMPLATE,
        type="text",
        labels=["candidate"],
        commit_message="v2 candidate - gioi han 3 cau, yeu cau neu tin hieu kiem tra",
    )
    print(f"Đã tạo v{candidate.version} với label candidate")

    _print_versions(client, name, "Trạng thái sau khi init:")
    print(
        "\nBước tiếp theo: chạy cùng một input với LANGFUSE_PROMPT_LABEL=baseline rồi "
        "=candidate để lấy 2 trace ID."
    )
    return 0


def cmd_list(client, name: str) -> int:
    _print_versions(client, name, f"Prompt '{name}' hiện tại:")
    return 0


def _move_production(client, name: str, version: int, action: str) -> int:
    _print_versions(client, name, f"TRƯỚC khi {action} production -> v{version}:")

    # Label là duy nhất trên toàn bộ version: gán production cho version mới sẽ tự gỡ
    # khỏi version cũ. Phải gửi kèm label sẵn có của version đích, nếu không sẽ mất chúng.
    try:
        detail = client.api.prompts.get(prompt_name=name, version=version)
        existing = [str(label) for label in (getattr(detail, "labels", None) or [])]
    except Exception as exc:
        print(f"Không đọc được v{version}: {type(exc).__name__}: {exc}")
        return 1

    new_labels = sorted(set(existing) | {"production"})
    client.update_prompt(name=name, version=version, new_labels=new_labels)
    print(f"\nĐã {action}: v{version} giờ giữ label {new_labels}")

    _print_versions(client, name, f"SAU khi {action} production -> v{version}:")
    print(
        "\nLưu toàn bộ output này vào submission/evidence/ làm bằng chứng đổi label. "
        "Chạy thêm một request để có trace gắn version mới."
    )
    return 0


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Tạo v1 (baseline+production) và v2 (candidate)")
    sub.add_parser("list", help="In version và label hiện tại")

    promote = sub.add_parser("promote", help="Chuyển label production sang một version")
    promote.add_argument("--version", type=int, default=2)

    rollback = sub.add_parser("rollback", help="Trả label production về version cũ")
    rollback.add_argument("--version", type=int, default=1)

    args = parser.parse_args()

    _require_langfuse()
    client = get_langfuse_client()
    name = _prompt_name()

    if args.command == "init":
        return cmd_init(client, name)
    if args.command == "list":
        return cmd_list(client, name)
    if args.command == "promote":
        return _move_production(client, name, args.version, "promote")
    return _move_production(client, name, args.version, "rollback")


if __name__ == "__main__":
    sys.exit(main())
