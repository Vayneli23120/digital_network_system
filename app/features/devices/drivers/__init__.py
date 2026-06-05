"""
设备驱动模块

提供：
- base: 抽象基类
- registry: 驱动注册表
- 各厂商驱动实现
"""

from app.features.devices.drivers.base import BaseDeviceDriver
from app.features.devices.drivers.registry import DriverRegistry

__all__ = ["BaseDeviceDriver", "DriverRegistry"]