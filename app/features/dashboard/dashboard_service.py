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

from app.shared.models import Device, BackupRecord, FaultRecord, MaintenanceRecord, SparePart
from app.shared.cache import cache


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """获取 Dashboard 摘要数据

    Args:
        db: 数据库会话

    Returns:
        摘要数据字典
    """
    # 设备统计
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "online").count()
    offline_devices = db.query(Device).filter(Device.status == "offline").count()
    maintenance_devices = db.query(Device).filter(Device.status == "maintenance").count()
    retired_devices = db.query(Device).filter(Device.status == "retired").count()

    # 按设备类型统计
    device_types = ["uce", "core_switch", "server_switch", "office_switch", "ap", "router", "firewall", "other"]
    devices_by_type = {}
    for dtype in device_types:
        devices_by_type[dtype] = {
            "total": db.query(Device).filter(Device.device_type == dtype).count(),
            "online": db.query(Device).filter(Device.device_type == dtype, Device.status == "online").count(),
            "offline": db.query(Device).filter(Device.device_type == dtype, Device.status == "offline").count(),
            "maintenance": db.query(Device).filter(Device.device_type == dtype, Device.status == "maintenance").count(),
            "retired": db.query(Device).filter(Device.device_type == dtype, Device.status == "retired").count(),
        }

    # 备份统计（最近 10 条）
    recent_backups = db.query(BackupRecord).order_by(BackupRecord.backup_time.desc()).limit(10).all()

    # 故障统计（近 30 天，限制数量避免全表加载）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_faults = db.query(FaultRecord).filter(
        FaultRecord.created_at >= thirty_days_ago
    ).limit(1000).all()

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
            "total": total_devices,
            "online": online_devices,
            "offline": offline_devices,
            "maintenance": maintenance_devices,
            "retired": retired_devices,
            "by_type": devices_by_type,
        },
        "backups": {
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
