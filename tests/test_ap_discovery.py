"""Tests for CDP/LLDP-based AP neighbor detection."""

from app.services.ap_discovery import is_ap_neighbor


def test_platform_based_ap_detection():
    assert is_ap_neighbor(platform="AIR-AP2802I-B-K9") is True
    assert is_ap_neighbor(platform="cisco AIRONET 3702") is True
    assert is_ap_neighbor(platform="C9120AXI-E") is True
    assert is_ap_neighbor(platform="CW9163E") is True


def test_capability_based_ap_detection():
    assert is_ap_neighbor(platform="", capabilities="Trans-Bridge WLAN") is True
    assert is_ap_neighbor(platform="", capabilities="Router Switch") is False


def test_hostname_based_ap_detection_for_lab_simulation():
    # PNETLab 模拟：主机名含独立 ap 词元
    assert is_ap_neighbor(host="office-ap-01") is True
    assert is_ap_neighbor(host="ap-3f-12") is True
    assert is_ap_neighbor(host="AP12") is True


def test_non_ap_devices_are_not_misclassified():
    # 普通交换机
    assert is_ap_neighbor(platform="cisco WS-C3850-48P", host="cn-office-sw01") is False
    # WLC 控制器主机名含 "apc"，不应被当成 AP
    assert is_ap_neighbor(platform="", host="cn-pulandian1-apc_new") is False
    # 空输入
    assert is_ap_neighbor() is False
