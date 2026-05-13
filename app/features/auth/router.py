"""
用户认证和权限管理路由

注意：当前版本 (v1.0) 认证功能默认关闭
通过 config.yaml 中的 security.auth_enabled 控制
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from typing import Optional, List
import uuid

from app.shared.database import get_db
from app.shared.config import get_config
from app.shared.models import User, Role, Permission, UserSession

config = get_config()
router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# 尝试导入可选依赖
try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    PWD_CONTEXT_AVAILABLE = True
except ImportError:
    PWD_CONTEXT_AVAILABLE = False
    pwd_context = None


# =============================================================================
# Pydantic Models
# =============================================================================

class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = Field(None, max_length=100)
    role_ids: List[int] = []
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)  # 管理员重置密码


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    roles: List[dict]
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: Optional[str] = None  # 返回数据库中的标准用户名


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


# =============================================================================
# Helper Functions
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    if not PWD_CONTEXT_AVAILABLE:
        # 预留模式：明文比较（仅开发测试用，需安装 passlib）
        return plain_password == hashed_password
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    if not PWD_CONTEXT_AVAILABLE:
        # 预留模式：返回明文
        return password
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌"""
    if not JWT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT 功能未安装，请安装 python-jose[cryptography]"
        )

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=config.security.jwt_access_token_expire_minutes))
    jti = str(uuid.uuid4())

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        config.security.jwt_secret,
        algorithm=config.security.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """解码 JWT 令牌

    Args:
        token: JWT token string

    Returns:
        decoded payload dict

    Raises:
        AuthenticationException: if token is invalid or JWT not available
    """
    if not JWT_AVAILABLE:
        from app.shared.exceptions import AuthenticationException
        raise AuthenticationException("JWT 功能未安装")
    try:
        payload = jwt.decode(
            token,
            config.security.jwt_secret,
            algorithms=[config.security.jwt_algorithm]
        )
        return payload
    except JWTError:
        from app.shared.exceptions import AuthenticationException
        raise AuthenticationException("Invalid token")


def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """从令牌获取当前用户"""
    # 如果认证未启用，返回 None
    if not config.security.auth_enabled:
        return None

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌数据",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 检查 Token 是否被撤销
    jti = payload.get("jti")
    if jti:
        revoked = db.query(UserSession).filter(
            UserSession.token_jti == jti,
            UserSession.revoked == True
        ).first()
        if revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已被撤销",
                headers={"WWW-Authenticate": "Bearer"}
            )

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user_from_token)
) -> User:
    """获取当前活跃用户（认证启用时）"""
    if not config.security.auth_enabled:
        # 认证关闭时返回模拟用户
        return None

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证"
        )
    return current_user


