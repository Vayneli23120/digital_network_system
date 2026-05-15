# 配置部署增强功能设计文档

## 概述

为企业级网络自动化系统添加配置部署实时进度跟踪、CLI命令行回显和生产环境安全控制功能。

## 核心功能

### 1. 实时任务执行进度

**前端组件**: `DeployExecutionDialog.vue`

- **进度条**: 总体进度 + 每个设备的独立进度
- **实时状态**: pending → running → completed/failed/aborted
- **统计信息**: 总设备数、已完成、执行中、失败
- **执行时间**: 计时器显示已用时间

**后端实现**: `deploy_stream.py`

- SSE (Server-Sent Events) 流推送
- 事件类型:
  - `device_start`: 设备开始执行
  - `device_progress`: 进度更新 (0-100%)
  - `device_cli`: CLI输出日志
  - `device_complete`: 设备执行成功
  - `device_failed`: 设备执行失败
  - `execution_complete`: 整体任务完成
  - `execution_aborted`: 任务被中止

### 2. CLI命令行实时回显

**终端仿真**: 
- 黑色背景终端风格
- 时间戳标记
- 语法高亮:
  - 命令: 绿色 (#4ec9b0)
  - 错误: 红色 (#f48771)
  - 警告: 黄色 (#dcdcaa)
  - 成功: 绿色 (#7ee787)
  - 普通信息: 灰色 (#d4d4d4)

**示例回显内容**:
```
[10:30:15] Connecting to 192.168.1.1...
[10:30:16] SSH connection established
[10:30:16] Username: admin
[10:30:16] Password: ********
[10:30:17] Authentication successful
[10:30:17] Device> enable
[10:30:18] Device# configure terminal
[10:30:18] Enter configuration commands, one per line. End with CNTL/Z.
[10:30:18] Device(config)# hostname CORE-SW-01
[10:30:19] Device(config)# end
[10:30:19] Device# write memory
[10:30:20] Building configuration...
[10:30:21] [OK]
[10:30:21] Configuration saved successfully
```

### 3. 生产环境安全控制

**环境检测** (前端):
```javascript
const productionPatterns = [
  /prod/i,
  /production/i,
  /core/i,
  /core-sw/i,
  /border/i,
  /wan/i,
  /^10\.0\./,
  /^192\.168\./
]
```

**并发控制策略**:
- 生产环境: `parallel_limit = 1` (串行执行)
- 新环境: `parallel_limit = 3` (可配置并行)

**用户警告**:
- 生产环境 + 多设备选择时弹出确认对话框
- 显示警告信息和设备数量

**后端实现**:
```python
if is_production or parallel_limit == 1:
    # 串行执行 - 安全
    for device_id in device_ids:
        await execute_device(task_id, device_id, ...)
else:
    # 并行执行 - 受限制
    semaphore = asyncio.Semaphore(parallel_limit)
    await asyncio.gather(*[
        execute_with_limit(did) for did in device_ids
    ])
```

### 4. 部署历史记录

**数据库模型**: `app/models/deploy.py`

- `DeployTask`: 主任务表
  - UUID主键
  - 状态、模式、环境信息
  - 执行时间统计
  - 成功/失败计数

- `DeployDeviceRecord`: 设备执行记录表
  - 关联任务
  - 设备信息快照
  - 执行状态和进度
  - CLI日志存储

**API端点**:
- `GET /api/deploy-history/tasks` - 任务列表
- `GET /api/deploy-history/tasks/{id}` - 任务详情
- `GET /api/deploy-history/tasks/{id}/devices` - 设备记录
- `GET /api/deploy-history/tasks/{id}/logs` - CLI日志

## 文件变更列表

### 前端文件
1. `src/components/DeployExecutionDialog.vue` - 新增执行对话框
2. `src/views/Deploy.vue` - 集成执行对话框和安全控制

### 后端文件
1. `app/api/deploy_stream.py` - SSE流端点和任务管理
2. `app/services/deploy_service_stream.py` - 带CLI回显的服务
3. `app/models/deploy.py` - 数据库模型
4. `app/api/deploy_history.py` - 历史记录API

## 使用流程

1. 用户选择配置源（备份/模板）
2. 选择目标设备
3. 系统自动检测生产环境
4. 确认部署（生产环境显示额外警告）
5. 打开实时执行对话框
6. SSE连接建立，开始接收事件
7. 显示设备进度和CLI回显
8. 可点击设备切换查看不同设备的CLI
9. 执行完成后显示摘要
10. 可下载完整日志

## 安全措施

1. **串行执行**: 生产环境设备逐个执行配置变更
2. **中止功能**: 用户可随时中止正在执行的任务
3. **确认对话框**: 生产环境+多设备时强制确认
4. **日志记录**: 所有CLI交互完整记录
5. **执行历史**: 持久化存储供审计

## 扩展建议

1. **配置差异预览**: 部署前对比新旧配置
2. **回滚功能**: 失败时自动回滚到上一个配置
3. **定时部署**: 支持设置执行时间窗口
4. **审批流程**: 生产环境配置变更需要审批
5. **影响分析**: 部署前分析影响范围

## API设计

### 创建部署任务
```http
POST /api/deploy/execute-stream
Content-Type: application/json

{
  "mode": "template",
  "template_id": 1,
  "target_devices": [1, 2, 3],
  "variables": {"HOSTNAME": "SW-01"},
  "is_production": true,
  "parallel_limit": 1
}

Response:
{
  "success": true,
  "task_id": "uuid-here",
  "message": "部署任务已创建"
}
```

### SSE流端点
```http
GET /api/deploy/execute/{task_id}/stream

Event: device_start
data: {"type": "device_start", "device_id": 1, "device_name": "CORE-SW-01"}

Event: device_cli
data: {"type": "device_cli", "device_id": 1, "cli_output": "configure terminal", "timestamp": "10:30:18"}

Event: device_progress
data: {"type": "device_progress", "device_id": 1, "progress": 50, "message": "应用配置中..."}

Event: device_complete
data: {"type": "device_complete", "device_id": 1, "success": true, "message": "配置部署成功"}

Event: execution_complete
data: {"type": "execution_complete", "success": true, "summary": {"total": 3, "success": 3, "failed": 0}}
```

### 中止任务
```http
POST /api/deploy/execute/{task_id}/abort

Response:
{
  "success": true,
  "message": "任务已中止"
}
```

## 技术栈

- **前端**: Vue 3 + Element Plus + SSE
- **后端**: FastAPI + SQLAlchemy + asyncio
- **实时通信**: Server-Sent Events (SSE)
- **数据库**: PostgreSQL (JSON字段存储CLI日志)
