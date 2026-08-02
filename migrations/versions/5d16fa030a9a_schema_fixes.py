"""schema fixes

Revision ID: 5d16fa030a9a
Revises: ed628a533673
Create Date: 2026-08-02 16:02:16.555971

为既有库（真实 nas / 历史 create_all 结构）补齐与模型一致的约束与默认值：
- 环形 FK（fault_records.maintenance_id ↔ maintenance_records.fault_id）及两处
  maintenance FK（maintenance_tasks.maintenance_id、device_spare_relations.maintenance_id）
  的 ondelete=SET NULL（幂等：自动探测约束名，已 SET NULL 则跳过）
- 8 个索引（CREATE INDEX IF NOT EXISTS，幂等）
- 布尔列 server_default + NULL 回填（有界安全子集，见 plan 3.3 P2）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d16fa030a9a'
down_revision: Union[str, Sequence[str], None] = 'ed628a533673'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _has_column(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return column in {c['name'] for c in inspector.get_columns(table)}


def _set_fk_null(bind, table: str, local_col: str, refer_table: str) -> None:
    """将 FK ondelete 置为 SET NULL（幂等）：自动探测约束名，已 SET NULL 则跳过。

    真实库上存在历史孤儿数据（本地行引用已不存在的父行，例如旧版本未建 FK 时
    写入的 maintenance_tasks），直接 ADD CONSTRAINT ... ON DELETE SET NULL 会因
    孤儿行违反约束而失败。故在重建约束前，先把引用不存在父行的本地行置 NULL——
    这与 ON DELETE SET NULL 的语义一致，属安全清理。
    """
    if not _has_table(bind, table):
        return
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table):
        if fk.get('constrained_columns') == [local_col] and fk.get('referred_table') == refer_table:
            name = fk.get('name')
            if name is None:
                return
            if fk.get('options', {}).get('ondelete') == 'SET NULL':
                return
            op.drop_constraint(name, table, type_='foreignkey')
            # 清理孤儿引用（引用已不存在的父行 → 置 NULL），否则 ADD CONSTRAINT 失败
            op.execute(sa.text(
                f'UPDATE {table} SET {local_col} = NULL WHERE {local_col} IS NOT NULL '
                f'AND {local_col} NOT IN (SELECT id FROM {refer_table})'
            ))
            op.create_foreign_key(name, table, refer_table, [local_col], ['id'], ondelete='SET NULL')
            return


def _unset_fk_null(bind, table: str, local_col: str, refer_table: str) -> None:
    """FK 反向：移除 SET NULL（重建为默认无 ondelete）。"""
    if not _has_table(bind, table):
        return
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table):
        if fk.get('constrained_columns') == [local_col] and fk.get('referred_table') == refer_table:
            name = fk.get('name')
            if name is None:
                return
            op.drop_constraint(name, table, type_='foreignkey')
            op.create_foreign_key(name, table, refer_table, [local_col], ['id'])
            return


def _ensure_index(bind, name: str, table: str, column: str) -> None:
    """CREATE INDEX IF NOT EXISTS（幂等）。"""
    if not _has_table(bind, table):
        return
    if not _has_column(bind, table, column):
        return
    op.execute(sa.text(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})'))


def _backfill_default(bind, table: str, column: str, default: str) -> None:
    """设置 server_default 并回填既有 NULL 行（default 为 SQL 布尔字面量，如 'false'/'true'）。"""
    if not _has_table(bind, table):
        return
    if not _has_column(bind, table, column):
        return
    op.alter_column(table, column, server_default=sa.text(default))
    op.execute(sa.text(f'UPDATE {table} SET {column} = {default} WHERE {column} IS NULL'))


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # ===== FK ondelete=SET NULL（环形对 + 两处 maintenance FK）=====
    _set_fk_null(bind, 'fault_records', 'maintenance_id', 'maintenance_records')
    _set_fk_null(bind, 'maintenance_records', 'fault_id', 'fault_records')
    _set_fk_null(bind, 'maintenance_tasks', 'maintenance_id', 'maintenance_records')
    _set_fk_null(bind, 'device_spare_relations', 'maintenance_id', 'maintenance_records')

    # ===== 索引（幂等）=====
    _ensure_index(bind, 'ix_devices_serial_number', 'devices', 'serial_number')
    _ensure_index(bind, 'ix_devices_deployment_status', 'devices', 'deployment_status')
    _ensure_index(bind, 'ix_devices_monitor_tier', 'devices', 'monitor_tier')
    _ensure_index(bind, 'ix_devices_reachability', 'devices', 'reachability')
    _ensure_index(bind, 'ix_devices_risk_level', 'devices', 'risk_level')
    _ensure_index(bind, 'ix_devices_lifecycle_stage', 'devices', 'lifecycle_stage')
    _ensure_index(bind, 'ix_audit_logs_created_at', 'audit_logs', 'created_at')
    _ensure_index(bind, 'ix_audit_logs_operator', 'audit_logs', 'operator')

    # ===== server_default + NULL 回填（有界安全子集）=====
    _backfill_default(bind, 'devices', 'snmp_enabled', 'false')
    _backfill_default(bind, 'device_interfaces', 'is_uplink', 'false')
    _backfill_default(bind, 'device_interfaces', 'monitored', 'false')
    _backfill_default(bind, 'fault_records', 'false_positive', 'false')
    _backfill_default(bind, 'fault_records', 'review_required', 'true')
    _backfill_default(bind, 'maintenance_records', 'auto_created', 'false')
    _backfill_default(bind, 'maintenance_records', 'ai_recommended', 'false')
    _backfill_default(bind, 'maintenance_records', 'verify_passed', 'false')
    _backfill_default(bind, 'notifications', 'read', 'false')


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    # ===== server_default 反向（移除默认值，保留数据）=====
    for table, column in [
        ('notifications', 'read'),
        ('maintenance_records', 'verify_passed'),
        ('maintenance_records', 'ai_recommended'),
        ('maintenance_records', 'auto_created'),
        ('fault_records', 'review_required'),
        ('fault_records', 'false_positive'),
        ('device_interfaces', 'monitored'),
        ('device_interfaces', 'is_uplink'),
        ('devices', 'snmp_enabled'),
    ]:
        if _has_column(bind, table, column):
            op.alter_column(table, column, server_default=None)

    # ===== 索引反向 =====
    for name in [
        'ix_audit_logs_operator',
        'ix_audit_logs_created_at',
        'ix_devices_lifecycle_stage',
        'ix_devices_risk_level',
        'ix_devices_reachability',
        'ix_devices_monitor_tier',
        'ix_devices_deployment_status',
        'ix_devices_serial_number',
    ]:
        op.execute(sa.text(f'DROP INDEX IF EXISTS {name}'))

    # ===== FK 反向（移除 SET NULL）=====
    _unset_fk_null(bind, 'device_spare_relations', 'maintenance_id', 'maintenance_records')
    _unset_fk_null(bind, 'maintenance_tasks', 'maintenance_id', 'maintenance_records')
    _unset_fk_null(bind, 'maintenance_records', 'fault_id', 'fault_records')
    _unset_fk_null(bind, 'fault_records', 'maintenance_id', 'maintenance_records')
