"""AI 审计记录

保留自建的审计机制，适配 ADK 输出格式。
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from app.shared.database import get_db
from app.shared.models import AIAnalysisRecord, AIConfig


class AIAuditTracker:
    """AI 使用审计追踪"""

    def record(
        self,
        analysis_type: str,
        target_type: str,
        target_id: int,
        result: str,
        processing_time_ms: int = 0,
        tool_calls: List[Dict] = None,
        db = None,
    ):
        """记录一次 AI 分析"""
        if not db:
            return

        try:
            ai_config = db.query(AIConfig).filter(AIConfig.is_active == True).first()

            log = AIAnalysisRecord(
                analysis_type=analysis_type,
                target_type=target_type,
                target_id=target_id,
                input_data=json.dumps({"tool_calls": tool_calls or []}),
                ai_provider=ai_config.provider if ai_config else None,
                model_name=ai_config.model_name if ai_config else None,
                output_result=result[:5000] if result else "",
                processing_time_ms=processing_time_ms,
                status="completed",
                created_at=datetime.utcnow(),
            )
            db.add(log)
            db.commit()
            logger.info(f"AI审计记录: type={analysis_type}, time={processing_time_ms}ms")
        except Exception as e:
            logger.error(f"审计记录失败: {e}")
            if db:
                db.rollback()

    def get_summary(self, hours: int = 24, db=None) -> Dict:
        """获取统计摘要"""
        if not db:
            return {}

        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        records = db.query(AIAnalysisRecord).filter(
            AIAnalysisRecord.created_at >= cutoff
        ).all()

        total = len(records)
        success = len([r for r in records if r.status == 'completed'])
        total_tokens = sum(r.tokens_used or 0 for r in records)
        total_cost = sum(float(r.cost) if r.cost else 0 for r in records)

        return {
            "period_hours": hours,
            "total_calls": total,
            "success_rate": round(success / total * 100 if total > 0 else 0, 1),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
        }


# 单例
ai_audit = AIAuditTracker()