"""
日志服务 - 提供日志文件读取和实时推送功能
"""

from collections import deque
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re
from loguru import logger

from .security import UnsafeLogPathError, resolve_log_file


class LogService:
    """日志服务"""

    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _log_paths(self, days: Optional[int] = None) -> List[Path]:
        """Return safe regular .log files, newest first."""
        now = datetime.now()
        paths = []
        for entry in self.log_dir.glob("*.log"):
            try:
                log_path = resolve_log_file(entry.name, self.log_dir)
                age_days = (now - datetime.fromtimestamp(log_path.stat().st_mtime)).days
                if days is None or age_days <= days:
                    paths.append(log_path)
            except (UnsafeLogPathError, FileNotFoundError, OSError):
                logger.warning(f"忽略不安全或不可读的日志条目: {entry.name}")
        paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return paths

    def get_log_files(self, days: int = 7) -> List[Dict]:
        """获取指定天数内的日志文件列表"""
        log_files = []
        now = datetime.now()

        for log_file in self._log_paths(days):
            stat = log_file.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)
            age_days = (now - mtime).days

            log_files.append({
                "filename": log_file.name,
                "size": stat.st_size,
                "modified": mtime.isoformat(),
                "age_days": age_days
            })

        # 按修改时间排序，最新的在前
        log_files.sort(key=lambda x: x["modified"], reverse=True)
        return log_files

    def read_log_file(self, filename: str, lines: int = 100, level: Optional[str] = None) -> List[Dict]:
        """读取日志文件内容

        Args:
            filename: 日志文件名
            lines: 读取行数（默认最后 100 行）
            level: 日志级别过滤（DEBUG/INFO/WARNING/ERROR）
        """
        try:
            log_path = resolve_log_file(filename, self.log_dir)
        except FileNotFoundError:
            return []

        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                target_lines = list(deque(f, maxlen=max(1, lines)))

            # 解析日志行
            result = []
            for line in target_lines:
                parsed = self._parse_log_line(line.strip())
                if parsed:
                    # 级别过滤
                    if level and parsed.get("level", "").upper() != level.upper():
                        continue
                    result.append(parsed)

            return result

        except OSError:
            logger.error("读取日志文件失败")
            return []

    def _parse_log_line(self, line: str) -> Optional[Dict]:
        """解析单行日志

        支持 Loguru 格式：
        2026-03-30 11:20:28.517 | INFO    | app.main:startup_event:103 - Network Automation System v1.0.0 启动
        """
        if not line:
            return None

        # Loguru 默认格式正则
        pattern = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s*\|\s*(\w+)\s*\|\s*([^:]+):([^:]+):(\d+)\s*-\s*(.*)$'
        match = re.match(pattern, line)

        if match:
            return {
                "timestamp": match.group(1),
                "level": match.group(2).strip(),
                "module": match.group(3).strip(),
                "function": match.group(4).strip(),
                "line": int(match.group(5)),
                "message": match.group(6)
            }

        # 无法解析的行返回原始内容
        return {
            "timestamp": "",
            "level": "RAW",
            "message": line
        }

    def search_logs(self, keyword: str, days: int = 7, level: Optional[str] = None, max_results: int = 500) -> List[Dict]:
        """搜索日志（限制结果数量，避免内存爆炸）"""
        results = []
        log_files = self._log_paths(days)

        for log_file in log_files:
            if len(results) >= max_results:
                break
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword.lower() in line.lower():
                            parsed = self._parse_log_line(line.strip())
                            if parsed:
                                if level and parsed.get("level", "").upper() != level.upper():
                                    continue
                                parsed["source_file"] = log_file.name
                                parsed["line_number"] = line_num
                                results.append(parsed)
                                if len(results) >= max_results:
                                    break
            except OSError:
                logger.error(f"搜索日志失败：{log_file.name}")

        # 按时间排序，最新的在前
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results

    def create_stream_cursor(self) -> tuple[Optional[str], int]:
        """Start following at the end of the newest log file."""
        log_files = self._log_paths(days=1)
        if not log_files:
            return None, 0
        latest = log_files[0]
        return latest.name, latest.stat().st_size

    def poll_log_updates(
        self,
        filename: Optional[str],
        offset: int,
        max_lines: int = 200,
    ) -> tuple[List[Dict], Optional[str], int]:
        """Read newly appended lines without waiting or sleeping."""
        log_files = self._log_paths(days=1)
        if not log_files:
            return [], None, 0

        latest = log_files[0]
        if filename != latest.name:
            filename = latest.name
            offset = 0

        log_path = resolve_log_file(filename, self.log_dir)
        if log_path.stat().st_size < offset:
            offset = 0

        updates = []
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as log_file:
            log_file.seek(offset)
            for _ in range(max_lines):
                line = log_file.readline()
                if not line:
                    break
                parsed = self._parse_log_line(line.strip())
                if parsed:
                    updates.append(parsed)
            new_offset = log_file.tell()
        return updates, filename, new_offset

    def get_latest_logs(
        self,
        count: int = 100,
        level: Optional[str] = None,
        days: int = 7,
    ) -> List[Dict]:
        """获取所有日志文件的最新 N 条记录"""
        all_logs = []
        log_files = self.get_log_files(days=days)

        for log_file in log_files[:3]:  # 只读取最近 3 个文件
            logs = self.read_log_file(
                log_file["filename"],
                lines=max(1, count // 3),
                level=level,
            )
            all_logs.extend(logs)

        # 按时间排序
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_logs[:count]

    def clear_old_logs(self, days: int = 30) -> int:
        """清理旧日志文件"""
        cleared = 0
        now = datetime.now()
        for log_path in self._log_paths(days=None):
            age_days = (now - datetime.fromtimestamp(log_path.stat().st_mtime)).days
            if age_days > days:
                try:
                    log_path.unlink()
                    cleared += 1
                    logger.info(f"清理旧日志文件：{log_path.name}")
                except OSError:
                    logger.error(f"清理日志文件失败：{log_path.name}")

        return cleared


# 全局服务实例
_log_service: Optional[LogService] = None


def get_log_service() -> LogService:
    """获取日志服务实例"""
    global _log_service
    if _log_service is None:
        from app.shared.config import get_config
        config = get_config()
        _log_service = LogService(log_dir=config.storage.log_dir)
    return _log_service
