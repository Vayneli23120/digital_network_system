"""
Network Automation System - 命令行工具
"""

import click
import sys
import uuid
from pathlib import Path
from loguru import logger
from datetime import datetime

from app.models import BackupRecord, FaultRecord

# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO"
)


@click.group()
@click.version_option(version="1.0.0", prog_name="nas")
def cli():
    """Network Automation System - Cisco IOS 交换机管理工具"""
    pass


# ============ 设备命令 ============

@cli.group()
def device():
    """设备管理"""
    pass


@device.command("list")
@click.option("--status", "-s", default=None, help="按状态过滤 (online/offline/maintenance/retired)")
@click.option("--role", "-r", default=None, help="按角色过滤 (access/distribution/core)")
def device_list(status, role):
    """列出所有设备"""
    from app.database import get_db_manager
    from app.models import Device

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        query = db.query(Device)
        if status:
            query = query.filter(Device.status == status)
        if role:
            query = query.filter(Device.role == role)

        devices = query.all()

        if not devices:
            click.echo("没有找到设备")
            return

        click.echo(f"\n{'ID':<6} {'设备名称':<20} {'IP 地址':<18} {'状态':<12} {'角色':<12} {'位置'}")
        click.echo("-" * 90)

        for d in devices:
            click.echo(f"{d.id:<6} {d.name:<20} {d.ip or 'N/A':<18} {d.status:<12} {d.role or 'N/A':<12} {d.location or 'N/A'}")

        click.echo(f"\n共 {len(devices)} 台设备\n")
    finally:
        db.close()


@device.command("show")
@click.argument("device_name")
def device_show(device_name):
    """查看设备详情"""
    from app.database import get_db_manager
    from app.models import Device, BackupRecord, FaultRecord, MaintenanceRecord

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        device = db.query(Device).filter(Device.name == device_name).first()

        if not device:
            click.echo(f"错误：设备 '{device_name}' 不存在")
            return

        click.echo(f"\n{'='*60}")
        click.echo(f"设备详情：{device.name}")
        click.echo(f"{'='*60}")
        click.echo(f"  IP 地址：      {device.ip or 'N/A'}")
        click.echo(f"  设备型号：     {device.model or 'N/A'}")
        click.echo(f"  序列号：       {device.serial_number or 'N/A'}")
        click.echo(f"  位置：         {device.location or 'N/A'}")
        click.echo(f"  角色：         {device.role or 'N/A'}")
        click.echo(f"  状态：         {device.status}")
        click.echo(f"  供应商：       {device.vendor or 'N/A'}")
        click.echo(f"  采购日期：     {device.purchase_date.strftime('%Y-%m-%d') if device.purchase_date else 'N/A'}")
        click.echo(f"  采购成本：     ¥{device.purchase_cost:,.2f}" if device.purchase_cost else "  采购成本：     N/A")
        click.echo(f"  最后备份时间： {device.last_backup_time.strftime('%Y-%m-%d %H:%M:%S') if device.last_backup_time else '从未备份'}")

        # 统计信息
        backup_count = db.query(BackupRecord).filter(BackupRecord.device_id == device.id).count()
        fault_count = db.query(FaultRecord).filter(FaultRecord.device_id == device.id).count()
        maint_count = db.query(MaintenanceRecord).filter(MaintenanceRecord.device_id == device.id).count()

        click.echo(f"\n  备份次数：     {backup_count}")
        click.echo(f"  故障记录：     {fault_count}")
        click.echo(f"  维修记录：     {maint_count}")

        # 计算总拥有成本
        total_cost = device.purchase_cost or 0
        maint_costs = db.query(
            MaintenanceRecord.parts_cost,
            MaintenanceRecord.labor_cost
        ).filter(MaintenanceRecord.device_id == device.id).all()

        maint_total = sum([(m[0] or 0) + (m[1] or 0) for m in maint_costs])
        total_cost += maint_total

        click.echo(f"\n  总拥有成本：   ¥{total_cost:,.2f} (采购 ¥{device.purchase_cost or 0:,.2f} + 维护 ¥{maint_total:,.2f})")

        click.echo(f"{'='*60}\n")
    finally:
        db.close()


