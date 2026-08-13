from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import xml.etree.ElementTree as ET


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
}


def qn(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


@dataclass(frozen=True)
class CommentRecord:
    comment_id: int
    author: str
    date: str
    initials: str
    para_id: str
    text: str
    anchor_text: str
    anchor_paragraph_text: str
    anchor_paragraph_id: str
    is_reply: bool
    parent_comment_id: int | None
    has_reply: bool
    reply_count: int


def _clean_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _paragraph_text(p: ET.Element) -> str:
    parts: list[str] = []
    for t in p.findall(".//w:t", NS):
        if t.text:
            parts.append(t.text)
    return "".join(parts).strip()


def _load_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def _find_parent_paragraph(parent_map: dict[ET.Element, ET.Element], el: ET.Element) -> ET.Element | None:
    p = parent_map.get(el)
    while p is not None and p.tag != qn("w", "p"):
        p = parent_map.get(p)
    return p


def _comment_marker_indices(p: ET.Element, cid: int) -> tuple[int | None, int | None, int | None]:
    children = list(p)

    def is_start(el: ET.Element) -> bool:
        return el.tag == qn("w", "commentRangeStart") and el.attrib.get(qn("w", "id")) == str(cid)

    def is_end(el: ET.Element) -> bool:
        return el.tag == qn("w", "commentRangeEnd") and el.attrib.get(qn("w", "id")) == str(cid)

    def is_ref_run(el: ET.Element) -> bool:
        if el.tag != qn("w", "r"):
            return False
        cref = el.find(".//w:commentReference", NS)
        return cref is not None and cref.attrib.get(qn("w", "id")) == str(cid)

    start_idx = next((i for i, ch in enumerate(children) if is_start(ch)), None)
    end_idx = next((i for i, ch in enumerate(children) if is_end(ch)), None)
    ref_idx = next((i for i, ch in enumerate(children) if is_ref_run(ch)), None)
    return start_idx, end_idx, ref_idx


def _extract_text_between_children(p: ET.Element, start_idx: int, end_idx: int) -> str:
    children = list(p)
    start_idx = max(0, min(start_idx, len(children)))
    end_idx = max(0, min(end_idx, len(children)))
    if end_idx < start_idx:
        start_idx, end_idx = end_idx, start_idx

    parts: list[str] = []
    for ch in children[start_idx:end_idx]:
        for t in ch.findall(".//w:t", NS):
            if t.text:
                parts.append(t.text)
    return "".join(parts).strip()


def extract_anchor_context(document_xml: Path, cid: int) -> tuple[str, str, str]:
    """
    Return (anchor_text, containing_paragraph_text, containing_paragraph_id).
    Best-effort extraction from w:commentRangeStart/End markers.
    """
    tree = ET.parse(document_xml)
    root = tree.getroot()
    parent_map = _load_parent_map(root)

    start = root.find(f'.//w:commentRangeStart[@w:id="{cid}"]', NS)
    end = root.find(f'.//w:commentRangeEnd[@w:id="{cid}"]', NS)
    if start is None:
        return "", "", ""

    start_p = _find_parent_paragraph(parent_map, start)
    end_p = _find_parent_paragraph(parent_map, end) if end is not None else None
    if start_p is None:
        return "", "", ""

    start_para_id = start_p.attrib.get(qn("w14", "paraId"), "")

    if end_p is None or end_p == start_p:
        s_idx, e_idx, r_idx = _comment_marker_indices(start_p, cid)
        if s_idx is None:
            return "", _clean_ws(_paragraph_text(start_p)), start_para_id
        if e_idx is None:
            e_idx = r_idx if r_idx is not None else s_idx
        selected = _extract_text_between_children(start_p, s_idx + 1, e_idx)
        return _clean_ws(selected), _clean_ws(_paragraph_text(start_p)), start_para_id

    # Multi-paragraph span: collect from start_p (after start) to end_p (before end)
    paragraphs = list(root.findall(".//w:p", NS))
    try:
        sp_i = paragraphs.index(start_p)
        ep_i = paragraphs.index(end_p)
    except ValueError:
        return "", _clean_ws(_paragraph_text(start_p)), start_para_id

    if ep_i < sp_i:
        sp_i, ep_i = ep_i, sp_i

    selected_parts: list[str] = []
    for i in range(sp_i, ep_i + 1):
        p = paragraphs[i]
        children = list(p)
        s_idx, e_idx, r_idx = _comment_marker_indices(p, cid)

        if p is start_p:
            if s_idx is None:
                continue
            selected_parts.append(_extract_text_between_children(p, s_idx + 1, len(children)))
            continue
        if p is end_p:
            if e_idx is None:
                e_idx = r_idx if r_idx is not None else len(children)
            selected_parts.append(_extract_text_between_children(p, 0, e_idx))
            continue

        selected_parts.append(_paragraph_text(p))

    selected = _clean_ws(" ".join(x for x in selected_parts if x))
    return selected, _clean_ws(_paragraph_text(start_p)), start_para_id


def load_comments(comments_xml: Path) -> list[dict[str, Any]]:
    root = ET.parse(comments_xml).getroot()
    out: list[dict[str, Any]] = []
    for c in root.findall("w:comment", NS):
        cid_raw = c.attrib.get(qn("w", "id"), "")
        if not cid_raw.strip():
            continue
        cid = int(cid_raw)
        author = c.attrib.get(qn("w", "author"), "")
        date = c.attrib.get(qn("w", "date"), "")
        initials = c.attrib.get(qn("w", "initials"), "")

        first_p = c.find(".//w:p", NS)
        para_id = ""
        if first_p is not None:
            para_id = first_p.attrib.get(qn("w14", "paraId"), "")

        paras: list[str] = []
        for p in c.findall(".//w:p", NS):
            pt = "".join((t.text or "") for t in p.findall(".//w:t", NS))
            if pt.strip():
                paras.append(pt.strip())
        text = "\n".join(paras).strip()

        out.append(
            {
                "comment_id": cid,
                "author": author,
                "date": date,
                "initials": initials,
                "para_id": para_id,
                "text": text,
            }
        )

    out.sort(key=lambda x: x["comment_id"])
    return out


def load_threading(comments_extended_xml: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    """
    Returns:
      - child_para_id -> parent_para_id
      - parent_para_id -> [child_para_id, ...]
    """
    if not comments_extended_xml.exists():
        return {}, {}

    root = ET.parse(comments_extended_xml).getroot()
    child_to_parent: dict[str, str] = {}
    parent_to_children: dict[str, list[str]] = {}

    for ex in root.findall(".//w15:commentEx", NS):
        para_id = ex.attrib.get(qn("w15", "paraId"), "")
        parent_para_id = ex.attrib.get(qn("w15", "paraIdParent"), "")
        if para_id and parent_para_id:
            child_to_parent[para_id] = parent_para_id
            parent_to_children.setdefault(parent_para_id, []).append(para_id)

    return child_to_parent, parent_to_children


def unpack_docx(docx_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx_path) as zf:
        zf.extractall(out_dir)


def convert_doc_to_docx(doc_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                str(out_dir),
                str(doc_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as e:
        raise RuntimeError("未找到 soffice（LibreOffice）。请安装 LibreOffice 或先手动另存为 .docx。") from e
    except subprocess.CalledProcessError as e:
        msg = e.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(f"soffice 转换失败：{msg}") from e

    # LibreOffice outputs <stem>.docx in out_dir
    candidates = sorted(out_dir.glob(f"{doc_path.stem}*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError("soffice 已运行，但未在 out_dir 发现生成的 .docx 文件。")
    return candidates[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input .docx or .doc file path")
    ap.add_argument("--out-dir", default="outputs", help="Output directory (default: outputs)")
    ap.add_argument(
        "--mode",
        default="reply_unanswered",
        choices=["reply_unanswered", "reply_all"],
        help="Which root comments to include in replies todo template",
    )
    args = ap.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    out_root = Path(args.out_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    source_docx = in_path
    converted_from_doc = False
    if in_path.suffix.lower() == ".doc":
        converted_from_doc = True
        convert_dir = out_root / f"{in_path.stem}_converted_{stamp}"
        source_docx = convert_doc_to_docx(in_path, convert_dir)

    if source_docx.suffix.lower() != ".docx":
        raise SystemExit(f"Unsupported input: {in_path} (need .docx or .doc)")

    unpacked_dir = out_root / f"{source_docx.stem}_unpacked_{stamp}"
    unpack_docx(source_docx, unpacked_dir)

    word_dir = unpacked_dir / "word"
    comments_xml = word_dir / "comments.xml"
    document_xml = word_dir / "document.xml"
    comments_extended_xml = word_dir / "commentsExtended.xml"

    if not comments_xml.exists():
        # No comments in this file
        ctx = {
            "input": str(in_path),
            "source_docx": str(source_docx),
            "converted_from_doc": converted_from_doc,
            "unpacked_dir": str(unpacked_dir),
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "comments": [],
        }
        ctx_path = out_root / f"{source_docx.stem}_comment_context_{stamp}.json"
        ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = out_root / f"{source_docx.stem}_批注定位与上下文_{stamp}.md"
        md_path.write_text("# 批注定位与上下文\n\n- comments: 0\n", encoding="utf-8")
        print(f"Wrote: {ctx_path}")
        print(f"Wrote: {md_path}")
        return

    comments = load_comments(comments_xml)
    child_to_parent_para, parent_to_children_para = load_threading(comments_extended_xml)

    para_to_cid = {c["para_id"]: c["comment_id"] for c in comments if c.get("para_id")}
    reply_para_ids = set(child_to_parent_para.keys())
    parent_para_ids = set(parent_to_children_para.keys())

    records: list[CommentRecord] = []
    for c in comments:
        cid = int(c["comment_id"])
        para_id = str(c.get("para_id") or "")
        anchor_text, para_text, anchor_para_id = ("", "", "")
        if document_xml.exists():
            anchor_text, para_text, anchor_para_id = extract_anchor_context(document_xml, cid)

        is_reply = bool(para_id and para_id in reply_para_ids)
        parent_comment_id: int | None = None
        if is_reply and para_id:
            parent_para = child_to_parent_para.get(para_id, "")
            parent_comment_id = para_to_cid.get(parent_para)

        reply_count = 0
        has_reply = False
        if para_id and para_id in parent_para_ids:
            reply_count = len(parent_to_children_para.get(para_id, []))
            has_reply = reply_count > 0

        records.append(
            CommentRecord(
                comment_id=cid,
                author=str(c.get("author") or ""),
                date=str(c.get("date") or ""),
                initials=str(c.get("initials") or ""),
                para_id=para_id,
                text=str(c.get("text") or "").strip(),
                anchor_text=_clean_ws(anchor_text),
                anchor_paragraph_text=_clean_ws(para_text),
                anchor_paragraph_id=str(anchor_para_id or ""),
                is_reply=is_reply,
                parent_comment_id=parent_comment_id,
                has_reply=has_reply,
                reply_count=reply_count,
            )
        )

    ctx = {
        "input": str(in_path),
        "source_docx": str(source_docx),
        "converted_from_doc": converted_from_doc,
        "unpacked_dir": str(unpacked_dir),
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "comments": [asdict(r) for r in records],
    }

    ctx_path = out_root / f"{source_docx.stem}_comment_context_{stamp}.json"
    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")

    # replies todo (root comments only)
    todo: dict[str, str] = {}
    for r in records:
        if r.is_reply:
            continue
        if args.mode == "reply_unanswered" and r.has_reply:
            continue
        todo[str(r.comment_id)] = ""
    todo_path = out_root / f"{source_docx.stem}_replies_todo_{stamp}.json"
    todo_path.write_text(json.dumps(todo, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines: list[str] = []
    md_lines.append(f"# {source_docx.name} — 批注定位与上下文")
    md_lines.append("")
    md_lines.append(f"- generated_at: {ctx['generated_at']}")
    md_lines.append(f"- unpacked_dir: {unpacked_dir}")
    md_lines.append(f"- comments_total: {len(records)}")
    md_lines.append(f"- root_comments: {len([r for r in records if not r.is_reply])}")
    md_lines.append(f"- reply_comments: {len([r for r in records if r.is_reply])}")
    md_lines.append("")
    md_lines.append(f"- replies_todo: {todo_path.name}")
    md_lines.append("")

    for r in records:
        md_lines.append(f"## id={r.comment_id}{' (reply)' if r.is_reply else ''}")
        md_lines.append("")
        md_lines.append(f"- author: {r.author}")
        md_lines.append(f"- date: {r.date}")
        if r.is_reply:
            md_lines.append(f"- parent_comment_id: {r.parent_comment_id}")
        else:
            md_lines.append(f"- has_reply: {int(r.has_reply)} (reply_count={r.reply_count})")
        if r.anchor_paragraph_id:
            md_lines.append(f"- anchor_paragraph_id: {r.anchor_paragraph_id}")
        md_lines.append("")
        md_lines.append("**批注内容**")
        md_lines.append("")
        md_lines.append(r.text if r.text else "(空)")
        md_lines.append("")
        md_lines.append("**标注文本(尽量提取)**")
        md_lines.append("")
        md_lines.append(r.anchor_text if r.anchor_text else "(未能提取到明确的标注文本)")
        md_lines.append("")
        md_lines.append("**所在段落(合并文本)**")
        md_lines.append("")
        md_lines.append(r.anchor_paragraph_text if r.anchor_paragraph_text else "(未定位到段落)")
        md_lines.append("")

    md_path = out_root / f"{source_docx.stem}_批注定位与上下文_{stamp}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Wrote: {ctx_path}")
    print(f"Wrote: {todo_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()

