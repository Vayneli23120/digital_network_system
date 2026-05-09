"""AI使用审计

追踪AI调用次数、成本、成功率等统计信息。
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json


@dataclass
class AuditRecord:
    """审计记录"""
    timestamp: datetime
    provider: str
    model: str
    analysis_type: str
    success: bool
    tokens_used: int
    cost: float
    processing_time_ms: int
    error: Optional[str] = None


class AIAudit:
    """AI使用审计追踪"""

    def __init__(self, max_records: int = 1000):
        """
        Args:
            max_records: 最大保存记录数
        """
        self.records: List[AuditRecord] = []
        self.max_records = max_records

    def record(
        self,
        provider: str,
        model: str,
        analysis_type: str,
        success: bool,
        tokens_used: int = 0,
        cost: float = 0.0,
        processing_time_ms: int = 0,
        error: Optional[str] = None
    ):
        """记录一次AI调用"""
        record = AuditRecord(
            timestamp=datetime.utcnow(),
            provider=provider,
            model=model,
            analysis_type=analysis_type,
            success=success,
            tokens_used=tokens_used,
            cost=cost,
            processing_time_ms=processing_time_ms,
            error=error
        )

        self.records.append(record)

        # 保持最大记录数限制
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]

    def get_summary(self, hours: int = 24) -> Dict:
        """获取统计摘要"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_records = [r for r in self.records if r.timestamp >= cutoff]

        if not recent_records:
            return {
                'period_hours': hours,
                'total_calls': 0,
                'success_rate': 0,
                'total_tokens': 0,
                'total_cost': 0,
                'avg_processing_time_ms': 0
            }

        success_count = len([r for r in recent_records if r.success])
        total_tokens = sum(r.tokens_used for r in recent_records)
        total_cost = sum(r.cost for r in recent_records)
        total_time = sum(r.processing_time_ms for r in recent_records)

        # 按分析类型统计
        by_type = {}
        for r in recent_records:
            if r.analysis_type not in by_type:
                by_type[r.analysis_type] = {'count': 0, 'success': 0}
            by_type[r.analysis_type]['count'] += 1
            if r.success:
                by_type[r.analysis_type]['success'] += 1

        # 按Provider统计
        by_provider = {}
        for r in recent_records:
            if r.provider not in by_provider:
                by_provider[r.provider] = {'calls': 0, 'cost': 0}
            by_provider[r.provider]['calls'] += 1
            by_provider[r.provider]['cost'] += r.cost

        return {
            'period_hours': hours,
            'total_calls': len(recent_records),
            'success_count': success_count,
            'success_rate': round(success_count / len(recent_records) * 100, 1),
            'total_tokens': total_tokens,
            'total_cost': round(total_cost, 4),
            'avg_processing_time_ms': round(total_time / len(recent_records), 1),
            'by_analysis_type': by_type,
            'by_provider': by_provider
        }

    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """获取最近的错误记录"""
        errors = [r for r in self.records if not r.success][-limit:]
        return [
            {
                'timestamp': r.timestamp.isoformat(),
                'provider': r.provider,
                'analysis_type': r.analysis_type,
                'error': r.error
            }
            for r in errors
        ]

    def clear(self):
        """清空记录"""
        self.records.clear()


# 单例实例
ai_audit = AIAudit()