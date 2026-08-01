"""统一请求身份解析。

JWT 是正式身份凭据；X-User 仅允许在显式 debug 且关闭认证的开发模式使用。
路由不得自行解码 token 或直接信任客户端用户名。
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.shared.config import get_config
from app.shared.database import get_db
from app.shared.models import User, UserSession

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    username: str
    user_id: Optional[int]
    user: Optional[User]
    auth_source: str
    is_development: bool = False

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None and not self.is_development


def development_auth_bypass_enabled() -> bool:
    """开发身份旁路必须由两个开关共同确认。"""
    config = get_config()
    return bool(config.app.debug and not config.security.auth_enabled)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token_payload(token: str) -> dict:
    """解码并验证正式 access token 的通用入口。"""
    from app.features.auth.router import decode_token

    try:
        payload = decode_token(token)
    except Exception as exc:
        raise _unauthorized("令牌已失效或无效") from exc

    if payload.get("type") != "access":
        raise _unauthorized("无效的令牌类型")
    if not payload.get("sub"):
        raise _unauthorized("无效的令牌数据")
    return payload


def _resolve_payload_user(payload: dict, db: Session) -> User:
    username = payload["sub"]

    jti = payload.get("jti")
    if jti:
        revoked = db.query(UserSession).filter(
            UserSession.token_jti == jti,
            UserSession.revoked == True,
        ).first()
        if revoked:
            raise _unauthorized("令牌已被撤销")

    user = db.query(User).options(joinedload(User.roles)).filter(User.username == username).first()
    if not user:
        raise _unauthorized("用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    return user


def _resolve_token_user(token: str, db: Session) -> User:
    return _resolve_payload_user(decode_access_token_payload(token), db)


def resolve_principal(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
) -> Principal:
    """根据当前安全模式解析唯一可信身份。"""
    config = get_config()

    if (
        credentials
        and credentials.credentials == "placeholder_token_auth_disabled"
        and development_auth_bypass_enabled()
    ):
        credentials = None

    if credentials:
        payload = getattr(request.state, "token_payload", None)
        user = (
            _resolve_payload_user(payload, db)
            if payload
            else _resolve_token_user(credentials.credentials, db)
        )
        return Principal(
            username=user.username,
            user_id=user.id,
            user=user,
            auth_source="jwt",
        )

    if config.security.auth_enabled:
        raise _unauthorized("未提供认证令牌")

    if not development_auth_bypass_enabled():
        raise _unauthorized("认证已关闭，但开发身份旁路未启用")

    x_user = request.headers.get("X-User")
    if x_user:
        user = db.query(User).filter(User.username == x_user, User.is_active == True).first()
        if not user:
            raise _unauthorized("开发身份不存在或已停用")
        return Principal(
            username=user.username,
            user_id=user.id,
            user=user,
            auth_source="development_header",
            is_development=True,
        )

    return Principal(
        username="developer",
        user_id=None,
        user=None,
        auth_source="development_bypass",
        is_development=True,
    )


async def get_current_principal(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Principal:
    existing = getattr(request.state, "principal", None)
    if existing is not None:
        return existing

    principal = resolve_principal(request, credentials, db)
    request.state.principal = principal
    request.state.user_id = principal.user_id
    return principal


async def get_optional_principal(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[Principal]:
    """仅用于真正允许匿名访问、但可利用登录身份增强响应的端点。"""
    if not credentials and not development_auth_bypass_enabled():
        return None
    return await get_current_principal(request, credentials, db)
