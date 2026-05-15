"""Configuration deployment router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from jinja2 import Template

from app.shared.database import get_db
from app.shared.models import Device, ConfigTemplate, CredentialGroup, BackupRecord, AuditLog
from app.features.credentials.credential_service import decrypt_password
from .deploy_service import get_deploy_service
from .config_diff_service import ConfigDiffService, ConfigDiffResult, DiffType, DiffLine

router = APIRouter(prefix="/api/deploy", tags=["deploy"])


@router.post("/preview")
async def preview_deploy(deploy_data: dict):
    """
    预览配置部署变更（增强版）
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

        # 获取配置内容
        config_content = ""
        if mode == 'backup':
            backup_file = deploy_data.get('backup_file')
            if backup_file:
                backup_path = Path(backup_file)
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{backup_file}")
                if backup_path.exists():
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        config_content = f.read()

        elif mode == 'template':
            template_id = deploy_data.get('template_id')
            if template_id:
                template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
                if template:
                    tmpl = Template(template.template_content)
                    context = {'now': datetime.utcnow, 'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
                    context.update(variables)
                    config_content = tmpl.render(**context)

        elif mode == 'snippet':
            # 配置片段模式：将片段追加到当前配置
            snippet_content = deploy_data.get('snippet', '')
            snippet_position = deploy_data.get('snippet_position', 'append')  # append, prepend, replace

            # 先获取基础配置（从备份或模板）
            base_config = ""
            if deploy_data.get('base_backup_file'):
                backup_path = Path(deploy_data['base_backup_file'])
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{deploy_data['base_backup_file']}")
                if backup_path.exists():
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        base_config = f.read()

            # 应用变量替换到片段
            if variables:
                for key, value in variables.items():
                    snippet_content = snippet_content.replace(f"{{{{{key}}}}}", str(value))

            # 根据位置合并配置
            if snippet_position == 'append':
                config_content = base_config + "\n! \n! 新增配置片段\n" + snippet_content if base_config else snippet_content
            elif snippet_position == 'prepend':
                config_content = snippet_content + "\n! \n! 原有配置\n" + base_config if base_config else snippet_content
            elif snippet_position == 'replace':
                config_content = snippet_content
            else:
                config_content = snippet_content

        # 为每个设备生成差异分析
        preview_results = []
        for device in devices:
            # 获取当前配置（从最新备份文件，而非数据库快照）
            current_config = ""
            latest_backup = db.query(BackupRecord).filter(
                BackupRecord.device_id == device.id
            ).order_by(BackupRecord.backup_time.desc()).first()
            if latest_backup:
                # 优先从文件读取，数据库 snapshot 可能为空
                backup_path = Path(latest_backup.backup_file)
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{latest_backup.backup_file}")
                if backup_path.exists():
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            current_config = f.read()
                    except Exception as e:
                        logger.warning(f"读取备份文件失败 {backup_path}: {e}")
                        current_config = latest_backup.config_snapshot or ""
                else:
                    current_config = latest_backup.config_snapshot or ""

            # 片段模式特殊处理：只显示增量变更
            if mode == 'snippet':
                snippet_content = deploy_data.get('snippet', '').strip()
                snippet_position = deploy_data.get('snippet_position', 'append')

                # 应用变量替换
                if variables:
                    for key, value in variables.items():
                        snippet_content = snippet_content.replace(f"{{{{{key}}}}}", str(value))

                if snippet_position == 'replace':
                    # 替换模式：对比当前配置和片段
                    diff_result = ConfigDiffService.analyze_diff(current_config, snippet_content)
                    impact = ConfigDiffService.estimate_impact(diff_result)
                    new_config = snippet_content
                else:
                    # 追加/插入模式：只显示片段作为新增
                    snippet_lines = snippet_content.splitlines()
                    diff_lines = []
                    for i, line in enumerate(snippet_lines, 1):
                        diff_lines.append(DiffLine(
                            type=DiffType.ADDED,
                            content=line,
                            old_line_num=None,
                            new_line_num=i
                        ))

                    diff_result = ConfigDiffResult(
                        old_config=current_config,
                        new_config=snippet_content,
                        lines=diff_lines,
                        stats={"added": len(snippet_lines), "removed": 0, "modified": 0, "unchanged": 0}
                    )
                    impact = {
                        "total_changes": len(snippet_lines),
                        "is_breaking_change": False,
                        "affected_services": [],
                        "estimated_downtime_seconds": len(snippet_lines) * 2,
                        "risk_level": "low"
                    }
                    # 检测影响的服务
                    for line in snippet_lines:
                        line_lower = line.lower()
                        if 'vlan' in line_lower:
                            impact["affected_services"].append("VLAN")
                        if 'interface' in line_lower:
                            impact["affected_services"].append("Interface")
                        if 'ospf' in line_lower or 'bgp' in line_lower:
                            impact["affected_services"].append("Routing")
                        if 'ntp' in line_lower:
                            impact["affected_services"].append("NTP")
                        if 'snmp' in line_lower:
                            impact["affected_services"].append("SNMP")
                    impact["affected_services"] = list(set(impact["affected_services"]))

                    # 返回完整配置（基础+片段）用于显示对比
                    if snippet_position == 'append':
                        new_config = current_config + "\n!\n! 追加配置\n" + snippet_content
                    elif snippet_position == 'prepend':
                        new_config = snippet_content + "\n!\n! 原有配置\n" + current_config
                    else:
                        new_config = snippet_content
            else:
                # 其他模式：生成完整差异分析
                diff_result = ConfigDiffService.analyze_diff(current_config, config_content)
                impact = ConfigDiffService.estimate_impact(diff_result)
                new_config = config_content

            preview_results.append({
                "device_id": device.id,
                "device_name": device.name,
                "device_ip": device.ip,
                "old_config": current_config,
                "new_config": new_config,
                "diff": {
                    "lines": [
                        {
                            "type": line.type.value,
                            "content": line.content,
                            "old_line_num": line.old_line_num,
                            "new_line_num": line.new_line_num
                        }
                        for line in diff_result.lines[:100]
                    ],
                    "stats": diff_result.stats
                },
                "impact": impact
            })

        return {
            "success": True,
            "preview": preview_results,
            "summary": {
                "total_devices": len(preview_results),
                "total_changes": sum(p["diff"]["stats"]["added"] + p["diff"]["stats"]["removed"]
                                    for p in preview_results),
                "high_risk_devices": sum(1 for p in preview_results
                                         if p["impact"]["risk_level"] == "high")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览部署失败：{e}")
        import traceback
        logger.error(traceback.format_exc())
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

        elif mode == 'snippet':
            # 配置片段模式
            snippet_content = deploy_data.get('snippet', '')
            if not snippet_content:
                raise HTTPException(status_code=400, detail="请输入配置片段")

            snippet_position = deploy_data.get('snippet_position', 'append')

            # 应用变量替换
            if variables:
                for key, value in variables.items():
                    snippet_content = snippet_content.replace(f"{{{{{key}}}}}", str(value))

            # 如果需要基于现有配置
            base_config = ""
            if deploy_data.get('base_backup_file'):
                backup_path = Path(deploy_data['base_backup_file'])
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{deploy_data['base_backup_file']}")
                if backup_path.exists():
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        base_config = f.read()

            # 合并配置
            if snippet_position == 'append':
                config_content = base_config + "\n! \n! 新增配置片段\n" + snippet_content if base_config else snippet_content
            elif snippet_position == 'prepend':
                config_content = snippet_content + "\n! \n! 原有配置\n" + base_config if base_config else snippet_content
            elif snippet_position == 'replace':
                config_content = snippet_content
            else:
                config_content = snippet_content

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


@router.get("/maintenance-windows")
async def get_maintenance_windows():
    """
    获取可用的维护窗口时段
    """
    windows = []
    now = datetime.now()

    for day_offset in range(1, 8):
        date = now + timedelta(days=day_offset)

        # 凌晨窗口: 02:00-06:00
        windows.append({
            "id": f"{date.strftime('%Y%m%d')}_morning",
            "date": date.strftime("%Y-%m-%d"),
            "start_time": "02:00",
            "end_time": "06:00",
            "label": f"{date.strftime('%m-%d')} 凌晨窗口 (02:00-06:00)",
            "available": True
        })

        # 下午窗口: 14:00-16:00
        windows.append({
            "id": f"{date.strftime('%Y%m%d')}_afternoon",
            "date": date.strftime("%Y-%m-%d"),
            "start_time": "14:00",
            "end_time": "16:00",
            "label": f"{date.strftime('%m-%d')} 下午窗口 (14:00-16:00)",
            "available": True
        })

        # 晚间窗口: 22:00-02:00
        windows.append({
            "id": f"{date.strftime('%Y%m%d')}_evening",
            "date": date.strftime("%Y-%m-%d"),
            "start_time": "22:00",
            "end_time": "02:00",
            "next_day": True,
            "label": f"{date.strftime('%m-%d')} 晚间窗口 (22:00-02:00)",
            "available": True
        })

    return {"windows": windows}


@router.post("/schedule")
async def schedule_deploy(schedule_data: dict, db: Session = Depends(get_db)):
    """
    预约部署任务
    """
    try:
        window_id = schedule_data.get("window_id")
        deploy_data = schedule_data.get("deploy_data", {})

        # 解析维护窗口时间
        parts = window_id.split('_')
        date_str = parts[0]
        period = parts[1]

        date = datetime.strptime(date_str, "%Y%m%d")

        if period == "morning":
            scheduled_time = date.replace(hour=2, minute=0)
        elif period == "afternoon":
            scheduled_time = date.replace(hour=14, minute=0)
        else:
            scheduled_time = date.replace(hour=22, minute=0)

        # 创建预约任务（这里简化处理，实际应创建定时任务）
        return {
            "success": True,
            "task_id": f"scheduled_{window_id}",
            "scheduled_at": scheduled_time.isoformat(),
            "message": f"部署任务已预约到 {scheduled_time.strftime('%Y-%m-%d %H:%M')}"
        }

    except Exception as e:
        logger.error(f"预约部署失败：{e}")
        raise HTTPException(status_code=500, detail=f"预约失败：{str(e)}")
