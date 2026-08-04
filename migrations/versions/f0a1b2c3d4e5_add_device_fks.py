"""add device FKs

Revision ID: f0a1b2c3d4e5
Revises: 5e6a7b8c9d0e
Create Date: 2026-08-04

批次十：把 6 处裸 Integer 伪外键转为真 FK（引用 devices.id），防止孤儿数据。
幂等（自动探测约束名；已存在且 ondelete 匹配则跳过；ondelete 不符则重建）。
建约束前清既有孤儿：SET NULL → 置 NULL（保留父行）；CASCADE → 删除（无法置空）。

表.列：
- fault_records.peer_device_id（SET NULL）
- device_interfaces.peer_device_id（SET NULL）
- interface_traffic_samples.device_id（CASCADE）
- deploy_device_results.device_id（CASCADE，NOT NULL）
- ai_knowledge_documents.device_id（SET NULL）
- jobs.device_id（SET NULL）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = '5e6a7b8c9d0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _existing_fk(bind, table: str, local_col: str, refer_table: str):
    """返回 (table, local_col, refer_table) 对应的现存 FK 元信息，无则 None。"""
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table):
        if fk.get('constrained_columns') == [local_col] and fk.get('referred_table') == refer_table:
            return fk
    return None


def _add_fk(bind, table: str, local_col: str, refer_table: str, ondelete: str) -> None:
    """幂等建 FK：探测约束名，ondelete 一致则跳过，不一致则重建；建约束前清孤儿。"""
    if not _has_table(bind, table):
        return
    existing = _existing_fk(bind, table, local_col, refer_table)
    if existing is not None:
        name = existing.get('name')
        if existing.get('options', {}).get('ondelete') == ondelete:
            return  # 已存在且 ondelete 一致，幂等跳过
        if name is None:
            return
        op.drop_constraint(name, table, type_='foreignkey')

    # 清理孤儿引用（引用已不存在的父行），否则 ADD CONSTRAINT 会因孤儿行失败。
    # SET NULL → 置 NULL 保留本行；CASCADE → 直接删除（如 NOT NULL 列无法置空）。
    if ondelete == 'SET NULL':
        op.execute(sa.text(
            f'UPDATE {table} SET {local_col} = NULL WHERE {local_col} IS NOT NULL '
            f'AND {local_col} NOT IN (SELECT id FROM {refer_table})'
        ))
    else:  # CASCADE
        op.execute(sa.text(
            f'DELETE FROM {table} WHERE {local_col} IS NOT NULL '
            f'AND {local_col} NOT IN (SELECT id FROM {refer_table})'
        ))

    op.create_foreign_key(
        f'{table}_{local_col}_fkey', table, refer_table, [local_col], ['id'],
        ondelete=ondelete,
    )


def _drop_fk(bind, table: str, local_col: str, refer_table: str) -> None:
    """FK 反向：探测并删除对应约束。"""
    if not _has_table(bind, table):
        return
    existing = _existing_fk(bind, table, local_col, refer_table)
    if existing is None:
        return
    name = existing.get('name')
    if name is None:
        return
    op.drop_constraint(name, table, type_='foreignkey')


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    _add_fk(bind, 'fault_records', 'peer_device_id', 'devices', 'SET NULL')
    _add_fk(bind, 'device_interfaces', 'peer_device_id', 'devices', 'SET NULL')
    _add_fk(bind, 'interface_traffic_samples', 'device_id', 'devices', 'CASCADE')
    _add_fk(bind, 'deploy_device_results', 'device_id', 'devices', 'CASCADE')
    _add_fk(bind, 'ai_knowledge_documents', 'device_id', 'devices', 'SET NULL')
    _add_fk(bind, 'jobs', 'device_id', 'devices', 'SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    _drop_fk(bind, 'fault_records', 'peer_device_id', 'devices')
    _drop_fk(bind, 'device_interfaces', 'peer_device_id', 'devices')
    _drop_fk(bind, 'interface_traffic_samples', 'device_id', 'devices')
    _drop_fk(bind, 'deploy_device_results', 'device_id', 'devices')
    _drop_fk(bind, 'ai_knowledge_documents', 'device_id', 'devices')
    _drop_fk(bind, 'jobs', 'device_id', 'devices')
