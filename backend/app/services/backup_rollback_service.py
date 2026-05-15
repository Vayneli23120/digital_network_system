"""
备份与回滚服务
"""
import asyncio
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.device import Device
from app.models.deploy import DeployTask, DeployDeviceRecord


class BackupService:
    """配置备份服务"""

    @staticmethod
    async def create_pre_deploy_backup(
        db: Session,
        task_id: str,
        device_ids: List[int]
    ) -> dict:
        """
        部署前自动创建配置备份

        Args:
            db: 数据库会话
            task_id: 部署任务ID
            device_ids: 设备ID列表

        Returns:
            dict: {device_id: backup_id, ...}
        """
        backup_map = {}

        for device_id in device_ids:
            try:
                device = db.query(Device).filter(Device.id == device_id).first()
                if not device:
                    continue

                # 创建设备配置备份
                backup_result = await BackupService._backup_device_config(
                    db=db,
                    device=device,
                    backup_type='auto_pre_deploy',
                    task_id=task_id
                )

                backup_map[device_id] = backup_result.get('backup_id')

            except Exception as e:
                print(f"Failed to backup device {device_id}: {e}")
                continue

        return backup_map

    @staticmethod
    async def _backup_device_config(
        db: Session,
        device: Device,
        backup_type: str,
        task_id: str
    ) -> dict:
        """备份单个设备配置"""
        # 模拟备份配置（实际实现需连接设备获取配置）
        await asyncio.sleep(0.5)  # 模拟网络延迟

        # 这里应该连接设备并获取当前配置
        config_content = f"! Backup of {device.name} ({device.ip})\n"
        config_content += f"! Created at {datetime.now().isoformat()}\n"
        config_content += f"! Task ID: {task_id}\n"
        config_content += "!\n"
        config_content += "hostname " + device.name + "\n"
        # ... 更多配置

        # 创建备份记录
        backup_id = f"backup_{device.id}_{int(datetime.now().timestamp())}"

        return {
            'backup_id': backup_id,
            'device_id': device.id,
            'device_name': device.name,
            'backup_type': backup_type,
            'created_at': datetime.now().isoformat()
        }


class RollbackService:
    """配置回滚服务"""

    @staticmethod
    async def auto_rollback_on_failure(
        db: Session,
        task_id: str,
        device_backup_map: dict,
        failed_devices: List[int],
        cli_callback=None
    ) -> dict:
        """
        部署失败时自动回滚

        Args:
            db: 数据库会话
            task_id: 部署任务ID
            device_backup_map: {device_id: backup_id} 映射
            failed_devices: 失败的设备ID列表
            cli_callback: CLI输出回调

        Returns:
            dict: 回滚结果
        """
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }

        if cli_callback:
            cli_callback("", "info")
            cli_callback("=" * 60, "warning")
            cli_callback("DEPLOYMENT FAILED - INITIATING AUTOMATIC ROLLBACK", "warning")
            cli_callback("=" * 60, "warning")
            cli_callback("", "info")

        for device_id in failed_devices:
            backup_id = device_backup_map.get(device_id)

            if not backup_id:
                results['skipped'].append({
                    'device_id': device_id,
                    'reason': 'No backup found'
                })
                continue

            try:
                device = db.query(Device).filter(Device.id == device_id).first()
                if not device:
                    continue

                if cli_callback:
                    cli_callback(f"Rolling back {device.name} ({device.ip})...", "info")

                # 执行回滚
                rollback_result = await RollbackService._rollback_device(
                    db=db,
                    device=device,
                    backup_id=backup_id,
                    cli_callback=cli_callback
                )

                if rollback_result['success']:
                    results['success'].append({
                        'device_id': device_id,
                        'device_name': device.name,
                        'backup_id': backup_id
                    })
                    if cli_callback:
                        cli_callback(f"Rollback successful for {device.name}", "success")
                else:
                    results['failed'].append({
                        'device_id': device_id,
                        'device_name': device.name,
                        'reason': rollback_result.get('error', 'Unknown error')
                    })
                    if cli_callback:
                        cli_callback(f"Rollback failed for {device.name}: {rollback_result.get('error')}", "error")

            except Exception as e:
                results['failed'].append({
                    'device_id': device_id,
                    'reason': str(e)
                })
                if cli_callback:
                    cli_callback(f"Rollback exception for device {device_id}: {str(e)}", "error")

        if cli_callback:
            cli_callback("", "info")
            cli_callback(f"Rollback completed: {len(results['success'])} success, {len(results['failed'])} failed", "info")

        return results

    @staticmethod
    async def _rollback_device(
        db: Session,
        device: Device,
        backup_id: str,
        cli_callback=None
    ) -> dict:
        """回滚单个设备配置"""
        try:
            # 获取备份配置
            # 实际实现需要从备份存储中读取配置

            if cli_callback:
                cli_callback(f"Restoring configuration from backup {backup_id}...", "info")
                await asyncio.sleep(0.5)
                cli_callback("Loading backup configuration...", "info")
                await asyncio.sleep(0.5)
                cli_callback("Applying configuration...", "info")
                await asyncio.sleep(1)
                cli_callback("Verifying configuration...", "info")
                await asyncio.sleep(0.5)
                cli_callback("Configuration restored successfully", "success")

            return {
                'success': True,
                'device_id': device.id,
                'backup_id': backup_id,
                'message': 'Configuration restored successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'device_id': device.id,
                'error': str(e)
            }

    @staticmethod
    async def manual_rollback(
        db: Session,
        task_id: str,
        device_ids: Optional[List[int]] = None
    ) -> dict:
        """
        手动回滚部署

        Args:
            db: 数据库会话
            task_id: 部署任务ID
            device_ids: 指定要回滚的设备，None表示全部

        Returns:
            dict: 回滚结果
        """
        # 获取任务信息
        task = db.query(DeployTask).filter(DeployTask.id == task_id).first()
        if not task:
            return {'success': False, 'error': 'Task not found'}

        # 获取备份映射
        # 实际应从数据库或存储中读取
        device_backup_map = {}  # {device_id: backup_id}

        # 如果没有指定设备，回滚所有失败的设备
        if device_ids is None:
            device_ids = [d['device_id'] for d in task.summary.get('failed_devices', [])]

        return await RollbackService.auto_rollback_on_failure(
            db=db,
            task_id=task_id,
            device_backup_map=device_backup_map,
            failed_devices=device_ids,
            cli_callback=None
        )