@device.command("add")
@click.option("--name", "-n", required=True, help="设备名称")
@click.option("--ip", "-i", required=True, help="管理 IP 地址")
@click.option("--model", "-m", default=None, help="设备型号")
@click.option("--serial", "-s", default=None, help="序列号")
@click.option("--location", "-l", default=None, help="位置")
@click.option("--role", "-r", default="access", help="角色 (access/distribution/core)")
def device_add(name, ip, model, serial, location, role):
    """添加新设备"""
    from app.database import get_db_manager
    from app.models import Device

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        device = Device(
            name=name,
            ip=ip,
            model=model,
            serial_number=serial,
            location=location,
            role=role,
            status="online"
        )
        db.add(device)

        click.echo(f"设备 '{name}' 添加成功 (ID: {device.id})")


# ============ 备份命令 ============

@cli.group()
def backup():
    """配置备份"""
    pass


@backup.command("run")
@click.argument("device_name")
@click.option("--operator", "-o", default="CLI", help="操作人员")
def backup_run(device_name, operator):
    """备份单个设备配置"""
    from app.database import get_db_manager
    from app.models import Device
    from app.services import backup_device_config
    from app.config import get_config

    db_manager = get_db_manager()
    config = get_config()

    with db_manager.session_scope() as db:
        device = db.query(Device).filter(Device.name == device_name).first()

        if not device:
            click.echo(f"错误：设备 '{device_name}' 不存在")
            return

        click.echo(f"正在备份设备 {device.name} ({device.ip})...")

        # TODO: 从凭证管理获取
        credentials = {"username": "admin", "password": "admin", "secret": "admin"}

        result = backup_device_config(device, credentials, config.storage.backup_dir)

        if result["success"]:
            # 保存备份记录
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

            click.echo(f"备份成功!")
            click.echo(f"  文件：{result['file_path']}")
            click.echo(f"  大小：{result['file_size']} 字节")
            click.echo(f"  MD5: {result['md5_hash']}")
            click.echo(f"  配置变更：{'是' if result['has_change'] else '否'}")
        else:
            click.echo(f"备份失败：{result['message']}")
            sys.exit(1)


@backup.command("list")
@click.option("--device", "-d", default=None, help="按设备名称过滤")
@click.option("--limit", "-l", default=20, help="显示数量")
def backup_list(device, limit):
    """列出备份记录"""
    from app.database import get_db_manager
    from app.models import BackupRecord

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        query = db.query(BackupRecord)
        if device:
            query = query.filter(BackupRecord.device_name == device)

        backups = query.order_by(BackupRecord.backup_time.desc()).limit(limit).all()

        if not backups:
            click.echo("没有找到备份记录")
            return

        click.echo(f"\n{'时间':<20} {'设备名称':<20} {'文件大小':<12} {'变更':<6} {'操作员'}")
        click.echo("-" * 75)

        for b in backups:
            change_mark = "是" if b.has_change else "否"
            time_str = b.backup_time.strftime("%Y-%m-%d %H:%M") if b.backup_time else "N/A"
            click.echo(f"{time_str:<20} {b.device_name:<20} {b.file_size or 0:<12} {change_mark:<6} {b.operator or 'N/A'}")

        click.echo(f"\n共 {len(backups)} 条记录\n")
    finally:
        db.close()


# ============ 故障管理命令 ============

@cli.group()
def fault():
    """故障记录管理"""
    pass


@fault.command("add")
@click.option("--device", "-d", required=True, help="设备名称")
@click.option("--severity", "-s", type=click.Choice(["critical", "major", "minor", "warning"]), default="major", help="故障级别")
@click.option("--description", "-desc", required=True, help="故障描述")
@click.option("--downtime", "-t", default=0, help="停机时长 (分钟)")
@click.option("--reporter", "-r", default=None, help="报告人")
def fault_add(device, severity, description, downtime, reporter):
    """添加故障记录"""
    from app.database import get_db_manager
    from app.models import Device, FaultRecord

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        device_obj = db.query(Device).filter(Device.name == device).first()

        if not device_obj:
            click.echo(f"错误：设备 '{device}' 不存在")
            return

        fault_no = f"FAULT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        fault = FaultRecord(
            fault_no=fault_no,
            device_id=device_obj.id,
            device_name=device,
            severity=severity,
            description=description,
            downtime_minutes=downtime,
            reporter=reporter or "CLI",
            status="open"
        )
        db.add(fault)

        click.echo(f"故障记录创建成功!")
        click.echo(f"  故障单号：{fault_no}")
        click.echo(f"  设备：{device}")
        click.echo(f"  级别：{severity}")


