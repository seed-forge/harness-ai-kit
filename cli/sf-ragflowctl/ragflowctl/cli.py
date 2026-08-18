from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path

from . import __version__
from .api_client import RagflowClient, RagflowError
from .config import get_config

DEFAULT_BASE_URL = "http://127.0.0.1:9380"


def _emit(payload: dict, as_json: bool) -> int:
    ok = payload.get("ok", True)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        cmd = payload.get("command", "?")
        if ok:
            extra = payload.get("summary")
            print(f"{cmd}: ok" + (f" | {extra}" if extra else ""))
            data = payload.get("data")
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        print("  " + " ".join(f"{k}={v}" for k, v in row.items() if v not in (None, "")))
                    else:
                        print(f"  {row}")
            elif isinstance(data, dict):
                for k, v in data.items():
                    print(f"  {k}={v}")
        else:
            print(f"{cmd}: failed | {payload.get('error', '')}")
    return 0 if ok else 1


def _resolve(cfg: dict, args: argparse.Namespace) -> tuple[str, str, int]:
    base_url = (args.base_url or cfg.get("base_url") or os.environ.get("RAGFLOW_BASE_URL")
                or DEFAULT_BASE_URL).rstrip("/")
    api_key = args.api_key or cfg.get("api_key") or os.environ.get("RAGFLOW_API_KEY") or ""
    timeout = int(args.timeout or cfg.get("timeout") or 60)
    return base_url, api_key, timeout


def _client(cfg: dict, args: argparse.Namespace) -> RagflowClient:
    base_url, api_key, timeout = _resolve(cfg, args)
    return RagflowClient(base_url, api_key, timeout=timeout)


def _dataset_id(client: RagflowClient, ref: str) -> str:
    """Accept a dataset id or name; resolve name → id."""
    ds = client.dataset_find(ref)
    if ds:
        return ds["id"]
    return ref  # assume it is already an id


def _confirm_or_abort(args: argparse.Namespace, what: str) -> bool:
    """HD (human-decision) gate for destructive ops.

    ``--yes`` bypasses for scripts; otherwise requires interactive 'yes'.
    Non-interactive stdin (EOF) fails closed.
    """
    if getattr(args, "yes", False):
        return True
    print(f"[HD] about to delete {what}. Type 'yes' to confirm: ", end="", file=sys.stderr, flush=True)
    try:
        return input().strip().lower() == "yes"
    except EOFError:
        return False


def _load_dsl_arg(raw: str) -> dict:
    """Load DSL JSON from @path or inline string."""
    text = Path(raw[1:]).read_text(encoding="utf-8") if raw.startswith("@") else raw
    return json.loads(text)


