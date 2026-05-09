"""设备健康评分计算器

评分因素权重：
- 故障频率：30%
- 维修频率：20%
- 设备年龄/生命周期：15%
- 日志异常：15%
- AI分析：20%

健康评分范围：0-100
风险等级：low(>=80) / medium(60-79) / high(40-59) / critical(<40)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import json

from sqlalchemy.orm import Session
from app.shared.models import (
    Device, FaultRecord, MaintenanceRecord, DeviceHealthScore,
    LogEntry, AIAnalysisRecord
)


class HealthScoreCalculator:
    """设备健康评分计算器"""

    # 评分权重配置
    WEIGHTS = {
        'fault_frequency': 0.30,    # 故障频率权重
        'repair_frequency': 0.20,   # 维修频率权重
        'device_age': 0.15,         # 设备年龄权重
        'log_anomalies': 0.15,      # 日志异常权重
        'ai_analysis': 0.20         # AI分析权重
    }

    # 风险等级阈值
    RISK_THRESHOLDS = {
        'low': 80,       # >=80 为低风险
        'medium': 60,    # 60-79 为中风险
        'high': 40,      # 40-59 为高风险
        'critical': 0    # <40 为严重风险
    }

    def __init__(self, db: Session):
        self.db = db

    def calculate(self, device: Device, include_ai: bool = False) -> Tuple[int, Dict, str]:
        """
        计算设备健康评分

        Args:
            device: 设备对象
            include_ai: 是否包含AI分析结果

        Returns:
            (health_score, score_factors, risk_level)
        """
        score_factors = {}

        # 1. 计算故障频率分数 (0-100)
        fault_score = self._calculate_fault_score(device)
        score_factors['fault_frequency'] = {
            'score': fault_score,
            'weight': self.WEIGHTS['fault_frequency'],
            'contribution': fault_score * self.WEIGHTS['fault_frequency'],
            'details': self._get_fault_details(device)
        }

        # 2. 计算维修频率分数 (0-100)
        repair_score = self._calculate_repair_score(device)
        score_factors['repair_frequency'] = {
            'score': repair_score,
            'weight': self.WEIGHTS['repair_frequency'],
            'contribution': repair_score * self.WEIGHTS['repair_frequency'],
            'details': self._get_repair_details(device)
        }

        # 3. 计算设备年龄分数 (0-100)
        age_score = self._calculate_age_score(device)
        score_factors['device_age'] = {
            'score': age_score,
            'weight': self.WEIGHTS['device_age'],
            'contribution': age_score * self.WEIGHTS['device_age'],
            'details': self._get_age_details(device)
        }

        # 4. 计算日志异常分数 (0-100)
        log_score = self._calculate_log_score(device)
        score_factors['log_anomalies'] = {
            'score': log_score,
            'weight': self.WEIGHTS['log_anomalies'],
            'contribution': log_score * self.WEIGHTS['log_anomalies'],
            'details': self._get_log_details(device)
        }

        # 5. 计算AI分析分数 (0-100)
        ai_score = 100  # 默认满分，无AI分析时不扣分
        if include_ai:
            ai_score = self._calculate_ai_score(device)
        score_factors['ai_analysis'] = {
            'score': ai_score,
            'weight': self.WEIGHTS['ai_analysis'],
            'contribution': ai_score * self.WEIGHTS['ai_analysis'],
            'details': self._get_ai_details(device)
        }

        # 计算总分数
        total_score = sum(
            factor['contribution'] for factor in score_factors.values()
        )

        # 四舍五入到整数
        health_score = int(round(total_score))

        # 确定风险等级
        risk_level = self._determine_risk_level(health_score)

        return health_score, score_factors, risk_level

    def _calculate_fault_score(self, device: Device) -> int:
        """
        计算故障频率分数
        规则：近30天故障次数影响评分
        - 0次故障：100分
        - 1次故障：90分
        - 2次故障：80分
        - 3次故障：70分
        - 4次故障：60分
        - >=5次故障：50分
        severity影响：critical扣10分，major扣5分
        """
        # 查询近30天故障
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        faults = self.db.query(FaultRecord).filter(
            FaultRecord.device_id == device.id,
            FaultRecord.created_at >= thirty_days_ago
        ).all()

        fault_count = len(faults)

        # 基础分数
        base_scores = {
            0: 100, 1: 90, 2: 80, 3: 70, 4: 60
        }
        base_score = base_scores.get(fault_count, 50)

        # 根据严重程度扣分
        severity_penalty = 0
        for fault in faults:
            if fault.severity == 'critical':
                severity_penalty += 10
            elif fault.severity == 'major':
                severity_penalty += 5

        # 确保分数不低于0
        final_score = max(0, base_score - severity_penalty)

        return final_score

    def _get_fault_details(self, device: Device) -> Dict:
        """获取故障详情"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        faults = self.db.query(FaultRecord).filter(
            FaultRecord.device_id == device.id,
            FaultRecord.created_at >= thirty_days_ago
        ).all()

        return {
            'count_30days': len(faults),
            'critical_count': len([f for f in faults if f.severity == 'critical']),
            'major_count': len([f for f in faults if f.severity == 'major']),
            'minor_count': len([f for f in faults if f.severity == 'minor']),
            'warning_count': len([f for f in faults if f.severity == 'warning'])
        }

    def _calculate_repair_score(self, device: Device) -> int:
        """
        计算维修频率分数
        规则：近90天维修次数影响评分
        - 0次维修：100分
        - 1次维修：90分
        - 2次维修：80分
        - 3次维修：70分
        - >=4次维修：60分
        """
        # 查询近90天维修
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        repairs = self.db.query(MaintenanceRecord).filter(
            MaintenanceRecord.device_id == device.id,
            MaintenanceRecord.created_at >= ninety_days_ago
        ).all()

        repair_count = len(repairs)

        # 基础分数
        base_scores = {
            0: 100, 1: 90, 2: 80, 3: 70
        }
        base_score = base_scores.get(repair_count, 60)

        return base_score

    def _get_repair_details(self, device: Device) -> Dict:
        """获取维修详情"""
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        repairs = self.db.query(MaintenanceRecord).filter(
            MaintenanceRecord.device_id == device.id,
            MaintenanceRecord.created_at >= ninety_days_ago
        ).all()

        from decimal import Decimal

        return {
            'count_90days': len(repairs),
            'corrective_count': len([r for r in repairs if r.maint_type == 'corrective']),
            'emergency_count': len([r for r in repairs if r.maint_type == 'emergency']),
            'total_parts_cost': float(sum(r.parts_cost or Decimal('0') for r in repairs)),
            'total_labor_cost': float(sum(r.labor_cost or Decimal('0') for r in repairs))
        }

    def _calculate_age_score(self, device: Device) -> int:
        """
        计算设备年龄分数
        规则：根据设备运行时间/购买日期计算
        - <1年：100分
        - 1-3年：90分
        - 3-5年：80分
        - 5-7年：70分
        - >=7年：60分
        设备状态影响：offline扣20分，maintenance扣10分
        """
        # 计算设备年龄
        if device.purchase_date:
            age_days = (datetime.utcnow() - device.purchase_date).days
        else:
            age_days = device.uptime_days or 0

        age_years = age_days / 365

        # 基础分数
        if age_years < 1:
            base_score = 100
        elif age_years < 3:
            base_score = 90
        elif age_years < 5:
            base_score = 80
        elif age_years < 7:
            base_score = 70
        else:
            base_score = 60

        # 根据状态扣分
        status_penalty = 0
        if device.status == 'offline':
            status_penalty = 20
        elif device.status == 'maintenance':
            status_penalty = 10

        final_score = max(0, base_score - status_penalty)

        return final_score

    def _get_age_details(self, device: Device) -> Dict:
        """获取设备年龄详情"""
        if device.purchase_date:
            age_days = (datetime.utcnow() - device.purchase_date).days
        else:
            age_days = device.uptime_days or 0

        return {
            'age_days': age_days,
            'age_years': round(age_days / 365, 1),
            'purchase_date': device.purchase_date.isoformat() if device.purchase_date else None,
            'warranty_expire': device.warranty_expire.isoformat() if device.warranty_expire else None,
            'lifecycle_stage': device.lifecycle_stage,
            'status': device.status
        }

    def _calculate_log_score(self, device: Device) -> int:
        """
        计算日志异常分数
        规则：根据工具执行日志中的失败次数计算
        - 无失败：100分
        - 1次失败：95分
        - 2-3次失败：85分
        - 4-5次失败：75分
        - >=6次失败：60分
        """
        # 查询近7天的工具执行日志（针对该设备）
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        logs = self.db.query(LogEntry).filter(
            LogEntry.target == device.name,
            LogEntry.timestamp >= seven_days_ago
        ).all()

        failed_count = len([l for l in logs if l.status == 'failed'])

        # 基础分数
        if failed_count == 0:
            base_score = 100
        elif failed_count == 1:
            base_score = 95
        elif failed_count <= 3:
            base_score = 85
        elif failed_count <= 5:
            base_score = 75
        else:
            base_score = 60

        return base_score

    def _get_log_details(self, device: Device) -> Dict:
        """获取日志详情"""
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        logs = self.db.query(LogEntry).filter(
            LogEntry.target == device.name,
            LogEntry.timestamp >= seven_days_ago
        ).all()

        return {
            'total_count': len(logs),
            'failed_count': len([l for l in logs if l.status == 'failed']),
            'success_count': len([l for l in logs if l.status == 'success']),
            'running_count': len([l for l in logs if l.status == 'running'])
        }

    def _calculate_ai_score(self, device: Device) -> int:
        """
        计算AI分析分数
        规则：根据最近的AI分析结果计算
        - 有最近的AI健康分析：使用AI评分
        - 无AI分析：默认100分
        """
        # 查询最近的AI健康分析
        ai_record = self.db.query(AIAnalysisRecord).filter(
            AIAnalysisRecord.target_type == 'device',
            AIAnalysisRecord.target_id == device.id,
            AIAnalysisRecord.analysis_type == 'health',
            AIAnalysisRecord.status == 'completed'
        ).order_by(AIAnalysisRecord.created_at.desc()).first()

        if ai_record:
            output = ai_record.get_output_dict()
            ai_score = output.get('health_score', 100)
            return int(ai_score)

        return 100

    def _get_ai_details(self, device: Device) -> Dict:
        """获取AI分析详情"""
        ai_record = self.db.query(AIAnalysisRecord).filter(
            AIAnalysisRecord.target_type == 'device',
            AIAnalysisRecord.target_id == device.id,
            AIAnalysisRecord.analysis_type == 'health',
            AIAnalysisRecord.status == 'completed'
        ).order_by(AIAnalysisRecord.created_at.desc()).first()

        if ai_record:
            return {
                'last_analyzed': ai_record.created_at.isoformat(),
                'ai_provider': ai_record.ai_provider,
                'confidence': float(ai_record.confidence_score) if ai_record.confidence_score else None,
                'has_analysis': True
            }

        return {
            'last_analyzed': None,
            'has_analysis': False
        }

    def _determine_risk_level(self, health_score: int) -> str:
        """确定风险等级"""
        if health_score >= self.RISK_THRESHOLDS['low']:
            return 'low'
        elif health_score >= self.RISK_THRESHOLDS['medium']:
            return 'medium'
        elif health_score >= self.RISK_THRESHOLDS['high']:
            return 'high'
        else:
            return 'critical'

    def calculate_trend(self, device: Device) -> str:
        """
        计算健康趋势
        比较最近两次健康评分记录
        """
        # 获取最近两次健康评分记录
        records = self.db.query(DeviceHealthScore).filter(
            DeviceHealthScore.device_id == device.id
        ).order_by(DeviceHealthScore.last_calculated_at.desc()).limit(2).all()

        if len(records) < 2:
            return 'stable'

        current_score = records[0].health_score
        previous_score = records[1].health_score

        diff = current_score - previous_score

        if diff > 5:
            return 'improving'
        elif diff < -5:
            return 'declining'
        else:
            return 'stable'

    def save_health_record(
        self,
        device: Device,
        health_score: int,
        score_factors: Dict,
        risk_level: str,
        trend: str = 'stable',
        ai_analysis_text: Optional[str] = None,
        recommendations: Optional[List[str]] = None
    ) -> DeviceHealthScore:
        """
        保存健康评分记录
        """
        record = DeviceHealthScore(
            device_id=device.id,
            health_score=health_score,
            score_factors=json.dumps(score_factors),
            risk_level=risk_level,
            trend=trend,
            ai_analysis_text=ai_analysis_text,
            recommendations=json.dumps(recommendations or []),
            last_calculated_at=datetime.utcnow()
        )

        self.db.add(record)

        # 同时更新设备表的健康评分字段
        device.health_score = health_score
        device.risk_level = risk_level
        device.last_health_check = datetime.utcnow()

        self.db.commit()
        self.db.refresh(record)

        return record

    def generate_recommendations(
        self,
        health_score: int,
        risk_level: str,
        score_factors: Dict
    ) -> List[str]:
        """
        根据评分因素生成建议
        """
        recommendations = []

        # 故障相关建议
        fault_details = score_factors.get('fault_frequency', {}).get('details', {})
        if fault_details.get('critical_count', 0) > 0:
            recommendations.append('设备近期有严重故障，建议尽快检查')
        if fault_details.get('count_30days', 0) >= 3:
            recommendations.append('故障频率较高，建议安排预防性巡检')

        # 维修相关建议
        repair_details = score_factors.get('repair_frequency', {}).get('details', {})
        if repair_details.get('corrective_count', 0) >= 2:
            recommendations.append('近期多次故障维修，考虑更换老化部件')
        if repair_details.get('emergency_count', 0) > 0:
            recommendations.append('有紧急维修记录，建议加强监控')

        # 年龄相关建议
        age_details = score_factors.get('device_age', {}).get('details', {})
        if age_details.get('age_years', 0) >= 5:
            recommendations.append('设备运行超过5年，建议评估更换计划')
        if age_details.get('warranty_expire'):
            recommendations.append('关注保修到期时间，提前规划维护')

        # 状态相关建议
        if age_details.get('status') == 'offline':
            recommendations.append('设备当前离线，请检查网络连接或设备状态')

        # 通用建议
        if risk_level == 'high':
            recommendations.append('设备健康风险较高，建议优先处理')
        elif risk_level == 'critical':
            recommendations.append('设备健康状态严重，建议立即处理或更换')

        return recommendations


