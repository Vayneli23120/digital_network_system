"""
日志管理 API
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from typing import Optional, List
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.log_service import get_log_service

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def list_logs(
    days: int = Query(default=7, description="查看最近 N 天的日志"),
    level: Optional[str] = Query(default=None, description="日志级别过滤"),
    limit: int = Query(default=100, description="返回条数限制")
):
    """获取日志列表"""
    log_service = get_log_service()
    logs = log_service.get_latest_logs(count=limit, level=level)
    return {"items": logs, "total": len(logs)}


@router.get("/files")
async def list_log_files(days: int = Query(default=7, description="查看最近 N 天的日志文件")):
    """获取日志文件列表"""
    log_service = get_log_service()
    files = log_service.get_log_files(days=days)
    return {"items": files, "total": len(files)}


@router.get("/files/{filename}")
async def get_log_file_content(
    filename: str,
    lines: int = Query(default=100, description="读取行数"),
    level: Optional[str] = Query(default=None, description="日志级别过滤")
):
    """读取日志文件内容"""
    log_service = get_log_service()
    logs = log_service.read_log_file(filename, lines=lines, level=level)
    return {"items": logs, "filename": filename}


@router.get("/search")
async def search_logs(
    keyword: str = Query(..., description="搜索关键词"),
    days: int = Query(default=7, description="搜索范围（天）"),
    level: Optional[str] = Query(default=None, description="日志级别过滤")
):
    """搜索日志"""
    log_service = get_log_service()
    results = log_service.search_logs(keyword, days=days, level=level)
    return {"items": results, "total": len(results), "keyword": keyword}


@router.websocket("/ws")
async def logs_websocket(websocket: WebSocket):
    """WebSocket 实时日志推送"""
    await websocket.accept()
    log_service = get_log_service()

    try:
        for log_entry in log_service.stream_logs(follow=True):
            await websocket.send_json(log_entry)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"level": "ERROR", "message": str(e)})


@router.post("/clear")
async def clear_old_logs(days: int = Query(default=30, description="保留 N 天内的日志")):
    """清理旧日志"""
    log_service = get_log_service()
    cleared = log_service.clear_old_logs(days=days)
    return {"cleared": cleared, "message": f"清理了 {cleared} 个旧日志文件"}