def _chat_id(client: RagflowClient, ref: str) -> str:
    """Accept a chat assistant id or name; resolve name → id.

    Pre-check matters: POST /chat/completions returns a misleading
    ``code=109 No authorization`` when chat_id is not a chat owned by this
    token (including nonexistent ids and dataset ids passed by mistake).
    """
    for c in client.chat_list():
        if ref in (c.get("id"), c.get("name")):
            return c["id"]
    raise RagflowError(
        f"chat '{ref}' not found or not owned by this token (run `chat list`; "
        f"note --chat wants a chat assistant id/name, NOT a dataset id)"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ragflowctl", description="RAGFlow ops CLI (datasets, documents, ingest, retrieval).")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--profile", default="default")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--version", "-V", action="version", version=f"ragflowctl {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Authenticated health check (lists datasets).")
    sub.add_parser("probe", help="Unauthenticated reachability probe.")

    cfg = sub.add_parser("config", help="Inspect effective config.")
    cfg_sub = cfg.add_subparsers(dest="config_command", required=True)
    cfg_sub.add_parser("show")
    cfg_get = cfg_sub.add_parser("get")
    cfg_get.add_argument("key")

    ds = sub.add_parser("dataset", help="Manage knowledge bases (datasets).")
    ds_sub = ds.add_subparsers(dest="dataset_command", required=True)
    ds_list = ds_sub.add_parser("list")
    ds_list.add_argument("--name")
    ds_create = ds_sub.add_parser("create")
    ds_create.add_argument("--name", required=True)
    ds_create.add_argument("--embedding-model")
    ds_create.add_argument("--chunk-method", default="naive")
    ds_get = ds_sub.add_parser("get")
    ds_get.add_argument("--name", required=True)
    ds_se = ds_sub.add_parser("set-embedding", help="Rebind dataset embedding model reference (same weights, no re-parse).")
    ds_se.add_argument("--dataset", required=True, help="dataset id or name")
    ds_se.add_argument("--model", required=True, help="e.g. bge-m3@newapi@OpenAI-API-Compatible")
    ds_rm = ds_sub.add_parser("rm", help="Delete dataset(s) by id or name (comma-separated).")
    ds_rm.add_argument("--dataset", required=True)
    ds_rm.add_argument("--yes", action="store_true", help="skip HD interactive confirmation")

    doc = sub.add_parser("document", help="Manage documents in a dataset.")
    doc_sub = doc.add_subparsers(dest="document_command", required=True)
    doc_list = doc_sub.add_parser("list")
    doc_list.add_argument("--dataset", required=True, help="dataset id or name")
    doc_up = doc_sub.add_parser("upload")
    doc_up.add_argument("--dataset", required=True)
    doc_up.add_argument("files", nargs="+")
    doc_parse = doc_sub.add_parser("parse")
    doc_parse.add_argument("--dataset", required=True)
    doc_parse.add_argument("--doc", action="append", default=[], help="document id (repeatable)")
    doc_parse.add_argument("--all", action="store_true", help="parse all docs in dataset")
    doc_del = doc_sub.add_parser("delete", help="Delete documents by id / name pattern / failed / all (destructive).")
    doc_del.add_argument("--dataset", required=True, help="dataset id or name")
    doc_del.add_argument("--doc", action="append", default=[], help="document id (repeatable)")
    doc_del.add_argument("--name", help="fnmatch pattern on document name, e.g. '*.md' or an exact name")
    doc_del.add_argument("--failed", action="store_true", help="select all docs with run=FAIL")
    doc_del.add_argument("--all", action="store_true", help="select all docs in dataset (destructive)")
    doc_del.add_argument("--yes", action="store_true", help="skip HD interactive confirmation")

    ing = sub.add_parser("ingest", help="High-level: (create) dataset + upload a dir + parse.")
    ing.add_argument("--dataset", required=True, help="dataset name")
    ing.add_argument("--dir", required=True, help="directory of files to upload")
    ing.add_argument("--glob", default="*", help="filename glob within --dir (recursive)")
    ing.add_argument("--create", action="store_true", help="create dataset if missing")
    ing.add_argument("--embedding-model")
    ing.add_argument("--no-parse", action="store_true", help="upload only, skip parse trigger")

    ret = sub.add_parser("retrieval", help="Retrieval test against a dataset.")
    ret.add_argument("--dataset", required=True, help="dataset id or name (repeatable via comma)")
    ret.add_argument("--question", required=True)
    ret.add_argument("--top-k", type=int, default=8)

    llm = sub.add_parser("llm", help="Model provider governance (v0.26 provider/models API).")
    llm_sub = llm.add_subparsers(dest="llm_command", required=True)
    llm_sub.add_parser("providers", help="List tenant-configured providers.")
    llm_sub.add_parser("factories", help="List system-available provider factories.")
    llm_verify = llm_sub.add_parser("verify", help="Verify provider api key/connectivity.")
    llm_verify.add_argument("--provider", required=True)
    llm_verify.add_argument("--api-key", dest="provider_api_key", required=True)
    llm_verify.add_argument("--base-url", dest="provider_base_url", default="")
    llm_addi = llm_sub.add_parser("add-instance", help="Add provider (if missing) + create instance.")
    llm_addi.add_argument("--provider", required=True)
    llm_addi.add_argument("--name", required=True, help="instance name (not 'default')")
    llm_addi.add_argument("--api-key", dest="provider_api_key", required=True)
    llm_addi.add_argument("--base-url", dest="provider_base_url", default="")
    llm_addi.add_argument("--models", default="",
                          help="comma-separated name:type pairs verified at creation, e.g. mimo-v2.5-pro:chat,bge-m3:embedding")
    llm_addm = llm_sub.add_parser("add-model", help="Add a model to an instance.")
    llm_addm.add_argument("--provider", required=True)
    llm_addm.add_argument("--instance", required=True)
    llm_addm.add_argument("--name", required=True, help="model name, e.g. bge-m3")
    llm_addm.add_argument("--type", required=True,
                          help="chat|embedding|rerank|asr|vision|tts|ocr|image2text (asr/vision auto-mapped to internal types)")
    llm_addm.add_argument("--max-tokens", type=int, default=8192)
    llm_models = llm_sub.add_parser("models", help="List models configured on an instance.")
    llm_models.add_argument("--provider", required=True)
    llm_models.add_argument("--instance", required=True)
    llm_remote = llm_sub.add_parser("remote-models", help="List models fetchable from remote endpoint (auto-populate).")
    llm_remote.add_argument("--provider", required=True)
    llm_remote.add_argument("--api-key", dest="provider_api_key", default="")
    llm_remote.add_argument("--base-url", dest="provider_base_url", default="")
    llm_sub.add_parser("default", help="Show tenant default models.")
    llm_rm = llm_sub.add_parser("remove-provider", help="Delete a provider with all its instances/models.")
    llm_rm.add_argument("--provider", required=True)
    llm_setd = llm_sub.add_parser("set-default", help="Set tenant default model per type (repeat --type).")
    llm_setd.add_argument("--provider", required=True)
    llm_setd.add_argument("--instance", required=True)
    llm_setd.add_argument("--model", required=True)
    llm_setd.add_argument("--type", action="append", required=True,
                          help="model type; repeat for multiple, e.g. --type chat --type embedding")

    chat = sub.add_parser("chat", help="Dataset-backed chat assistants (知识库半径智能体).")
    chat_sub = chat.add_subparsers(dest="chat_command", required=True)
    chat_sub.add_parser("list")
    chat_create = chat_sub.add_parser("create")
    chat_create.add_argument("--name", required=True)
    chat_create.add_argument("--dataset", required=True, help="dataset id or name (comma-separated)")
    chat_create.add_argument("--llm-id", help="model@instance@provider; default = tenant chat model")
    chat_sessions = chat_sub.add_parser("sessions")
    chat_sessions.add_argument("--chat", required=True, help="chat assistant id or name")
    chat_ns = chat_sub.add_parser("new-session")
    chat_ns.add_argument("--chat", required=True)
    chat_ns.add_argument("--name")
    chat_ask = chat_sub.add_parser("ask", help="Ask assistant (non-streaming; auto session when --session omitted).")
    chat_ask.add_argument("--chat", required=True, help="chat id or name (NOT dataset id)")
    chat_ask.add_argument("--question", required=True)
    chat_ask.add_argument("--session")
    chat_del = chat_sub.add_parser("delete", help="Delete assistant(s) by id (comma-separated; HD gate).")
    chat_del.add_argument("--chat", required=True)
    chat_del.add_argument("--yes", action="store_true", help="skip HD interactive confirmation")

    agent = sub.add_parser("agent", help="Canvas agents (deep_research 等模板智能体).")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    agent_sub.add_parser("list")
    agent_sub.add_parser("templates", help="List builtin canvas templates (DSL included).")
    agent_create = agent_sub.add_parser("create")
    agent_create.add_argument("--title", required=True)
    agent_create.add_argument("--dsl", required=True, help="DSL JSON inline or @path")
    agent_create.add_argument("--canvas-type")
    agent_sessions = agent_sub.add_parser("sessions")
    agent_sessions.add_argument("--agent", required=True, help="agent id")
    agent_ns = agent_sub.add_parser("new-session")
    agent_ns.add_argument("--agent", required=True)
    agent_ask = agent_sub.add_parser("ask", help="Ask agent (non-streaming).")
    agent_ask.add_argument("--agent", required=True)
    agent_ask.add_argument("--question", required=True)
    agent_ask.add_argument("--session")
    agent_del = agent_sub.add_parser("delete", help="Delete agent(s) by id (comma-separated; HD gate).")
    agent_del.add_argument("--agent", required=True)
    agent_del.add_argument("--yes", action="store_true", help="skip HD interactive confirmation")

    graph = sub.add_parser("graph", help="GraphRAG / RAPTOR task triggers.")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)
    for gcmd, ghelp in (("run-graphrag", "Trigger GraphRAG build"),
                        ("trace-graphrag", "Trace GraphRAG task status"),
                        ("run-raptor", "Trigger RAPTOR processing"),
                        ("trace-raptor", "Trace RAPTOR task status")):
        gp = graph_sub.add_parser(gcmd, help=ghelp)
        gp.add_argument("--dataset", required=True, help="dataset id or name")

    chunk = sub.add_parser("chunk", help="Chunk-level operations (三级召回支撑).")
    chunk_sub = chunk.add_subparsers(dest="chunk_command", required=True)
    for ccmd, chelp in (("list", "List chunks of a document"),
                        ("add", "Add a chunk"),
                        ("update", "Update a chunk"),
                        ("expand", "Show chunk with +/-N neighbors context"),
                        ("delete", "Delete chunk(s) (HD gate)")):
        cp = chunk_sub.add_parser(ccmd, help=chelp)
        cp.add_argument("--dataset", required=True, help="dataset id or name")
        cp.add_argument("--doc", required=True, help="document id")
        if ccmd == "add":
            cp.add_argument("--content", required=True)
        if ccmd == "update":
            cp.add_argument("--chunk", required=True)
            cp.add_argument("--content", required=True)
        if ccmd == "expand":
            cp.add_argument("--chunk", required=True)
            cp.add_argument("--before", type=int, default=2)
            cp.add_argument("--after", type=int, default=2)
        if ccmd == "delete":
            cp.add_argument("--chunk", required=True, help="chunk id (comma-separated)")
            cp.add_argument("--yes", action="store_true", help="skip HD interactive confirmation")
    return parser


