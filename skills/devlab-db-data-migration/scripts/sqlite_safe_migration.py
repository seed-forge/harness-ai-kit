#!/usr/bin/env python3
"""sqlite_safe_migration.py — SQLite 安全迁移脚手架模板.

流程骨架已固化: 备份 -> 幂等检测 -> 迁移(重建表路径) -> 验证 -> 失败回滚.
按具体迁移需求填充 MIGRATION 区即可. 源自真实生产修复实践.

用法:
    python sqlite_safe_migration.py --db app.db [--dry-run] [--rollback]
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ══════════════ MIGRATION 区: 按需修改 ══════════════
TABLE = "example_table"          # 目标表
NEW_COLUMNS = [                  # 需新增的列 (name, ddl_fragment)
    # ("new_col", "TEXT DEFAULT ''"),
]
REBUILD_DDL = None               # 需改约束时填新表完整 DDL(触发重建路径); 否则 None
# 例: REBUILD_DDL = "CREATE TABLE {t} (id INTEGER PRIMARY KEY, name TEXT, UNIQUE(name, ts))"
REBUILD_COPY_COLS = "*"          # 重建时 INSERT INTO new SELECT <cols> FROM old
POST_INDEXES = [                 # 迁移完成后需保证存在的索引 (name, ddl)
    # ("idx_example_name", "CREATE INDEX idx_example_name ON example_table(name)"),
]
# ═══════════════════════════════════════════════════


def backup(db: Path) -> Path:
    bak = db.with_suffix(f".{datetime.now():%Y%m%d%H%M%S}.bak")
    shutil.copy2(db, bak)
    print(f"[backup] {bak}")
    return bak


def restore(db: Path, bak: Path) -> None:
    shutil.copy2(bak, db)
    print(f"[rollback] restored from {bak}")


def existing_columns(cur: sqlite3.Cursor, table: str) -> set:
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}


def existing_indexes(cur: sqlite3.Cursor, table: str) -> set:
    return {row[1] for row in cur.execute(f"PRAGMA index_list({table})")}


def is_migrated(cur: sqlite3.Cursor) -> bool:
    """幂等检测: 目标结构已全部存在则视为已迁移."""
    cols = existing_columns(cur, TABLE)
    if any(name not in cols for name, _ in NEW_COLUMNS):
        return False
    idx = existing_indexes(cur, TABLE)
    if any(name not in idx for name, _ in POST_INDEXES):
        return False
    if REBUILD_DDL is not None:
        return False  # 约束变更无法用 PRAGMA 简单判定, 由使用者按需补充判据
    return True


def migrate(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    # 顺序硬约束 1: 先加列
    cols = existing_columns(cur, TABLE)
    for name, ddl in NEW_COLUMNS:
        if name not in cols:
            cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN {name} {ddl}")
            print(f"[migrate] added column {name}")
    # 顺序硬约束 2: 约束变更走四步重建
    if REBUILD_DDL is not None:
        old_count = cur.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        tmp = f"{TABLE}__new"
        cur.execute(REBUILD_DDL.format(t=tmp))
        cur.execute(f"INSERT INTO {tmp} SELECT {REBUILD_COPY_COLS} FROM {TABLE}")
        cur.execute(f"DROP TABLE {TABLE}")
        cur.execute(f"ALTER TABLE {tmp} RENAME TO {TABLE}")
        new_count = cur.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        if new_count != old_count:
            raise RuntimeError(f"row count mismatch: {old_count} -> {new_count}")
        print(f"[migrate] rebuilt {TABLE} ({new_count} rows verified)")
    # 顺序硬约束 3: 索引最后建
    idx = existing_indexes(cur, TABLE)
    for name, ddl in POST_INDEXES:
        if name not in idx:
            cur.execute(ddl)
            print(f"[migrate] created index {name}")
    conn.commit()


def verify(cur: sqlite3.Cursor) -> None:
    cols = existing_columns(cur, TABLE)
    for name, _ in NEW_COLUMNS:
        assert name in cols, f"schema assert failed: column {name} missing"
    idx = existing_indexes(cur, TABLE)
    for name, _ in POST_INDEXES:
        assert name in idx, f"schema assert failed: index {name} missing"
    print("[verify] schema assertions passed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="SQLite db file path")
    ap.add_argument("--dry-run", action="store_true", help="Only report migration status")
    ap.add_argument("--rollback", metavar="BAK", help="Restore db from given backup file")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"error: db not found: {db}", file=sys.stderr)
        return 1

    if args.rollback:
        restore(db, Path(args.rollback))
        return 0

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    if is_migrated(cur):
        print("[idempotent] already migrated, nothing to do")
        return 0
    if args.dry_run:
        print("[dry-run] migration needed (not applied)")
        return 0

    bak = backup(db)
    try:
        migrate(conn)
        verify(cur)
        print("[done] migration completed successfully")
        return 0
    except Exception as exc:  # noqa: BLE001 - 任何异常都必须回滚
        conn.close()
        restore(db, bak)
        print(f"error: migration failed and rolled back: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
