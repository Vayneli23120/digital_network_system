"""add_health_ai_tables

Revision ID: c1d2e3f4g5h6
Revises: b7a8c9d0e1f2
Create Date: 2026-05-09 10:00:00.000000

企业级智能运维平台 Phase 1 数据模型扩展：
- Device 表新增健康评分、生命周期字段
- 新增 DeviceHealthScore 健康评分历史表
- 新增 AIAnalysisRecord AI分析记录表
- 新增 WorkflowRule 工作流规则表
- 新增 DeviceSpareRelation 设备-备件关系表

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, Sequence[str], None] = None  # 独立迁移，不依赖版本链
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema"""
    # ===== Device 表扩展字段 =====
    with op.batch_alter_table('devices', schema=None) as batch_op:
        # 健康评分字段
        try:
            batch_op.add_column(sa.Column('health_score', sa.Integer(), nullable=True, server_default='100'))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('risk_level', sa.String(20), nullable=True, server_default='low'))
            batch_op.create_index('ix_devices_risk_level', ['risk_level'], unique=False)
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('last_health_check', sa.DateTime(), nullable=True))
        except Exception:
            pass

        # 生命周期字段
        try:
            batch_op.add_column(sa.Column('uptime_days', sa.Integer(), nullable=True, server_default='0'))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('warranty_expire', sa.DateTime(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('lifecycle_stage', sa.String(20), nullable=True, server_default='new'))
            batch_op.create_index('ix_devices_lifecycle_stage', ['lifecycle_stage'], unique=False)
        except Exception:
            pass

        # AI分析字段
        try:
            batch_op.add_column(sa.Column('ai_last_analyzed', sa.DateTime(), nullable=True))
        except Exception:
            pass

    # ===== DeviceHealthScore 健康评分历史表 =====
    op.create_table(
        'device_health_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('health_score', sa.Integer(), nullable=False),
        sa.Column('score_factors', sa.Text(), nullable=True),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('trend', sa.String(20), nullable=True, server_default='stable'),
        sa.Column('ai_analysis_text', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('last_calculated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_device_health_scores_device_id', 'device_health_scores', ['device_id'], unique=False)
    op.create_index('ix_device_health_scores_risk_level', 'device_health_scores', ['risk_level'], unique=False)

    # ===== AIAnalysisRecord AI分析记录表 =====
    op.create_table(
        'ai_analysis_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('input_data', sa.Text(), nullable=True),
        sa.Column('ai_provider', sa.String(50), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=True),
        sa.Column('output_result', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.NUMERIC(3, 2), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost', sa.NUMERIC(10, 4), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='completed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_analysis_records_analysis_type', 'ai_analysis_records', ['analysis_type'], unique=False)
    op.create_index('ix_ai_analysis_records_target_type', 'ai_analysis_records', ['target_type'], unique=False)
    op.create_index('ix_ai_analysis_records_target_id', 'ai_analysis_records', ['target_id'], unique=False)
    op.create_index('ix_ai_analysis_records_created_at', 'ai_analysis_records', ['created_at'], unique=False)

    # ===== WorkflowRule 工作流规则表 =====
    op.create_table(
        'workflow_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('trigger_conditions', sa.Text(), nullable=True),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('action_config', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('execution_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_rules_trigger_type', 'workflow_rules', ['trigger_type'], unique=False)
    op.create_index('ix_workflow_rules_is_active', 'workflow_rules', ['is_active'], unique=False)

    # ===== DeviceSpareRelation 设备-备件关系表 =====
    op.create_table(
        'device_spare_relations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('spare_instance_id', sa.Integer(), nullable=True),
        sa.Column('part_number', sa.String(100), nullable=True),
        sa.Column('part_name', sa.String(200), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('position', sa.String(100), nullable=True),
        sa.Column('installed_at', sa.DateTime(), nullable=False),
        sa.Column('installed_by', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='active'),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.Column('removed_by', sa.String(100), nullable=True),
        sa.Column('removal_reason', sa.String(200), nullable=True),
        sa.Column('maintenance_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['spare_instance_id'], ['spare_part_instances.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance_records.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_device_spare_relations_device_id', 'device_spare_relations', ['device_id'], unique=False)
    op.create_index('ix_device_spare_relations_spare_instance_id', 'device_spare_relations', ['spare_instance_id'], unique=False)
    op.create_index('ix_device_spare_relations_status', 'device_spare_relations', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema"""
    # 删除新表
    op.drop_table('device_spare_relations')
    op.drop_table('workflow_rules')
    op.drop_table('ai_analysis_records')
    op.drop_table('device_health_scores')

    # 删除 Device 表新增字段
    with op.batch_alter_table('devices', schema=None) as batch_op:
        try:
            batch_op.drop_column('ai_last_analyzed')
        except Exception:
            pass
        try:
            batch_op.drop_index('ix_devices_lifecycle_stage')
            batch_op.drop_column('lifecycle_stage')
        except Exception:
            pass
        try:
            batch_op.drop_column('warranty_expire')
        except Exception:
            pass
        try:
            batch_op.drop_column('uptime_days')
        except Exception:
            pass
        try:
            batch_op.drop_column('last_health_check')
        except Exception:
            pass
        try:
            batch_op.drop_index('ix_devices_risk_level')
            batch_op.drop_column('risk_level')
        except Exception:
            pass
        try:
            batch_op.drop_column('health_score')
        except Exception:
            pass