class ApprovalService:
    """审批服务"""

    @staticmethod
    def check_requires_approval(deploy_data: dict, devices: list) -> tuple:
        """
        检查是否需要审批

        Returns:
            (requires_approval: bool, approval_level: ApprovalLevel)
        """
        is_production = deploy_data.get('is_production', False)
        device_count = len(devices)

        # 生产环境 + 多设备 = 需要审批
        if is_production and device_count >= 1:
            return True, ApprovalLevel.LEVEL_1

        # 大量设备 = 需要审批
        if device_count >= 10:
            return True, ApprovalLevel.LEVEL_1

        # 核心设备 = 需要高级审批
        core_patterns = ['core', 'border', 'wan', 'internet']
        has_core_device = any(
            any(pattern in (d.name or '').lower() for pattern in core_patterns)
            or any(pattern in (d.ip or '').lower() for pattern in core_patterns)
            for d in devices
        )

        if has_core_device:
            return True, ApprovalLevel.LEVEL_2

        return False, ApprovalLevel.NONE

    @staticmethod
    async def create_approval_request(
        db: Session,
        task_id: str,
        requester_id: int,
        approval_level: ApprovalLevel,
        deploy_data: dict
    ) -> dict:
        """创建审批请求"""
        from app.models.approval import DeployApproval, ApprovalStatus

        approval = DeployApproval(
            task_id=task_id,
            approval_level=approval_level,
            status=ApprovalStatus.PENDING_APPROVAL,
            requester_id=requester_id,
            requested_at=datetime.now()
        )

        db.add(approval)
        db.commit()
        db.refresh(approval)

        # 发送通知
        await ApprovalService._send_approval_notification(
            db=db,
            approval=approval,
            notification_type='approval_request'
        )

        return {
            'success': True,
            'approval_id': approval.id,
            'status': approval.status.value
        }

    @staticmethod
    async def approve_deployment(
        db: Session,
        approval_id: int,
        approver_id: int,
        comment: Optional[str] = None
    ) -> dict:
        """批准部署"""
        from app.models.approval import DeployApproval, ApprovalStatus

        approval = db.query(DeployApproval).filter(DeployApproval.id == approval_id).first()
        if not approval:
            return {'success': False, 'error': 'Approval request not found'}

        if approval.status != ApprovalStatus.PENDING_APPROVAL:
            return {'success': False, 'error': f'Invalid status: {approval.status}'}

        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = approver_id
        approval.approved_at = datetime.now()
        approval.approval_comment = comment

        # 更新审批链
        approval.approval_chain.append({
            'level': approval.approval_level.value,
            'approver_id': approver_id,
            'status': 'approved',
            'comment': comment,
            'time': datetime.now().isoformat()
        })

        db.commit()

        # 发送通知
        await ApprovalService._send_approval_notification(
            db=db,
            approval=approval,
            notification_type='approved'
        )

        return {
            'success': True,
            'message': 'Deployment approved',
            'can_execute': True
        }

    @staticmethod
    async def reject_deployment(
        db: Session,
        approval_id: int,
        approver_id: int,
        reason: str
    ) -> dict:
        """拒绝部署"""
        from app.models.approval import DeployApproval, ApprovalStatus

        approval = db.query(DeployApproval).filter(DeployApproval.id == approval_id).first()
        if not approval:
            return {'success': False, 'error': 'Approval request not found'}

        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = approver_id
        approval.approved_at = datetime.now()
        approval.rejection_reason = reason

        # 更新审批链
        approval.approval_chain.append({
            'level': approval.approval_level.value,
            'approver_id': approver_id,
            'status': 'rejected',
            'comment': reason,
            'time': datetime.now().isoformat()
        })

        db.commit()

        # 发送通知
        await ApprovalService._send_approval_notification(
            db=db,
            approval=approval,
            notification_type='rejected'
        )

        return {'success': True, 'message': 'Deployment rejected'}

    @staticmethod
    async def _send_approval_notification(db, approval, notification_type: str):
        """发送审批通知（模拟）"""
        # 实际实现应集成邮件/企业微信/钉钉
        print(f"[NOTIFICATION] {notification_type}: Approval {approval.id}")
        await asyncio.sleep(0.1)
