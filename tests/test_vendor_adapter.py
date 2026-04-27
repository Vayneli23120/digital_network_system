"""
Tests for vendor_adapter.py
"""

import pytest
from app.features.devices.vendor_adapter import (
    get_vendor_profile, get_all_vendors, VENDOR_REGISTRY, VendorProfile
)
from app.features.devices.vendor_service import get_supported_vendors, get_vendor_info


class TestVendorProfile:
    def test_cisco_profile(self):
        profile = get_vendor_profile("cisco")
        assert profile.netmiko_device_type == "cisco_ios"
        assert profile.enter_enable_mode is True
        assert profile.display_name == "Cisco"

    def test_huawei_profile(self):
        profile = get_vendor_profile("huawei")
        assert profile.netmiko_device_type == "huawei"
        assert profile.enter_enable_mode is False
        assert profile.show_run_command == "display current-configuration"

    def test_h3c_profile(self):
        profile = get_vendor_profile("h3c")
        assert profile.netmiko_device_type == "hp_comware"
        assert profile.config_mode_command == "system-view"

    def test_juniper_profile(self):
        profile = get_vendor_profile("juniper")
        assert profile.netmiko_device_type == "juniper_junos"
        assert profile.save_config_command == "commit and-quit"

    def test_arista_profile(self):
        profile = get_vendor_profile("arista")
        assert profile.netmiko_device_type == "arista_eos"

    def test_unknown_vendor_defaults_to_cisco(self):
        profile = get_vendor_profile("unknown_vendor_xyz")
        assert profile.netmiko_device_type == "cisco_ios"

    def test_empty_vendor_defaults_to_cisco(self):
        profile = get_vendor_profile("")
        assert profile.netmiko_device_type == "cisco_ios"

    def test_none_vendor_defaults_to_cisco(self):
        profile = get_vendor_profile(None)
        assert profile.netmiko_device_type == "cisco_ios"


class TestVendorAliases:
    def test_chinese_huawei_alias(self):
        profile = get_vendor_profile("华为")
        assert profile.netmiko_device_type == "huawei"

    def test_chinese_h3c_alias(self):
        profile = get_vendor_profile("新华三")
        assert profile.netmiko_device_type == "hp_comware"

    def test_hp_maps_to_h3c(self):
        profile = get_vendor_profile("hp")
        assert profile.netmiko_device_type == "hp_comware"

    def test_case_insensitive(self):
        profile = get_vendor_profile("CISCO")
        assert profile.netmiko_device_type == "cisco_ios"


class TestGetAllVendors:
    def test_returns_all_vendors(self):
        vendors = get_all_vendors()
        assert "cisco" in vendors
        assert "huawei" in vendors
        assert "h3c" in vendors
        assert "juniper" in vendors
        assert "arista" in vendors

    def test_returns_display_names(self):
        vendors = get_all_vendors()
        assert vendors["cisco"] == "Cisco"
        assert vendors["huawei"] == "Huawei"


class TestVendorService:
    def test_get_supported_vendors(self):
        result = get_supported_vendors()
        assert result["total"] == 5
        assert len(result["vendors"]) == 5

    def test_vendor_info_structure(self):
        info = get_vendor_info("huawei")
        assert info["key"] == "huawei"
        assert info["name"] == "Huawei"
        assert info["device_type"] == "huawei"
        assert "show_run_command" in info
        assert "save_config_command" in info

    def test_vendor_info_unknown_returns_cisco(self):
        info = get_vendor_info("unknown_xyz")
        assert info["device_type"] == "cisco_ios"