def _cmd_config(args: argparse.Namespace, cfg: dict) -> int:
    if args.config_command == "show":
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return 0
    value = cfg.get(args.key)
    print(f"{args.key} = {value}" if value is not None else f"[NOT FOUND] {args.key}")
    return 0


def _cmd_dataset(args: argparse.Namespace, client: RagflowClient) -> int:
    if args.dataset_command == "list":
        data = client.dataset_list(name=args.name)
        rows = [{"id": d.get("id"), "name": d.get("name"),
                 "docs": d.get("document_count"), "chunks": d.get("chunk_count")} for d in data]
        return _emit({"command": "dataset.list", "ok": True, "summary": f"{len(rows)} dataset(s)", "data": rows}, args.json)
    if args.dataset_command == "create":
        d = client.dataset_create(args.name, embedding_model=args.embedding_model, chunk_method=args.chunk_method)
        return _emit({"command": "dataset.create", "ok": True, "summary": f"id={d.get('id')}", "data": d}, args.json)
    if args.dataset_command == "get":
        d = client.dataset_find(args.name)
        return _emit({"command": "dataset.get", "ok": bool(d), "error": None if d else "not found", "data": d}, args.json)
    if args.dataset_command == "set-embedding":
        ds_id = _dataset_id(client, args.dataset)
        client.dataset_update(ds_id, {"embedding_model": args.model})
        return _emit({"command": "dataset.set-embedding", "ok": True,
                      "summary": f"{args.dataset} -> {args.model}"}, args.json)
    if args.dataset_command == "rm":
        ds_ids = [_dataset_id(client, r) for r in [x.strip() for x in args.dataset.split(",") if x.strip()]]
        if not _confirm_or_abort(args, f"{len(ds_ids)} dataset(s): {','.join(ds_ids)}"):
            return _emit({"command": "dataset.rm", "ok": False, "error": "aborted by HD gate (use --yes to skip)"}, args.json)
        client.dataset_delete(ds_ids)
        return _emit({"command": "dataset.rm", "ok": True, "summary": f"deleted {len(ds_ids)} dataset(s)"}, args.json)
    return 2


