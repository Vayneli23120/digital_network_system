"""统一设备操作执行器。

把 netmiko / napalm / serial / subprocess 等同步阻塞的设备操作统一放到
进程级线程池中执行，避免阻塞 asyncio 事件循环；支持超时保护。
"""

import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

_DEVICE_EXECUTOR: Optional[ThreadPoolExecutor] = None


def get_device_executor(max_workers: int = 8) -> ThreadPoolExecutor:
    """进程级统一设备操作线程池（懒加载单例）。"""
    global _DEVICE_EXECUTOR
    if _DEVICE_EXECUTOR is None:
        _DEVICE_EXECUTOR = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="device-op",
        )
    return _DEVICE_EXECUTOR


async def run_device_op(
    fn: Callable[..., Any],
    *args: Any,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> Any:
    """在线程池中执行同步设备操作，可选超时。

    示例:
        output = await run_device_op(conn.send_command, cmd, timeout=30)
    """
    loop = asyncio.get_event_loop()
    fut = loop.run_in_executor(get_device_executor(), lambda: fn(*args, **kwargs))
    if timeout is not None:
        return await asyncio.wait_for(fut, timeout=timeout)
    return await fut


@asynccontextmanager
async def get_device_executor_pool(max_workers: int = 8):
    """受控临时线程池，用于并发设备操作组（如多设备部署/回滚）。"""
    executor = ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="device-op",
    )
    try:
        yield executor
    finally:
        executor.shutdown(wait=False)
