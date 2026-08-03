"""Backup management router"""

import asyncio
import difflib
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from loguru import logger
from sqlalchemy.orm import Session

from app.features.auth.identity import Principal, get_current_principal
from app.features.credentials.credential_service import decrypt_password
from app.shared.config import get_config
from app.shared.database import get_db
from app.shared.dependencies import require_permission
from app.shared.device_ops import run_device_op
from app.shared.models import BackupRecord, Device, CredentialGroup, LogEntry
from app.shared.time_utils import utc_iso
from .backup_service import delete_backup as svc_delete_backup
from .needs_backup import list_needs_backup, mark_devices_config_changed
from .netmiko_service import NetmikoAuthenticationException, backup_device_config
from .schemas import BackupRequest, BatchBackupRequest
from .security import (
    UnsafeBackupRecordPathError,
    delete_backup_file,
    read_backup_bytes,
    read_backup_text,
    resolve_backup_record_file,
    safe_backup_reference,
)

router = APIRouter(prefix="/api/backups", tags=["backups"])
require_backup_read = require_permission("backup:read")
require_backup_execute = require_permission("backup:execute")
require_backup_batch = require_permission("backup:batch")
require_backup_delete = require_permission("backup:delete")


def _operator_credentials(request) -> Optional[dict]:
    """从请求提取操作者会话级 SSH 凭证；未提供返回 None。

    部分填写视为错误（避免静默降级）；凭证仅存于请求/线程内存，不落库、不入日志。
    """
    if request is None:
        return None
    provided = any([request.username, request.password, request.secret])
    username = (request.username or "").strip()
    password = request.password or ""
    if provided and (not username or not password):
        raise HTTPException(status_code=400, detail="请完整填写操作者 SSH 凭证（用户名与密码必填）")
    if not username or not password:
        return None
    return {"username": username, "password": password, "secret": request.secret or ""}