@fault.command("list")
@click.option("--device", "-d", default=None, help="按设备名称过滤")
@click.option("--status", "-s", default=None, help="按状态过滤 (open/investigating/resolved/closed)")
def fault_list(device, status):
    """列出故障记录"""
    from app.database import get_db_manager
    from app.models import FaultRecord

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        query = db.query(FaultRecord)
        if device:
            query = query.filter(FaultRecord.device_name == device)
        if status:
            query = query.filter(FaultRecord.status == status)

        faults = query.order_by(FaultRecord.created_at.desc()).limit(50).all()

        if not faults:
            click.echo("没有找到故障记录")
            return

        click.echo(f"\n{'单号':<25} {'设备':<20} {'级别':<10} {'状态':<15} {'停机 (分)':<10} {'时间'}")
        click.echo("-" * 100)

        for f in faults:
            time_str = f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "N/A"
            click.echo(f"{f.fault_no:<25} {f.device_name:<20} {f.severity:<10} {f.status:<15} {f.downtime_minutes:<10} {time_str}")

        click.echo(f"\n共 {len(faults)} 条记录\n")
    finally:
        db.close()


# ============ 统计命令 ============

@cli.command("stats")
def stats():
    """显示统计信息"""
    from app.database import get_db_manager
    from app.models import Device, BackupRecord, FaultRecord, MaintenanceRecord
    from datetime import datetime, timedelta

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        # 设备统计
        total = db.query(Device).count()
        online = db.query(Device).filter(Device.status == "online").count()
        offline = db.query(Device).filter(Device.status == "offline").count()
        maintenance = db.query(Device).filter(Device.status == "maintenance").count()

        # 备份统计
        total_backups = db.query(BackupRecord).count()

        # 30 天内故障
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        faults_30d = db.query(FaultRecord).filter(FaultRecord.created_at >= thirty_days_ago).count()

        # 本月维修成本
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.created_at >= current_month).all()
        month_cost = sum([(m.parts_cost or 0) + (m.labor_cost or 0) for m in month_maint])

        click.echo(f"\n{'='*50}")
        click.echo("  Network Automation System - 统计信息")
        click.echo(f"{'='*50}")
        click.echo(f"\n  设备统计:")
        click.echo(f"    总数：{total}")
        click.echo(f"    在线：{online}")
        click.echo(f"    离线：{offline}")
        click.echo(f"    维护中：{maintenance}")
        click.echo(f"    已退役：{total - online - offline - maintenance}")
        click.echo(f"\n  备份统计:")
        click.echo(f"    总备份次数：{total_backups}")
        click.echo(f"\n  故障统计 (近 30 天):")
        click.echo(f"    故障次数：{faults_30d}")
        click.echo(f"\n  成本统计 (本月):")
        click.echo(f"    维修成本：¥{month_cost:,.2f}")
        click.echo(f"\n{'='*50}\n")
    finally:
        db.close()


# ============ 初始化命令 ============

@cli.command("init-db")
def init_db():
    """初始化数据库"""
    from app.database import get_db_manager

    click.echo("正在初始化数据库...")
    db_manager = get_db_manager()
    db_manager.init_db()
    click.echo("数据库初始化完成!")


# ============ 日志命令 ============

@cli.group()
def log():
    """日志管理"""
    pass


@log.command("list")
@click.option("--level", "-l", default=None, help="日志级别 (DEBUG/INFO/WARNING/ERROR)")
@click.option("--days", "-d", default=7, help="查看最近 N 天的日志")
@click.option("--limit", "-n", default=50, help="显示数量")
def log_list(level, days, limit):
    """列出最新日志"""
    from app.services.log_service import get_log_service

    log_service = get_log_service()
    logs = log_service.get_latest_logs(count=limit, level=level)

    if not logs:
        click.echo("没有找到日志记录")
        return

    click.echo(f"\n{'时间':<20} {'级别':<10} {'模块':<25} {'消息'}")
    click.echo("-" * 100)

    for log in logs:
        timestamp = log.get('timestamp', '')[:19] if log.get('timestamp') else 'N/A'
        level_str = log.get('level', 'INFO')[:8]
        module = log.get('module', '')[:22]
        message = log.get('message', '')[:40]
        click.echo(f"{timestamp:<20} {level_str:<10} {module:<25} {message}")

    click.echo(f"\n共 {len(logs)} 条记录\n")


