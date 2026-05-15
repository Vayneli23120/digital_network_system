# 后端运行说明

## 环境要求

- Python 3.9+
- SQLite（无需额外安装）

## 安装依赖

```bash
cd /home/vayne/network-automation-system/backend

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 运行服务

```bash
# 方式1：直接运行
python main.py

# 方式2：使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后会自动创建数据库表（SQLite）。

## API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 部署执行
- `POST /api/deploy/execute-stream` - 创建部署任务
- `GET /api/deploy/execute/{task_id}/stream` - SSE 实时流
- `POST /api/deploy/execute/{task_id}/abort` - 中止任务
- `GET /api/deploy/execute/{task_id}/status` - 任务状态

### 部署历史
- `GET /api/deploy-history/tasks` - 任务列表
- `GET /api/deploy-history/tasks/{task_id}` - 任务详情
- `DELETE /api/deploy-history/tasks/{task_id}` - 删除任务

## 注意事项

1. 当前使用内存队列存储实时事件（生产环境建议用 Redis）
2. CLI 输出为模拟数据（实际部署需集成 SSH 库如 asyncssh）
3. 认证为模拟实现（生产环境需实现 JWT 验证）