@router.post("/backup/{device_id}")
async def backup_device(
    device_id: int,
    request: Optional[BackupRequest] = None,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_execute),
):
    """备份单个设备配置（同步）。

    默认（credential_session_required=True）必须携带操作者会话级 SSH 凭证，
    密码仅存于请求内存、不落库不入日志；未提供返回 400。
    仅当管理员显式关闭开关（credential_session_required=False）才降级回退
    服务器存储的凭证组。
    """
    operator = principal.username
    start_time = time.time()
    device = None

    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")

        config = get_config()
        credentials = _operator_credentials(request)
        if credentials is not None:
            # 操作者会话级凭证（仅内存，不落库不入日志）
            cred_group_name = "操作者会话凭证"
        elif config.security.credential_session_required:
            raise HTTPException(
                status_code=400,
                detail="请使用操作者 SSH 凭证（密码不存储在服务器上）"
            )
        else:
            # 显式降级：服务器存储的凭证组
            cred_group_name = device.credential_group or "default"
            cred_group = db.query(CredentialGroup).filter(
                CredentialGroup.name == cred_group_name
            ).first()
            if not cred_group:
                cred_group = db.query(CredentialGroup).filter(
                    CredentialGroup.name == "default"
                ).first()
            if not cred_group:
                raise HTTPException(
                    status_code=500,
                    detail="未配置 SSH 凭证，请改用操作者凭证或先添加凭证组"
                )
            credentials = {
                "username": cred_group.username,
                "password": decrypt_password(cred_group.password_encrypted),
                "secret": decrypt_password(cred_group.enable_password_encrypted) if cred_group.enable_password_encrypted else ""
            }

        # 检查凭证是否完整（操作者凭证不完整已在 _operator_credentials 拦截）
        if not credentials.get("username") or not credentials.get("password"):
            raise HTTPException(
                status_code=400,
                detail="请完整填写操作者 SSH 凭证（用户名与密码必填）"
            )

        # 执行备份（经统一设备操作执行器）
        result = await run_device_op(
            backup_device_config,
            device,
            credentials,
            config.storage.backup_dir,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # 创建工具日志记录
        log_entry = LogEntry(
            tool_type="netmiko",
            operation="备份配置",
            target=device.name,
            status="success" if result["success"] else "failed",
            log_content=f"[INFO] 开始备份设备配置: {device.name} ({device.ip})\n"
                       f"[INFO] 使用凭证组: {cred_group_name}\n"
                       f"[INFO] 执行命令: show running-config\n"
                       f"[{result['success'] if result['success'] else 'ERROR'}] {result['message']}\n"
                       f"[INFO] 耗时: {duration_ms}ms\n"
                       f"[INFO] 文件大小: {result.get('file_size', 0)} bytes\n"
                       f"[INFO] MD5: {result.get('md5_hash', 'N/A')}\n"
                       f"[INFO] 配置变更: {'有' if result.get('has_change') else '无'}",
            duration_ms=duration_ms,
            created_by=operator,
        )
        db.add(log_entry)

        if result["success"]:
            # 记录备份记录
            backup_record = BackupRecord(
                device_id=device.id,
                device_name=device.name,
                backup_file=result["file_path"],
                file_size=result["file_size"],
                md5_hash=result["md5_hash"],
                has_change=result["has_change"],
                operator=operator,
            )
            db.add(backup_record)

            # 更新设备最后备份时间
            device.last_backup_time = datetime.utcnow()

            db.commit()

            # 提交到 Git 版本控制
            try:
                from app.shared.git_config_service import get_git_config_service
                git_service = get_git_config_service()
                if git_service.available:
                    git_commit = await asyncio.to_thread(
                        git_service.commit_backup,
                        device_name=device.name,
                        backup_file=result["file_path"],
                        has_change=result["has_change"],
                        operator=operator,
                    )
                    log_entry.log_content += f"\n[INFO] Git commit: {git_commit[:8] if git_commit else 'N/A'}"
                    db.commit()
            except Exception as git_err:
                logger.warning(f"Git 版本控制失败（不影响备份）: {git_err}")

            # 清除 Dashboard 缓存
            from app.shared.cache import cache
            cache.invalidate_prefix("dashboard:")

            return {"success": True, "message": result["message"], "backup_id": backup_record.id, "log_id": log_entry.id}
        else:
            # 发送多渠道告警
            from app.services.notification_service import get_notification_service
            await asyncio.to_thread(
                get_notification_service().notify_backup_failure,
                device.name,
                result["message"],
                operator,
            )

            db.commit()

            # 清除 Dashboard 缓存
            from app.shared.cache import cache
            cache.invalidate_prefix("dashboard:")

            raise HTTPException(status_code=500, detail="备份失败，请查看服务端日志")

    except HTTPException:
        # HTTPException 直接重新抛出，不拦截
        raise

    except NetmikoAuthenticationException:
        # SSH 认证失败：记录日志并返回 401（消息不含任何口令）
        db.rollback()
        log_entry = LogEntry(
            tool_type="netmiko",
            operation="备份配置",
            target=device.name if device else f"device_id:{device_id}",
            status="failed",
            log_content=f"[ERROR] SSH 认证失败: {device.name if device else device_id} ({device.ip if device else 'unknown'})\n[INFO] 耗时: {int((time.time() - start_time) * 1000)}ms",
            duration_ms=int((time.time() - start_time) * 1000),
            created_by=operator,
        )
        db.add(log_entry)
        db.commit()
        raise HTTPException(status_code=401, detail="SSH 认证失败，请检查操作者凭证")

    except Exception:
        # 记录失败日志
        db.rollback()
        duration_ms = int((time.time() - start_time) * 1000)
        log_entry = LogEntry(
            tool_type="netmiko",
            operation="备份配置",
            target=device.name if device else f"device_id:{device_id}",
            status="failed",
            log_content=f"[ERROR] 备份失败，详见服务端日志\n[INFO] 耗时: {duration_ms}ms",
            duration_ms=duration_ms,
            created_by=operator,
        )
        db.add(log_entry)
        db.commit()
        raise HTTPException(status_code=500, detail="备份失败，请查看服务端日志")


# 注：异步备份端点已下线（celery worker 无法携带操作者会话级凭证，
# 与「密码不存储在服务器上」原则互斥）。备份统一走同步端点。


@router.get("/needs-backup")
async def list_needs_backup_endpoint(
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_read),
):
    """需备份设备统一列表（备份不再自动，改为提醒）。

    - config_changed：配置已变更（部署成功/手动标记）且尚未备份
    - backup_overdue：超过 backup_reminder_days 天未备份
    由管理员批量备份。
    """
    return {"items": list_needs_backup(db)}


@router.get("")
async def list_backups(
    device_id: Optional[int] = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_read),
):
    """获取备份记录列表"""
    from .backup_service import list_backups as svc_list_backups
    result = svc_list_backups(db, device_id=device_id, skip=skip, limit=limit)
    for item in result["items"]:
        try:
            item["backup_file"] = safe_backup_reference(item["backup_file"])
        except UnsafeBackupRecordPathError:
            item["backup_file"] = None
    return result


@router.get("/{backup_id}/content")
async def get_backup_content(
    backup_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_read),
):
    """获取备份配置内容"""
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    try:
        content = await asyncio.to_thread(read_backup_text, backup.backup_file)
    except UnsafeBackupRecordPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="备份文件不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return {
        "backup_id": backup_id,
        "device_name": backup.device_name,
        "backup_time": utc_iso(backup.backup_time),
        "content": content
    }


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_read),
):
    """下载受管备份文件。"""
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    try:
        content = await asyncio.to_thread(read_backup_bytes, backup.backup_file)
    except UnsafeBackupRecordPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="备份文件不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="backup-{backup_id}.cfg"'
        },
    )