@log.command("search")
@click.argument("keyword")
@click.option("--days", "-d", default=7, help="搜索范围（天）")
@click.option("--level", "-l", default=None, help="日志级别过滤")
def log_search(keyword, days, level):
    """搜索日志"""
    from app.services.log_service import get_log_service

    log_service = get_log_service()
    results = log_service.search_logs(keyword, days=days, level=level)

    if not results:
        click.echo(f"没有找到包含 '{keyword}' 的日志")
        return

    click.echo(f"\n搜索结果：'{keyword}' (共 {len(results)} 条)\n")
    click.echo("-" * 80)

    for log in results[:20]:  # 最多显示 20 条
        timestamp = log.get('timestamp', '')[:19] if log.get('timestamp') else ''
        level_str = log.get('level', 'INFO')
        source = log.get('source_file', '')
        message = log.get('message', '')
        click.echo(f"[{timestamp}] [{level_str}] {source}")
        click.echo(f"  {message}\n")

    click.echo("-" * 80)


# ============ 模板命令 ============

@cli.group()
def template():
    """配置模板管理"""
    pass


@template.command("list")
def template_list():
    """列出所有配置模板"""
    from app.database import get_db_manager
    from app.models import ConfigTemplate

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        templates = db.query(ConfigTemplate).all()

        if not templates:
            click.echo("没有找到配置模板")
            return

        click.echo(f"\n{'ID':<6} {'模板名称':<25} {'描述':<40}")
        click.echo("-" * 75)

        for t in templates:
            desc = (t.description or '')[:37] + '...' if len(t.description or '') > 40 else t.description
            click.echo(f"{t.id:<6} {t.name:<25} {desc or 'N/A':<40}")

        click.echo(f"\n共 {len(templates)} 个模板\n")
    finally:
        db.close()


@template.command("show")
@click.argument("template_id", type=int)
def template_show(template_id):
    """查看模板详情"""
    from app.database import get_db_manager
    from app.models import ConfigTemplate

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()

        if not template:
            click.echo(f"错误：模板 ID {template_id} 不存在")
            return

        click.echo(f"\n{'='*60}")
        click.echo(f"模板：{template.name}")
        click.echo(f"{'='*60}")
        click.echo(f"描述：{template.description or 'N/A'}\n")
        click.echo("变量定义:")

        import json
        variables = json.loads(template.variables) if template.variables else []
        for var in variables:
            default = var.get('default', '')
            click.echo(f"  - {var.get('key', '')}: {var.get('description', '')} (默认：{default})")

        click.echo(f"\n{'='*60}\n")
    finally:
        db.close()


# ============ 凭证命令 ============

@cli.group()
def credential():
    """SSH 凭证管理"""
    pass


@credential.command("list")
def credential_list():
    """列出所有凭证组"""
    from app.database import get_db_manager
    from app.models import CredentialGroup

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        credentials = db.query(CredentialGroup).all()

        if not credentials:
            click.echo("没有找到凭证组")
            return

        click.echo(f"\n{'ID':<6} {'名称':<20} {'用户名':<15}")
        click.echo("-" * 45)

        for c in credentials:
            click.echo(f"{c.id:<6} {c.name:<20} {c.username or 'N/A':<15}")

        click.echo(f"\n共 {len(credentials)} 个凭证组\n")
    finally:
        db.close()


# ============ 维修管理命令 ============

@cli.group()
def maintenance():
    """维修记录管理"""
    pass


