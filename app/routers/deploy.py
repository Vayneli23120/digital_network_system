"""Configuration deployment router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from datetime import datetime
from loguru import logger
from jinja2 import Template

from ..database import get_db
from ..models import Device, ConfigTemplate, CredentialGroup, BackupRecord, AuditLog
from ..services.credential_service import decrypt_password
from ..services.deploy_service import get_deploy_service

router = APIRouter(prefix="/api/deploy", tags=["deploy"])


@router.post("/preview")
async def preview_deploy(deploy_data: dict):
    """
    预览配置部署变更

    请求体:
    {
        "mode": "backup" | "template",  # 部署模式
        "backup_file": "备份文件路径",    # mode=backup 时使用
        "template_id": 模板 ID,           # mode=template 时使用
        "variables": {"变量名": "变量值"}, # 模板变量
        "target_devices": [设备 ID 列表]
    }
    """
    db: Session = next(get_db())

    try:
        mode = deploy_data.get('mode', 'backup')
        target_device_ids = deploy_data.get('target_devices', [])
        variables = deploy_data.get('variables', {})

        if not target_device_ids:
            raise HTTPException(status_code=400, detail="请选择至少一台设备")

        # 获取设备列表
        devices = db.query(Device).filter(Device.id.in_(target_device_ids)).all()
        if not devices:
            raise HTTPException(status_code=404, detail="未找到指定的设备")

        # 获取凭证组列表
        credential_groups_data = db.query(CredentialGroup).all()
        credential_groups = [
            {
                'id': g.id,
                'name': g.name,
                'username': g.username,
                'password': decrypt_password(g.password_encrypted),
                'enable_password': decrypt_password(g.enable_password_encrypted) if g.enable_password_encrypted else None
            }
            for g in credential_groups_data
        ]

        # 获取配置内容
        config_content = None
        if mode == 'backup':
            backup_file = deploy_data.get('backup_file')
            if not backup_file:
                raise HTTPException(status_code=400, detail="请选择备份文件")

            # 从备份文件读取配置
            backup_path = Path(backup_file)
            if not backup_path.exists():
                backup_path = Path(f"./backups/{backup_file}")

            if not backup_path.exists():
                raise HTTPException(status_code=404, detail=f"备份文件不存在：{backup_file}")

            with open(backup_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

        elif mode == 'template':
            template_id = deploy_data.get('template_id')
            if not template_id:
                raise HTTPException(status_code=400, detail="请选择配置模板")

            template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
            if not template:
                raise HTTPException(status_code=404, detail=f"模板不存在：{template_id}")

            # 渲染模板
            tmpl = Template(template.template_content)
            context = {
                'now': datetime.utcnow,
                'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }
            context.update(variables)
            config_content = tmpl.render(**context)

        else:
            raise HTTPException(status_code=400, detail=f"不支持的部署模式：{mode}")

        # 使用部署服务预览变更
        deploy_service = get_deploy_service()
        results = []

        for device in devices:
            device_dict = {
                'id': device.id,
                'name': device.name,
                'ip': device.ip,
                'device_type': 'cisco_ios',
                'credential_group': device.credential_group or 'default'
            }

            result = deploy_service.deploy_to_device(
                device=device_dict,
                config=config_content,
                credential_groups=credential_groups,
                dry_run=True
            )
            results.append(result)

        return {
            "success": True,
            "message": "预览完成",
            "results": results,
            "config_preview": config_content[:2000] + "..." if len(config_content) > 2000 else config_content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览部署失败：{e}")
        raise HTTPException(status_code=500, detail=f"预览失败：{str(e)}")
    finally:
        db.close()


@router.post("/execute")
async def execute_deploy(deploy_data: dict):
    """
    执行配置部署

    请求体:
    {
        "mode": "backup" | "template",
        "backup_file": "备份文件路径",
        "template_id": 模板 ID,
        "variables": {"变量名": "变量值"},
        "target_devices": [设备 ID 列表],
        "dry_run": false
    }
    """
    db: Session = next(get_db())

    try:
        mode = deploy_data.get('mode', 'backup')
        target_device_ids = deploy_data.get('target_devices', [])
        variables = deploy_data.get('variables', {})
        dry_run = deploy_data.get('dry_run', False)

        if not target_device_ids:
            raise HTTPException(status_code=400, detail="请选择至少一台设备")

        # 获取设备列表
        devices = db.query(Device).filter(Device.id.in_(target_device_ids)).all()
        if not devices:
            raise HTTPException(status_code=404, detail="未找到指定的设备")

        # 获取凭证组列表
        credential_groups_data = db.query(CredentialGroup).all()
        credential_groups = [
            {
                'id': g.id,
                'name': g.name,
                'username': g.username,
                'password': decrypt_password(g.password_encrypted),
                'enable_password': decrypt_password(g.enable_password_encrypted) if g.enable_password_encrypted else None
            }
            for g in credential_groups_data
        ]

        # 获取配置内容
        config_content = None
        if mode == 'backup':
            backup_file = deploy_data.get('backup_file')
            if not backup_file:
                raise HTTPException(status_code=400, detail="请选择备份文件")

            backup_path = Path(backup_file)
            if not backup_path.exists():
                backup_path = Path(f"./backups/{backup_file}")

            if not backup_path.exists():
                raise HTTPException(status_code=404, detail=f"备份文件不存在：{backup_file}")

            with open(backup_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

        elif mode == 'template':
            template_id = deploy_data.get('template_id')
            if not template_id:
                raise HTTPException(status_code=400, detail="请选择配置模板")

            template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
            if not template:
                raise HTTPException(status_code=404, detail=f"模板不存在：{template_id}")

            tmpl = Template(template.template_content)
            context = {
                'now': datetime.utcnow,
                'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }
            context.update(variables)
            config_content = tmpl.render(**context)

        else:
            raise HTTPException(status_code=400, detail=f"不支持的部署模式：{mode}")

        # 执行部署
        deploy_service = get_deploy_service()
        results = []
        success_count = 0
        failed_count = 0

        for device in devices:
            device_dict = {
                'id': device.id,
                'name': device.name,
                'ip': device.ip,
                'device_type': 'cisco_ios',
                'credential_group': device.credential_group or 'default'
            }

            result = deploy_service.deploy_to_device(
                device=device_dict,
                config=config_content,
                credential_groups=credential_groups,
                dry_run=dry_run
            )
            results.append(result)

            if result.get('success'):
                success_count += 1
            else:
                failed_count += 1

        # 记录审计日志
        for device, result in zip(devices, results):
            action = "deploy_config_dry_run" if dry_run else "deploy_config"
            details = f"部署模式：{mode}, 结果：{'成功' if result.get('success') else '失败'}"

            audit_log = AuditLog(
                operator="Web",
                action=action,
                target_type="device",
                target_id=device.id,
                details=details
            )
            db.add(audit_log)

        db.commit()

        return {
            "success": True,
            "message": f"部署完成：{success_count} 成功，{failed_count} 失败",
            "results": results,
            "summary": {
                "total": len(devices),
                "success": success_count,
                "failed": failed_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"执行部署失败：{e}")
        raise HTTPException(status_code=500, detail=f"部署失败：{str(e)}")
    finally:
        db.close()


@router.get("/compatible-variables")
async def get_compatible_variables():
    """
    获取所有兼容的变量列表和说明
    """
    return {
        "variables": [
            {"key": "HOSTNAME", "description": "设备主机名", "example": "SW-Access-01"},
            {"key": "ENABLE_SECRET", "description": "Enable 密码", "example": "YourPassword123"},
            {"key": "ADMIN_USERNAME", "description": "管理员用户名", "example": "admin"},
            {"key": "ADMIN_PASSWORD", "description": "管理员密码", "example": "YourAdminPass"},
            {"key": "DOMAIN_NAME", "description": "域名", "example": "company.local"},
            {"key": "MGMT_VLAN_ID", "description": "管理 VLAN ID", "example": "100"},
            {"key": "MGMT_IP", "description": "管理 IP 地址", "example": "192.168.1.10"},
            {"key": "MGMT_NETMASK", "description": "管理子网掩码", "example": "255.255.255.0"},
            {"key": "DEFAULT_GATEWAY", "description": "默认网关", "example": "192.168.1.1"},
            {"key": "SNMP_COMMUNITY", "description": "SNMP 团体名", "example": "public"},
            {"key": "LOCATION", "description": "设备位置", "example": "Building-A-Floor-2"},
            {"key": "CONTACT", "description": "联系人邮箱", "example": "network-admin@company.com"},
            {"key": "NTP_SERVER", "description": "NTP 服务器", "example": "10.0.0.1"},
            {"key": "SYSLOG_SERVER", "description": "Syslog 服务器", "example": "10.0.0.2"},
            {"key": "DEFAULT_ROUTE", "description": "默认路由下一跳", "example": "10.0.0.1"},
            {"key": "OSPF_ROUTER_ID", "description": "OSPF Router ID", "example": "1.1.1.1"},
            {"key": "ACCESS_PORT_RANGE", "description": "接入端口范围", "example": "GigabitEthernet1/0/1-48"},
            {"key": "UPLINK_PORT", "description": "上联端口", "example": "TenGigabitEthernet1/1/1"},
            {"key": "BUSINESS_VLAN_LIST", "description": "业务 VLAN 列表", "example": "10,20,30,100"},
            {"key": "TRUNK_VLANS", "description": "Trunk VLAN 范围", "example": "10,20,30,100,200"}
        ]
    }