@router.get("/{backup_id}/diff")
async def get_backup_diff(
    backup_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_read),
):
    """获取配置差异对比"""
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    prev_backup = db.query(BackupRecord).filter(
        BackupRecord.device_id == backup.device_id,
        BackupRecord.backup_time < backup.backup_time
    ).order_by(BackupRecord.backup_time.desc()).first()

    if not prev_backup:
        return {"diff": "这是第一个备份，没有可对比的配置"}

    try:
        new_content, old_content = await asyncio.gather(
            asyncio.to_thread(read_backup_text, backup.backup_file),
            asyncio.to_thread(read_backup_text, prev_backup.backup_file),
        )
    except UnsafeBackupRecordPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="备份文件不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    new_lines = new_content.splitlines(keepends=True)
    old_lines = old_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"backup-{prev_backup.id}",
        tofile=f"backup-{backup.id}",
        lineterm=""
    )

    return {
        "backup_id": backup_id,
        "prev_backup_id": prev_backup.id,
        "diff": "".join(diff)
    }


@router.post("/batch")
async def batch_backup(
    request: BatchBackupRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_batch),
):
    """批量备份设备配置（同步，同批一次输入操作者凭证）。

    默认（credential_session_required=True）必须携带操作者会话级 SSH 凭证；
    逐台执行，认证失败的设备标记 auth_failed（不中断整批），便于单独重试。
    仅当管理员显式关闭开关才降级回退服务器存储的凭证组。
    """
    device_ids = request.device_ids
    operator = principal.username
    operator_creds = _operator_credentials(request)
    config = get_config()
    results = []
    try:
        devices = db.query(Device).filter(Device.id.in_(device_ids)).all()

        if operator_creds is None and config.security.credential_session_required:
            raise HTTPException(
                status_code=400,
                detail="请使用操作者 SSH 凭证（密码不存储在服务器上）"
            )

        # 显式降级时才一次性加载凭证组
        all_cred_groups = db.query(CredentialGroup).all()
        cred_group_map = {g.name: g for g in all_cred_groups}

        for device in devices:
            start_time = time.time()

            if operator_creds is not None:
                credentials = operator_creds
            else:
                cred_group_name = device.credential_group or "default"
                cred_group = cred_group_map.get(cred_group_name) or cred_group_map.get("default")
                if cred_group:
                    credentials = {
                        "username": cred_group.username,
                        "password": decrypt_password(cred_group.password_encrypted),
                        "secret": decrypt_password(cred_group.enable_password_encrypted) if cred_group.enable_password_encrypted else ""
                    }
                else:
                    credentials = {"username": "admin", "password": "", "secret": ""}

            try:
                result = await run_device_op(
                    backup_device_config,
                    device,
                    credentials,
                    config.storage.backup_dir,
                )
            except NetmikoAuthenticationException:
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": False,
                    "auth_failed": True,
                    "message": "SSH 认证失败，请检查操作者凭证",
                })
                continue

            duration_ms = int((time.time() - start_time) * 1000)

            # 记录工具日志
            log_entry = LogEntry(
                tool_type="netmiko",
                operation="批量备份配置",
                target=device.name,
                status="success" if result["success"] else "failed",
                log_content=f"[INFO] 批量备份: {device.name} ({device.ip})\n"
                           f"[{result['success'] if result['success'] else 'ERROR'}] {result['message']}\n"
                           f"[INFO] 耗时: {duration_ms}ms",
                duration_ms=duration_ms,
                created_by=operator,
            )
            db.add(log_entry)

            if result["success"]:
                backup_record = BackupRecord(
                    device_id=device.id,
                    device_name=device.name,
                    backup_file=result["file_path"],
                    file_size=result["file_size"],
                    md5_hash=result["md5_hash"],
                    has_change=result["has_change"],
                    operator=operator,
                )
                db.add(backup_record)
                device.last_backup_time = datetime.utcnow()

            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "success": result["success"],
                "message": (
                    result["message"]
                    if result["success"]
                    else "备份失败，请查看服务端日志"
                ),
            })

        db.commit()

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {"results": results}
    except Exception:
        db.rollback()
        raise


@router.post("/mark-config-changed")
async def mark_config_changed(
    request: BatchBackupRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_execute),
):
    """手动标记设备配置已变更（离系统外改动），使其进入需备份列表。"""
    count = mark_devices_config_changed(db, request.device_ids, source=principal.username)
    return {"marked": count, "device_ids": request.device_ids}


@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_delete),
):
    """删除备份记录及其受管文件。"""
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    try:
        backup_path = resolve_backup_record_file(backup.backup_file, must_exist=False)
    except UnsafeBackupRecordPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = svc_delete_backup(db, backup_id)
    if backup_path.exists():
        try:
            await asyncio.to_thread(delete_backup_file, backup_path)
        except OSError:
            logger.warning("备份记录已删除，但文件清理失败")
    return result