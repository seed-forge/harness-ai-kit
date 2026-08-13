from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path


def _load_replies(path: Path) -> dict[int, str]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("Replies JSON must be an object: {\"comment_id\": \"reply text\"}")
    out: dict[int, str] = {}
    for k, v in raw.items():
        try:
            cid = int(k)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Invalid comment id key: {k}") from e
        text = (v or "").strip() if isinstance(v, str) else ""
        if text:
            out[cid] = text
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unpacked", required=True, help="Unpacked docx directory (contains word/document.xml)")
    ap.add_argument("--replies", required=True, help="Replies JSON mapping: {id: text}")
    ap.add_argument("--out-dir", default="outputs", help="Output directory (default: outputs)")
    ap.add_argument("--author", default="Claude", help="Reply author name")
    ap.add_argument("--initials", default="C", help="Reply author initials")
    ap.add_argument("--no-validate", action="store_true", help="Skip schema/redlining validation (not recommended)")
    args = ap.parse_args()

    base_unpacked = Path(args.unpacked).expanduser().resolve()
    if not base_unpacked.is_dir():
        raise SystemExit(f"Unpacked dir not found: {base_unpacked}")

    replies_path = Path(args.replies).expanduser().resolve()
    if not replies_path.exists():
        raise SystemExit(f"Replies JSON not found: {replies_path}")

    replies = _load_replies(replies_path)
    if not replies:
        raise SystemExit("No non-empty replies found in replies JSON.")

    # Use bundled docx skill (sibling folder) for Document + pack
    skill_root = Path(__file__).resolve().parents[2]
    docx_root = skill_root / "docx"
    sys.path.insert(0, str(docx_root))
    from scripts.document import Document  # noqa: E402
    from ooxml.scripts.pack import pack_document  # noqa: E402

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = Path(args.out_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    out_unpacked = out_root / f"{base_unpacked.name}_replied_{stamp}"
    out_docx = out_root / f"{base_unpacked.name}_批注已回复_{stamp}.docx"

    doc = Document(base_unpacked, author=args.author, initials=args.initials, track_revisions=False)
    for cid in sorted(replies):
        doc.reply_to_comment(parent_comment_id=cid, text=replies[cid])

    doc.save(destination=out_unpacked, validate=not args.no_validate)
    pack_document(out_unpacked, out_docx, validate=False)

    print(f"Unpacked written: {out_unpacked}")
    print(f"DOCX written: {out_docx}")


if __name__ == "__main__":
    main()
