"""SSO 登录端点（Microsoft Entra ID / OIDC 授权码流）

当前状态：**占位实现**。三个端点已经就位、前端登录页已经对接，
等 IT 批下 Entra ID 应用注册后，只需在 config.yaml 填入
tenant_id / client_id / client_secret / redirect_uri 并把 sso.enabled 置 true，
再补上 `_exchange_code_for_identity()` 里的 MSAL 调用即可。

为什么先做占位而不是等 SSO 批下来再一起做：
- 登录页的双入口、路由、状态查询这些前端工作与 IdP 无关，可以先完成
- 未开通时返回明确的 501 + 缺失项清单，而不是 404/500，便于排查配置

接入清单（申请时一并确认）：
1. 应用注册（App registration）→ tenant_id / client_id / client_secret
2. 重定向 URI 注册为 https://<内网主机>/api/auth/sso/callback（Entra 要求
   非 localhost 必须是 https）
3. 服务器需要能出站访问 login.microsoftonline.com（换取令牌 + 拉取 JWKS 验签）
4. 如需用 AD 组直接映射系统角色，请让 IT 在应用注册里开启 groups claim
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.shared.config import get_config
from app.shared.database import get_db

router = APIRouter(prefix="/api/auth/sso", tags=["auth"])


def _sso_unavailable_detail() -> dict:
    """未开通时返回可操作的诊断信息，而不是笼统报错"""
    cfg = get_config().sso
    if not cfg.enabled:
        return {
            "reason": "not_enabled",
            "message": "SSO 尚未开通，请使用本地账号登录",
            "hint": "在 config.yaml 的 sso 段落中设置 enabled: true 并填写 Entra ID 应用注册信息",
        }
    missing = cfg.missing_fields()
    return {
        "reason": "misconfigured",
        "message": "SSO 已启用但配置不完整",
        "missing_fields": missing,
        "hint": "补齐上述配置项后重启服务",
    }


@router.get("/status")
async def sso_status():
    """登录页用它决定 SSO 入口是否可点、以及显示什么名字

    此接口不需要认证：它只暴露"是否开通"，不泄漏任何密钥。
    """
    cfg = get_config().sso
    missing = cfg.missing_fields() if cfg.enabled else []
    return {
        "enabled": bool(cfg.enabled and not missing),
        "provider": cfg.provider,
        "display_name": cfg.display_name,
        # 已启用但配置不全时告诉前端，避免用户点进去才发现不能用
        "configured": not missing,
        "missing_fields": missing,
        "login_url": "/api/auth/sso/login",
    }


@router.get("/login")
async def sso_login():
    """跳转到身份提供方登录页（占位）

    正式实现：用 MSAL 的 ConfidentialClientApplication 生成 authorization URL
    （含 state / nonce / PKCE），然后 307 重定向过去。
    """
    cfg = get_config().sso
    detail = _sso_unavailable_detail()

    if not cfg.enabled or cfg.missing_fields():
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)

    logger.warning("SSO 已配置但跳转逻辑尚未实现（等待 Entra ID 应用注册落地）")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "reason": "not_implemented",
            "message": "SSO 配置已就绪，但授权跳转逻辑尚未接入",
            "hint": "实现 sso_router._build_authorization_url() 并安装 msal",
        },
    )


@router.get("/callback")
async def sso_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """身份提供方回调（占位）

    正式实现的步骤：
    1. 校验 state，防 CSRF
    2. 用 code 换 id_token（MSAL acquire_token_by_authorization_code）
    3. 验签 id_token（JWKS）并取出 oid / preferred_username / email / groups
    4. 按 external_id=oid 查本地用户；不存在且 auto_provision=true 则建号并赋
       default_role（建号前需要先把 User.password_hash 改成可空，并补
       auth_source / external_id 两个字段）
    5. 签发系统自己的 access token，重定向回前端
    """
    if error:
        logger.warning(f"SSO 回调返回错误: {error} - {error_description}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"reason": "idp_error", "error": error, "description": error_description},
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_sso_unavailable_detail(),
    )