def _cmd_document(args: argparse.Namespace, client: RagflowClient) -> int:
    ds_id = _dataset_id(client, args.dataset)
    if args.document_command == "list":
        data = client.document_list(ds_id)
        docs = data.get("docs", data if isinstance(data, list) else [])
        rows = [{"id": d.get("id"), "name": d.get("name"), "run": d.get("run"),
                 "progress": d.get("progress"), "chunks": d.get("chunk_count")} for d in docs]
        return _emit({"command": "document.list", "ok": True, "summary": f"{len(rows)} doc(s)", "data": rows}, args.json)
    if args.document_command == "upload":
        files = []
        for f in args.files:
            p = Path(f)
            files.append((p.name, p.read_bytes()))
        data = client.document_upload(ds_id, files)
        return _emit({"command": "document.upload", "ok": True, "summary": f"{len(data)} uploaded", "data": data}, args.json)
    if args.document_command == "parse":
        doc_ids = list(args.doc)
        if args.all:
            data = client.document_list(ds_id)
            docs = data.get("docs", data if isinstance(data, list) else [])
            doc_ids = [d["id"] for d in docs]
        if not doc_ids:
            return _emit({"command": "document.parse", "ok": False, "error": "no document ids"}, args.json)
        client.parse_start(ds_id, doc_ids)
        return _emit({"command": "document.parse", "ok": True, "summary": f"parse triggered for {len(doc_ids)} doc(s)"}, args.json)
    if args.document_command == "delete":
        target = list(args.doc)
        if args.all or args.failed or args.name:
            data = client.document_list(ds_id)
            docs = data.get("docs", data if isinstance(data, list) else [])
            for d in docs:
                did, name, run = d.get("id"), d.get("name", ""), str(d.get("run", "")).upper()
                if args.all:
                    target.append(did)
                elif args.failed and run == "FAIL":
                    target.append(did)
                elif args.name and fnmatch.fnmatch(name, args.name):
                    target.append(did)
        target = [t for t in dict.fromkeys(target) if t]
        if not target:
            return _emit({"command": "document.delete", "ok": False,
                          "error": "no matching documents (use --doc/--name/--failed/--all)"}, args.json)
        if not _confirm_or_abort(args, f"{len(target)} doc(s) from dataset {ds_id}"):
            return _emit({"command": "document.delete", "ok": False, "error": "aborted by HD gate (use --yes to skip)"}, args.json)
        client.document_delete(ds_id, target)
        return _emit({"command": "document.delete", "ok": True,
                      "summary": f"deleted {len(target)} doc(s)"}, args.json)
    return 2


