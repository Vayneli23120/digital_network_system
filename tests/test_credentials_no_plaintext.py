"""凭证接口与本地登录的安全回归测试

对应 docs/CODE_REVIEW_ISSUES.md 批次二：
- SSH 密码明文曾经通过 `GET /api/credentials/{id}` 直接返回（前端根本没用这个字段），
  叠加当时的无鉴权状态，等于把全网设备的 SSH 口令公开在内网里
- 前端不回填密码后，更新接口必须把"留空"理解为"保持不变"，否则每次编辑都会
  静默清掉已保存的 enable 密码
- 启用认证后，错误密码必须被拒绝（`auth_enabled=false` 时曾经任意密码都能登录）
"""

import asyncio

import pytest

import app.shared.models_jobs  # noqa: F401  让 jobs 表进入 Base.metadata


# ---------------------------------------------------------------------------
# 本地登录链路（SSO 之外的第二条通道）
# ---------------------------------------------------------------------------

def test_passlib_is_installed():
    """passlib 缺失时 auth/router.py 会退化成明文存储密码，必须装上"""
    from app.features.auth.router import PWD_CONTEXT_AVAILABLE

    assert PWD_CONTEXT_AVAILABLE, "缺少 passlib[bcrypt]，密码会以明文入库"


def test_password_hash_roundtrip():
    from app.features.auth.router import get_password_hash, verify_password

    hashed = get_password_hash("Str0ngPassw0rd!")
    assert hashed != "Str0ngPassw0rd!"
    assert verify_password("Str0ngPassw0rd!", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.fixture
def auth_enabled_config(monkeypatch):
    """把全局配置切成"认证开启"，并同步给已捕获 config 的模块"""
    import app.features.auth.router as auth_router
    from app.shared.config import get_config

    cfg = get_config()
    monkeypatch.setattr(cfg.security, "auth_enabled", True)
    monkeypatch.setattr(cfg.security, "jwt_secret", "x" * 40)
    monkeypatch.setattr(auth_router, "config", cfg)
    return cfg


@pytest.fixture
def local_admin(db_session):
    from app.features.auth.router import get_password_hash
    from app.shared.models import Role, User

    role = Role(name="admin", description="系统管理员", is_system=True)
    db_session.add(role)
    db_session.flush()

    admin = User(
        username="nasadmin",
        email="nasadmin@example.com",
        full_name="NAS Admin",
        password_hash=get_password_hash("Str0ngPassw0rd!"),
        is_active=True,
        is_superuser=True,
    )
    admin.roles.append(role)
    db_session.add(admin)
    db_session.commit()
    return admin


def test_login_issues_real_access_token(db_session, local_admin, auth_enabled_config):
    from app.features.auth.router import UserLogin, decode_token, login

    token = asyncio.run(login(UserLogin(username="nasadmin", password="Str0ngPassw0rd!"), db_session))

    assert token["token_type"] == "bearer"
    assert token["access_token"] != "placeholder_token_auth_disabled"

    payload = decode_token(token["access_token"])
    assert payload["sub"] == "nasadmin"
    assert payload["type"] == "access"


def test_login_rejects_wrong_password(db_session, local_admin, auth_enabled_config):
    from fastapi import HTTPException

    from app.features.auth.router import UserLogin, login

    with pytest.raises(HTTPException) as exc:
        asyncio.run(login(UserLogin(username="nasadmin", password="wrong"), db_session))

    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# 凭证接口不得回传任何明文
# ---------------------------------------------------------------------------

@pytest.fixture
def credential_group(db_session):
    from app.features.credentials.credential_service import encrypt_password
    from app.shared.models import CredentialGroup

    group = CredentialGroup(
        name="default",
        username="netadmin",
        password_encrypted=encrypt_password("ssh-secret"),
        enable_password_encrypted=encrypt_password("enable-secret"),
    )
    db_session.add(group)
    db_session.commit()
    return group


def test_credential_detail_hides_plaintext(db_session, credential_group):
    from app.features.credentials.router import get_credential

    detail = asyncio.run(get_credential(credential_group.id, None, db_session))

    assert "password" not in detail
    assert "enable_password" not in detail
    assert detail["has_password"] is True
    assert detail["has_enable_password"] is True
    assert "ssh-secret" not in str(detail)
    assert "enable-secret" not in str(detail)


def test_credential_list_hides_plaintext(db_session, credential_group):
    from app.features.credentials.router import list_credentials

    listing = asyncio.run(list_credentials(None, db_session))

    assert "ssh-secret" not in str(listing)
    assert listing["items"][0]["has_password"] is True


def test_credential_update_keeps_passwords_when_blank(db_session, credential_group):
    """前端不回填密码，因此"留空"必须等于"保持不变" """
    from app.features.credentials.router import CredentialUpdate, update_credential

    asyncio.run(update_credential(
        credential_group.id, CredentialUpdate(description="仅改描述"), None, db_session
    ))
    db_session.refresh(credential_group)

    assert credential_group.password_encrypted
    assert credential_group.enable_password_encrypted
    assert credential_group.description == "仅改描述"


def test_credential_update_can_clear_enable_password_explicitly(db_session, credential_group):
    from app.features.credentials.router import CredentialUpdate, update_credential

    asyncio.run(update_credential(
        credential_group.id, CredentialUpdate(clear_enable_password=True), None, db_session
    ))
    db_session.refresh(credential_group)

    assert credential_group.enable_password_encrypted is None
    assert credential_group.password_encrypted, "清空 enable 密码不应影响 SSH 密码"


def test_credential_create_rejects_missing_fields(db_session):
    """请求体从裸 dict 换成 Pydantic 模型后，缺字段应在校验层被拦住"""
    from pydantic import ValidationError

    from app.features.credentials.router import CredentialCreate

    with pytest.raises(ValidationError):
        CredentialCreate(description="没有名字和用户名")


def test_credential_endpoints_require_permission():
    """四个接口都必须挂上 credential:* 权限依赖"""
    import inspect

    from app.features.credentials import router as cred_router

    for func_name in ("list_credentials", "create_credential", "get_credential",
                      "update_credential", "delete_credential"):
        func = getattr(cred_router, func_name)
        params = inspect.signature(func).parameters
        assert "_" in params, f"{func_name} 缺少权限依赖"
        assert params["_"].default is not inspect.Parameter.empty, f"{func_name} 权限依赖未注入"
