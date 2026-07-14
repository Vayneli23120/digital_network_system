"""
Dashboard 服务层

封装 Dashboard 统计和业务逻辑，供路由和测试使用。
集成内存缓存提升读多写少场景性能。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.shared.models import Device, BackupRecord, FaultRecord, MaintenanceRecord, SparePart, SparePartMovement, SystemConfig
from app.shared.cache import cache


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """获取 Dashboard 摘要数据

    Args:
        db: 数据库会话

    Returns:
        摘要数据字典
    """
    # 设备统计 - 改用 reachability 字段（只统计已部署设备）
    total_deployed = db.query(Device).filter(Device.deployment_status == "in-use").count()
    reachable_devices = db.query(Device).filter(
        Device.deployment_status == "in-use",
        Device.reachability == "reachable"
    ).count()
    unreachable_devices = db.query(Device).filter(
        Device.deployment_status == "in-use",
        Device.reachability == "unreachable"
    ).count()
    unknown_devices = db.query(Device).filter(
        Device.deployment_status == "in-use",
        Device.reachability == "unknown"
    ).count()

    # 部署状态统计（全部设备）
    in_use_devices = db.query(Device).filter(Device.deployment_status == "in-use").count()
    un_used_devices = db.query(Device).filter(Device.deployment_status == "un-used").count()
    maintenance_devices = db.query(Device).filter(Device.deployment_status == "maintenance").count()
    retired_devices = db.query(Device).filter(Device.deployment_status == "retired").count()

    # 按设备类型统计 - 同时包含 deployment_status 和 reachability
    device_types = ["uce", "core_switch", "server_switch", "office_switch", "ap", "wlc", "router", "pa", "ftd", "other"]
    devices_by_type = {}
    for dtype in device_types:
        total = db.query(Device).filter(Device.device_type == dtype).count()
        devices_by_type[dtype] = {
            "total": total,
            # 部署状态
            "in_use": db.query(Device).filter(Device.device_type == dtype, Device.deployment_status == "in-use").count(),
            "un_used": db.query(Device).filter(Device.device_type == dtype, Device.deployment_status == "un-used").count(),
            "maintenance": db.query(Device).filter(Device.device_type == dtype, Device.deployment_status == "maintenance").count(),
            "retired": db.query(Device).filter(Device.device_type == dtype, Device.deployment_status == "retired").count(),
            # 可达性状态（仅统计 in-use 设备）
            "reachable": db.query(Device).filter(
                Device.device_type == dtype,
                Device.deployment_status == "in-use",
                Device.reachability == "reachable"
            ).count(),
            "unreachable": db.query(Device).filter(
                Device.device_type == dtype,
                Device.deployment_status == "in-use",
                Device.reachability == "unreachable"
            ).count(),
            "unknown": db.query(Device).filter(
                Device.device_type == dtype,
                Device.deployment_status == "in-use",
                Device.reachability == "unknown"
            ).count(),
            # 兼容旧字段（向后兼容）
            "online": db.query(Device).filter(Device.device_type == dtype, Device.reachability == "reachable", Device.deployment_status == "in-use").count(),
            "offline": db.query(Device).filter(Device.device_type == dtype, Device.reachability == "unreachable", Device.deployment_status == "in-use").count(),
        }

    # 备份统计（最近 10 条）
    recent_backups = db.query(BackupRecord).order_by(BackupRecord.backup_time.desc()).limit(10).all()

    # 真实备份覆盖率：有备份记录的设备数 / 在网设备数
    backed_up_devices = db.query(func.count(func.distinct(BackupRecord.device_id))).scalar() or 0

    # 故障统计（近 30 天，按状态分组）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_faults = db.query(FaultRecord).filter(
        FaultRecord.created_at >= thirty_days_ago
    ).limit(1000).all()

    # 活跃故障（未解决）
    ACTIVE_STATUS = ('open', 'assigned', 'accepted', 'diagnosing', 'resolving', 'transferred')
    active_faults = [f for f in recent_faults if f.status in ACTIVE_STATUS]
    active_count = len(active_faults)
    active_critical = len([f for f in active_faults if f.severity == "critical"])
    active_major = len([f for f in active_faults if f.severity == "major"])
    active_minor = len([f for f in active_faults if f.severity == "minor"])

    # 已解决故障
    RESOLVED_STATUS = ('resolved', 'closed')
    resolved_faults = [f for f in recent_faults if f.status in RESOLVED_STATUS]
    resolved_count = len(resolved_faults)

    # 维修任务统计
    all_maintenance = db.query(MaintenanceRecord).limit(5000).all()
    maintenance_pending = len([m for m in all_maintenance if m.status in ("created",)])
    maintenance_in_progress = len([m for m in all_maintenance if m.status in ("diagnosing", "repairing", "verifying")])
    maintenance_completed = len([m for m in all_maintenance if m.status == "completed"])

    # 备件库存统计
    spare_parts = db.query(SparePart).filter(SparePart.status == "active").all()
    total_models = len(spare_parts)
    total_quantity = sum(sp.quantity_in_stock or 0 for sp in spare_parts)
    low_stock_count = len([sp for sp in spare_parts if sp.quantity_in_stock <= (sp.min_quantity or 0) and (sp.min_quantity or 0) > 0])

    # 成本统计（本月，限制数量避免全表加载）
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_maintenance = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.created_at >= current_month
    ).limit(1000).all()

    total_parts_cost = sum(m.parts_cost or 0 for m in month_maintenance)
    total_labor_cost = sum(m.labor_cost or 0 for m in month_maintenance)

    return {
        "devices": {
            "total": total_deployed,  # 只统计已部署设备
            "reachable": reachable_devices,
            "unreachable": unreachable_devices,
            "unknown": unknown_devices,
            # 兼容旧字段（向后兼容）
            "online": reachable_devices,
            "offline": unreachable_devices,
            # 部署状态统计
            "deployment": {
                "in_use": in_use_devices,
                "un_used": un_used_devices,
                "maintenance": maintenance_devices,
                "retired": retired_devices,
            },
            "by_type": devices_by_type,
        },
        "backups": {
            "backed_up_devices": backed_up_devices,
            "recent": [
                {
                    "device_name": b.device_name,
                    "backup_time": b.backup_time.isoformat(),
                    "has_change": b.has_change,
                }
                for b in recent_backups
            ]
        },
        "faults": {
            "count_30days": len(recent_faults),
            # 活跃故障（未解决）- DNAC 风格
            "active": active_count,
            "active_critical": active_critical,
            "active_major": active_major,
            "active_minor": active_minor,
            # 已解决故障
            "resolved": resolved_count,
            # 兼容旧字段（按严重级别统计全部）
            "critical_count": len([f for f in recent_faults if f.severity == "critical"]),
            "major_count": len([f for f in recent_faults if f.severity == "major"]),
            "minor_count": len([f for f in recent_faults if f.severity == "minor"]),
        },
        "costs": {
            "month_maintenance": float(total_parts_cost),
            "month_labor": float(total_labor_cost),
            "month_total": float(total_parts_cost + total_labor_cost),
        },
        "maintenance": {
            "pending": maintenance_pending,
            "in_progress": maintenance_in_progress,
            "completed": maintenance_completed,
        },
        "spare_parts": {
            "total_models": total_models,
            "total_quantity": total_quantity,
            "low_stock_count": low_stock_count,
        },
    }


def get_cost_trend(db: Session, months: int = 6) -> Dict[str, Any]:
    """获取近 N 个月的运维成本趋势

    Args:
        db: 数据库会话
        months: 回溯月数（默认 6）

    Returns:
        包含 labels、total、parts、labor 的成本趋势数据
    """
    now = datetime.utcnow()
    labels = []
    total_costs = []
    parts_costs = []
    labor_costs = []

    for i in reversed(range(months)):
        if i == 0:
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = now
        else:
            # 回溯 i 个月
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            month_start = datetime(y, m, 1, 0, 0, 0, 0)
            if m == 12:
                month_end = datetime(y + 1, 1, 1, 0, 0, 0, 0)
            else:
                month_end = datetime(y, m + 1, 1, 0, 0, 0, 0)

        records = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.created_at >= month_start,
            MaintenanceRecord.created_at < month_end,
        ).limit(5000).all()

        parts = sum(r.parts_cost or 0 for r in records)
        labor = sum(r.labor_cost or 0 for r in records)

        month_label = month_start.strftime("%b")
        labels.append(month_label)
        total_costs.append(round(float(parts + labor), 2))
        parts_costs.append(round(float(parts), 2))
        labor_costs.append(round(float(labor), 2))

    return {
        "labels": labels,
        "total": total_costs,
        "parts": parts_costs,
        "labor": labor_costs,
    }


def get_top_fault_devices(db: Session, days: int = 30, limit: int = 5) -> List[Dict[str, Any]]:
    """获取近 N 天故障最多的设备

    Args:
        db: 数据库会话
        days: 回溯天数（默认 30）
        limit: 返回设备数量（默认 5）

    Returns:
        按故障数排序的设备列表 [{device_id, device_name, count, severity_breakdown}]
    """
    from collections import Counter
    from sqlalchemy import desc

    cutoff = datetime.utcnow() - timedelta(days=days)
    faults = db.query(FaultRecord).filter(
        FaultRecord.created_at >= cutoff
    ).limit(5000).all()

    # 按设备分组统计
    by_device = defaultdict(list)
    for f in faults:
        key = f.device_id or f.device_name or "unknown"
        by_device[key].append(f)

    result = []
    for key, device_faults in by_device.items():
        if key == "unknown":
            device_name = "Unknown"
        else:
            first = device_faults[0]
            device_name = first.device_name or f"Device {key}"

        severities = Counter(f.severity for f in device_faults)
        result.append({
            "device_id": device_faults[0].device_id,
            "device_name": device_name,
            "count": len(device_faults),
            "critical": severities.get("critical", 0),
            "major": severities.get("major", 0),
            "minor": severities.get("minor", 0),
        })

    # 按故障数降序，取 top N
    result.sort(key=lambda x: x["count"], reverse=True)
    return result[:limit]


def get_fault_trend(
    db: Session,
    time_range: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """获取故障趋势数据

    Args:
        db: 数据库会话
        time_range: 7d / 30d / 3m / 1y / custom
        start_date: 自定义开始日期 (YYYY-MM-DD)
        end_date: 自定义结束日期 (YYYY-MM-DD)

    Returns:
        包含 labels, values, total, by_severity 的字典
    """
    now = datetime.utcnow()
    group_format = "%m-%d"
    group_by = "day"

    # 计算时间范围
    if time_range == "custom" and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return {"labels": [], "values": [], "error": "日期格式错误"}

        query_start_date = start_dt
        query_end_date = end_dt
        days_diff = (end_dt - start_dt).days

        if days_diff <= 30:
            group_format = "%m-%d"
            group_by = "day"
        elif days_diff <= 90:
            group_format = "%Y-%W"
            group_by = "week"
        else:
            group_format = "%Y-%m"
            group_by = "month"
    elif time_range == "7d":
        query_start_date = now - timedelta(days=7)
        group_format = "%m-%d"
        query_end_date = now
    elif time_range == "30d":
        query_start_date = now - timedelta(days=30)
        group_format = "%m-%d"
        query_end_date = now
    elif time_range == "3m":
        query_start_date = now - timedelta(days=90)
        group_format = "%Y-%W"
        group_by = "week"
        query_end_date = now
    elif time_range == "1y":
        query_start_date = now - timedelta(days=365)
        group_format = "%Y-%m"
        group_by = "month"
        query_end_date = now
    else:
        query_start_date = now - timedelta(days=30)
        query_end_date = now

    # 查询故障记录（限制数量，避免全表加载到内存）
    faults = db.query(FaultRecord).filter(
        FaultRecord.created_at >= query_start_date,
        FaultRecord.created_at <= query_end_date,
    ).limit(5000).all()

    # 按时间 + 级别分组
    fault_counts = defaultdict(int)
    fault_by_severity = defaultdict(lambda: defaultdict(int))
    total_faults = 0

    for fault in faults:
        if group_by == "week":
            # 使用 ISO 周格式: 显示为 "04-W1" (月-周)
            iso_year, iso_week = fault.created_at.isocalendar()[:2]
            # 计算该 ISO 周对应的月份
            week_start = fault.created_at - timedelta(days=fault.created_at.weekday())
            month = week_start.month
            label = f"{month:02d}-W{iso_week}"
        elif group_by == "month":
            label = fault.created_at.strftime("%Y-%m")
        else:
            label = fault.created_at.strftime(group_format)

        fault_counts[label] += 1
        fault_by_severity[label][fault.severity] += 1
        total_faults += 1

    # 生成完整时间序列
    labels: List[str] = []
    values: List[int] = []
    severity_timeline = {}

    if group_by == "day":
        current = query_start_date
        while current < query_end_date:
            label = current.strftime(group_format)
            labels.append(label)
            values.append(fault_counts.get(label, 0))
            severity_timeline[label] = {
                "critical": fault_by_severity[label].get("critical", 0),
                "major": fault_by_severity[label].get("major", 0),
                "minor": fault_by_severity[label].get("minor", 0),
                "warning": fault_by_severity[label].get("warning", 0),
            }
            current += timedelta(days=1)

    elif group_by == "week":
        week_data = {}
        for label, count in fault_counts.items():
            try:
                # 解析新格式 "04-W1" -> 提取周数用于排序
                parts = label.split("-W")
                if len(parts) == 2:
                    week_idx = int(parts[1])
                    week_data[week_idx] = {
                        "label": label,
                        "count": count,
                        "severity": fault_by_severity[label],
                    }
            except (ValueError, KeyError):
                continue

        if week_data:
            min_week = min(week_data.keys())
            max_week = max(week_data.keys())
            for week_num in range(min_week, max_week + 1):
                if week_num in week_data:
                    label = week_data[week_num]["label"]
                    labels.append(label)
                    values.append(week_data[week_num]["count"])
                    severity_timeline[label] = {
                        "critical": week_data[week_num]["severity"].get("critical", 0),
                        "major": week_data[week_num]["severity"].get("major", 0),
                        "minor": week_data[week_num]["severity"].get("minor", 0),
                        "warning": week_data[week_num]["severity"].get("warning", 0),
                    }
                else:
                    # 为缺失的周生成占位标签
                    # 推算该周应该显示的月份
                    placeholder_month = (min_week + week_num - min_week) % 12 + 1
                    if placeholder_month < 1:
                        placeholder_month = 1
                    label = f"{placeholder_month:02d}-W{week_num}"
                    labels.append(label)
                    values.append(0)
                    severity_timeline[label] = {
                        "critical": 0,
                        "major": 0,
                        "minor": 0,
                        "warning": 0,
                    }

    elif group_by == "month":
        # 从起始日期的下一个月开始，避免 day=31 导致的月份遍历错误
        current = query_start_date.replace(day=1)
        end_month = query_end_date.replace(day=1)
        while current <= end_month:
            label = current.strftime("%Y-%m")
            labels.append(label)
            values.append(fault_counts.get(label, 0))
            severity_timeline[label] = {
                "critical": fault_by_severity.get(label, {}).get("critical", 0),
                "major": fault_by_severity.get(label, {}).get("major", 0),
                "minor": fault_by_severity.get(label, {}).get("minor", 0),
                "warning": fault_by_severity.get(label, {}).get("warning", 0),
            }
            # 安全地增加一个月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

    return {
        "labels": labels,
        "values": values,
        "total": total_faults,
        "by_severity": severity_timeline,
    }


def get_alerts(db: Session) -> List[Dict[str, Any]]:
    """获取实时告警列表

    Returns:
        告警列表，每条包含 alert_key + 结构化参数，前端负责 i18n 渲染
    """
    from datetime import datetime, timedelta
    from app.shared.models import FaultRecord, Device
    from sqlalchemy import func

    alerts = []
    now = datetime.utcnow()

    # 1. 高危故障：severity in (critical, major) 且 status 属未关闭
    critical_faults = db.query(FaultRecord).filter(
        FaultRecord.severity.in_(['critical', 'major']),
        FaultRecord.status.in_(['open', 'assigned', 'accepted', 'diagnosing', 'resolving'])
    ).order_by(FaultRecord.created_at.desc()).limit(3).all()

    for fault in critical_faults:
        time_diff = now - fault.created_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days}d"
        elif time_diff.seconds >= 3600:
            time_str = f"{int(time_diff.seconds / 3600)}h"
        else:
            time_str = f"{int(time_diff.seconds / 60)}m"

        severity_map = {'critical': 'danger', 'major': 'warn'}
        alerts.append({
            "severity": severity_map.get(fault.severity, 'warn'),
            "alert_key": "fault",
            "device_name": fault.device_name,  # None 表示未知，前端兜底
            "description": fault.description[:50] if fault.description else None,  # None → 前端显示"无描述"
            "time": time_str,
            "link": "/faults?status=open"
        })

    # 2. 备份超期：设备 last_backup_time 超过 30 天
    thirty_days_ago = now - timedelta(days=30)
    devices_with_old_backup = db.query(Device).filter(
        Device.deployment_status == 'in-use',
        Device.last_backup_time < thirty_days_ago
    ).limit(3).all()

    for device in devices_with_old_backup:
        if device.last_backup_time:
            days_overdue = (now - device.last_backup_time).days
            alerts.append({
                "severity": "warn",
                "alert_key": "backup_overdue",
                "device_name": device.name,
                "days_overdue": days_overdue,
                "time": f"{days_overdue}d",
                "link": "/backups"
            })

    # 3. 如果没有任何告警，显示系统健康状态
    if not alerts:
        alerts.append({
            "severity": "success",
            "alert_key": "system_healthy",
            "time": "now",
            "link": None
        })

    return alerts


def get_executive_summary(db: Session, time_range: str = "30d") -> Dict[str, Any]:
    """管理层聚合接口 - 返回所有核心 KPI

    Args:
        db: 数据库会话
        time_range: 时间范围 - 7d, 30d, 90d, 12m

    Returns:
        包含所有管理层 KPI 的字典，每个 KPI 带 value/unit/target/threshold/trend/status
    """
    from app.shared.models import SystemConfig, SparePartMovement, ServiceSlo, BackupRecord
    from collections import Counter

    # 计算时间范围
    now = datetime.utcnow()
    days_map = {"7d": 7, "30d": 30, "90d": 90, "12m": 365}
    days = days_map.get(time_range, 30)
    range_start = now - timedelta(days=days)
    prev_range_start = range_start - timedelta(days=days)  # 上一周期起点
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (current_month_start.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ===== 1. 系统可用率 =====
    total_deployed = db.query(Device).filter(Device.deployment_status == "in-use").count()
    reachable_devices = db.query(Device).filter(
        Device.deployment_status == "in-use",
        Device.reachability == "reachable"
    ).count()

    availability_value = (reachable_devices / total_deployed * 100) if total_deployed > 0 else 0
    availability_status = _get_status(availability_value, 99.5, 98, higher_is_good=True)

    # 可用率趋势：可达性是实时状态，无法回溯历史 → 趋势未知（不显示箭头）
    availability_trend = None

    # ===== 2. 活跃故障数 =====
    ACTIVE_STATUS = ('open', 'assigned', 'accepted', 'diagnosing', 'resolving', 'transferred')
    active_faults = db.query(FaultRecord).filter(
        FaultRecord.status.in_(ACTIVE_STATUS)
    ).count()

    # 计算趋势（与上一周期对比）
    prev_active_faults = db.query(FaultRecord).filter(
        FaultRecord.created_at >= prev_range_start,
        FaultRecord.created_at < range_start,
        FaultRecord.status.in_(ACTIVE_STATUS)
    ).count()
    # 活跃故障是“当前快照”，无法与历史快照可比 → 趋势未知（不显示箭头）
    active_faults_trend = None
    active_faults_status = "green" if active_faults == 0 else ("yellow" if active_faults <= 5 else "red")

    # ===== 3. SLA 达标率 =====
    # 本期：基于 MaintenanceRecord 的 sla_deadline
    completed_maints = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.status == "completed",
        MaintenanceRecord.completed_at >= range_start
    ).limit(1000).all()

    sla_compliant = 0
    sla_total = 0
    for m in completed_maints:
        if m.sla_deadline and m.completed_at:
            sla_total += 1
            if m.completed_at <= m.sla_deadline:
                sla_compliant += 1

    sla_rate_value = (sla_compliant / sla_total * 100) if sla_total > 0 else 100
    sla_rate_status = _get_status(sla_rate_value, 95, 90, higher_is_good=True) if sla_total > 0 else "gray"

    # 上期 SLA 达标率
    prev_completed_maints = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.status == "completed",
        MaintenanceRecord.completed_at >= prev_range_start,
        MaintenanceRecord.completed_at < range_start
    ).limit(1000).all()

    prev_sla_compliant = 0
    prev_sla_total = 0
    for m in prev_completed_maints:
        if m.sla_deadline and m.completed_at:
            prev_sla_total += 1
            if m.completed_at <= m.sla_deadline:
                prev_sla_compliant += 1

    prev_sla_rate = (prev_sla_compliant / prev_sla_total * 100) if prev_sla_total > 0 else None
    sla_rate_trend = (sla_rate_value - prev_sla_rate) if prev_sla_rate is not None else 0

    # ===== 4. MTTR（平均修复时长） =====
    resolved_faults = db.query(FaultRecord).filter(
        FaultRecord.status.in_(('resolved', 'closed')),
        FaultRecord.resolved_at.isnot(None),
        FaultRecord.created_at >= range_start
    ).limit(1000).all()

    mttr_hours = 0
    if resolved_faults:
        total_resolve_hours = sum(
            (f.resolved_at - f.created_at).total_seconds() / 3600
            for f in resolved_faults
        )
        mttr_hours = total_resolve_hours / len(resolved_faults)

    mttr_status = _get_status(mttr_hours, 4, 8, higher_is_good=False) if resolved_faults else "gray"

    # 上期 MTTR
    prev_resolved_faults = db.query(FaultRecord).filter(
        FaultRecord.status.in_(('resolved', 'closed')),
        FaultRecord.resolved_at.isnot(None),
        FaultRecord.created_at >= prev_range_start,
        FaultRecord.created_at < range_start
    ).limit(1000).all()

    prev_mttr_hours = 0
    if prev_resolved_faults:
        prev_total_hours = sum(
            (f.resolved_at - f.created_at).total_seconds() / 3600
            for f in prev_resolved_faults
        )
        prev_mttr_hours = prev_total_hours / len(prev_resolved_faults)

    mttr_trend = mttr_hours - prev_mttr_hours if prev_resolved_faults else 0

    # ===== 5. MTBF（平均无故障间隔） =====
    total_faults_in_range = db.query(FaultRecord).filter(
        FaultRecord.created_at >= range_start
    ).count()

    mtbf_days = (days * total_deployed / total_faults_in_range) if total_faults_in_range > 0 else 999
    mtbf_status = "green" if mtbf_days >= 30 else ("yellow" if mtbf_days >= 14 else "red")

    # 上期 MTBF
    prev_faults = db.query(FaultRecord).filter(
        FaultRecord.created_at >= prev_range_start,
        FaultRecord.created_at < range_start
    ).count()

    prev_mtbf_days = (days * total_deployed / prev_faults) if prev_faults > 0 else 999
    mtbf_trend = mtbf_days - prev_mtbf_days if prev_faults > 0 else 0

    # ===== 6. 复发故障占比 =====
    # 30天内同设备同类型出现 ≥2 次的故障
    all_faults_30d = db.query(FaultRecord).filter(
        FaultRecord.created_at >= now - timedelta(days=30)
    ).limit(2000).all()

    recurring_count = 0
    device_type_counter = Counter()
    for f in all_faults_30d:
        key = (f.device_id, f.fault_type)
        device_type_counter[key] += 1

    for key, count in device_type_counter.items():
        if count >= 2:
            recurring_count += count

    recurring_rate = (recurring_count / len(all_faults_30d) * 100) if all_faults_30d else 0
    recurring_status = _get_status(recurring_rate, 15, 25, higher_is_good=False)

    # 上期复发率（前30-60天）
    prev_faults_30d = db.query(FaultRecord).filter(
        FaultRecord.created_at >= now - timedelta(days=60),
        FaultRecord.created_at < now - timedelta(days=30)
    ).limit(2000).all()

    prev_device_type_counter = Counter()
    for f in prev_faults_30d:
        key = (f.device_id, f.fault_type)
        prev_device_type_counter[key] += 1

    prev_recurring_count = sum(count for count in prev_device_type_counter.values() if count >= 2)
    prev_recurring_rate = (prev_recurring_count / len(prev_faults_30d) * 100) if prev_faults_30d else None
    recurring_trend = (recurring_rate - prev_recurring_rate) if prev_recurring_rate is not None else 0

    # ===== 7. 本月运维成本 =====
    month_maints = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.created_at >= current_month_start
    ).limit(1000).all()

    month_parts_cost = sum(m.parts_cost or 0 for m in month_maints)
    month_labor_cost = sum(m.labor_cost or 0 for m in month_maints)
    month_total_cost = month_parts_cost + month_labor_cost

    # 上月成本
    prev_month_maints = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.created_at >= prev_month_start,
        MaintenanceRecord.created_at < current_month_start
    ).limit(1000).all()

    prev_month_cost = sum((m.parts_cost or 0) + (m.labor_cost or 0) for m in prev_month_maints)
    month_cost_trend = ((month_total_cost - prev_month_cost) / prev_month_cost * 100) if prev_month_cost > 0 else 0

    # ===== 8. 预算偏差率 =====
    budget_config = db.query(SystemConfig).filter(SystemConfig.key == "monthly_it_budget").first()
    budget_value = float(budget_config.value) if budget_config and budget_config.value else None

    if budget_value is not None and budget_value > 0:
        budget_variance = (month_total_cost - budget_value) / budget_value * 100
        budget_status = _get_status(abs(budget_variance), 5, 10, higher_is_good=False)
    else:
        budget_variance = None
        budget_status = "gray"

    month_cost_status = "green" if budget_value is not None and month_total_cost <= budget_value else "yellow"
    budget_variance_trend = month_cost_trend  # 预算偏差趋势与成本趋势一致

    # ===== 9. 低库存备件数 =====
    spare_parts = db.query(SparePart).filter(SparePart.status == "active").all()
    low_stock_count = len([sp for sp in spare_parts
                           if sp.quantity_in_stock <= (sp.min_quantity or 0) and (sp.min_quantity or 0) > 0])
    low_stock_status = "green" if low_stock_count == 0 else ("yellow" if low_stock_count < 3 else "red")

    # 低库存是实时状态，无法回溯历史 → 趋势未知（不显示箭头）
    low_stock_trend = None

    # ===== 10. 备件保障天数 =====
    consumption_start = now - timedelta(days=90)
    movements = db.query(SparePartMovement).filter(
        SparePartMovement.movement_type == "out",
        SparePartMovement.created_at >= consumption_start
    ).limit(5000).all()

    part_consumption = Counter()
    for m in movements:
        part_consumption[m.part_id] += m.quantity

    daily_consumption = {pid: qty / 90 for pid, qty in part_consumption.items()}

    days_cover_values = []
    for sp in spare_parts:
        if sp.quantity_in_stock > 0:
            daily = daily_consumption.get(sp.id, 0)
            if daily > 0:
                days_cover = sp.quantity_in_stock / daily
                days_cover_values.append(days_cover)

    spare_days_cover = min(days_cover_values) if days_cover_values else 999
    spare_days_cover_estimated = len(days_cover_values) == 0
    days_cover_status = _get_status(spare_days_cover, 30, 14, higher_is_good=True)

    # 保障天数趋势：消耗周期长、无历史快照 → 趋势未知（不显示箭头）
    days_cover_trend = None

    # ===== 11. 根因分布 =====
    fault_types = Counter(f.fault_type or "other" for f in all_faults_30d)
    root_cause_distribution = dict(fault_types)

    # ===== 12. 复发设备 Top 5 =====
    recurring_devices = []
    for key, count in device_type_counter.most_common(5):
        if count >= 2:
            device_id, fault_type = key
            device = db.query(Device).filter(Device.id == device_id).first()
            device_name = device.name if device else f"Device {device_id}"
            recurring_devices.append({
                "device_name": device_name,
                "device_id": device_id,
                "count": count,
                "fault_type": fault_type or "other"
            })

    # ===== 14. MTTR 四段拆解 =====
    # MTTA (平均响应时间): accepted_at - created_at
    # 诊断时间: diagnosing_at - accepted_at
    # 修复时间: resolved_at - diagnosing_at（修复段不含诊断）
    # 验证时间: closed_at - resolved_at（解决→正式关闭）
    # 注：验证段不计入端到端 MTTR，因 resolved 后故障已恢复
    mtta_minutes = 0
    diagnose_minutes = 0
    repair_hours = 0
    verify_hours = 0
    verify_count = 0
    verify_anomalies = 0  # 超过72h的异常样本数
    VERIFY_THRESHOLD_H = 72  # 验证段异常阈值

    for f in resolved_faults:
        if f.created_at and f.accepted_at:
            mtta_minutes += (f.accepted_at - f.created_at).total_seconds() / 60
            # 诊断段：受理 → 开始诊断
            if f.diagnosing_at and f.accepted_at:
                diagnose_minutes += (f.diagnosing_at - f.accepted_at).total_seconds() / 60
            # 修复段：开始诊断 → 解决
            if f.resolved_at and f.diagnosing_at:
                repair_hours += (f.resolved_at - f.diagnosing_at).total_seconds() / 3600
            elif f.resolved_at and f.accepted_at:
                repair_hours += (f.resolved_at - f.accepted_at).total_seconds() / 3600
        # 验证段：解决 → 正式关闭（异常值保护）
        if f.closed_at and f.resolved_at:
            verify_duration = (f.closed_at - f.resolved_at).total_seconds() / 3600
            if verify_duration <= VERIFY_THRESHOLD_H:
                verify_hours += verify_duration
                verify_count += 1
            else:
                # 超过阈值视为"未及时关单"，不计入平均
                verify_anomalies += 1

    # 各段平均值（只统计有效样本）
    mttr_breakdown_count = len(resolved_faults)
    if mttr_breakdown_count > 0:
        mtta_minutes = mtta_minutes / mttr_breakdown_count
        diagnose_minutes = diagnose_minutes / mttr_breakdown_count
        repair_hours = repair_hours / mttr_breakdown_count
    if verify_count > 0:
        verify_hours = verify_hours / verify_count

    mttr_breakdown = {
        "mtta_min": round(mtta_minutes, 1),
        "diagnose_min": round(diagnose_minutes, 1),
        "repair_h": round(repair_hours, 2),
        "verify_h": round(verify_hours, 2),
        "verify_anomalies": verify_anomalies,  # 未及时关单数
        "total_h": round(mttr_hours, 2),  # 端到端 = 响应+诊断+修复，不含验证
        "target_mtta": 30,      # 目标 ≤30min
        "target_diagnose": 60,  # 目标 ≤1h
        "target_repair": 4,     # 目标 ≤4h
        "target_verify": 2,     # 目标 ≤2h
        "note": "验证段为解决→正式关闭时间，不计入端到端MTTR",
    }

    # ===== 15. 根因帕累托分析 =====
    # 按 fault_type 分组计数并降序，计算累计占比
    fault_type_counts = Counter(f.fault_type or "other" for f in all_faults_30d)
    total_faults_for_pareto = sum(fault_type_counts.values())

    root_cause_pareto = []
    cumulative = 0
    for fault_type, count in fault_type_counts.most_common(10):
        pct = (count / total_faults_for_pareto * 100) if total_faults_for_pareto > 0 else 0
        cumulative += pct
        root_cause_pareto.append({
            "type": fault_type,
            "count": count,
            "pct": round(pct, 1),
            "cumulative_pct": round(cumulative, 1)
        })

    # ===== 15. SLO 错误预算 =====
    # 查询配置的 SLO 目标
    slo_configs = db.query(ServiceSlo).filter(ServiceSlo.is_active == True).all()

    slo_results = []
    for slo in slo_configs:
        window_days = slo.window_days or 30
        window_minutes = window_days * 24 * 60  # 窗口总分钟数
        slo_target_pct = float(slo.slo_target)  # 如 99.9

        # 错误预算 = 窗口分钟数 * (1 - SLO目标)
        error_budget_minutes = window_minutes * (1 - slo_target_pct / 100)

        # 解析该 SLO 绑定的设备类型范围
        type_list = [t.strip() for t in (slo.device_types or "").split(",") if t.strip()]

        # 该服务范围内的设备 id
        scope_device_ids = []
        if type_list:
            scope_devices = db.query(Device.id).filter(Device.device_type.in_(type_list)).all()
            scope_device_ids = [d.id for d in scope_devices]

        # 已消耗：窗口内故障造成的停机分钟数。
        # 自动按故障时长推导（不再依赖手工 downtime_minutes，否则自动工单永远算 0）：
        # - 优先使用手工填写的 downtime_minutes（>0）
        # - 否则对 critical/major 故障按 时长(创建→解决；未关单则→现在) 计算
        window_start = now - timedelta(days=window_days)
        last_24h_start = now - timedelta(hours=24)
        OUTAGE_SEVERITIES = ("critical", "major")

        scope_fault_q = db.query(FaultRecord).filter(FaultRecord.created_at >= window_start)
        if type_list and scope_device_ids:
            scope_fault_q = scope_fault_q.filter(FaultRecord.device_id.in_(scope_device_ids))
        scope_faults = scope_fault_q.all()

        def _auto_downtime(f, floor_start):
            """故障停机分钟数（可选起点下限，用于 24h 窗口切分）"""
            if (f.severity or "").lower() not in OUTAGE_SEVERITIES:
                return 0.0
            start = f.created_at
            if not start:
                return 0.0
            end = f.resolved_at or f.closed_at
            if end is None:
                if f.status in ("resolved", "closed"):
                    return 0.0
                end = now  # 未关单：算到现在（反映进行中的停机）
            if floor_start and start < floor_start:
                start = floor_start
            if end <= start:
                return 0.0
            return (end - start).total_seconds() / 60.0

        consumed_minutes = 0.0
        for f in scope_faults:
            manual = float(f.downtime_minutes) if f.downtime_minutes else 0.0
            consumed_minutes += manual if manual > 0 else _auto_downtime(f, None)

        # 剩余预算百分比
        remaining_minutes = error_budget_minutes - float(consumed_minutes)
        remaining_pct = (remaining_minutes / error_budget_minutes * 100) if error_budget_minutes > 0 else 100

        # 燃尽率 burn_rate = 近24h停机速率 / 允许平均速率（含进行中的故障）
        last_24h_consumed = sum(_auto_downtime(f, last_24h_start) for f in scope_faults)

        allowed_avg_rate = error_budget_minutes / window_days  # 每天允许消耗
        actual_24h_rate = float(last_24h_consumed)  # 24小时实际消耗
        burn_rate = actual_24h_rate / allowed_avg_rate if allowed_avg_rate > 0 else 0

        # 状态判定
        if remaining_pct < 0:
            slo_status = "red"  # 预算耗尽
        elif remaining_pct < 30 or burn_rate >= 2:
            slo_status = "yellow"  # 预警（剩余<30%或燃尽率>=2）
        else:
            slo_status = "green"

        slo_results.append({
            "service_key": slo.service_key or slo.service_name.lower().replace(' ', '_'),  # 语言无关标识
            "service": slo.service_name,  # 兜底显示名称
            "target": slo_target_pct,
            "window_days": window_days,
            "device_types": type_list,
            "error_budget_min": round(error_budget_minutes, 1),
            "consumed_min": float(consumed_minutes),
            "remaining_pct": round(remaining_pct, 1),
            "burn_rate": round(burn_rate, 2),
            "status": slo_status,
            "alert": burn_rate >= 2 and remaining_pct < 50  # 建议冻结变更
        })

    # 默认 SLO（如未配置）
    if not slo_results:
        default_window = 30
        default_target = 99.9
        default_budget = default_window * 24 * 60 * (1 - default_target / 100)  # = 43.2
        slo_results.append({
            "service_key": "default",
            "service": "default",
            "target": default_target,
            "window_days": default_window,
            "device_types": [],
            "error_budget_min": round(default_budget, 1),  # 43.2
            "consumed_min": 0,
            "remaining_pct": 100,
            "burn_rate": 0,
            "status": "gray",
            "alert": False
        })

    # ===== 16. 变更-故障关联分析 =====
    # 查询配置变更记录（has_change = True 表示有变更）
    config_changes = db.query(BackupRecord).filter(
        BackupRecord.has_change == True,
        BackupRecord.backup_time >= range_start
    ).all()

    total_changes = len(config_changes)
    change_fault_correlation = []

    # 定义故障关联时间窗口（72小时内）
    correlation_window_hours = 72
    correlation_window = timedelta(hours=correlation_window_hours)

    # 统计变更后发生故障的次数
    changes_with_faults = 0
    device_change_fault_map = defaultdict(lambda: {"changes": 0, "faults_after_change": 0})

    for change in config_changes:
        # 查找变更后时间窗口内该设备的故障
        window_end = change.backup_time + correlation_window
        faults_after_change = db.query(FaultRecord).filter(
            FaultRecord.device_id == change.device_id,
            FaultRecord.created_at >= change.backup_time,
            FaultRecord.created_at <= window_end
        ).count()

        if faults_after_change > 0:
            changes_with_faults += 1
            device_change_fault_map[change.device_name]["changes"] += 1
            device_change_fault_map[change.device_name]["faults_after_change"] += faults_after_change

    # 变更成功率 = (1 - 变更引发故障比例) * 100
    change_success_rate = (1 - changes_with_faults / total_changes) * 100 if total_changes > 0 else 100

    # 变更风险状态判定
    if change_success_rate >= 95:
        change_status = "green"
    elif change_success_rate >= 85:
        change_status = "yellow"
    else:
        change_status = "red"

    # 找出变更后故障最多的设备（Top 5）
    device_correlation_list = []
    for device_name, stats in device_change_fault_map.items():
        if stats["changes"] > 0:
            fault_rate = stats["faults_after_change"] / stats["changes"]
            device_correlation_list.append({
                "device": device_name,
                "changes": stats["changes"],
                "faults_after": stats["faults_after_change"],
                "fault_rate": round(fault_rate, 2)
            })

    # 按故障率排序
    device_correlation_list.sort(key=lambda x: x["fault_rate"], reverse=True)
    risky_devices = device_correlation_list[:5]

    # 上周期对比（趋势）
    prev_changes = db.query(BackupRecord).filter(
        BackupRecord.has_change == True,
        BackupRecord.backup_time >= prev_range_start,
        BackupRecord.backup_time < range_start
    ).count()

    prev_changes_with_faults = 0
    for change in db.query(BackupRecord).filter(
        BackupRecord.has_change == True,
        BackupRecord.backup_time >= prev_range_start,
        BackupRecord.backup_time < range_start
    ).all():
        window_end = change.backup_time + correlation_window
        faults = db.query(FaultRecord).filter(
            FaultRecord.device_id == change.device_id,
            FaultRecord.created_at >= change.backup_time,
            FaultRecord.created_at <= window_end
        ).count()
        if faults > 0:
            prev_changes_with_faults += 1

    prev_change_success_rate = (1 - prev_changes_with_faults / prev_changes) * 100 if prev_changes > 0 else 100
    change_trend = change_success_rate - prev_change_success_rate

    # ===== 17. 自动生成摘要文本 =====
    summary_parts = []
    if offlineDeviceCount := (total_deployed - reachable_devices):
        summary_parts.append(f"离线设备 {offlineDeviceCount} 台")
    if sla_overdue := (sla_total - sla_compliant):
        summary_parts.append(f"SLA 超期 {sla_overdue} 单")
    if low_stock_count > 0:
        summary_parts.append(f"低库存 {low_stock_count} 项")
    if recurring_rate > 15:
        summary_parts.append(f"复发故障率 {recurring_rate:.0f}%")
    if change_success_rate < 90 and changes_with_faults > 0:
        summary_parts.append(f"变更引发故障 {changes_with_faults} 次")

    if summary_parts:
        summary_text = "风险提示：" + "、".join(summary_parts)
    else:
        summary_text = "系统运行平稳，各项指标正常"

    # ===== 组装返回结果 =====
    def _make_kpi(value, unit, target, threshold, trend, status, is_estimated=False):
        return {
            "value": round(value, 2) if isinstance(value, float) else value,
            "unit": unit,
            "target": target,
            "threshold": threshold,
            "trend": round(trend, 2) if isinstance(trend, float) else trend,
            "status": status,
            "is_estimated": is_estimated
        }

    return {
        "generated_at": now.isoformat(),
        "range": time_range,
        "kpis": {
            "availability": _make_kpi(availability_value, "%", 99.5, 98, availability_trend, availability_status),
            "active_faults": _make_kpi(active_faults, "", None, None, active_faults_trend, active_faults_status),
            "sla_rate": _make_kpi(sla_rate_value if sla_total > 0 else None, "%", 95, 90, sla_rate_trend if sla_total > 0 else None, sla_rate_status),
            "mttr_hours": _make_kpi(mttr_hours if resolved_faults else None, "h", 4, 8, mttr_trend if resolved_faults else None, mttr_status),
            "mtbf_days": _make_kpi(mtbf_days if total_faults_in_range > 0 else None, "d", None, None, mtbf_trend if total_faults_in_range > 0 else None, mtbf_status),
            "recurring_rate": _make_kpi(recurring_rate, "%", 15, 25, recurring_trend, recurring_status),
            "month_cost": _make_kpi(month_total_cost, "¥", budget_value, None, month_cost_trend, month_cost_status, is_estimated=False),
            "budget_variance": _make_kpi(
                budget_variance if budget_variance is not None else 0,
                "%", 5, 10, budget_variance_trend, budget_status,
                is_estimated=budget_value is None
            ),
            "spare_low_stock": _make_kpi(low_stock_count, "", 0, 3, low_stock_trend, low_stock_status),
            "spare_days_cover": _make_kpi(spare_days_cover if not spare_days_cover_estimated else None, "d", 30, 14, days_cover_trend, days_cover_status, is_estimated=spare_days_cover_estimated),
            "change_success_rate": _make_kpi(change_success_rate, "%", 95, 85, change_trend, change_status),
        },
        "summary_text": summary_text,
        "root_cause_distribution": root_cause_distribution,
        "root_cause_pareto": root_cause_pareto,
        "mttr_breakdown": mttr_breakdown,
        "recurring_devices": recurring_devices,
        "slo": slo_results,
        "change_fault_correlation": {
            "total_changes": total_changes,
            "changes_with_faults": changes_with_faults,
            "success_rate": round(change_success_rate, 1),
            "correlation_window_hours": correlation_window_hours,
            "risky_devices": risky_devices,
        },
    }


def _get_status(value: float, target: float, threshold: float, higher_is_good: bool = True) -> str:
    """根据目标值和红线判断状态

    Args:
        value: 当前值
        target: 目标值（达标线）
        threshold: 红线（危险线）
        higher_is_good: True 表示数值越高越好（如可用率），False 表示越低越好（如 MTTR）

    Returns:
        green/yellow/red/gray
    """
    if value is None:
        return "gray"

    if higher_is_good:
        if value >= target:
            return "green"
        elif value >= threshold:
            return "yellow"
        else:
            return "red"
    else:
        if value <= target:
            return "green"
        elif value <= threshold:
            return "yellow"
        else:
            return "red"
