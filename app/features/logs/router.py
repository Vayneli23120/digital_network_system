"""
日志管理 API
"""

import asyncio
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.shared.dependencies import require_permission
from .log_service import get_log_service
from .security import (
    UnsafeLogPathError,
    authenticate_log_websocket,
)

router = APIRouter(prefix="/api/logs", tags=["logs"])
require_log_read = require_permission("log:read")
require_log_clear = require_permission("log:clear")
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "RAW"]


@router.get("")
async def list_logs(
    days: int = Query(default=7, ge=0, le=365, description="查看最近 N 天的日志"),
    level: Optional[LogLevel] = Query(default=None, description="日志级别过滤"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回条数限制"),
    _: None = Depends(require_log_read),
):
    """获取日志列表"""
    log_service = get_log_service()
    logs = await asyncio.to_thread(
        log_service.get_latest_logs,
        count=limit,
        level=level,
        days=days,
    )
    return {"items": logs, "total": len(logs)}


@router.get("/files")
async def list_log_files(
    days: int = Query(default=7, ge=0, le=365, description="查看最近 N 天的日志文件"),
    _: None = Depends(require_log_read),
):
    """获取日志文件列表"""
    log_service = get_log_service()
    files = await asyncio.to_thread(log_service.get_log_files, days=days)
    return {"items": files, "total": len(files)}


@router.get("/files/{filename}")
async def get_log_file_content(
    filename: str,
    lines: int = Query(default=100, ge=1, le=5000, description="读取行数"),
    level: Optional[LogLevel] = Query(default=None, description="日志级别过滤"),
    _: None = Depends(require_log_read),
):
    """读取日志文件内容"""
    log_service = get_log_service()
    try:
        logs = await asyncio.to_thread(
            log_service.read_log_file,
            filename,
            lines=lines,
            level=level,
        )
    except UnsafeLogPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"items": logs, "filename": filename}


@router.get("/search")
async def search_logs(
    keyword: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    days: int = Query(default=7, ge=0, le=365, description="搜索范围（天）"),
    level: Optional[LogLevel] = Query(default=None, description="日志级别过滤"),
    max_results: int = Query(default=500, ge=1, le=1000, description="最大返回条数"),
    _: None = Depends(require_log_read),
):
    """搜索日志"""
    log_service = get_log_service()
    results = await asyncio.to_thread(
        log_service.search_logs,
        keyword,
        days=days,
        level=level,
        max_results=max_results,
    )
    return {"items": results, "total": len(results), "keyword": keyword}


@router.websocket("/ws")
async def logs_websocket(websocket: WebSocket):
    """WebSocket 实时日志推送"""
    principal = await authenticate_log_websocket(websocket)
    if principal is None:
        return

    log_service = get_log_service()
    filename, offset = await asyncio.to_thread(log_service.create_stream_cursor)

    try:
        while True:
            updates, filename, offset = await asyncio.to_thread(
                log_service.poll_log_updates,
                filename,
                offset,
            )
            for log_entry in updates:
                await websocket.send_json(log_entry)

            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                if message == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.send_json({
                "level": "ERROR",
                "message": "日志流处理失败，请查看服务端日志",
            })
        except RuntimeError:
            pass


@router.post("/clear")
async def clear_old_logs(
    days: int = Query(default=30, ge=1, le=3650, description="保留 N 天内的日志"),
    _: None = Depends(require_log_clear),
):
    """清理旧日志"""
    log_service = get_log_service()
    cleared = await asyncio.to_thread(log_service.clear_old_logs, days=days)
    return {"cleared": cleared, "message": f"清理了 {cleared} 个旧日志文件"}