@maintenance.command("add")
@click.option("--device", "-d", required=True, help="设备名称")
@click.option("--type", "-t", "maint_type", default="corrective", help="维修类型 (preventive/corrective/upgrade/emergency)")
@click.option("--description", "-desc", required=True, help="维修描述")
@click.option("--parts", "-p", default=0, help="配件费用")
@click.option("--labor", "-l", default=0, help="人工费用")
@click.option("--hours", "-h", default=0, help="工时")
@click.option("--operator", "-o", default=None, help="操作员")
def maintenance_add(device, maint_type, description, parts, labor, hours, operator):
    """添加维修记录"""
    from app.database import get_db_manager
    from app.models import Device, MaintenanceRecord
    from datetime import datetime
    import uuid

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        device_obj = db.query(Device).filter(Device.name == device).first()

        if not device_obj:
            click.echo(f"错误：设备 '{device}' 不存在")
            return

        maint_no = f"MNT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        maint = MaintenanceRecord(
            maint_no=maint_no,
            device_id=device_obj.id,
            device_name=device,
            maint_type=maint_type,
            description=description,
            parts_cost=parts,
            labor_cost=labor,
            labor_hours=hours,
            operator=operator or "CLI",
            maint_time=datetime.utcnow()
        )
        db.add(maint)

        click.echo(f"维修记录创建成功!")
        click.echo(f"  维修单号：{maint_no}")
        click.echo(f"  设备：{device}")
        click.echo(f"  类型：{maint_type}")
        click.echo(f"  费用：¥{parts + labor:,.2f} (配件 ¥{parts:,.2f} + 人工 ¥{labor:,.2f})")


@maintenance.command("list")
@click.option("--device", "-d", default=None, help="按设备名称过滤")
@click.option("--type", "-t", "maint_type", default=None, help="按类型过滤 (preventive/corrective/upgrade/emergency)")
@click.option("--limit", "-n", default=20, help="显示数量")
def maintenance_list(device, maint_type, limit):
    """列出维修记录"""
    from app.database import get_db_manager
    from app.models import MaintenanceRecord

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        query = db.query(MaintenanceRecord)
        if device:
            query = query.filter(MaintenanceRecord.device_name == device)
        if maint_type:
            query = query.filter(MaintenanceRecord.maint_type == maint_type)

        maints = query.order_by(MaintenanceRecord.maint_time.desc()).limit(limit).all()

        if not maints:
            click.echo("没有找到维修记录")
            return

        click.echo(f"\n{'日期':<12} {'设备':<20} {'类型':<12} {'费用':<12} {'工时 (h)':<10} {'操作员'}")
        click.echo("-" * 85)

        for m in maints:
            date_str = m.maint_time.strftime("%Y-%m-%d") if m.maint_time else "N/A"
            total_cost = (m.parts_cost or 0) + (m.labor_cost or 0)
            click.echo(f"{date_str:<12} {m.device_name:<20} {m.maint_type:<12} ¥{total_cost:<12.2f} {m.labor_hours or 0:<10} {m.operator or 'N/A'}")

        click.echo(f"\n共 {len(maints)} 条记录\n")
    finally:
        db.close()


@maintenance.command("update")
@click.argument("maint_id", type=int)
@click.option("--status", "-s", type=click.Choice(["pending", "in_progress", "completed", "cancelled"]), help="更新状态")
@click.option("--description", "-desc", help="更新描述")
@click.option("--parts", "-p", type=float, help="更新配件费用")
@click.option("--labor", "-l", type=float, help="更新人工费用")
def maintenance_update(maint_id, status, description, parts, labor):
    """更新维修记录"""
    from app.database import get_db_manager
    from app.models import MaintenanceRecord

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()

        if not maint:
            click.echo(f"错误：维修记录 ID {maint_id} 不存在")
            return

        updated = False
        if status:
            maint.status = status
            updated = True
        if description:
            maint.description = description
            updated = True
        if parts is not None:
            maint.parts_cost = parts
            updated = True
        if labor is not None:
            maint.labor_cost = labor
            updated = True

        if updated:
            click.echo(f"维修记录 {maint_id} 更新成功!")
        else:
            click.echo("没有进行任何更新")


@maintenance.command("delete")
@click.argument("maint_id", type=int)
@click.option("--confirm", "-y", is_flag=True, help="确认删除")
def maintenance_delete(maint_id, confirm):
    """删除维修记录"""
    from app.database import get_db_manager
    from app.models import MaintenanceRecord

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()

        if not maint:
            click.echo(f"错误：维修记录 ID {maint_id} 不存在")
            return

        if not confirm:
            click.confirm(f"确定要删除维修记录 {maint_id} 吗？", abort=True)

        db.delete(maint)
        click.echo(f"维修记录 {maint_id} 已删除")


# ============ 设备更新命令 ============