def _user_to_response(user: User) -> dict:
    """将 User 对象转换为响应字典"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": [{"id": r.id, "name": r.name, "description": r.description} for r in user.roles],
        "last_login": user.last_login,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }


# =============================================================================
# Testable Helper Functions (用于测试的直接调用接口)
# =============================================================================

def create_user(user_data: dict, db: Session) -> dict:
    """创建新用户（供测试直接调用的函数版本）

    Args:
        user_data: 用户数据字典，包含 username, password, email 等
        db: 数据库会话

    Returns:
        创建的用户信息字典

    Raises:
        ConflictException: 用户名或邮箱已存在
    """
    from app.shared.exceptions import ConflictException

    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == user_data.get("username")).first()
    if existing:
        raise ConflictException(f"用户名 '{user_data.get('username')}' already exists")

    # 检查邮箱是否已存在
    email = user_data.get("email")
    if email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise ConflictException(f"邮箱 '{email}' already exists")

    # 创建用户
    user = User(
        username=user_data["username"],
        email=email,
        password_hash=get_password_hash(user_data["password"]),
        full_name=user_data.get("full_name"),
        is_active=user_data.get("is_active", True),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
    }


def login_user(username: str, password: str, db: Session) -> dict:
    """用户登录（供测试直接调用的函数版本）

    Args:
        username: 用户名
        password: 明文密码
        db: 数据库会话

    Returns:
        包含 access_token 的字典

    Raises:
        AuthenticationException: 用户名或密码错误
    """
    from app.shared.exceptions import AuthenticationException

    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        raise AuthenticationException("用户名或密码错误")

    if not user.is_active:
        raise AuthenticationException("用户已被禁用")

    # 创建访问令牌
    access_token_expires = timedelta(minutes=config.security.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )

    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.security.jwt_access_token_expire_minutes * 60,
    }


# =============================================================================
# Authentication Endpoints
# =============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录

    - 认证关闭时：返回模拟令牌，始终成功
    - 认证启用时：验证用户名密码
    """
    # 认证关闭时的预留模式
    if not config.security.auth_enabled:
        return {
            "access_token": "placeholder_token_auth_disabled",
            "token_type": "bearer",
            "expires_in": 3600
        }

    # 认证启用时的正常流程
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    # 创建访问令牌
    access_token_expires = timedelta(minutes=config.security.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )

    # 更新最后登录时间
    user.last_login = datetime.utcnow()

    # 记录会话
    payload = decode_token(access_token)
    if payload:
        session = UserSession(
            user_id=user.id,
            token_jti=payload.get("jti"),
            token_type="access",
            expires_at=datetime.utcfromtimestamp(payload.get("exp")),
            revoked=False
        )
        db.add(session)

    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.security.jwt_access_token_expire_minutes * 60,
        "username": user.username  # 返回数据库中的标准用户名
    }


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    用户登出

    将令牌加入黑名单
    """
    if not config.security.auth_enabled:
        return {"message": "登出成功（认证未启用）"}

    if not credentials:
        return {"message": "登出成功"}

    token = credentials.credentials
    payload = decode_token(token)

    if payload and "jti" in payload:
        revoked_session = db.query(UserSession).filter(
            UserSession.token_jti == payload["jti"]
        ).first()
        if revoked_session:
            revoked_session.revoked = True
            revoked_session.revoked_at = datetime.utcnow()
            db.commit()

    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """获取当前登录用户信息"""
    if not config.security.auth_enabled:
        # 预留模式：返回模拟超级管理员
        return {
            "id": 0,
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "System Administrator",
            "is_active": True,
            "is_superuser": True,
            "roles": [{"id": 1, "name": "admin", "description": "系统管理员"}],
            "last_login": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")

    return _user_to_response(current_user)


# =============================================================================
# User CRUD Endpoints
# =============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    query = db.query(User).options(joinedload(User.roles))

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.offset(skip).limit(limit).all()
    return [_user_to_response(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户详情"""
    user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return _user_to_response(user)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def _create_user_endpoint(user_data: UserCreate, db: Session = Depends(get_db)):
    """创建新用户"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否已存在
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已存在")

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=user_data.is_active
    )

    # 分配角色
    if user_data.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
        user.roles = roles

    db.add(user)
    db.commit()
    db.refresh(user)

    return _user_to_response(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新邮箱
    if user_data.email is not None:
        if user_data.email != user.email:
            existing = db.query(User).filter(User.email == user_data.email).first()
            if existing:
                raise HTTPException(status_code=400, detail="邮箱已存在")
        user.email = user_data.email

    # 更新全名
    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    # 更新激活状态
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    # 更新角色
    if user_data.role_ids is not None:
        roles = db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
        user.roles = roles

    # 重置密码（管理员功能）
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _user_to_response(user)


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.is_superuser:
        raise HTTPException(status_code=403, detail="不能删除超级用户")

    db.delete(user)
    db.commit()

    return {"message": "用户删除成功"}


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    if not config.security.auth_enabled:
        return {"message": "密码修改成功（认证未启用）"}

    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")

    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    # 更新密码
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "密码修改成功"}


@router.get("/status")
async def get_auth_status():
    """获取认证系统状态"""
    return {
        "auth_enabled": config.security.auth_enabled,
        "jwt_available": JWT_AVAILABLE,
        "password_hash_available": PWD_CONTEXT_AVAILABLE,
        "version": "1.0.0"
    }


@router.get("/roles")
async def list_roles(db: Session = Depends(get_db)):
    """获取角色列表"""
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]
