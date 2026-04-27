"""
日志服务 - 提供日志文件读取和实时推送功能
"""

from pathlib import Path
from typing import List, Dict, Optional, Generator
from datetime import datetime
import re
from loguru import logger


class LogService:
    """日志服务"""

    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_log_files(self, days: int = 7) -> List[Dict]:
        """获取指定天数内的日志文件列表"""
        log_files = []
        now = datetime.now()

        for log_file in self.log_dir.glob("*.log"):
            stat = log_file.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)
            age_days = (now - mtime).days

            if age_days <= days:
                log_files.append({
                    "filename": log_file.name,
                    "path": str(log_file),
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
        log_path = self.log_dir / filename

        if not log_path.exists():
            return []

        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()

            # 取最后 N 行
            target_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

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

        except Exception as e:
            logger.error(f"读取日志文件失败：{e}")
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
        log_files = self.get_log_files(days)

        for log_file in log_files:
            if len(results) >= max_results:
                break
            try:
                with open(log_file["path"], 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword.lower() in line.lower():
                            parsed = self._parse_log_line(line.strip())
                            if parsed:
                                if level and parsed.get("level", "").upper() != level.upper():
                                    continue
                                parsed["source_file"] = log_file["filename"]
                                parsed["line_number"] = line_num
                                results.append(parsed)
                                if len(results) >= max_results:
                                    break
            except Exception as e:
                logger.error(f"搜索日志失败：{log_file['filename']}, error: {e}")

        # 按时间排序，最新的在前
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results

    def stream_logs(self, follow: bool = True) -> Generator[Dict, None, None]:
        """实时推送最新日志（类似 tail -f）"""
        import time

        # 获取最新的日志文件
        log_files = self.get_log_files(days=1)
        if not log_files:
            yield {"level": "SYSTEM", "message": "未找到日志文件"}
            return

        # 监控最新的日志文件
        current_log = log_files[0]["path"]

        try:
            with open(current_log, 'r', encoding='utf-8', errors='ignore') as f:
                # 先读取现有内容到最后
                f.seek(0, 2)  # 移动到文件末尾

                while follow:
                    line = f.readline()
                    if line:
                        parsed = self._parse_log_line(line.strip())
                        if parsed:
                            yield parsed
                    else:
                        time.sleep(0.5)  # 等待新内容

        except Exception as e:
            logger.error(f"日志推送失败：{e}")
            yield {"level": "ERROR", "message": f"日志推送失败：{e}"}

    def get_latest_logs(self, count: int = 100, level: Optional[str] = None) -> List[Dict]:
        """获取所有日志文件的最新 N 条记录"""
        all_logs = []
        log_files = self.get_log_files(days=7)

        for log_file in log_files[:3]:  # 只读取最近 3 个文件
            logs = self.read_log_file(log_file["filename"], lines=count // 3, level=level)
            all_logs.extend(logs)

        # 按时间排序
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_logs[:count]

    def clear_old_logs(self, days: int = 30) -> int:
        """清理旧日志文件"""
        cleared = 0
        log_files = self.get_log_files(days=days + 1)

        for log_file in log_files:
            if log_file["age_days"] > days:
                try:
                    Path(log_file["path"]).unlink()
                    cleared += 1
                    logger.info(f"清理旧日志文件：{log_file['filename']}")
                except Exception as e:
                    logger.error(f"清理日志文件失败：{e}")

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
