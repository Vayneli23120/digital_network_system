"""
设备发现 API 路由

提供网络设备自动发现功能：
- Ping Sweep：扫描网段内活跃主机
- CDP Discovery：在 Cisco 设备上使用 CDP 协议发现邻居
- 设备识别：识别发现的设备是否为 Cisco 设备
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.discovery_service import (
    get_discovery_service,
    DiscoveredDevice,
    quick_discovery,
    NETMIKO_AVAILABLE,
)
from .auth import get_current_active_user
from ..models import User

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class PingSweepRequest(BaseModel):
    """Ping Sweep 请求"""
    subnet: str = Field(..., description="CIDR 格式，如 192.168.1.0/24")
    timeout: float = Field(default=2.0, description="单主机超时时间（秒）")
    workers: int = Field(default=50, description="并发线程数")


class DiscoveryRequest(BaseModel):
    """综合发现请求"""
    subnet: str = Field(..., description="CIDR 格式")
    username: Optional[str] = Field(default=None, description="SSH 用户名")
    password: Optional[str] = Field(default=None, description="SSH 密码")
    secret: Optional[str] = Field(default=None, description="Enable 密码")
    use_cdp: bool = Field(default=False, description="是否使用 CDP 发现")
    use_nmap: bool = Field(default=False, description="是否使用 nmap（需要安装）")
    timeout: float = Field(default=2.0, description="超时时间")


class DiscoveredDeviceResponse(BaseModel):
    """发现设备响应"""
    ip: str
    hostname: Optional[str] = None
    model: Optional[str] = None
    vendor: str
    discovery_method: str
    port: int
    is_cisco: bool
    cdp_neighbors: List[Dict[str, str]] = []


class DiscoveryResponse(BaseModel):
    """发现结果响应"""
    total: int
    devices: List[DiscoveredDeviceResponse]
    subnet: str
    scan_duration_ms: Optional[float] = None


# =============================================================================
# API 端点
# =============================================================================

@router.post("/ping-sweep", response_model=DiscoveryResponse)
async def ping_sweep(
    request: PingSweepRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Ping Sweep 网段扫描

    发现指定网段内开放 22 端口的主机。
    不需要 SSH 凭证，仅检测主机是否存活。
    """
    import time
    start = time.time()

    try:
        service = get_discovery_service(
            timeout=request.timeout,
            workers=request.workers
        )
        devices = service.ping_sweep(request.subnet)
        duration_ms = (time.time() - start) * 1000

        return DiscoveryResponse(
            total=len(devices),
            devices=[
                DiscoveredDeviceResponse(
                    ip=d.ip,
                    hostname=d.hostname,
                    model=d.model,
                    vendor=d.vendor,
                    discovery_method=d.discovery_method,
                    port=d.port,
                    is_cisco=d.is_cisco,
                    cdp_neighbors=d.cdp_neighbors,
                )
                for d in devices
            ],
            subnet=request.subnet,
            scan_duration_ms=round(duration_ms, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ping Sweep 失败: {str(e)}")


@router.post("/discover", response_model=DiscoveryResponse)
async def discover_devices(
    request: DiscoveryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    综合设备发现

    执行完整的发现流程：
    1. Ping Sweep 发现活跃主机
    2. SSH 连接识别是否为 Cisco 设备
    3. 可选：CDP 发现邻居设备
    """
    import time
    start = time.time()

    if not NETMIKO_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="netmiko 未安装，无法执行发现。请运行: pip install netmiko"
        )

    credentials = None
    if request.username and request.password:
        credentials = {
            "username": request.username,
            "password": request.password,
            "secret": request.secret or "",
        }

    try:
        service = get_discovery_service(timeout=request.timeout)
        devices = service.discover_subnet(
            subnet=request.subnet,
            credentials=credentials,
            use_cdp=request.use_cdp,
            use_nmap=request.use_nmap,
        )
        duration_ms = (time.time() - start) * 1000

        return DiscoveryResponse(
            total=len(devices),
            devices=[
                DiscoveredDeviceResponse(
                    ip=d.ip,
                    hostname=d.hostname,
                    model=d.model,
                    vendor=d.vendor,
                    discovery_method=d.discovery_method,
                    port=d.port,
                    is_cisco=d.is_cisco,
                    cdp_neighbors=d.cdp_neighbors,
                )
                for d in devices
            ],
            subnet=request.subnet,
            scan_duration_ms=round(duration_ms, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发现失败: {str(e)}")


@router.get("/capabilities")
async def get_discovery_capabilities(current_user: User = Depends(get_current_active_user)):
    """
    获取发现服务能力信息

    返回当前环境支持的发现功能
    """
    return {
        "netmiko_available": NETMIKO_AVAILABLE,
        "supported_methods": [
            "ping-sweep" if True else None,
            "netmiko-ssh" if NETMIKO_AVAILABLE else None,
            "cdp" if NETMIKO_AVAILABLE else None,
            "nmap" if False else None,  # 需要额外安装
        ],
        "description": {
            "ping-sweep": "Ping sweep 网段，检测 22 端口开放的主机",
            "netmiko-ssh": "SSH 连接 Cisco 设备获取详细信息",
            "cdp": "Cisco Discovery Protocol，发现邻居设备",
            "nmap": "nmap 深度扫描（需要安装 python-nmap）",
        }
    }
