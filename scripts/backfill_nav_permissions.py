"""数据迁移脚本 - 为已有数据库补齐导航可见权限 (nav_*)

背景
----
角色导航可见性功能引入了 28 个 `nav_*` 权限。`POST /api/permissions/init`
只会同步 `is_system=True` 的预置角色（admin / operator / viewer），
`device_manager`、`fault_handler` 这类 `is_system=False` 的预置角色，
以及管理员自建的角色，都不会被自动补齐。

本脚本按 `PRESET_ROLES` 的定义，给这些角色补齐缺失的 `nav_*` 权限。
只做「添加」，不会删除任何已有权限，也不会改动功能权限。

运行方式
--------
    python scripts/backfill_nav_permissions.py --dry-run    # 预览
    python scripts/backfill_nav_permissions.py              # 实际写入

    # 工作目录没有 config.yaml 时，显式指定数据库
    python scripts/backfill_nav_permissions.py --db-url \\
        "postgresql+psycopg2://user:pass@127.0.0.1:5432/nas" --dry-run

注意
----
脚本连接的数据库由 config.yaml（或 --db-url / DATABASE_URL）决定。没有配置时会
回退到本地 SQLite，那通常不是你要迁移的库——启动时会把实际连接目标打印出来，
执行前请先核对。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features.permissions.router import (  # noqa: E402
    EXTENDED_PERMISSIONS,
    PRESET_ROLES,
)
from app.shared.config import describe_db_url, get_config  # noqa: E402
from app.shared.database import DatabaseManager, get_db_manager  # noqa: E402
from app.shared.models import Permission, Role  # noqa: E402

NAV_PREFIX = "nav_"

# Windows 控制台默认可能是 GBK/cp1252，中文输出会直接抛 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def is_nav(name: str) -> bool:
    return name.startswith(NAV_PREFIX)


def ensure_nav_permissions(db, dry_run: bool) -> set:
    """确保权限表里存在全部 nav_* 权限

    Returns:
        本次新建（预览模式下为「将要新建」）的权限名集合
    """
    existing = {p.name for p in db.query(Permission).all()}
    created = set()

    for perm_data in EXTENDED_PERMISSIONS:
        if not is_nav(perm_data["name"]) or perm_data["name"] in existing:
            continue
        print(f"  + 权限 {perm_data['name']}  ({perm_data.get('description')})")
        if not dry_run:
            db.add(Permission(
                name=perm_data["name"],
                description=perm_data.get("description"),
                resource=perm_data["resource"],
                action=perm_data["action"],
            ))
        created.add(perm_data["name"])

    if created and not dry_run:
        db.flush()
    return created


def backfill_roles(db, dry_run: bool, pending_perms: set) -> int:
    """给预置角色补齐缺失的 nav_* 权限，返回受影响的角色数

    Args:
        pending_perms: 预览模式下「将要新建」的权限名。这些权限还没有进入
            session，查库查不到，但在实际执行时是存在的 —— 不把它们算进来，
            预览会把每一条都报成「不在权限表中，跳过」
    """
    perm_by_name = {p.name: p for p in db.query(Permission).all()}
    touched = 0

    for role_data in PRESET_ROLES:
        expected_nav = [n for n in role_data.get("permissions", []) if is_nav(n)]
        if not expected_nav:
            continue

        role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if role is None:
            print(f"- 角色 {role_data['name']}: 数据库中不存在，跳过"
                  f"（可调用 POST /api/permissions/init 创建）")
            continue

        current = {p.name for p in role.permissions}
        missing = [n for n in expected_nav if n not in current]

        if not missing:
            print(f"- 角色 {role.name}: 导航权限已齐全（{len(expected_nav)} 条），无需处理")
            continue

        print(f"- 角色 {role.name}: 补齐 {len(missing)} 条导航权限")
        for name in missing:
            perm = perm_by_name.get(name)
            if perm is None and name not in pending_perms:
                print(f"    ! 权限 {name} 不在权限表中，跳过")
                continue
            print(f"    + {name}")
            if not dry_run and perm is not None:
                role.permissions.append(perm)
        touched += 1

    return touched


def report_custom_roles(db) -> None:
    """列出没有任何 nav_* 权限的自建角色，交给管理员决定"""
    preset_names = {r["name"] for r in PRESET_ROLES}
    orphans = []

    for role in db.query(Role).all():
        if role.name in preset_names:
            continue
        names = {p.name for p in role.permissions}
        if names and not any(is_nav(n) for n in names):
            orphans.append((role.name, len(names)))

    if not orphans:
        return

    print("\n以下自建角色没有任何导航权限，前端会按「未纳管」处理并显示全部菜单：")
    for name, count in orphans:
        print(f"  - {name}（{count} 条功能权限）")
    print("如需限制其可见菜单，请在「系统设置 → 角色权限」中编辑该角色的「可见菜单」。")


def resolve_db_manager(db_url: str | None):
    """返回 (DatabaseManager, 有效 URL, 来源说明)"""
    if db_url:
        return DatabaseManager(db_url=db_url), db_url, "--db-url 参数"

    config = get_config()
    return (
        get_db_manager(),
        config.database.get_effective_url(),
        config.database.url_source,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="为已有数据库补齐导航可见权限")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将要执行的变更，不写入数据库")
    parser.add_argument("--db-url", default=None,
                        help="显式指定数据库连接串，优先于 config.yaml / DATABASE_URL")
    parser.add_argument("--yes", action="store_true",
                        help="跳过写入前的确认（用于非交互执行）")
    args = parser.parse_args()

    mode = "预览模式（不会写入）" if args.dry_run else "写入模式"
    print(f"=== 补齐导航可见权限 - {mode} ===\n")

    db_manager, effective_url, source = resolve_db_manager(args.db_url)
    db_type = "SQLite" if db_manager.is_sqlite else "PostgreSQL"
    print(f"目标数据库: {db_type} -> {describe_db_url(effective_url)}")
    print(f"配置来源  : {source}\n")

    if db_manager.is_sqlite:
        print("! 当前连接的是 SQLite。如果你的系统实际运行在 PostgreSQL 上，")
        print("!  说明没有读到 config.yaml —— 请切换到部署目录，或用 --db-url 指定 PostgreSQL。\n")

    if not args.dry_run and not args.yes:
        if not sys.stdin.isatty():
            print("非交互环境下需要显式确认，请加 --yes（或先用 --dry-run 预览）。")
            return 1
        answer = input("以上数据库将被写入，确认继续？(yes/no): ").strip().lower()
        if answer not in ("y", "yes"):
            print("已取消，未做任何修改。")
            return 1
        print()

    with db_manager.session_scope() as db:
        total_roles = db.query(Role).count()
        if total_roles == 0:
            print("角色表为空，无需迁移。请先调用 POST /api/permissions/init 初始化。")
            return 0

        print("[1/3] 检查 nav_* 权限清单")
        created = ensure_nav_permissions(db, args.dry_run)
        print(f"      新建权限: {len(created)}\n")

        print("[2/3] 补齐预置角色的导航权限")
        touched = backfill_roles(db, args.dry_run, created)
        print(f"      受影响角色: {touched}\n")

        print("[3/3] 检查自建角色")
        report_custom_roles(db)

        if args.dry_run:
            db.rollback()
            print("\n预览结束，未写入任何数据。去掉 --dry-run 即可执行。")
        else:
            print("\n迁移完成。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
