"""
网络设备厂商适配层

将厂商标识映射到 Netmiko device_type，并提供厂商特定的配置处理逻辑。
支持 Cisco、Huawei、H3C、Juniper。
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class VendorProfile:
    """厂商配置档案"""
    display_name: str
    netmiko_device_type: str
    enter_enable_mode: bool = True  # 是否需要 enable 模式
    config_mode_command: str = "configure terminal"
    exit_config_mode: str = "end"
    save_config_command: str = "write memory"
    show_run_command: str = "show running-config"
    prompt_patterns: Dict[str, str] = field(default_factory=dict)


# 厂商注册表
VENDOR_REGISTRY: Dict[str, VendorProfile] = {
    "cisco": VendorProfile(
        display_name="Cisco",
        netmiko_device_type="cisco_ios",
        enter_enable_mode=True,
    ),
    "huawei": VendorProfile(
        display_name="Huawei",
        netmiko_device_type="huawei",
        enter_enable_mode=False,
        config_mode_command="system-view",
        exit_config_mode="return",
        save_config_command="save",
        show_run_command="display current-configuration",
    ),
    "h3c": VendorProfile(
        display_name="H3C",
        netmiko_device_type="hp_comware",
        enter_enable_mode=False,
        config_mode_command="system-view",
        exit_config_mode="return",
        save_config_command="save force",
        show_run_command="display current-configuration",
    ),
    "juniper": VendorProfile(
        display_name="Juniper",
        netmiko_device_type="juniper_junos",
        enter_enable_mode=False,
        config_mode_command="configure",
        exit_config_mode="exit configuration-mode",
        save_config_command="commit and-quit",
        show_run_command="show configuration | display set",
    ),
    "arista": VendorProfile(
        display_name="Arista",
        netmiko_device_type="arista_eos",
        enter_enable_mode=True,
    ),
}


def get_vendor_profile(vendor: str) -> VendorProfile:
    """根据厂商标识获取配置档案"""
    vendor_lower = vendor.lower().strip() if vendor else "cisco"
    # 支持别名映射
    aliases = {
        "huawei": "huawei",
        "华为": "huawei",
        "h3c": "h3c",
        "新华三": "h3c",
        "hp": "h3c",  # H3C 前身是 HP，部分设备用 hp_comware
        "juniper": "juniper",
        "juniper_junos": "juniper",
        "cisco": "cisco",
        "cisco_ios": "cisco",
        "arista": "arista",
    }
    key = aliases.get(vendor_lower, vendor_lower)
    return VENDOR_REGISTRY.get(key, VENDOR_REGISTRY["cisco"])


def get_all_vendors() -> Dict[str, str]:
    """获取所有支持的厂商标识和显示名称"""
    return {k: v.display_name for k, v in VENDOR_REGISTRY.items()}
