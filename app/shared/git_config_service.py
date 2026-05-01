"""
配置版本控制服务

使用 Git 存储设备配置历史，提供版本回溯、差异对比等功能。
每个备份文件变更都会自动 commit，支持按时间范围查看历史。
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

try:
    import git
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False


class GitConfigService:
    """配置版本控制服务"""

    def __init__(self, backup_dir: str = "./backups", git_repo_path: Optional[str] = None):
        self.backup_dir = Path(backup_dir).resolve()
        self.repo_path = Path(git_repo_path) if git_repo_path else self.backup_dir
        self._repo = None

        if not GITPYTHON_AVAILABLE:
            logger.warning("GitPython 未安装，配置版本控制不可用")
            return

        self._init_or_open_repo()

    @property
    def available(self) -> bool:
        return self._repo is not None and GITPYTHON_AVAILABLE

    def _init_or_open_repo(self):
        """初始化或打开 Git 仓库"""
        try:
            if GITPYTHON_AVAILABLE:
                if (self.repo_path / ".git").exists():
                    self._repo = git.Repo(self.repo_path)
                    logger.info(f"已打开配置仓库 {self.repo_path}")
                else:
                    self._repo = git.Repo.init(self.repo_path)
                    # 创建 .gitignore
                    gitignore = self.repo_path / ".gitignore"
                    if not gitignore.exists():
                        gitignore.write_text("# Auto-generated\n*.lock\n")
                    self._repo.index.add([".gitignore"])
                    self._repo.index.commit("Initial commit: config backup repository")
                    logger.info(f"已创建配置仓库 {self.repo_path}")
        except Exception as e:
            logger.warning(f"Git 仓库初始化失败: {e}")
            self._repo = None

    def commit_backup(self, device_name: str, backup_file: str,
                      has_change: bool = False, operator: Optional[str] = None) -> Optional[str]:
        """提交备份文件到 Git

        Args:
            device_name: 设备名称
            backup_file: 备份文件路径
            has_change: 是否发生变更
            operator: 操作人

        Returns:
            commit hash 或 None
        """
        if not self.available:
            return None

        try:
            full_path = Path(backup_file)
            if not full_path.exists():
                logger.warning(f"备份文件不存在: {backup_file}")
                return None

            # 将文件添加到 Git 索引
            rel_path = full_path.relative_to(self.repo_path)
            self._repo.index.add([str(rel_path)])

            # 构建 commit message
            change_flag = " (配置变更)" if has_change else ""
            op = f" by {operator}" if operator else ""
            message = f"backup: {device_name}{change_flag}{op}"

            commit = self._repo.index.commit(message)
            logger.info(f"Git commit: {commit.hexsha[:8]} - {message}")
            return commit.hexsha
        except Exception as e:
            logger.error(f"Git commit 失败: {e}")
            return None

    def get_history(self, device_name: Optional[str] = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """获取配置变更历史

        Args:
            device_name: 按设备名称过滤
            limit: 返回条目数量

        Returns:
            历史记录列表
        """
        if not self.available:
            return []

        try:
            commits = list(self._repo.iter_commits(max_count=limit))
            history = []

            for commit in commits:
                # 过滤设备
                if device_name and device_name not in commit.message:
                    continue

                history.append({
                    "commit_hash": commit.hexsha[:8],
                    "full_hash": commit.hexsha,
                    "message": commit.message,
                    "author": str(commit.author),
                    "timestamp": datetime.fromtimestamp(commit.committed_date).isoformat(),
                })

            return history
        except Exception as e:
            logger.error(f"获取 Git 历史失败: {e}")
            return []

    def get_diff(self, commit_hash: str) -> Dict[str, Any]:
        """获取指定 commit 的差异

        Args:
            commit_hash: commit hash (完整或前 8 位)

        Returns:
            差异信息
        """
        if not self.available:
            return {"diff": ""}

        try:
            commit = self._repo.commit(commit_hash)
            # 与上一个 commit 的差异
            if commit.parents:
                parent = commit.parents[0]
                diff = parent.diff(commit, create_patch=True)
            else:
                # 第一个 commit，与空树比较
                diff = commit.diff(git.NULL_TREE, create_patch=True)

            diff_text = ""
            for d in diff:
                if d.diff:
                    diff_text += d.diff.decode("utf-8", errors="replace") + "\n"

            return {
                "commit_hash": commit.hexsha[:8],
                "message": commit.message,
                "author": str(commit.author),
                "timestamp": datetime.fromtimestamp(commit.committed_date).isoformat(),
                "diff": diff_text,
            }
        except Exception as e:
            logger.error(f"获取 Git diff 失败: {e}")
            return {"commit_hash": commit_hash, "diff": "", "error": str(e)}

    def rollback(self, commit_hash: str) -> bool:
        """回滚到指定 commit

        Args:
            commit_hash: commit hash

        Returns:
            是否成功
        """
        if not self.available:
            return False

        try:
            self._repo.git.reset(commit_hash, hard=True)
            logger.info(f"回滚到 commit: {commit_hash[:8]}")
            return True
        except Exception as e:
            logger.error(f"Git rollback 失败: {e}")
            return False

    def get_file_at_commit(self, file_path: str, commit_hash: str) -> Optional[str]:
        """获取指定 commit 中的文件内容

        Args:
            file_path: 文件路径（相对于 repo）
            commit_hash: commit hash

        Returns:
            文件内容或 None
        """
        if not self.available:
            return None

        try:
            commit = self._repo.commit(commit_hash)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode("utf-8")
        except Exception as e:
            logger.error(f"获取文件内容失败: {e}")
            return None


# 全局服务实例
_git_config_service: Optional[GitConfigService] = None


def get_git_config_service() -> GitConfigService:
    """获取配置版本控制服务实例"""
    global _git_config_service
    if _git_config_service is None:
        from app.shared.config import get_config
        config = get_config()
        _git_config_service = GitConfigService(
            backup_dir=config.storage.backup_dir,
        )
    return _git_config_service
