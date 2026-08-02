-- 备件资产追踪功能迁移脚本
-- 执行时间：2026-05-07
-- 说明：增加 SparePartMovement 和 SparePartInstance 的设备关联字段

-- 1. SparePartMovement 增加 target_device_id 和 source_device_id
ALTER TABLE spare_part_movements ADD COLUMN target_device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL;
ALTER TABLE spare_part_movements ADD COLUMN source_device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL;

-- 2. SparePartInstance 增加 installed_device_id 和 removed_from_device_id 等字段
ALTER TABLE spare_part_instances ADD COLUMN installed_device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL;
ALTER TABLE spare_part_instances ADD COLUMN installed_at TIMESTAMP;
ALTER TABLE spare_part_instances ADD COLUMN installed_by VARCHAR(100);
ALTER TABLE spare_part_instances ADD COLUMN removed_from_device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL;
ALTER TABLE spare_part_instances ADD COLUMN removed_at TIMESTAMP;

-- 3. 删除旧的 out_to_device 字段（用 installed_device_id 替代）
ALTER TABLE spare_part_instances DROP COLUMN IF EXISTS out_to_device;

-- 4. 更新状态值：将 'out' 改为 'installed'（在设备上使用）
UPDATE spare_part_instances SET status = 'installed' WHERE status = 'out';

-- 5. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_spare_part_movements_target_device ON spare_part_movements(target_device_id);
CREATE INDEX IF NOT EXISTS idx_spare_part_movements_source_device ON spare_part_movements(source_device_id);
CREATE INDEX IF NOT EXISTS idx_spare_part_instances_installed_device ON spare_part_instances(installed_device_id);