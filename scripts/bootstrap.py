"""
容器首次启动引导脚本（幂等）。

在 `alembic upgrade head` 之后运行（见 docker-compose.yml 的 migrate 服务）：
1. 初始化默认角色与配置模板
2. 创建初始超级管理员（若不存在）

环境变量：
    ADMIN_USERNAME  初始管理员用户名（默认 admin）
    ADMIN_PASSWORD  初始管理员密码（>= 8 位；未设置则跳过创建）
"""

import os
import sys

# 确保无论从哪个目录执行（如 `python scripts/bootstrap.py`），都能导入 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import get_db_manager
from app.shared.db_init import init_default_roles, init_default_templates
from app.features.auth.router import get_password_hash
from app.shared.models import Role, User


def ensure_admin() -> None:
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        print("[bootstrap] ADMIN_PASSWORD 未设置，跳过初始管理员创建", file=sys.stderr)
        return

    if len(password) < 8:
        print("[bootstrap] 错误：ADMIN_PASSWORD 至少 8 位", file=sys.stderr)
        sys.exit(1)

    db = get_db_manager().get_session()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"[bootstrap] 管理员 {username} 已存在，跳过创建")
            return

        admin_role = db.query(Role).filter(Role.name == "admin").first()
        user = User(
            username=username,
            email=None,
            full_name=username,
            password_hash=get_password_hash(password),
            is_active=True,
            is_superuser=True,
        )
        if admin_role:
            user.roles.append(admin_role)

        db.add(user)
        db.commit()
        print(
            f"[bootstrap] 超级管理员 {username} 创建成功"
            f"{'（已关联 admin 角色）' if admin_role else '（未找到 admin 角色）'}"
        )
    finally:
        db.close()


def main() -> None:
    print("[bootstrap] 初始化默认角色与配置模板 ...")
    init_default_roles()
    init_default_templates()
    print("[bootstrap] 确保初始管理员存在 ...")
    ensure_admin()
    print("[bootstrap] 完成")


if __name__ == "__main__":
    main()
