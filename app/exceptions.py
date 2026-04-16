"""
集中式异常处理模块

提供统一的异常类层次结构和异常处理器，用于全局错误处理。
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI


class AppException(Exception):
    """应用基础异常类

    所有自定义应用异常都应继承此类
    """
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ResourceNotFoundException(AppException):
    """资源不存在异常

    当请求的资源（设备、备份、故障记录等）不存在时抛出
    """
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", 404)


class DeviceConnectionException(AppException):
    """设备连接异常

    当无法连接到网络设备时抛出
    """
    def __init__(self, message: str):
        super().__init__(message, 503)


class DeviceOperationException(AppException):
    """设备操作异常

    当设备操作（备份、配置部署等）失败时抛出
    """
    def __init__(self, message: str):
        super().__init__(message, 500)


class ValidationException(AppException):
    """验证异常

    当输入数据验证失败时抛出
    """
    def __init__(self, message: str):
        super().__init__(message, 400)


class AuthenticationException(AppException):
    """认证异常

    当用户认证失败时抛出
    """
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)


class AuthorizationException(AppException):
    """授权异常

    当用户没有权限执行操作时抛出
    """
    def __init__(self, message: str = "Authorization failed"):
        super().__init__(message, 403)


class ConflictException(AppException):
    """冲突异常

    当操作会导致数据冲突时抛出（如重复名称）
    """
    def __init__(self, message: str):
        super().__init__(message, 409)


# ============ 异常处理器 ============

async def app_exception_handler(request: Request, exc: AppException):
    """处理 AppException 及其子类异常

    返回统一的 JSON 错误响应格式
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.__class__.__name__,
            "path": str(request.url.path)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理 FastAPI 请求验证异常

    返回详细的验证错误信息
    """
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation failed",
            "details": exc.errors(),
            "path": str(request.url.path)
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """处理未预期的通用异常

    返回 500 错误，避免泄露敏感信息
    """
    from loguru import logger
    logger.error(f"Unhandled exception at {request.url.path}: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "InternalError",
            "path": str(request.url.path)
        }
    )


def register_exception_handlers(app: FastAPI):
    """注册所有异常处理器到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
