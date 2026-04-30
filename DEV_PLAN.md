# Network Automation System — 开发路线

## 当前状态（4月30日 v1.4.0 已完成）
- ✅ **225 个测试通过**（核心服务层 100% 覆盖）
- ✅ Feature-first 架构重构完成（20 个业务模块）
- ✅ Docker 配置 + Fail-fast 校验 + Alembic 迁移
- ✅ 设备发现服务
- ✅ 告警通知模块（企业微信/钉钉/邮件）
- ✅ 前端优化（分页/错误处理/加载状态/暗色主题/响应式）
- ✅ 性能优化（DB 索引 + API 分页 + 限流中间件 + Redis 缓存）
- ✅ 安全加固（安全头 + Request ID + Auth 拦截器）
- ✅ **维修管理备件集成**（备件选择 + 自动出库）
- ✅ **返回件报废入库流程**（手动录入 + 报废库存页面）
- ✅ **资产管理模块**（备件库存 + 报废库存）
- ✅ **Dashboard 交互优化**（可点击卡片 + 动态故障 badge）
- ✅ **故障-维修关联**（故障转维修 + 双向关联）
- ✅ **计划性运维模块**（维护计划 + 任务自动生成 + 统计报表）
- ✅ **用户管理**（用户 CRUD + 角色分配 + 密码重置）
- ✅ **备件序列号/PO号**（扫码枪接口预留）
- ✅ **时间显示修复**（UTC 正确转本地时间）

## 项目结构（Feature-first）

```
app/
  shared/          ← 公共基础设施
    config.py, database.py, models.py, exceptions.py
    cache.py, middleware/
  features/        ← 20 个业务模块
    devices/       router.py + device_service.py
    backups/       router.py + backup_service.py + netmiko_service.py
    faults/        router.py
    maintenance/   router.py
    planned_maintenance/ router.py  ← 新增
    templates/     router.py + template_service.py
    credentials/   router.py + credential_service.py
    deploy/        router.py + deploy_service.py
    console/       router.py + console_service.py
    dashboard/     router.py + dashboard_service.py
    logs/          router.py + log_service.py
    auth/          router.py  ← 用户管理 API
    permissions/   router.py
    tool_logs/     router.py + tool_executor.py
    spare_parts/   router.py + spare_part_service.py
    spare_movements/ router.py
    discovery/     router.py + discovery_service.py
    alerts/        router.py
    compliance/    router.py + compliance_service.py
    websocket/     router.py
  services/        ← 跨领域服务
    email_service.py, notification_service.py
    wechat_work_service.py, dingtalk_service.py
    redis_cache_service.py  ← 新增 Redis 缓存
  main.py, cli.py
```

## 已完成清单

### Phase 1-9:（详见 CHANGELOG.md）

### Phase 10: 维修管理 + 资产管理（4月29日）⭐
- ✅ 维修备件集成、返回件报废入库、报废库存页面、Dashboard优化

### Phase 11: 故障-维修关联 + 计划性运维（4月30日）⭐
- ✅ **故障-维修关联**
  - `FaultRecord` 增加 `maintenance_id` 字段
  - `MaintenanceRecord` 增加 `fault_id` 字段
  - 故障详情页"转维修"按钮 + 关联维修信息显示
  - 维修列表支持故障筛选
  
- ✅ **计划性运维模块**
  - `MaintenancePlan` 模型：计划名称、类型、周期、下次执行日期
  - `MaintenanceTask` 模型：任务编号、状态、计划日期、实际日期
  - 任务自动生成（按计划周期）
  - 任务详情页（任务信息 + 执行记录 + 时间线）
  - 完成任务支持备件选择 + 返回件报废入库
  - 统计报表（时间/设备/类型筛选）
  - 超期任务动态判断

### Phase 12: 用户管理 + 备件增强（4月30日）⭐
- ✅ **用户管理**
  - 用户 CRUD API（`/api/auth/users`）
  - 用户管理页面
  - 默认角色初始化（admin/operator/viewer）
  - 管理员重置密码
  
- ✅ **备件序列号/PO号**
  - `serial_number` 字段（扫码枪接口）
  - `po_number` 字段（采购订单号）
  - 扫码查询接口：`GET /api/spare-parts/by-serial/{serial_number}`
  
- ✅ **时间显示修复**
  - 创建 `src/utils/time.js` 统一时间工具
  - UTC → 本地时间正确转换

### Phase 13: 导航优化（4月30日）
- ✅ Console 配置移至配置管理导航栏
- ✅ 计划性运维菜单加入设备管理导航

## 核心指标

| 指标 | 数值 |
|------|------|
| 测试用例 | **225 个**，100% 通过 |
| 后端路由 | **120+ 个**端点 |
| 前端页面 | **23 个** Vue 组件 |
| API 函数 | **85+** |
| DB 累引 | **14 个**高频查询列 |
| Git 提交 | **20+ commits** |

## 下一步建议

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P1 | 扫码枪集成 | 监听键盘事件，扫描序列号入库/出库 |
| P1 | 多厂商支持 | Huawei/H3C/Juniper 适配 |
| P2 | 配置版本控制 | Git 后端存储配置历史 |
| P2 | OAuth2 SSO | 对接企业 SSO |
| P3 | 可视化拓扑 | 网络拓扑自动发现 |
| P3 | UI 升级 | Goodyear 企业风格（已完成设计稿）|

## 新增文件清单（v1.4.0）

| 文件 | 说明 |
|------|------|
| `frontend/src/views/TaskDetail.vue` | 任务详情页 |
| `frontend/src/views/Users.vue` | 用户管理页面 |
| `frontend/src/views/PlannedMaintenance.vue` | 计划性运维页面 |
| `frontend/src/utils/time.js` | UTC 时间转换工具 |
| `app/features/planned_maintenance/router.py` | 计划性运维 API |
| `app/shared/db_init.py` (更新) | 默认角色初始化 |
| `migrations/add_spare_part_fields.py` | 备件序列号/PO号迁移 |

## 修改文件清单（v1.4.0）

| 文件 | 修改内容 |
|------|------|
| `app/shared/models.py` | 故障-维修关联字段、计划/任务模型、备件序列号/PO号 |
| `app/features/faults/router.py` | 转维修接口 |
| `app/features/maintenance/router.py` | 故障筛选 |
| `app/features/spare_parts/router.py` | 扫码查询接口 |
| `app/features/auth/router.py` | 角色API、密码重置 |
| `frontend/src/views/Layout.vue` | 导航调整 |
| `frontend/src/views/FaultDetail.vue` | 转维修按钮 |
| `frontend/src/views/ScrapInventory.vue` | 时间转换 |
| `frontend/src/views/Backups.vue` | 时间转换 |
| `frontend/src/router/index.js` | 计划性运维、用户管理路由 |
| `frontend/src/locales/index.js` | 翻译更新 |
| `frontend/src/api/index.js` | 新增API函数 |