-- 给出入库记录增加批次关联字段
-- 执行时间：2026-05-07

-- SparePartMovement 增加 session_code 字段（关联扫码会话）
ALTER TABLE spare_part_movements ADD COLUMN session_code VARCHAR(20);

-- 创建索引便于查询同批次记录
CREATE INDEX IF NOT EXISTS idx_spare_part_movements_session ON spare_part_movements(session_code);
