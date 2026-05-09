"""AI工作流

定义各类AI分析的完整工作流程。
"""

from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from loguru import logger

from ..manager.ai_manager import ai_manager
from ..audit.audit_tracker import ai_audit


class AIWorkflow:
    """AI工作流基类"""

    async def execute(self, db: Session, **kwargs) -> Dict:
        """执行工作流"""
        raise NotImplementedError


class FaultAnalysisWorkflow(AIWorkflow):
    """故障分析工作流"""

    async def execute(
        self,
        fault_id: int,
        db: Session,
        auto_create_maintenance: bool = False
    ) -> Dict:
        """
        执行故障分析工作流

        Args:
            fault_id: 故障ID
            db: 数据库会话
            auto_create_maintenance: 是否自动创建维修单（如果AI建议需要维修）

        Returns:
            分析结果 + 可选的维修单信息
        """
        from app.shared.models import FaultRecord, MaintenanceRecord

        # 执行AI分析
        result = await ai_manager.analyze_fault(fault_id, db)

        if not result.get('success'):
            return result

        analysis_result = result.get('result', {})
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

        # 更新故障记录
        if fault:
            fault.ai_analysis_result = json.dumps(analysis_result)
            fault.ai_root_cause = analysis_result.get('root_cause', '')
            fault.ai_recommendation = analysis_result.get('need_repair', 'watch')
            fault.ai_confidence = analysis_result.get('confidence')

            db.commit()

        # 如果AI建议需要维修，自动创建维修单
        if auto_create_maintenance and analysis_result.get('need_repair'):
            maintenance = MaintenanceRecord(
                device_id=fault.device_id,
                title=f"AI推荐维修: {fault.title}",
                problem_description=fault.description,
                maint_type='corrective',
                status='pending',
                fault_id=fault.id,
                auto_created=True
            )
            db.add(maintenance)
            fault.auto_created_maintenance = True
            db.commit()
            db.refresh(maintenance)

            result['created_maintenance_id'] = maintenance.id
            logger.info(f"Auto created maintenance {maintenance.id} from fault {fault_id}")

        return result


class HealthAnalysisWorkflow(AIWorkflow):
    """健康评分分析工作流"""

    async def execute(
        self,
        device_id: int,
        db: Session,
        update_health_score: bool = True
    ) -> Dict:
        """
        执行健康评分分析工作流

        Args:
            device_id: 设备ID
            db: 数据库会话
            update_health_score: 是否更新设备健康评分

        Returns:
            分析结果
        """
        from app.shared.models import Device, DeviceHealthScore
        from app.services.health.calculator import HealthScoreCalculator

        # 执行AI分析
        result = await ai_manager.analyze_device_health(device_id, db)

        if not result.get('success'):
            return result

        analysis_result = result.get('result', {})
        device = db.query(Device).filter(Device.id == device_id).first()

        # 如果AI返回了健康评分，更新设备记录
        if update_health_score and device:
            ai_health_score = analysis_result.get('health_score')
            ai_risk_level = analysis_result.get('risk_level')

            if ai_health_score:
                # 保存AI分析结果到健康评分历史表
                health_record = DeviceHealthScore(
                    device_id=device_id,
                    health_score=int(ai_health_score),
                    risk_level=ai_risk_level or 'medium',
                    score_factors='{}',
                    trend='stable',
                    ai_analysis_text=json.dumps(analysis_result),
                    recommendations=json.dumps(analysis_result.get('recommendations', [])),
                    last_calculated_at=datetime.utcnow()
                )
                db.add(health_record)
                db.commit()

                logger.info(f"Updated health score for device {device_id}: {ai_health_score}")

        return result


class PredictiveMaintenanceWorkflow(AIWorkflow):
    """预测性维护工作流"""

    async def execute(
        self,
        device_id: int,
        db: Session,
        create_pm_task: bool = False
    ) -> Dict:
        """
        执行预测性维护分析

        Args:
            device_id: 设备ID
            db: 数据库会话
            create_pm_task: 是否自动创建巡检任务

        Returns:
            分析结果
        """
        from app.shared.models import Device, FaultRecord, MaintenanceRecord, PlannedMaintenanceTask
        from datetime import datetime, timedelta

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {'success': False, 'error': 'Device not found'}

        # 获取历史数据
        faults = db.query(FaultRecord).filter(
            FaultRecord.device_id == device_id
        ).order_by(FaultRecord.created_at.desc()).limit(20).all()

        repairs = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.device_id == device_id
        ).order_by(MaintenanceRecord.created_at.desc()).limit(10).all()

        # 构建统计数据
        fault_statistics = f"近一年共 {len(faults)} 次故障"
        repair_statistics = f"近一年共 {len(repairs)} 次维修"
        parts_replacement_history = "暂无部件更换记录"

        variables = {
            'device_name': device.name,
            'device_model': device.device_type,
            'uptime_days': device.uptime_days or 0,
            'health_score': device.health_score or 100,
            'fault_statistics': fault_statistics,
            'repair_statistics': repair_statistics,
            'parts_replacement_history': parts_replacement_history
        }

        result = await ai_manager.analyze(
            analysis_type='pm_recommend',
            target_type='device',
            target_id=device_id,
            variables=variables,
            db=db
        )

        if not result.get('success'):
            return result

        analysis_result = result.get('result', {})

        # 如果需要自动创建巡检任务
        if create_pm_task:
            next_maintenance_date = analysis_result.get('next_maintenance_date')
            if next_maintenance_date:
                # 创建计划性维护任务
                pm_task = PlannedMaintenanceTask(
                    device_id=device_id,
                    task_name=f"AI推荐巡检: {device.name}",
                    task_type='inspection',
                    scheduled_date=datetime.fromisoformat(next_maintenance_date),
                    status='pending',
                    ai_generated=True,
                    notes=json.dumps(analysis_result.get('recommendations', []))
                )
                db.add(pm_task)
                db.commit()

                result['created_pm_task_id'] = pm_task.id
                logger.info(f"Created PM task {pm_task.id} for device {device_id}")

        return result


# 工作流注册表
WORKFLOWS = {
    'fault_analysis': FaultAnalysisWorkflow(),
    'health_analysis': HealthAnalysisWorkflow(),
    'predictive_maintenance': PredictiveMaintenanceWorkflow()
}


def get_workflow(name: str) -> Optional[AIWorkflow]:
    """获取工作流"""
    return WORKFLOWS.get(name)


def list_workflows() -> list:
    """列出所有工作流"""
    return list(WORKFLOWS.keys())


# 需要导入的模块
import json
from datetime import datetime