def _cmd_ingest(args: argparse.Namespace, client: RagflowClient) -> int:
    ds = client.dataset_find(args.dataset)
    if not ds:
        if not args.create:
            return _emit({"command": "ingest", "ok": False, "error": f"dataset '{args.dataset}' not found (use --create)"}, args.json)
        ds = client.dataset_create(args.dataset, embedding_model=args.embedding_model)
    ds_id = ds["id"]
    root = Path(args.dir)
    paths = sorted(p for p in root.rglob(args.glob) if p.is_file())
    if not paths:
        return _emit({"command": "ingest", "ok": False, "error": f"no files matched {args.glob} under {root}"}, args.json)
    files = [(p.name, p.read_bytes()) for p in paths]
    uploaded = client.document_upload(ds_id, files)
    doc_ids = [d["id"] for d in uploaded if d.get("id")]
    parsed = 0
    if not args.no_parse and doc_ids:
        client.parse_start(ds_id, doc_ids)
        parsed = len(doc_ids)
    return _emit({"command": "ingest", "ok": True,
                  "summary": f"dataset={ds_id} uploaded={len(uploaded)} parse_triggered={parsed}",
                  "data": {"dataset_id": ds_id, "documents": uploaded}}, args.json)


def _cmd_retrieval(args: argparse.Namespace, client: RagflowClient) -> int:
    refs = [r.strip() for r in args.dataset.split(",") if r.strip()]
    ds_ids = [_dataset_id(client, r) for r in refs]
    data = client.retrieval(args.question, ds_ids, top_k=args.top_k)
    chunks = data.get("chunks", [])
    rows = [{"score": c.get("similarity"), "doc": c.get("document_keyword") or c.get("docnm_kwd"),
             "content": (c.get("content") or c.get("content_with_weight") or "")[:200]} for c in chunks]
    return _emit({"command": "retrieval", "ok": True, "summary": f"{len(rows)} chunk(s)", "data": rows}, args.json)


