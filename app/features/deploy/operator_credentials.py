"""操作者会话级 SSH 凭证解析（批次二·步骤5 切片 B）。

部署 / 回滚与备份一致，默认必须使用操作者自己的 SSH 凭证（密码不落服务器）：
- 请求携带 credentials{username, password, secret} → 构建单个 name='default'
  的凭证组，覆盖全部目标设备（各服务按 device.credential_group 名匹配并回退
  'default'，单个 default 组即可覆盖所有设备）。
- 未携带且 credential_session_required=True → 400 拒绝（不静默降级）。
- 未携带且 credential_session_required=False → 返回 None，调用方回退服务器
  存储的 CredentialGroup 解密。

凭证仅存于请求/线程内存，不落库、不进日志（部署日志只记用户名不记密码）。
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.shared.config import get_config


def _as_credentials_dict(credentials: Any) -> Dict[str, Any]:
    """将请求模型实例或原始 dict 归一化为 dict。"""
    if credentials is None:
        return {}
    if isinstance(credentials, dict):
        return credentials
    return {
        "username": getattr(credentials, "username", None),
        "password": getattr(credentials, "password", None),
        "secret": getattr(credentials, "secret", None),
    }


def build_operator_credential_groups(credentials: Any) -> Optional[List[Dict[str, Any]]]:
    """从请求 credentials 构建操作者凭证组列表；未提供返回 None。

    部分填写（用户名或密码缺一）视为错误，避免静默降级到服务器凭证组。
    """
    data = _as_credentials_dict(credentials)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    secret = data.get("secret") or ""
    provided = bool(username or password or secret)
    if provided and (not username or not password):
        raise HTTPException(status_code=400, detail="请完整填写操作者 SSH 凭证（用户名与密码必填）")
    if not username or not password:
        return None
    return [{
        "name": "default",
        "username": username,
        "password": password,
        "enable_password": secret or None,
    }]


def resolve_operator_credentials(credentials: Any) -> Optional[List[Dict[str, Any]]]:
    """按会话凭证开关解析操作者凭证组。

    - 携带凭证 → 返回单个 default 组；
    - 未携带且开关开（credential_session_required=True）→ 400；
    - 未携带且开关关 → 返回 None，调用方回退服务器存储的 CredentialGroup。
    """
    groups = build_operator_credential_groups(credentials)
    if groups is not None:
        return groups
    if get_config().security.credential_session_required:
        raise HTTPException(
            status_code=400,
            detail="请使用操作者 SSH 凭证（密码不存储在服务器上）",
        )
    return None
