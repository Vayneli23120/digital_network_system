"""
厂商管理服务

提供支持的厂商标识列表、厂商特定配置等。
"""

from typing import Dict, Any, List
from app.features.devices.vendor_adapter import get_vendor_profile, get_all_vendors, VENDOR_REGISTRY


def get_supported_vendors() -> Dict[str, Any]:
    """获取所有支持的厂商"""
    vendors = []
    for key, profile in VENDOR_REGISTRY.items():
        vendors.append({
            "key": key,
            "name": profile.display_name,
            "device_type": profile.netmiko_device_type,
        })
    return {
        "total": len(vendors),
        "vendors": vendors,
    }


def get_vendor_info(vendor: str) -> Dict[str, Any]:
    """获取指定厂商的详细信息"""
    profile = get_vendor_profile(vendor)
    return {
        "key": vendor,
        "name": profile.display_name,
        "device_type": profile.netmiko_device_type,
        "enter_enable_mode": profile.enter_enable_mode,
        "config_mode_command": profile.config_mode_command,
        "exit_config_mode": profile.exit_config_mode,
        "save_config_command": profile.save_config_command,
        "show_run_command": profile.show_run_command,
    }
