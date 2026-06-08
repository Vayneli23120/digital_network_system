"""
SNMP 查询服务 - 使用 puresnmp 库

通过 SNMP 协议获取设备性能指标：CPU、内存、温度、接口带宽
"""

from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime
import asyncio
import concurrent.futures

# 检查 puresnmp 是否可用
try:
    from puresnmp.api.raw import Client
    from puresnmp.api.pythonic import PyWrapper
    from puresnmp import V2C
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False
    logger.warning("puresnmp 未安装，SNMP 查询功能不可用")


class SNMPService:
    """SNMP 查询服务（使用 puresnmp）"""

    # Cisco 设备 OID
    CISCO_OID = {
        "sys_uptime": "1.3.6.1.2.1.1.3.0",
        "sys_name": "1.3.6.1.2.1.1.5.0",
        "sys_desc": "1.3.6.1.2.1.1.1.0",
        "cpu_5min": "1.3.6.1.4.1.9.9.109.1.1.1.1.8",
        "cpu_1min": "1.3.6.1.4.1.9.9.109.1.1.1.1.7",
        "memory_used": "1.3.6.1.4.1.9.9.109.1.1.1.1.12",
        "memory_free": "1.3.6.1.4.1.9.9.109.1.1.1.1.13",
        "temperature_value": "1.3.6.1.4.1.9.9.91.1.1.1.6",
        "if_desc": "1.3.6.1.2.1.2.2.1.2",
        "if_alias": "1.3.6.1.2.1.31.1.1.1.18",
        "if_oper_status": "1.3.6.1.2.1.2.2.1.8",
        "if_admin_status": "1.3.6.1.2.1.2.2.1.7",
        "if_speed": "1.3.6.1.2.1.2.2.1.5",
        "if_in_octets": "1.3.6.1.2.1.2.2.1.10",
        "if_out_octets": "1.3.6.1.2.1.2.2.1.16",
        "if_in_errors": "1.3.6.1.2.1.2.2.1.14",
        "if_out_errors": "1.3.6.1.2.1.2.2.1.20",
        "if_in_discards": "1.3.6.1.2.1.2.2.1.13",
        "if_out_discards": "1.3.6.1.2.1.2.2.1.19",
        "if_hc_in_octets": "1.3.6.1.2.1.31.1.1.1.6",
        "if_hc_out_octets": "1.3.6.1.2.1.31.1.1.1.10",
    }

    HUAWEI_OID = {
        "sys_uptime": "1.3.6.1.2.1.1.3.0",
        "sys_name": "1.3.6.1.2.1.1.5.0",
        "cpu_5min": "1.3.6.1.4.1.2011.6.3.4.1.1.3",
        "memory_used": "1.3.6.1.4.1.2011.6.3.4.1.2.1",
        "memory_free": "1.3.6.1.4.1.2011.6.3.4.1.2.2",
        "temperature_value": "1.3.6.1.4.1.2011.6.3.14.1.1.1",
        "if_desc": "1.3.6.1.2.1.2.2.1.2",
        "if_alias": "1.3.6.1.2.1.31.1.1.1.18",
        "if_oper_status": "1.3.6.1.2.1.2.2.1.8",
        "if_speed": "1.3.6.1.2.1.2.2.1.5",
        "if_in_octets": "1.3.6.1.2.1.2.2.1.10",
        "if_out_octets": "1.3.6.1.2.1.2.2.1.16",
        "if_in_errors": "1.3.6.1.2.1.2.2.1.14",
        "if_out_errors": "1.3.6.1.2.1.2.2.1.20",
    }

    def __init__(self):
        self._metric_cache: Dict[str, Dict] = {}

    def is_available(self) -> bool:
        return SNMP_AVAILABLE

    def get_oid_set(self, vendor: str) -> Dict[str, str]:
        vendor_lower = vendor.lower()
        if vendor_lower in ['huawei', 'h3c']:
            return self.HUAWEI_OID
        return self.CISCO_OID

    async def _create_wrapper(self, ip: str, community: str) -> PyWrapper:
        """创建 SNMP wrapper"""
        client = Client(ip, V2C(community))
        return PyWrapper(client)

    async def snmp_get_async(self, ip: str, community: str, oid: str, timeout: int = 2) -> Optional[Any]:
        """异步 SNMP GET"""
        if not SNMP_AVAILABLE:
            return None

        try:
            wrapper = await self._create_wrapper(ip, community)
            # 使用 asyncio.wait_for 添加超时控制
            result = await asyncio.wait_for(wrapper.get(oid), timeout=timeout)

            if result is None:
                return None

            # 处理 bytes 类型
            if isinstance(result, bytes):
                try:
                    return result.decode('utf-8', errors='ignore')
                except:
                    return str(result)

            return result

        except Exception as e:
            logger.debug(f"SNMP get failed {ip}/{oid}: {e}")
            return None

    async def snmp_walk_async(self, ip: str, community: str, oid: str, timeout: int = 3) -> Dict[str, Any]:
        """异步 SNMP WALK"""
        if not SNMP_AVAILABLE:
            return {}

        result = {}

        try:
            wrapper = await self._create_wrapper(ip, community)

            # 收集 walk 结果，限制最多收集 100 个结果避免无限循环
            count = 0
            max_items = 100

            try:
                async for item in wrapper.walk(oid):
                    if count >= max_items:
                        break
                    if hasattr(item, 'oid') and hasattr(item, 'value'):
                        full_oid = str(item.oid)
                        suffix = full_oid.replace(oid, "").lstrip(".")
                        value = item.value

                        if value is not None:
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8', errors='ignore')
                                except:
                                    value = str(value)
                            try:
                                result[suffix] = int(value)
                            except (TypeError, ValueError):
                                result[suffix] = str(value)
                        count += 1
            except asyncio.TimeoutError:
                logger.debug(f"SNMP walk timeout {ip}/{oid} after {timeout}s")
                # 返回已收集的部分结果
                return result

            return result

        except Exception as e:
            logger.debug(f"SNMP walk failed {ip}/{oid}: {e}")
            return {}

    def snmp_get(self, ip: str, community: str, oid: str, timeout: int = 2) -> Optional[Any]:
        """同步 SNMP GET"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.snmp_get_async(ip, community, oid, timeout)
                    )
                    return future.result(timeout=timeout + 1)
            else:
                return loop.run_until_complete(
                    self.snmp_get_async(ip, community, oid, timeout)
                )
        except Exception as e:
            logger.debug(f"SNMP get wrapper failed: {e}")
            return None

    def snmp_walk(self, ip: str, community: str, oid: str, timeout: int = 3) -> Dict[str, Any]:
        """同步 SNMP WALK"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.snmp_walk_async(ip, community, oid, timeout)
                    )
                    return future.result(timeout=timeout + 2)
            else:
                return loop.run_until_complete(
                    self.snmp_walk_async(ip, community, oid, timeout)
                )
        except Exception as e:
            logger.debug(f"SNMP walk wrapper failed: {e}")
            return {}

    def _get_status(self, value: float, thresholds: List[int] = [50, 75, 90]) -> str:
        if value is None:
            return "unknown"
        if value < thresholds[0]:
            return "normal"
        if value < thresholds[1]:
            return "warning"
        if value < thresholds[2]:
            return "danger"
        return "critical"

    def get_cpu_utilization(self, ip: str, community: str, vendor: str = "cisco") -> Dict[str, Any]:
        """获取 CPU 利用率"""
        oids = self.get_oid_set(vendor)
        cpu_oid = oids.get("cpu_5min")

        if not cpu_oid:
            return {"value": None, "status": "unknown"}

        cpu_values = self.snmp_walk(ip, community, cpu_oid)

        if cpu_values:
            values = [v for v in cpu_values.values() if isinstance(v, (int, float)) and v >= 0]
            if values:
                cpu_value = float(values[0])
                # CPU 可能是百分比，也可能需要除以100
                if cpu_value > 100:
                    cpu_value = cpu_value / 100
                status = self._get_status(cpu_value, [50, 75, 90])
                return {"value": round(cpu_value, 1), "status": status}

        return {"value": None, "status": "unknown"}

    def get_memory_usage(self, ip: str, community: str, vendor: str = "cisco") -> Dict[str, Any]:
        """获取内存使用率"""
        oids = self.get_oid_set(vendor)

        used = self.snmp_walk(ip, community, oids.get("memory_used", ""))
        free = self.snmp_walk(ip, community, oids.get("memory_free", ""))

        if used and free:
            try:
                used_values = [v for v in used.values() if isinstance(v, (int, float))]
                free_values = [v for v in free.values() if isinstance(v, (int, float))]

                if used_values and free_values:
                    total_used = sum(used_values)
                    total_free = sum(free_values)
                    total = total_used + total_free

                    if total > 0:
                        percent = (total_used / total) * 100
                        status = self._get_status(percent, [50, 75, 90])
                        return {
                            "used_percent": round(percent, 1),
                            "used_mb": round(total_used / 1024, 1),
                            "total_mb": round(total / 1024, 1),
                            "status": status
                        }
            except Exception as e:
                logger.error(f"Memory calculation error: {e}")

        return {"used_percent": None, "status": "unknown"}

    def get_temperature(self, ip: str, community: str, vendor: str = "cisco") -> Dict[str, Any]:
        """获取温度"""
        oids = self.get_oid_set(vendor)
        temp_oid = oids.get("temperature_value", "")

        temp_values = self.snmp_walk(ip, community, temp_oid)

        if temp_values:
            values = [v for v in temp_values.values() if isinstance(v, (int, float))]
            if values:
                temp = float(values[0])
                # 温度值可能需要特殊处理（有些设备返回的是原始值）
                status = self._get_status(temp, [40, 55, 70])
                return {"value": round(temp, 1), "status": status, "threshold": 70}

        return {"value": None, "status": "unknown"}

    def get_system_uptime(self, ip: str, community: str, vendor: str = "cisco") -> Dict[str, Any]:
        """获取系统运行时长"""
        oids = self.get_oid_set(vendor)
        uptime_oid = oids.get("sys_uptime", "")

        uptime_result = self.snmp_get(ip, community, uptime_oid)

        if uptime_result is not None:
            try:
                # puresnmp 返回 datetime.timedelta 类型
                from datetime import timedelta
                if isinstance(uptime_result, timedelta):
                    total_seconds = int(uptime_result.total_seconds())
                    days = total_seconds // 86400
                    hours = (total_seconds % 86400) // 3600
                    minutes = (total_seconds % 3600) // 60
                    return {
                        "uptime_days": days,
                        "uptime_hours": hours,
                        "uptime_minutes": minutes,
                        "human": f"{days}天 {hours}时 {minutes}分"
                    }
                elif isinstance(uptime_result, str):
                    # 解析 TimeTicks 字符串格式
                    import re
                    match = re.match(r'(\d+)\s*days?,\s*(\d+):(\d+):(\d+)', str(uptime_result))
                    if match:
                        days = int(match.group(1))
                        hours = int(match.group(2))
                        minutes = int(match.group(3))
                        return {
                            "uptime_days": days,
                            "uptime_hours": hours,
                            "uptime_minutes": minutes,
                            "human": f"{days}天 {hours}时 {minutes}分"
                        }
                elif isinstance(uptime_result, (int, float)):
                    # SNMP uptime 是 1/100 秒 (ticks)
                    ticks = int(uptime_result)
                    seconds = ticks / 100
                    days = int(seconds / 86400)
                    hours = int((seconds % 86400) / 3600)
                    minutes = int((seconds % 3600) / 60)

                    return {
                        "uptime_days": days,
                        "uptime_hours": hours,
                        "uptime_minutes": minutes,
                        "uptime_ticks": ticks,
                        "human": f"{days}天 {hours}时 {minutes}分"
                    }
            except Exception as e:
                logger.debug(f"Uptime parsing error: {e}")

        return {"uptime_days": None, "human": None}

        return {"uptime_days": None, "human": None}

    def get_interface_status_summary(self, ip: str, community: str, vendor: str = "cisco") -> Dict[str, Any]:
        """获取接口状态统计"""
        oids = self.get_oid_set(vendor)

        oper_status = self.snmp_walk(ip, community, oids.get("if_oper_status", ""))

        if oper_status:
            up_count = sum(1 for v in oper_status.values() if v == 1)
            down_count = sum(1 for v in oper_status.values() if v == 2)
            total = len(oper_status)

            return {
                "up": up_count,
                "down": down_count,
                "total": total
            }

        return {"up": None, "down": None, "total": None}

    def get_interface_errors(self, ip: str, community: str, vendor: str = "cisco") -> Dict[str, Any]:
        """获取接口错误包"""
        oids = self.get_oid_set(vendor)

        in_errors = self.snmp_walk(ip, community, oids.get("if_in_errors", ""))
        out_errors = self.snmp_walk(ip, community, oids.get("if_out_errors", ""))

        try:
            total_in = sum(v for v in in_errors.values() if isinstance(v, int))
            total_out = sum(v for v in out_errors.values() if isinstance(v, int))
            total = total_in + total_out

            return {
                "total_errors": total,
                "in_errors": total_in,
                "out_errors": total_out,
                "has_errors": total > 0
            }
        except:
            pass

        return {"total_errors": None, "has_errors": False}

    def get_uplink_bandwidth(self, ip: str, community: str, vendor: str = "cisco") -> List[Dict[str, Any]]:
        """获取上行链路信息"""
        oids = self.get_oid_set(vendor)

        if_desc = self.snmp_walk(ip, community, oids.get("if_desc", ""))
        if_alias = self.snmp_walk(ip, community, oids.get("if_alias", ""))
        if_speed = self.snmp_walk(ip, community, oids.get("if_speed", ""))
        if_oper_status = self.snmp_walk(ip, community, oids.get("if_oper_status", ""))

        uplinks = []

        for idx, desc in if_desc.items():
            desc_str = str(desc) if desc else ""
            # 判断是否是物理接口（上行链路）
            is_uplink = any(kw in desc_str.lower() for kw in ['gi', 'fa', 'xe', 'eth', 'ten'])

            if is_uplink and idx in if_oper_status and if_oper_status[idx] == 1:  # UP
                speed = if_speed.get(idx, 0) or 0
                speed_mbps = int(speed / 1000000) if speed > 0 else 0

                alias = if_alias.get(idx, desc_str)

                uplinks.append({
                    "index": idx,
                    "interface": desc_str,
                    "alias": alias,
                    "speed_mbps": speed_mbps,
                    "status": "up",
                    "utilization": None
                })

        return uplinks[:10]

    async def get_device_metrics_async(self, ip: str, community: str = "public", vendor: str = "cisco") -> Dict[str, Any]:
        """获取设备完整性能指标（异步版本）"""
        logger.info(f"开始获取设备 {ip} 的性能指标...")

        oids = self.get_oid_set(vendor)

        # 并行执行多个 SNMP 查询
        try:
            # 获取 CPU
            cpu_values = await self.snmp_walk_async(ip, community, oids.get("cpu_5min", ""), timeout=3)
            cpu = {"value": None, "status": "unknown"}
            if cpu_values:
                values = [v for v in cpu_values.values() if isinstance(v, (int, float)) and v >= 0]
                if values:
                    cpu_val = float(values[0])
                    if cpu_val > 100:
                        cpu_val = cpu_val / 100
                    cpu = {"value": round(cpu_val, 1), "status": self._get_status(cpu_val, [50, 75, 90])}

            # 获取 uptime
            uptime_result = await self.snmp_get_async(ip, community, oids.get("sys_uptime", ""), timeout=2)
            uptime = {"uptime_days": None, "human": None}
            if uptime_result is not None:
                from datetime import timedelta
                if isinstance(uptime_result, timedelta):
                    total_seconds = int(uptime_result.total_seconds())
                    days = total_seconds // 86400
                    hours = (total_seconds % 86400) // 3600
                    minutes = (total_seconds % 3600) // 60
                    uptime = {
                        "uptime_days": days,
                        "uptime_hours": hours,
                        "uptime_minutes": minutes,
                        "human": f"{days}天 {hours}时 {minutes}分"
                    }

            # 获取接口状态
            oper_status = await self.snmp_walk_async(ip, community, oids.get("if_oper_status", ""), timeout=3)
            interfaces = {"up": None, "down": None, "total": None}
            if oper_status:
                up_count = sum(1 for v in oper_status.values() if v == 1)
                down_count = sum(1 for v in oper_status.values() if v == 2)
                interfaces = {"up": up_count, "down": down_count, "total": len(oper_status)}

            # 获取错误包
            in_errors = await self.snmp_walk_async(ip, community, oids.get("if_in_errors", ""), timeout=2)
            out_errors = await self.snmp_walk_async(ip, community, oids.get("if_out_errors", ""), timeout=2)
            errors = {"total_errors": 0, "in_errors": 0, "out_errors": 0, "has_errors": False}
            try:
                total_in = sum(v for v in in_errors.values() if isinstance(v, int))
                total_out = sum(v for v in out_errors.values() if isinstance(v, int))
                total = total_in + total_out
                errors = {"total_errors": total, "in_errors": total_in, "out_errors": total_out, "has_errors": total > 0}
            except:
                pass

            # 获取上行链路
            if_desc = await self.snmp_walk_async(ip, community, oids.get("if_desc", ""), timeout=3)
            if_alias = await self.snmp_walk_async(ip, community, oids.get("if_alias", ""), timeout=2)
            if_speed = await self.snmp_walk_async(ip, community, oids.get("if_speed", ""), timeout=2)

            uplinks = []
            for idx, desc in if_desc.items():
                desc_str = str(desc) if desc else ""
                is_uplink = any(kw in desc_str.lower() for kw in ['gi', 'fa', 'xe', 'eth', 'ten'])
                if is_uplink and idx in oper_status and oper_status.get(idx) == 1:
                    speed = if_speed.get(idx, 0) or 0
                    speed_mbps = int(speed / 1000000) if speed > 0 else 0
                    alias = if_alias.get(idx, desc_str)
                    uplinks.append({
                        "index": idx,
                        "interface": desc_str,
                        "alias": alias,
                        "speed_mbps": speed_mbps,
                        "status": "up",
                        "utilization": None
                    })

            result = {
                "cpu": cpu,
                "memory": {"used_percent": None, "status": "unknown"},
                "temperature": {"value": None, "status": "unknown"},
                "uptime": uptime,
                "interfaces": interfaces,
                "errors": errors,
                "uplinks": uplinks[:10],
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"设备 {ip} 性能指标获取完成: CPU={cpu.get('value')}")
            return result

        except Exception as e:
            logger.error(f"SNMP query failed for {ip}: {e}")
            return {
                "cpu": {"value": None, "status": "unknown"},
                "memory": {"used_percent": None, "status": "unknown"},
                "temperature": {"value": None, "status": "unknown"},
                "uptime": {"uptime_days": None, "human": None},
                "interfaces": {"up": None, "down": None, "total": None},
                "errors": {"total_errors": 0, "has_errors": False},
                "uplinks": [],
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def get_device_metrics(self, ip: str, community: str = "public", vendor: str = "cisco") -> Dict[str, Any]:
        """获取设备完整性能指标"""
        logger.info(f"开始获取设备 {ip} 的性能指标...")

        result = {
            "cpu": self.get_cpu_utilization(ip, community, vendor),
            "memory": self.get_memory_usage(ip, community, vendor),
            "temperature": self.get_temperature(ip, community, vendor),
            "uptime": self.get_system_uptime(ip, community, vendor),
            "interfaces": self.get_interface_status_summary(ip, community, vendor),
            "errors": self.get_interface_errors(ip, community, vendor),
            "uplinks": self.get_uplink_bandwidth(ip, community, vendor),
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"设备 {ip} 性能指标获取完成: CPU={result['cpu'].get('value')}, Mem={result['memory'].get('used_percent')}")
        return result


# 单例服务
_snmp_service: Optional[SNMPService] = None


def get_snmp_service() -> SNMPService:
    """获取 SNMP 服务单例"""
    global _snmp_service
    if _snmp_service is None:
        _snmp_service = SNMPService()
    return _snmp_service