"""标准文档工具 - 供 AI Agent 调用"""

from typing import Dict, List

from app.shared.database import get_db
from app.shared.models import ComplianceStandard, ComplianceRule


def get_standard_document(standard_id: int) -> Dict:
    """获取标准文档内容

    Args:
        standard_id: 标准文档ID

    Returns:
        标准文档详情
    """
    db = next(get_db())
    try:
        standard = db.query(ComplianceStandard).filter(ComplianceStandard.id == standard_id).first()
        if not standard:
            return {"error": "标准文档不存在"}
        
        return {
            "id": standard.id,
            "name": standard.name,
            "category": standard.category,
            "content": standard.content or "",
            "description": standard.description or "",
            "version": standard.version or "1.0",
            "created_at": standard.created_at.isoformat() if standard.created_at else None,
            "updated_at": standard.updated_at.isoformat() if standard.updated_at else None,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


def list_standards(category: str = None) -> List[Dict]:
    """列出可用的标准文档
    
    Args:
        category: 可选，筛选特定类别
    
    Returns:
        标准文档列表
    """
    db = next(get_db())
    try:
        query = db.query(ComplianceStandard).filter(ComplianceStandard.is_active == True)
        if category:
            query = query.filter(ComplianceStandard.category == category)
        
        standards = query.all()
        
        return [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "description": s.description or "",
                "version": s.version or "1.0",
            }
            for s in standards
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


def get_rules_from_standard(standard_id: int) -> List[Dict]:
    """获取标准文档关联的规则
    
    Args:
        standard_id: 标准文档ID
    
    Returns:
        关联的规则列表
    """
    db = next(get_db())
    try:
        rules = db.query(ComplianceRule).filter(
            ComplianceRule.standard_id == standard_id,
            ComplianceRule.is_active == True
        ).all()
        
        return [
            {
                "id": r.id,
                "rule_id": r.rule_id,
                "name": r.name,
                "category": r.category,
                "severity": r.severity,
                "pattern": r.pattern or "",
            }
            for r in rules
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()
