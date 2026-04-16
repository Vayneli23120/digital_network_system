"""Console management router"""

from fastapi import APIRouter, Depends

from ..services.console_service import ConsoleService, find_console_port

router = APIRouter(prefix="/api/console", tags=["console"])


@router.get("/ports")
async def list_console_ports():
    """获取可用串口列表"""
    service = ConsoleService()
    ports = service.list_ports()

    return {"ports": ports}


@router.post("/auto-detect")
async def auto_detect_console():
    """自动检测 Console 端口"""
    port = find_console_port()

    if port:
        return {"found": True, "port": port}
    else:
        return {"found": False, "message": "未找到 Console 设备"}
