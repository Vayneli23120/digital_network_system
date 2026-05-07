-- 给出入库历史记录增加PO号字段
-- 执行时间：2026-05-07

-- 1. SparePartMovement 增加 po_number 字段
ALTER TABLE spare_part_movements ADD COLUMN po_number VARCHAR(100);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_spare_part_movements_po ON spare_part_movements(po_number);
