"""配置合规工具 - 供 AI Agent 调用"""

import re
from typing import Dict, List

from app.shared.database import get_db
from app.shared.models import ComplianceRule, Device


def check_config_rule(config_text: str, rule_pattern: str) -> Dict:
    """按规则检查配置是否符合
    
    Args:
        config_text: 设备配置文本
        rule_pattern: 检查规则模式（正则表达式或关键词）
    
    Returns:
        检查结果
    """
    try:
        # 尝试作为正则表达式匹配
        pattern = re.compile(rule_pattern, re.IGNORECASE | re.MULTILINE)
        matches = pattern.findall(config_text)
        
        if matches:
            return {
                "passed": True,
                "matches": matches[:10],  # 限制返回数量
                "count": len(matches),
            }
        else:
            return {
                "passed": False,
                "matches": [],
                "count": 0,
                "reason": f"配置中未找到匹配 '{rule_pattern}' 的内容",
            }
    except re.error:
        # 正则表达式无效，尝试关键词搜索
        if rule_pattern.lower() in config_text.lower():
            return {
                "passed": True,
                "matches": [rule_pattern],
                "count": 1,
            }
        else:
            return {
                "passed": False,
                "matches": [],
                "count": 0,
                "reason": f"配置中未包含关键词 '{rule_pattern}'",
            }


def get_compliance_rules(category: str = None) -> List[Dict]:
    """获取当前激活的合规规则列表
    
    Args:
        category: 可选，筛选特定类别的规则
    
    Returns:
        规则列表
    """
    db = next(get_db())
    try:
        query = db.query(ComplianceRule).filter(ComplianceRule.is_active == True)
        if category:
            query = query.filter(ComplianceRule.category == category)
        
        rules = query.all()
        
        return [
            {
                "id": r.id,
                "rule_id": r.rule_id,
                "name": r.name,
                "category": r.category,
                "severity": r.severity,
                "pattern": r.pattern or "",
                "check_logic": r.check_logic or "",
                "recommendation": r.recommendation or "",
            }
            for r in rules
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


def get_device_config(device_id: int) -> Dict:
    """获取设备当前配置
    
    Args:
        device_id: 设备ID
    
    Returns:
        设备配置信息
    """
    db = next(get_db())
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": "设备不存在"}
        
        # 返回设备的基本配置信息
        # 实际配置可能需要通过 Netmiko/NAPALM 获取
        return {
            "device_name": device.name,
            "device_type": device.device_type,
            "vendor": device.vendor,
            "config_available": False,
            "message": "需要通过配置备份功能获取实际配置",
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()