def _cmd_chat(args: argparse.Namespace, client: RagflowClient) -> int:
    cmd = args.chat_command
    if cmd == "list":
        rows = [{"id": c.get("id"), "name": c.get("name"),
                 "datasets": ",".join(c.get("dataset_ids") or c.get("kb_ids") or []),
                 "llm": c.get("llm_id", "")} for c in client.chat_list()]
        return _emit({"command": "chat.list", "ok": True, "summary": f"{len(rows)} assistant(s)", "data": rows}, args.json)
    if cmd == "create":
        ds_ids = [_dataset_id(client, r) for r in args.dataset.split(",") if r.strip()]
        c = client.chat_create(args.name, ds_ids, llm_id=args.llm_id)
        return _emit({"command": "chat.create", "ok": True, "summary": f"id={c.get('id')}", "data": c}, args.json)
    if cmd == "sessions":
        rows = [{"id": s.get("id"), "name": s.get("name"),
                 "create_time": s.get("create_time", "")} for s in client.chat_sessions_list(_chat_id(client, args.chat))]
        return _emit({"command": "chat.sessions", "ok": True, "summary": f"{len(rows)} session(s)", "data": rows}, args.json)
    if cmd == "new-session":
        s = client.chat_session_create(_chat_id(client, args.chat), args.name)
        return _emit({"command": "chat.new-session", "ok": True, "summary": f"id={s.get('id')}", "data": s}, args.json)
    if cmd == "ask":
        data = client.chat_completion(_chat_id(client, args.chat), args.question, session_id=args.session)
        answer = data.get("answer") or data.get("content") or ""
        return _emit({"command": "chat.ask", "ok": True,
                      "summary": f"session={data.get('session_id', '')} answer_len={len(answer)}",
                      "data": {"answer": answer, "session_id": data.get("session_id")}}, args.json)
    if cmd == "delete":
        ids = [_chat_id(client, x) for x in (x.strip() for x in args.chat.split(",") if x.strip())]
        if not _confirm_or_abort(args, f"{len(ids)} chat assistant(s): {','.join(ids)}"):
            return _emit({"command": "chat.delete", "ok": False, "error": "aborted by HD gate (use --yes to skip)"}, args.json)
        client.chat_delete(ids)
        return _emit({"command": "chat.delete", "ok": True, "summary": f"deleted {len(ids)} assistant(s)"}, args.json)
    return 2


def _cmd_agent(args: argparse.Namespace, client: RagflowClient) -> int:
    cmd = args.agent_command
    if cmd == "list":
        rows = [{"id": a.get("id"), "title": a.get("title"),
                 "canvas_type": a.get("canvas_type", "")} for a in client.agent_list()]
        return _emit({"command": "agent.list", "ok": True, "summary": f"{len(rows)} agent(s)", "data": rows}, args.json)
    if cmd == "templates":
        def _i18n_title(t: dict) -> str:
            title = t.get("title", "")
            return title.get("zh") or title.get("en") or str(title) if isinstance(title, dict) else str(title)
        rows = [{"id": t.get("id"), "title": _i18n_title(t)} for t in client.agent_templates()]
        return _emit({"command": "agent.templates", "ok": True, "summary": f"{len(rows)} template(s)", "data": rows}, args.json)
    if cmd == "create":
        dsl = _load_dsl_arg(args.dsl)
        client.agent_create(args.title, dsl, canvas_type=args.canvas_type)
        # create returns true; resolve id by title
        found = next((a for a in client.agent_list() if a.get("title") == args.title), None)
        return _emit({"command": "agent.create", "ok": True,
                      "summary": f"title={args.title} id={(found or {}).get('id', '?')}",
                      "data": found or {}}, args.json)
    if cmd == "sessions":
        rows = [{"id": s.get("id"), "create_time": s.get("create_time", "")}
                for s in client.agent_sessions_list(args.agent)]
        return _emit({"command": "agent.sessions", "ok": True, "summary": f"{len(rows)} session(s)", "data": rows}, args.json)
    if cmd == "new-session":
        s = client.agent_session_create(args.agent)
        return _emit({"command": "agent.new-session", "ok": True, "summary": f"id={s.get('id')}", "data": s}, args.json)
    if cmd == "ask":
        data = client.agent_chat_completion(args.agent, args.question, session_id=args.session)
        answer = data.get("answer") or data.get("content") or ""
        return _emit({"command": "agent.ask", "ok": True,
                      "summary": f"session={data.get('session_id', '')} answer_len={len(answer)}",
                      "data": {"answer": answer, "session_id": data.get("session_id")}}, args.json)
    if cmd == "delete":
        ids = [x.strip() for x in args.agent.split(",") if x.strip()]
        if not _confirm_or_abort(args, f"{len(ids)} agent(s): {','.join(ids)}"):
            return _emit({"command": "agent.delete", "ok": False, "error": "aborted by HD gate (use --yes to skip)"}, args.json)
        client.agent_delete(ids)
        return _emit({"command": "agent.delete", "ok": True, "summary": f"deleted {len(ids)} agent(s)"}, args.json)
    return 2