@device.command("update")
@click.argument("device_name")
@click.option("--status", "-s", type=click.Choice(["online", "offline", "maintenance", "retired"]), help="更新状态")
@click.option("--ip", "-i", help="更新 IP 地址")
@click.option("--location", "-l", help="更新位置")
@click.option("--role", "-r", type=click.Choice(["access", "distribution", "core"]), help="更新角色")
def device_update(device_name, status, ip, location, role):
    """更新设备信息"""
    from app.database import get_db_manager
    from app.models import Device

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        device = db.query(Device).filter(Device.name == device_name).first()

        if not device:
            click.echo(f"错误：设备 '{device_name}' 不存在")
            return

        updated = False
        if status:
            device.status = status
            updated = True
        if ip:
            device.ip = ip
            updated = True
        if location:
            device.location = location
            updated = True
        if role:
            device.role = role
            updated = True

        if updated:
            click.echo(f"设备 '{device_name}' 更新成功!")
        else:
            click.echo("没有进行任何更新")


@device.command("delete")
@click.argument("device_name")
@click.option("--confirm", "-y", is_flag=True, help="确认删除")
def device_delete(device_name, confirm):
    """删除设备"""
    from app.database import get_db_manager
    from app.models import Device

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        device = db.query(Device).filter(Device.name == device_name).first()

        if not device:
            click.echo(f"错误：设备 '{device_name}' 不存在")
            return

        if not confirm:
            click.confirm(f"确定要删除设备 '{device_name}' 吗？此操作不可逆!", abort=True)

        db.delete(device)
        click.echo(f"设备 '{device_name}' 已删除")


# ============ 故障更新命令 ============

@fault.command("update")
@click.argument("fault_id", type=int)
@click.option("--status", "-s", type=click.Choice(["open", "investigating", "resolved", "closed"]), help="更新状态")
@click.option("--description", "-desc", help="更新描述")
@click.option("--downtime", "-t", type=int, help="更新停机时长 (分钟)")
def fault_update(fault_id, status, description, downtime):
    """更新故障记录"""
    from app.database import get_db_manager
    from app.models import FaultRecord

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

        if not fault:
            click.echo(f"错误：故障记录 ID {fault_id} 不存在")
            return

        updated = False
        if status:
            fault.status = status
            updated = True
        if description:
            fault.description = description
            updated = True
        if downtime is not None:
            fault.downtime_minutes = downtime
            updated = True

        if updated:
            click.echo(f"故障记录 {fault_id} 更新成功!")
        else:
            click.echo("没有进行任何更新")


@fault.command("delete")
@click.argument("fault_id", type=int)
@click.option("--confirm", "-y", is_flag=True, help="确认删除")
def fault_delete(fault_id, confirm):
    """删除故障记录"""
    from app.database import get_db_manager
    from app.models import FaultRecord

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

        if not fault:
            click.echo(f"错误：故障记录 ID {fault_id} 不存在")
            return

        if not confirm:
            click.confirm(f"确定要删除故障记录 {fault_id} 吗？", abort=True)

        db.delete(fault)
        click.echo(f"故障记录 {fault_id} 已删除")


# ============ 高级统计命令 ============

