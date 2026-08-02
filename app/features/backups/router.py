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
from .netmiko_service import backup_device_config
from .schemas import BatchBackupRequest
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


@router.post("/backup/{device_id}")
async def backup_device(
    device_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_execute),
):
    """备份单个设备配置"""
    operator = principal.username
    start_time = time.time()
    device = None

    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")

        # 从凭证组获取 SSH 凭证
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
                detail="未配置 SSH 凭证，请先在凭证管理页面添加凭证组"
            )

        credentials = {
            "username": cred_group.username,
            "password": decrypt_password(cred_group.password_encrypted),
            "secret": decrypt_password(cred_group.enable_password_encrypted) if cred_group.enable_password_encrypted else ""
        }

        # 检查凭证是否完整
        if not credentials["username"]:
            raise HTTPException(
                status_code=500,
                detail=f"凭证组 '{cred_group_name}' 未设置用户名"
            )
        if not credentials["password"]:
            raise HTTPException(
                status_code=500,
                detail=f"凭证组 '{cred_group_name}' 未设置密码"
            )

        # 执行备份（经统一设备操作执行器）
        config = get_config()
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


@router.post("/backup/{device_id}/async")
async def backup_device_async(
    device_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    _: None = Depends(require_backup_execute),
):
    """
    异步备份设备配置（推荐方式）

    将备份任务提交到 Celery 队列，返回 job_id 供轮询状态。
    适用场景：大批量备份、长时间操作、避免阻塞 HTTP 请求。
    """
    from app.shared.models_jobs import Job, JobType, JobStatus, create_job
    from app.tasks.backup_tasks import backup_device as backup_task

    # 检查设备是否存在
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 创建 Job 记录
    job = create_job(
        db,
        job_type=JobType.BACKUP,
        device_id=device_id,
        operator=principal.username,
        parameters={"device_name": device.name, "ip": device.ip}
    )

    # 提交 Celery 任务
    try:
        backup_task.delay(
            job_id=job.id,
            device_id=device_id,
            operator=principal.username,
        )
    except Exception as e:
        # Celery 可能不可用，回退到同步模式
        logger.warning(f"Celery unavailable, falling back to sync: {e}")
        job.status = JobStatus.FAILED
        job.error_message = f"Celery unavailable: {e}"
        db.commit()
        raise HTTPException(status_code=503, detail="任务队列不可用，请使用同步备份接口")

    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "message": "备份任务已提交到队列",
        "device_id": device_id,
        "device_name": device.name,
    }


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
    """批量备份设备配置"""
    device_ids = request.root
    operator = principal.username
    try:
        devices = db.query(Device).filter(Device.id.in_(device_ids)).all()

        # 一次性加载所有凭证组
        all_cred_groups = db.query(CredentialGroup).all()
        cred_group_map = {g.name: g for g in all_cred_groups}

        results = []

        for device in devices:
            start_time = time.time()

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

            config = get_config()
            result = await run_device_op(
                backup_device_config,
                device,
                credentials,
                config.storage.backup_dir,
            )

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