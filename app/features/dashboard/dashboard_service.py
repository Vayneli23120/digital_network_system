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

from app.shared.models import Device, BackupRecord, FaultRecord, MaintenanceRecord
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

    # 备份统计（最近 10 条）
    recent_backups = db.query(BackupRecord).order_by(BackupRecord.backup_time.desc()).limit(10).all()

    # 故障统计（近 30 天，限制数量避免全表加载）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_faults = db.query(FaultRecord).filter(
        FaultRecord.created_at >= thirty_days_ago
    ).limit(1000).all()

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
            "retired": total_devices - online_devices - offline_devices - maintenance_devices,
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
        },
        "costs": {
            "month_maintenance": float(total_parts_cost),
            "month_labor": float(total_labor_cost),
            "month_total": float(total_parts_cost + total_labor_cost),
        },
    }


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
            week_key = fault.created_at.strftime("%Y-%W")
            label = f"第{int(week_key.split('-')[1])}周"
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
                week_idx = int(label.replace("第", "").replace("周", ""))
                week_data[week_idx] = {
                    "count": count,
                    "severity": fault_by_severity[label],
                }
            except (ValueError, KeyError):
                continue

        if week_data:
            min_week = min(week_data.keys())
            for i in range(13):
                week_num = min_week + i
                label = f"第{week_num}周"
                labels.append(label)
                if week_num in week_data:
                    values.append(week_data[week_num]["count"])
                    severity_timeline[label] = {
                        "critical": week_data[week_num]["severity"].get("critical", 0),
                        "major": week_data[week_num]["severity"].get("major", 0),
                        "minor": week_data[week_num]["severity"].get("minor", 0),
                        "warning": week_data[week_num]["severity"].get("warning", 0),
                    }
                else:
                    values.append(0)
                    severity_timeline[label] = {
                        "critical": 0,
                        "major": 0,
                        "minor": 0,
                        "warning": 0,
                    }

    elif group_by == "month":
        current = query_start_date
        while current < query_end_date:
            label = current.strftime("%Y-%m")
            labels.append(label)
            values.append(fault_counts.get(label, 0))
            severity_timeline[label] = {
                "critical": fault_by_severity.get(label, {}).get("critical", 0),
                "major": fault_by_severity.get(label, {}).get("major", 0),
                "minor": fault_by_severity.get(label, {}).get("minor", 0),
                "warning": fault_by_severity.get(label, {}).get("warning", 0),
            }
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