@cli.command("report")
@click.option("--device", "-d", default=None, help="按设备统计")
@click.option("--days", "-n", default=30, help="统计天数")
def report(device, days):
    """生成统计报表"""
    from app.database import get_db_manager
    from app.models import Device, BackupRecord, FaultRecord, MaintenanceRecord
    from datetime import datetime, timedelta

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        click.echo(f"\n{'='*70}")
        click.echo(f"  Network Automation System - 统计报表")
        click.echo(f"  统计周期：{start_date.strftime('%Y-%m-%d')} 至 {datetime.utcnow().strftime('%Y-%m-%d')} ({days} 天)")
        click.echo(f"{'='*70}\n")

        # 设备统计
        if device:
            devices = db.query(Device).filter(Device.name == device).all()
        else:
            devices = db.query(Device).all()

        click.echo(f"【设备统计】")
        click.echo(f"  设备总数：{len(devices)}")
        status_counts = {}
        for d in devices:
            status_counts[d.status] = status_counts.get(d.status, 0) + 1
        for status, count in status_counts.items():
            click.echo(f"    {status}: {count} 台")

        # 备份统计
        backup_query = db.query(BackupRecord).filter(BackupRecord.backup_time >= start_date)
        if device:
            backup_query = backup_query.join(Device).filter(Device.name == device)
        backups = backup_query.all()

        click.echo(f"\n【备份统计】")
        click.echo(f"  备份次数：{len(backups)}")
        if backups:
            changes = sum(1 for b in backups if b.has_change)
            click.echo(f"  有变更：{changes} 次")
            click.echo(f"  无变更：{len(backups) - changes} 次")

        # 故障统计
        fault_query = db.query(FaultRecord).filter(FaultRecord.created_at >= start_date)
        if device:
            fault_query = fault_query.filter(FaultRecord.device_name == device)
        faults = fault_query.all()

        click.echo(f"\n【故障统计】")
        click.echo(f"  故障次数：{len(faults)}")
        severity_counts = {}
        for f in faults:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        for severity, count in severity_counts.items():
            click.echo(f"    {severity}: {count} 次")

        # 维修统计
        maint_query = db.query(MaintenanceRecord).filter(MaintenanceRecord.maint_time >= start_date)
        if device:
            maint_query = maint_query.filter(MaintenanceRecord.device_name == device)
        maints = maint_query.all()

        total_parts = sum(m.parts_cost or 0 for m in maints)
        total_labor = sum(m.labor_cost or 0 for m in maints)
        total_hours = sum(m.labor_hours or 0 for m in maints)

        click.echo(f"\n【维修统计】")
        click.echo(f"  维修次数：{len(maints)}")
        click.echo(f"  配件费用：¥{total_parts:,.2f}")
        click.echo(f"  人工费用：¥{total_labor:,.2f}")
        click.echo(f"  总费用：¥{total_parts + total_labor:,.2f}")
        click.echo(f"  累计工时：{total_hours} 小时")

        click.echo(f"\n{'='*70}\n")

    finally:
        db.close()


@cli.command("cost")
@click.option("--device", "-d", default=None, help="按设备统计")
@click.option("--month", "-m", default=None, help="指定月份 (YYYY-MM)")
def cost(device, month):
    """成本统计分析"""
    from app.database import get_db_manager
    from app.models import Device, MaintenanceRecord
    from datetime import datetime

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        if month:
            try:
                start = datetime.strptime(month, "%Y-%m")
            except ValueError:
                click.echo("错误：月份格式应为 YYYY-MM")
                return
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            period_str = month
        else:
            now = datetime.utcnow()
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = now.replace(year=now.year + 1, month=1, day=1)
            else:
                end = now.replace(month=now.month + 1, day=1)
            period_str = now.strftime("%Y-%m")

        click.echo(f"\n{'='*50}")
        click.echo(f"  成本分析 - {period_str}")
        click.echo(f"{'='*50}\n")

        # 查询维修记录
        query = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.maint_time >= start,
            MaintenanceRecord.maint_time < end
        )
        if device:
            device_obj = db.query(Device).filter(Device.name == device).first()
            if device_obj:
                query = query.filter(MaintenanceRecord.device_id == device_obj.id)

        maints = query.all()

        if not maints:
            click.echo("  本月无维修记录")
            click.echo(f"\n{'='*50}\n")
            return

        # 按设备分组统计
        device_costs = {}
        for m in maints:
            if m.device_name not in device_costs:
                device_costs[m.device_name] = {'parts': 0, 'labor': 0, 'count': 0}
            device_costs[m.device_name]['parts'] += m.parts_cost or 0
            device_costs[m.device_name]['labor'] += m.labor_cost or 0
            device_costs[m.device_name]['count'] += 1

        grand_total = 0
        click.echo(f"{'设备':<25} {'次数':<8} {'配件':<12} {'人工':<12} {'合计':<12}")
        click.echo("-" * 70)

        for dev_name, costs in sorted(device_costs.items()):
            total = costs['parts'] + costs['labor']
            grand_total += total
            click.echo(f"{dev_name:<25} {costs['count']:<8} ¥{costs['parts']:<11,.2f} ¥{costs['labor']:<11,.2f} ¥{total:<11,.2f}")

        click.echo("-" * 70)
        click.echo(f"{'总计':<25} {len(maints):<8} ¥{sum(c['parts'] for c in device_costs.values()):<11,.2f} ¥{sum(c['labor'] for c in device_costs.values()):<11,.2f} ¥{grand_total:<11,.2f}")
        click.echo(f"\n{'='*50}\n")

    finally:
        db.close()


if __name__ == "__main__":
    cli()
