from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


BAD_PREFIXES = [
    "您好",
    "老师您好",
    "毅老师您好",
    "老师你",
    "老师您",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replies", required=True, help="Replies JSON mapping: {id: text}")
    args = ap.parse_args()

    path = Path(args.replies).expanduser().resolve()
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise SystemExit("Replies JSON must be an object.")

    errors: list[str] = []
    for k, v in raw.items():
        text = (v or "").strip() if isinstance(v, str) else ""
        if not text:
            continue
        first_line = text.splitlines()[0].strip()
        for pref in BAD_PREFIXES:
            if first_line.startswith(pref):
                errors.append(f"id={k}: reply starts with banned prefix: {pref!r}")
                break
        if re.search(r"后续(再|会)?补充", text) and len(text) < 40:
            errors.append(f"id={k}: reply too vague (mentions 补充 but too short)")

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        sys.exit(2)

    print("[OK] replies lint passed")


if __name__ == "__main__":
    main()
