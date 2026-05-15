"""
配置差异分析服务
用于对比当前设备配置和新配置，生成diff结果
"""
import difflib
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class DiffType(Enum):
    """差异类型"""
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    MODIFIED = "modified"


@dataclass
class DiffLine:
    """差异行"""
    type: DiffType
    content: str
    old_line_num: Optional[int] = None
    new_line_num: Optional[int] = None


@dataclass
class ConfigDiffResult:
    """配置差异结果"""
    old_config: str
    new_config: str
    lines: List[DiffLine]
    stats: Dict[str, int]


class ConfigDiffService:
    """配置差异分析服务"""

    @staticmethod
    def analyze_diff(old_config: str, new_config: str) -> ConfigDiffResult:
        """
        分析两个配置文件的差异

        Args:
            old_config: 当前配置
            new_config: 新配置

        Returns:
            ConfigDiffResult: 差异分析结果
        """
        old_lines = old_config.splitlines() if old_config else []
        new_lines = new_config.splitlines() if new_config else []

        # 使用difflib生成统一差异
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='current',
            tofile='new',
            lineterm=''
        ))

        # 解析差异
        lines = []
        old_line_num = 0
        new_line_num = 0
        stats = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

        for line in diff:
            if line.startswith('@@'):
                # 解析行号信息 @@ -l,s +l,s @@
                parts = line.split()
                old_info = parts[1][1:].split(',')
                new_info = parts[2][1:].split(',')
                old_line_num = int(old_info[0]) if old_info[0] != '0' else 0
                new_line_num = int(new_info[0]) if new_info[0] != '0' else 0
            elif line.startswith('-') and not line.startswith('---'):
                lines.append(DiffLine(
                    type=DiffType.REMOVED,
                    content=line[1:],
                    old_line_num=old_line_num if old_line_num > 0 else None
                ))
                if old_line_num > 0:
                    old_line_num += 1
                stats["removed"] += 1
            elif line.startswith('+') and not line.startswith('+++'):
                lines.append(DiffLine(
                    type=DiffType.ADDED,
                    content=line[1:],
                    new_line_num=new_line_num if new_line_num > 0 else None
                ))
                if new_line_num > 0:
                    new_line_num += 1
                stats["added"] += 1
            elif line.startswith(' '):
                lines.append(DiffLine(
                    type=DiffType.UNCHANGED,
                    content=line[1:],
                    old_line_num=old_line_num if old_line_num > 0 else None,
                    new_line_num=new_line_num if new_line_num > 0 else None
                ))
                if old_line_num > 0:
                    old_line_num += 1
                if new_line_num > 0:
                    new_line_num += 1
                stats["unchanged"] += 1

        # 如果没有差异，直接对比
        if not lines:
            lines = ConfigDiffService._simple_diff(old_lines, new_lines)
            stats = {
                "added": sum(1 for l in lines if l.type == DiffType.ADDED),
                "removed": sum(1 for l in lines if l.type == DiffType.REMOVED),
                "modified": sum(1 for l in lines if l.type == DiffType.MODIFIED),
                "unchanged": sum(1 for l in lines if l.type == DiffType.UNCHANGED)
            }

        return ConfigDiffResult(
            old_config=old_config,
            new_config=new_config,
            lines=lines,
            stats=stats
        )

    @staticmethod
    def _simple_diff(old_lines: List[str], new_lines: List[str]) -> List[DiffLine]:
        """
        简化版diff算法 - 基于LCS
        """
        # 计算LCS
        m, n = len(old_lines), len(new_lines)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if old_lines[i - 1] == new_lines[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        # 回溯构建diff
        lines = []
        i, j = m, n

        while i > 0 or j > 0:
            if i > 0 and j > 0 and old_lines[i - 1] == new_lines[j - 1]:
                lines.append(DiffLine(
                    type=DiffType.UNCHANGED,
                    content=old_lines[i - 1],
                    old_line_num=i,
                    new_line_num=j
                ))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
                lines.append(DiffLine(
                    type=DiffType.ADDED,
                    content=new_lines[j - 1],
                    new_line_num=j
                ))
                j -= 1
            elif i > 0:
                lines.append(DiffLine(
                    type=DiffType.REMOVED,
                    content=old_lines[i - 1],
                    old_line_num=i
                ))
                i -= 1

        return list(reversed(lines))

    @staticmethod
    def generate_patch(diff_result: ConfigDiffResult) -> str:
        """
        生成可应用的patch文件

        Args:
            diff_result: 差异分析结果

        Returns:
            str: patch内容
        """
        lines = ['--- current', '+++ new']

        for line in diff_result.lines:
            if line.type == DiffType.UNCHANGED:
                lines.append(f' {line.content}')
            elif line.type == DiffType.ADDED:
                lines.append(f'+{line.content}')
            elif line.type == DiffType.REMOVED:
                lines.append(f'-{line.content}')

        return '\n'.join(lines)

    @staticmethod
    def estimate_impact(diff_result: ConfigDiffResult) -> Dict:
        """
        估计变更影响

        Args:
            diff_result: 差异分析结果

        Returns:
            Dict: 影响分析结果
        """
        impact = {
            "total_changes": diff_result.stats["added"] + diff_result.stats["removed"],
            "is_breaking_change": False,
            "affected_services": [],
            "estimated_downtime_seconds": 0,
            "risk_level": "low"
        }

        # 分析关键配置变更
        critical_patterns = [
            r'interface.*shutdown',
            r'no ip.*',
            r'hostname',
            r'password',
            r'username',
            r'snmp-server',
            r'vlan.*name'
        ]

        critical_changes = 0
        for line in diff_result.lines:
            if line.type in [DiffType.ADDED, DiffType.REMOVED]:
                content_lower = line.content.lower()

                # 检测关键变更
                if any(pattern in content_lower for pattern in ['shutdown', 'no ip', 'password']):
                    critical_changes += 1

                # 检测影响的服务
                if 'vlan' in content_lower:
                    impact["affected_services"].append("VLAN")
                if 'interface' in content_lower:
                    impact["affected_services"].append("Interface")
                if 'ospf' in content_lower or 'bgp' in content_lower:
                    impact["affected_services"].append("Routing")
                    impact["estimated_downtime_seconds"] += 30
                if 'acl' in content_lower:
                    impact["affected_services"].append("ACL/Security")

        # 评估风险等级
        total_changes = impact["total_changes"]
        if critical_changes > 0 or total_changes > 50:
            impact["risk_level"] = "high"
            impact["is_breaking_change"] = True
        elif total_changes > 20:
            impact["risk_level"] = "medium"
        else:
            impact["risk_level"] = "low"

        # 去重服务列表
        impact["affected_services"] = list(set(impact["affected_services"]))

        # 估计停机时间
        if impact["affected_services"]:
            base_downtime = len(impact["affected_services"]) * 10
            impact["estimated_downtime_seconds"] = max(
                impact["estimated_downtime_seconds"],
                base_downtime
            )

        return impact
