"""
SQLite -> PostgreSQL 一次性数据迁移脚本。

使用项目 ORM 的同一份 Base.metadata 读 SQLite、写 PG，
由 SQLAlchemy 自动处理 DateTime / Boolean 等类型转换。
迁移顺序按 sorted_tables（满足外键依赖），结束后重置自增序列。

用法（项目根目录 + .venv）:
    .venv/bin/python scripts/_migrate_sqlite_to_pg.py
"""
import os
import sys

# 确保能 import app.*
sys.path.insert(0, os.getcwd())

from sqlalchemy import create_engine, select, func, text, String  # noqa: E402
from app.shared.models import Base  # noqa: E402

SQLITE_PATH = os.environ.get("NAS_SQLITE_PATH", "data/nas.db")
PW_FILE = os.path.expanduser("~/.nas_pg_pw")


def read_pg_password() -> str:
    with open(PW_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_pg_url(pw: str) -> str:
    # 同步驱动 psycopg2；用户/库名固定为本次迁移创建的 nasuser / nas
    return f"postgresql+psycopg2://nasuser:{pw}@127.0.0.1:5432/nas"


def main() -> int:
    if not os.path.exists(SQLITE_PATH):
        print(f"[FATAL] SQLite 文件不存在: {SQLITE_PATH}", file=sys.stderr)
        return 2

    pw = read_pg_password()
    src = create_engine(f"sqlite:///{SQLITE_PATH}")
    dst = create_engine(build_pg_url(pw))

    # 验证 PG 连接
    with dst.connect() as c:
        who = c.execute(text("SELECT current_user, current_database()")).fetchone()
        print(f"[PG] connected as {who[0]} db={who[1]}")

    # 1) 在 PG 建表（与 ORM 完全一致）
    print("[STEP] create_all on PostgreSQL ...")
    Base.metadata.create_all(bind=dst)

    tables = list(Base.metadata.sorted_tables)
    print(f"[INFO] {len(tables)} 张表，按外键顺序迁移")

    # 1.5) SQLite 不强制 VARCHAR 长度，部分列实际数据超过 ORM 声明长度。
    #      迁移前把这些 PG 列加宽到实际最大长度，避免 StringDataRightTruncation 且不丢数据。
    print("[STEP] 校正 VARCHAR 列长度 ...")
    with src.connect() as sconn, dst.begin() as dconn:
        for table in tables:
            for col in table.columns:
                if isinstance(col.type, String) and col.type.length:
                    try:
                        maxlen = sconn.execute(
                            text(f'SELECT MAX(LENGTH("{col.name}")) FROM "{table.name}"')
                        ).scalar()
                    except Exception:
                        maxlen = None
                    if maxlen and maxlen > col.type.length:
                        newlen = maxlen
                        dconn.execute(text(
                            f'ALTER TABLE "{table.name}" '
                            f'ALTER COLUMN "{col.name}" TYPE VARCHAR({newlen})'
                        ))
                        print(f"  - widen {table.name}.{col.name}: "
                              f"{col.type.length} -> {newlen}")

    summary = []
    # 2) 逐表复制（同一 metadata，类型自动转换）
    #    存在循环外键 (fault_records <-> maintenance_records)，
    #    用 session_replication_role=replica 在复制期间跳过 FK 触发器检查
    #    （pg_dump 同款做法，需 superuser 会话）。
    with src.connect() as sconn, dst.begin() as dconn:
        dconn.execute(text("SET session_replication_role = 'replica'"))
        # 安全起见先清空（若之前有部分残留）
        for table in reversed(tables):
            dconn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
        for table in tables:
            rows = sconn.execute(select(table)).mappings().all()
            n = len(rows)
            if n:
                dconn.execute(table.insert(), [dict(r) for r in rows])
            summary.append((table.name, n))
            print(f"  - {table.name}: {n} 行")
        dconn.execute(text("SET session_replication_role = 'origin'"))

    # 3) 重置自增序列（针对整型自增主键）
    print("[STEP] 重置序列 ...")
    with dst.begin() as dconn:
        for table in tables:
            for col in table.primary_key.columns:
                # 仅整型自增主键
                pytype = None
                try:
                    pytype = col.type.python_type
                except Exception:
                    pytype = None
                if pytype is int and col.autoincrement in (True, "auto"):
                    seq_sql = text(
                        "SELECT setval("
                        "  pg_get_serial_sequence(:tname, :cname), "
                        "  COALESCE((SELECT MAX(" + col.name + ") FROM " + table.name + "), 1), "
                        "  (SELECT COUNT(*) FROM " + table.name + ") > 0"
                        ")"
                    )
                    seq_name = dconn.execute(
                        text("SELECT pg_get_serial_sequence(:tname, :cname)"),
                        {"tname": table.name, "cname": col.name},
                    ).scalar()
                    if seq_name:
                        dconn.execute(seq_sql, {"tname": table.name, "cname": col.name})
                        print(f"  - seq {table.name}.{col.name} -> {seq_name}")

    # 4) 校验行数一致
    print("[VERIFY] 行数核对 (SQLite vs PG):")
    ok = True
    with src.connect() as sconn, dst.connect() as dconn:
        for table in tables:
            sc = sconn.execute(select(func.count()).select_from(table)).scalar()
            dc = dconn.execute(select(func.count()).select_from(table)).scalar()
            flag = "OK" if sc == dc else "MISMATCH"
            if sc != dc:
                ok = False
            if sc or dc:
                print(f"  - {table.name}: sqlite={sc} pg={dc} [{flag}]")

    print("[DONE]" if ok else "[DONE-WITH-MISMATCH]")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