def _cmd_graph(args: argparse.Namespace, client: RagflowClient) -> int:
    ds_id = _dataset_id(client, args.dataset)
    cmd = args.graph_command
    if cmd == "run-graphrag":
        client.graphrag_run(ds_id)
        return _emit({"command": "graph.run-graphrag", "ok": True, "summary": f"triggered on {ds_id}"}, args.json)
    if cmd == "trace-graphrag":
        data = client.graphrag_trace(ds_id)
        return _emit({"command": "graph.trace-graphrag", "ok": True, "summary": str(data)[:200], "data": data}, args.json)
    if cmd == "run-raptor":
        client.raptor_run(ds_id)
        return _emit({"command": "graph.run-raptor", "ok": True, "summary": f"triggered on {ds_id}"}, args.json)
    if cmd == "trace-raptor":
        data = client.raptor_trace(ds_id)
        return _emit({"command": "graph.trace-raptor", "ok": True, "summary": str(data)[:200], "data": data}, args.json)
    return 2


def _cmd_chunk(args: argparse.Namespace, client: RagflowClient) -> int:
    ds_id = _dataset_id(client, args.dataset)
    cmd = args.chunk_command
    if cmd == "list":
        data = client.chunk_list(ds_id, args.doc)
        chunks = data.get("chunks", []) if isinstance(data, dict) else []
        rows = [{"id": c.get("id"), "available": c.get("available", ""),
                 "content": (c.get("content") or c.get("content_with_weight") or "")[:120]} for c in chunks]
        return _emit({"command": "chunk.list", "ok": True,
                      "summary": f"{len(rows)}/{data.get('total', len(rows))} chunk(s)", "data": rows}, args.json)
    if cmd == "add":
        data = client.chunk_add(ds_id, args.doc, args.content)
        chunk = data.get("chunk", data) if isinstance(data, dict) else {}
        return _emit({"command": "chunk.add", "ok": True, "summary": f"id={chunk.get('id')}", "data": chunk}, args.json)
    if cmd == "update":
        client.chunk_update(ds_id, args.doc, args.chunk, {"content": args.content})
        return _emit({"command": "chunk.update", "ok": True, "summary": f"updated {args.chunk}"}, args.json)
    if cmd == "expand":
        data = client.chunk_list(ds_id, args.doc)
        chunks = data.get("chunks", []) if isinstance(data, dict) else []
        idx = next((i for i, c in enumerate(chunks) if c.get("id") == args.chunk), None)
        if idx is None:
            return _emit({"command": "chunk.expand", "ok": False, "error": f"chunk {args.chunk} not in first 100 chunks"}, args.json)
        lo, hi = max(0, idx - args.before), min(len(chunks), idx + args.after + 1)
        rows = [{"id": c.get("id"), "mark": ("<<TARGET>>" if i == idx else ""),
                 "content": (c.get("content") or c.get("content_with_weight") or "")[:200]}
                for i, c in enumerate(chunks) if lo <= i < hi]
        return _emit({"command": "chunk.expand", "ok": True,
                      "summary": f"context [{lo},{hi}) around #{idx}", "data": rows}, args.json)
    if cmd == "delete":
        ids = [x.strip() for x in args.chunk.split(",") if x.strip()]
        if not _confirm_or_abort(args, f"{len(ids)} chunk(s) from doc {args.doc}"):
            return _emit({"command": "chunk.delete", "ok": False, "error": "aborted by HD gate (use --yes to skip)"}, args.json)
        client.chunk_delete(ds_id, args.doc, ids)
        return _emit({"command": "chunk.delete", "ok": True, "summary": f"deleted {len(ids)} chunk(s)"}, args.json)
    return 2


