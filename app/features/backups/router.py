"""Backup management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path
import difflib
from datetime import datetime
import time

from app.shared.database import get_db
from app.shared.models import BackupRecord, Device, CredentialGroup, LogEntry
from .netmiko_service import backup_device_config
from app.features.credentials.credential_service import decrypt_password

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.post("/backup/{device_id}")
async def backup_device(device_id: int, operator: Optional[str] = None):
    """备份单个设备配置"""
    db: Session = next(get_db())
    start_time = time.time()

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

        # 执行备份
        from app.shared.config import get_config
        config = get_config()
        result = backup_device_config(device, credentials, config.storage.backup_dir)

        duration_ms = int((time.time() - start_time) * 1000)

        # 创建工具日志记录
        log_entry = LogEntry(
            tool_type="netmiko",
            operation="备份配置",
            target=device.name,
            status=result["success"] if result["success"] else "failed",
            log_content=f"[INFO] 开始备份设备配置: {device.name} ({device.ip})\n"
                       f"[INFO] 使用凭证组: {cred_group_name}\n"
                       f"[INFO] 执行命令: show running-config\n"
                       f"[{result['success'] if result['success'] else 'ERROR'}] {result['message']}\n"
                       f"[INFO] 耗时: {duration_ms}ms\n"
                       f"[INFO] 文件大小: {result.get('file_size', 0)} bytes\n"
                       f"[INFO] MD5: {result.get('md5_hash', 'N/A')}\n"
                       f"[INFO] 配置变更: {'有' if result.get('has_change') else '无'}",
            duration_ms=duration_ms,
            created_by=operator or "system"
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
                operator=operator
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
                    git_commit = git_service.commit_backup(
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
            get_notification_service().notify_backup_failure(device.name, result["message"], operator)

            db.commit()

            # 清除 Dashboard 缓存
            from app.shared.cache import cache
            cache.invalidate_prefix("dashboard:")

            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        # HTTPException 直接重新抛出，不拦截
        raise

    except Exception as e:
        # 记录失败日志
        duration_ms = int((time.time() - start_time) * 1000)
        log_entry = LogEntry(
            tool_type="netmiko",
            operation="备份配置",
            target=device.name if device else f"device_id:{device_id}",
            status="failed",
            log_content=f"[ERROR] 备份失败\n[ERROR] 错误信息: {str(e)}\n[INFO] 耗时: {duration_ms}ms",
            duration_ms=duration_ms,
            created_by=operator or "system"
        )
        db.add(log_entry)
        db.commit()

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/backup/{device_id}/async")
async def backup_device_async(
    device_id: int,
    operator: Optional[str] = "system",
    db: Session = Depends(get_db)
):
    """
    异步备份设备配置（推荐方式）

    将备份任务提交到 Celery 队列，返回 job_id 供轮询状态。
    适用场景：大批量备份、长时间操作、避免阻塞 HTTP 请求。
    """
    import uuid
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
        operator=operator or "system",
        parameters={"device_name": device.name, "ip": device.ip}
    )

    # 提交 Celery 任务
    try:
        backup_task.delay(job_id=job.id, device_id=device_id, operator=operator or "system")
    except Exception as e:
        # Celery 可能不可用，回退到同步模式
        from loguru import logger
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
async def list_backups(device_id: Optional[int] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """获取备份记录列表"""
    from .backup_service import list_backups as svc_list_backups
    return svc_list_backups(db, device_id=device_id, skip=skip, limit=limit)


@router.get("/{backup_id}/content")
async def get_backup_content(backup_id: int):
    """获取备份配置内容"""
    db: Session = next(get_db())
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    backup_path = Path(backup.backup_file)
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")

    with open(backup_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "backup_id": backup_id,
        "device_name": backup.device_name,
        "backup_time": backup.backup_time.isoformat(),
        "content": content
    }


@router.get("/{backup_id}/diff")
async def get_backup_diff(backup_id: int):
    """获取配置差异对比"""
    db: Session = next(get_db())
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    prev_backup = db.query(BackupRecord).filter(
        BackupRecord.device_id == backup.device_id,
        BackupRecord.backup_time < backup.backup_time
    ).order_by(BackupRecord.backup_time.desc()).first()

    if not prev_backup:
        return {"diff": "这是第一个备份，没有可对比的配置"}

    with open(backup.backup_file, "r", encoding="utf-8") as f:
        new_lines = f.readlines()
    with open(prev_backup.backup_file, "r", encoding="utf-8") as f:
        old_lines = f.readlines()

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=prev_backup.backup_file,
        tofile=backup.backup_file,
        lineterm=""
    )

    return {
        "backup_id": backup_id,
        "prev_backup_id": prev_backup.id,
        "diff": "".join(diff)
    }


@router.post("/batch")
async def batch_backup(device_ids: List[int], operator: Optional[str] = None):
    """批量备份设备配置"""
    db: Session = next(get_db())
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

            from app.shared.config import get_config
            config = get_config()
            result = backup_device_config(device, credentials, config.storage.backup_dir)

            duration_ms = int((time.time() - start_time) * 1000)

            # 记录工具日志
            log_entry = LogEntry(
                tool_type="netmiko",
                operation="批量备份配置",
                target=device.name,
                status=result["success"] if result["success"] else "failed",
                log_content=f"[INFO] 批量备份: {device.name} ({device.ip})\n"
                           f"[{result['success'] if result['success'] else 'ERROR'}] {result['message']}\n"
                           f"[INFO] 耗时: {duration_ms}ms",
                duration_ms=duration_ms,
                created_by=operator or "system"
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
                    operator=operator
                )
                db.add(backup_record)
                device.last_backup_time = datetime.utcnow()

            results.append({
                "device_name": device.name,
                "success": result["success"],
                "message": result["message"]
            })

        db.commit()

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {"results": results}
    finally:
        db.close()