def calculate_device_health(db: Session, device_id: int, include_ai: bool = False) -> Dict:
    """
    计算单个设备健康评分的便捷函数

    Args:
        db: 数据库会话
        device_id: 设备ID
        include_ai: 是否包含AI分析

    Returns:
        健康评分结果字典
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return None

    calculator = HealthScoreCalculator(db)
    health_score, score_factors, risk_level = calculator.calculate(device, include_ai)
    trend = calculator.calculate_trend(device)
    recommendations = calculator.generate_recommendations(health_score, risk_level, score_factors)

    # 保存记录
    record = calculator.save_health_record(
        device,
        health_score,
        score_factors,
        risk_level,
        trend,
        recommendations=recommendations
    )

    return {
        'device_id': device.id,
        'device_name': device.name,
        'health_score': health_score,
        'risk_level': risk_level,
        'trend': trend,
        'score_factors': score_factors,
        'recommendations': recommendations,
        'last_calculated_at': record.last_calculated_at.isoformat()
    }


def calculate_all_devices_health(db: Session, include_ai: bool = False) -> List[Dict]:
    """
    计算所有设备健康评分
    """
    devices = db.query(Device).filter(Device.status != 'retired').all()

    results = []
    for device in devices:
        result = calculate_device_health(db, device.id, include_ai)
        if result:
            results.append(result)

    return results