def _cmd_llm(args: argparse.Namespace, client: RagflowClient) -> int:
    # API-facing tag -> internal stored model_type (models_api_service.MODEL_TAG_TO_TYPE)
    _TYPE_MAP = {"asr": "speech2text", "vision": "image2text"}
    cmd = args.llm_command
    if cmd == "providers":
        rows = [{"name": p.get("name") or p.get("provider_name"), "id": p.get("id"),
                 "status": p.get("status", "")} for p in client.provider_list()]
        return _emit({"command": "llm.providers", "ok": True, "summary": f"{len(rows)} provider(s)", "data": rows}, args.json)
    if cmd == "factories":
        rows = [{"name": p.get("name") or p.get("provider_name")} for p in client.provider_list(available=True)]
        return _emit({"command": "llm.factories", "ok": True, "summary": f"{len(rows)} factorie(s)", "data": rows}, args.json)
    if cmd == "verify":
        client.provider_verify(args.provider, args.provider_api_key, args.provider_base_url)
        return _emit({"command": "llm.verify", "ok": True, "summary": f"{args.provider} connection OK"}, args.json)
    if cmd == "add-instance":
        try:
            client.provider_add(args.provider)
        except RagflowError as exc:
            if "already exists" not in str(exc):
                raise
        model_info = []
        for pair in [p.strip() for p in args.models.split(",") if p.strip()]:
            model_name, _, model_type = pair.partition(":")
            if not model_type:
                return _emit({"command": "llm.add-instance", "ok": False,
                              "error": f"--models entry '{pair}' missing :type"}, args.json)
            model_info.append({"model_name": model_name, "model_type": [model_type],
                               "max_tokens": 8192, "extra": {}})
        client.instance_create(args.provider, args.name, args.provider_api_key, args.provider_base_url,
                               model_info=model_info)
        return _emit({"command": "llm.add-instance", "ok": True,
                      "summary": f"{args.provider}/{args.name} created (+{len(model_info)} model(s))"}, args.json)
    if cmd == "add-model":
        model_type = _TYPE_MAP.get(args.type, args.type)
        client.instance_add_model(args.provider, args.instance, args.name, model_type, args.max_tokens)
        return _emit({"command": "llm.add-model", "ok": True,
                      "summary": f"{args.name}({model_type}) -> {args.provider}/{args.instance}"}, args.json)
    if cmd == "models":
        rows = [{"name": m.get("name") or m.get("model_name"), "type": m.get("model_type") or m.get("type"),
                 "status": m.get("status", "")} for m in client.instance_models(args.provider, args.instance)]
        return _emit({"command": "llm.models", "ok": True, "summary": f"{len(rows)} model(s)", "data": rows}, args.json)
    if cmd == "remote-models":
        rows = [{"name": m.get("name") or m.get("model_name"), "type": m.get("model_type") or m.get("type")}
                for m in client.provider_remote_models(args.provider, args.provider_api_key, args.provider_base_url)]
        return _emit({"command": "llm.remote-models", "ok": True, "summary": f"{len(rows)} model(s)", "data": rows}, args.json)
    if cmd == "default":
        data = client.default_models_get()
        return _emit({"command": "llm.default", "ok": True, "data": data}, args.json)
    if cmd == "remove-provider":
        client.provider_delete(args.provider)
        return _emit({"command": "llm.remove-provider", "ok": True,
                      "summary": f"provider {args.provider} deleted (with instances/models)"}, args.json)
    if cmd == "set-default":
        done = []
        for model_type in args.type:
            client.default_model_set(model_type, args.provider, args.instance, args.model)
            done.append(model_type)
        return _emit({"command": "llm.set-default", "ok": True,
                      "summary": f"{args.model}@{args.instance}@{args.provider} -> {','.join(done)}"}, args.json)
    return 2


def main(argv: list[str] | None = None) -> int:
    # Windows GBK consoles choke on non-GBK glyphs (e.g. 'ö' in template titles).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = _build_parser()
    args = parser.parse_args(argv)
    cfg = get_config()

    if args.command == "config":
        return _cmd_config(args, cfg)

    if args.command == "probe":
        base_url, _, timeout = _resolve(cfg, args)
        from urllib import request as _rq
        try:
            with _rq.urlopen(base_url, timeout=min(timeout, 5)) as r:
                return _emit({"command": "probe", "ok": True, "summary": f"HTTP {r.status} {base_url}"}, args.json)
        except Exception as exc:  # noqa: BLE001 - probe reports any failure
            return _emit({"command": "probe", "ok": False, "error": str(exc)}, args.json)

    try:
        client = _client(cfg, args)
        if args.command == "doctor":
            client.ping()
            return _emit({"command": "doctor", "ok": True, "summary": f"authenticated OK @ {client.base}"}, args.json)
        if args.command == "dataset":
            return _cmd_dataset(args, client)
        if args.command == "document":
            return _cmd_document(args, client)
        if args.command == "ingest":
            return _cmd_ingest(args, client)
        if args.command == "retrieval":
            return _cmd_retrieval(args, client)
        if args.command == "llm":
            return _cmd_llm(args, client)
        if args.command == "chat":
            return _cmd_chat(args, client)
        if args.command == "agent":
            return _cmd_agent(args, client)
        if args.command == "graph":
            return _cmd_graph(args, client)
        if args.command == "chunk":
            return _cmd_chunk(args, client)
    except RagflowError as exc:
        return _emit({"command": args.command, "ok": False, "error": str(exc)}, args.json)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
