"""格式化输出模块：支持 table 和 json 两种输出格式。"""
import json
import sys
from typing import Any


def print_table(headers: list[str], rows: list[list[str]], title: str = "") -> None:
    """以表格形式输出。"""
    if title:
        print(f"\n{title}")
        print("-" * len(title))

    if not rows:
        print("(无数据)")
        return

    # 计算列宽
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # 打印表头
    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("  ".join("-" * w for w in col_widths))

    # 打印数据行
    for row in rows:
        print("  ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))


def print_json(data: Any) -> None:
    """以 JSON 格式输出。"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def print_kv(data: dict, title: str = "") -> None:
    """以 key-value 形式输出。"""
    if title:
        print(f"\n{title}")
        print("-" * len(title))
    max_key = max(len(k) for k in data) if data else 0
    for key, val in data.items():
        print(f"  {key.ljust(max_key)}  {val}")


def print_ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def print_warn(msg: str) -> None:
    print(f"  [WARN] {msg}", file=sys.stderr)


def print_err(msg: str) -> None:
    print(f"  [ERROR] {msg}", file=sys.stderr)
