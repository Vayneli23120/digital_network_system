"""
设备驱动注册表

所有 BaseDeviceDriver 子类自动注册，无需手动维护映射表。
"""

from typing import Type, Dict, Optional, List
from loguru import logger

from app.features.devices.drivers.base import BaseDeviceDriver


class DriverRegistry:
    """
    设备驱动注册表

    通过 vendor 或 os_type 获取对应驱动类。
    """

    _registry: Dict[str, Type[BaseDeviceDriver]] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, driver_class: Type[BaseDeviceDriver]) -> None:
        """
        注册驱动类

        Args:
            driver_class: BaseDeviceDriver 子类
        """
        if not driver_class.VENDOR:
            logger.warning(f"Driver {driver_class.__name__} has no VENDOR defined")
            return

        # 按 vendor 注册
        cls._registry[driver_class.VENDOR.lower()] = driver_class

        # 按 os_type 注册
        for os_type in driver_class.OS_TYPES:
            cls._registry[os_type.lower()] = driver_class

        logger.debug(f"Driver registered: {driver_class.VENDOR} ({driver_class.__name__})")

    @classmethod
    def get(cls, vendor: str) -> Type[BaseDeviceDriver]:
        """
        获取驱动类

        Args:
            vendor: 厂商名称或 OS 类型

        Returns:
            驱动类，未找到时返回默认 Cisco IOS 驱动
        """
        cls._ensure_initialized()

        vendor_lower = vendor.lower() if vendor else "cisco"
        driver_class = cls._registry.get(vendor_lower)

        if not driver_class:
            # 尝试部分匹配
            for key, drv in cls._registry.items():
                if vendor_lower in key or key in vendor_lower:
                    driver_class = drv
                    break

        if not driver_class:
            logger.warning(f"No driver found for vendor '{vendor}', using Cisco IOS")
            from app.features.devices.drivers.cisco_ios import CiscoIOSDriver
            driver_class = CiscoIOSDriver

        return driver_class

    @classmethod
    def list_vendors(cls) -> Dict[str, str]:
        """
        列出所有支持的厂商

        Returns:
            {vendor: driver_class_name}
        """
        cls._ensure_initialized()
        return {
            vendor: drv.__name__
            for vendor, drv in cls._registry.items()
            if drv.VENDOR == vendor  # 仅显示主要厂商
        }

    @classmethod
    def list_all_drivers(cls) -> List[Dict[str, str]]:
        """
        列出所有驱动详情

        Returns:
            [{vendor, os_types, netmiko_driver, napalm_driver}]
        """
        cls._ensure_initialized()

        seen_vendors = set()
        drivers = []

        for vendor, drv in cls._registry.items():
            if drv.VENDOR in seen_vendors:
                continue
            seen_vendors.add(drv.VENDOR)

            drivers.append({
                "vendor": drv.VENDOR,
                "os_types": drv.OS_TYPES,
                "netmiko_driver": drv.NETMIKO_DRIVER,
                "napalm_driver": drv.NAPALM_DRIVER or "N/A",
                "supports_enable": drv.SUPPORTS_ENABLE_MODE,
            })

        return drivers

    @classmethod
    def _ensure_initialized(cls) -> None:
        """确保所有驱动已注册"""
        if cls._initialized:
            return

        # 自动发现并注册所有驱动
        cls._auto_discover_drivers()
        cls._initialized = True

    @classmethod
    def _auto_discover_drivers(cls) -> None:
        """自动发现并注册 drivers 目录下的所有驱动"""
        import os
        import importlib
        from pathlib import Path

        drivers_dir = Path(__file__).parent

        for py_file in drivers_dir.glob("*.py"):
            if py_file.name in ("base.py", "registry.py", "__init__.py"):
                continue

            module_name = py_file.stem
            try:
                module = importlib.import_module(
                    f"app.features.devices.drivers.{module_name}"
                )
                # 查找所有 BaseDeviceDriver 子类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseDeviceDriver)
                        and attr != BaseDeviceDriver
                    ):
                        cls.register(attr)
            except Exception as e:
                logger.warning(f"Failed to import driver module {module_name}: {e}")