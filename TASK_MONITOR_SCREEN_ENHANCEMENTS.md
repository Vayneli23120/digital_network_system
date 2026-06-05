# 编程任务：监控大屏功能完善

## 任务概述

本任务涉及 **5 个文件** 的修改，实现以下 4 个功能：

1. **WebSocket 实时设备状态推送**（设备离线时大屏立即感知，无需等待轮询）
2. **地图节点故障严重度小圆点**（critical/high/medium/low 颜色区分）
3. **节点拖拽重新定位**（在平面图上拖动设备图标到新位置，自动保存）
4. **设备详情弹窗显示真实 Ping 延迟**（从数据库读取已检测值）

---

## 修改 1：`app/features/websocket/router.py`

### 改动说明
- 模块 docstring 更新
- 新增 `Optional` 类型导入
- 新增 `set_main_loop()` 和 `broadcast_device_status_sync()` 两个函数（跨线程 WebSocket 推送桥接）
- 新增 `/ws/device-status` WebSocket 端点

### 替换 1-A：更新文件头部注释和导入

**替换前：**
```python
"""
WebSocket 端点 - 实时日志推送

前端通过 WebSocket 连接订阅工具执行日志。
支持按 tool_type / operation 过滤。
"""
import asyncio
import json
import uuid
from typing import Dict, Set
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger
```

**替换后：**
```python
"""
WebSocket 端点 - 实时日志推送 & 设备状态推送

前端通过 WebSocket 连接订阅工具执行日志或设备实时状态变化。
支持按 tool_type / operation 过滤日志；设备状态通道独立分离。
"""
import asyncio
import json
import uuid
from typing import Dict, Optional, Set
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger
```

### 替换 1-B：在 `manager = ConnectionManager()` 之后、`@router.websocket("/ws/logs")` 之前插入桥接代码

**替换前：**
```python
manager = ConnectionManager()


@router.websocket("/ws/logs")
```

**替换后：**
```python
manager = ConnectionManager()

# ============ 跨线程 WebSocket 推送桥接 ============
# APScheduler 在后台线程运行，需要通过主事件循环来调用 async broadcast

_main_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """在 FastAPI startup 时注册主事件循环，供后台线程调用 WebSocket 推送。"""
    global _main_event_loop
    _main_event_loop = loop


def broadcast_device_status_sync(message: dict) -> None:
    """从后台线程（APScheduler）线程安全地推送设备状态变化到 WebSocket 客户端。"""
    global _main_event_loop
    if _main_event_loop and not _main_event_loop.is_closed():
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(message, "device-status"),
            _main_event_loop,
        )


@router.websocket("/ws/logs")
```

### 替换 1-C：在文件末尾 `/ws/logs` 端点的 `except WebSocketDisconnect` 块之后追加新端点

**替换前（文件末尾）：**
```python
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
```

**替换后：**
```python
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


@router.websocket("/ws/device-status")
async def websocket_device_status(websocket: WebSocket):
    """
    WebSocket 端点 - 订阅设备实时可达性状态变化

    消息格式（服务端推送）：
    {
        "event": "device_status_change",
        "device_id": 123,
        "device_name": "SW-Core-01",
        "ip": "192.168.1.1",
        "location": "车间A",
        "device_type": "switch",
        "old_state": "reachable",
        "new_state": "unreachable",
        "latency_ms": null,
        "timestamp": "2026-06-05T10:30:00"
    }
    """
    await manager.connect(websocket, "device-status")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "device-status")
```

---

## 修改 2：`app/services/reachability_monitor.py`

### 改动说明
在 `_trigger_state_change_alert` 方法中，`except Exception as e: logger.error(...)` 块之后追加 WebSocket 推送代码。

### 定位方式
搜索字符串：`logger.error(f"Failed to send reachability alert: {e}")`，在其后追加代码。

**替换前：**
```python
        except Exception as e:
            logger.error(f"Failed to send reachability alert: {e}")

    def _estimate_downtime(self, device: Device) -> Optional[int]:
```

**替换后：**
```python
        except Exception as e:
            logger.error(f"Failed to send reachability alert: {e}")

        # 推送实时状态变化到 WebSocket 前端（监控大屏立即感知）
        try:
            from app.features.websocket.router import broadcast_device_status_sync
            broadcast_device_status_sync({
                "event": "device_status_change",
                "device_id": device.id,
                "device_name": device.name,
                "ip": device.ip or "",
                "location": device.location or "",
                "device_type": device.device_type or "switch",
                "old_state": old_state,
                "new_state": new_state,
                "latency_ms": device.reachability_latency_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to push device status to WebSocket: {e}")

    def _estimate_downtime(self, device: Device) -> Optional[int]:
```

---

## 修改 3：`app/features/monitor_screen/monitor_service.py`

### 改动说明
3 处替换：
- 新增 `case` 导入（SQLAlchemy）
- `get_floor_plan_nodes` 函数：返回字段增加 `reachability`、`latency_ms`、`active_fault_severity`，并查询最严重活跃故障
- `get_device_detail` 函数：`ping_latency` 改为读取数据库中已有值

### 替换 3-A：新增 `case` 导入

**替换前：**
```python
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.shared.models import Device, FloorPlan, DeviceNode, BackupRecord, FaultRecord
```

**替换后：**
```python
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case

from app.shared.models import Device, FloorPlan, DeviceNode, BackupRecord, FaultRecord
```

### 替换 3-B：`get_floor_plan_nodes` 函数中 `result.append({...})` 整块替换

**替换前：**
```python
            result.append({
                "id": node.id,
                "device_id": device.id,
                "device_name": device.name,
                "device_type": device.device_type or "switch",
                "ip": device.ip,
                "model": device.model,
                "status": device.status,
                "location": device.location,
                "x_percent": float(node.x_percent),
                "y_percent": float(node.y_percent),
                "uptime_hours": round(uptime_hours, 1),
                "lifespan_days": lifespan_days,
                "created_at": node.created_at.isoformat() if node.created_at else None,
            })
```

**替换后：**
```python
            # 最严重的活跃故障（critical > high > medium > low）
            active_fault = db.query(FaultRecord).filter(
                FaultRecord.device_id == device.id,
                FaultRecord.status.in_(['open', 'in_progress']),
            ).order_by(
                case(
                    (FaultRecord.severity == 'critical', 0),
                    (FaultRecord.severity == 'high', 1),
                    (FaultRecord.severity == 'medium', 2),
                    else_=3,
                )
            ).first()

            result.append({
                "id": node.id,
                "device_id": device.id,
                "device_name": device.name,
                "device_type": device.device_type or "switch",
                "ip": device.ip,
                "model": device.model,
                "status": device.status,
                "reachability": device.reachability,
                "latency_ms": device.reachability_latency_ms,
                "location": device.location,
                "x_percent": float(node.x_percent),
                "y_percent": float(node.y_percent),
                "uptime_hours": round(uptime_hours, 1),
                "lifespan_days": lifespan_days,
                "active_fault_severity": active_fault.severity if active_fault else None,
                "created_at": node.created_at.isoformat() if node.created_at else None,
            })
```

### 替换 3-C：`get_device_detail` 中 `ping_latency` 字段

**替换前：**
```python
        "ping_latency": None,  # Ping延迟需要实时检测，暂时返回null
```

**替换后：**
```python
        "ping_latency": f"{device.reachability_latency_ms}ms" if device.reachability_latency_ms else None,
```

---

## 修改 4：`app/main.py`

### 改动说明
在 `startup_event` 函数中，`init_default_roles()` 之后、启动可达性监控之前，注册主事件循环。

**替换前：**
```python
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    db_manager = get_db_manager()
    db_manager.init_db()
    logger.info(f"Network Automation System v{config.app.version} 启动")
    logger.info(f"数据库路径：{config.database.sqlite_path}")
    logger.info(f"备份目录：{config.storage.backup_dir}")
    init_default_templates()
    init_default_roles()

    # 启动设备可达性监控服务
```

**替换后：**
```python
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    import asyncio
    db_manager = get_db_manager()
    db_manager.init_db()
    logger.info(f"Network Automation System v{config.app.version} 启动")
    logger.info(f"数据库路径：{config.database.sqlite_path}")
    logger.info(f"备份目录：{config.storage.backup_dir}")
    init_default_templates()
    init_default_roles()

    # 注册主事件循环，供 APScheduler 后台线程推送 WebSocket 状态变化
    from .features.websocket.router import set_main_loop
    set_main_loop(asyncio.get_event_loop())

    # 启动设备可达性监控服务
```

---

## 修改 5：`frontend/src/views/MonitorScreen.vue`

### 5 处修改，全部在 `<script setup>` 块内或 `<template>` / `<style>` 中。

---

### 替换 5-A：节点模板 — 将 `@click.stop` 改为 `@mousedown.stop`，新增 dragging class 和故障指示点

**替换前：**
```html
              v-for="node in filteredNodes"
                :key="node.id"
                :class="['device-node', node.status, node.device_type, { flashing: node.status === 'offline', highlighted: highlightedNodeId === node.id }]"
                :style="{ left: node.x_percent + '%', top: node.y_percent + '%' }"
                @click.stop="showNodeDetail(node)"
```

**替换后：**
```html
              v-for="node in filteredNodes"
                :key="node.id"
                :class="['device-node', node.status, node.device_type, { flashing: node.status === 'offline', highlighted: highlightedNodeId === node.id, dragging: dragState && dragState.nodeId === node.id }]"
                :style="{ left: node.x_percent + '%', top: node.y_percent + '%' }"
                @mousedown.stop="onNodeMouseDown($event, node)"
```

---

### 替换 5-B：在 default-icon 的 `</div>` 和 `<span class="node-label">` 之间插入故障指示点

**替换前：**
```html
              <div class="node-icon default-icon" v-if="node.device_type !== 'switch' && node.device_type !== 'ap'">
                <svg viewBox="0 0 24 24" width="16" height="16">
                  <circle cx="12" cy="12" r="8" fill="currentColor"/>
                </svg>
              </div>
              <span class="node-label">{{ node.device_name }}</span>
```

**替换后：**
```html
              <div class="node-icon default-icon" v-if="node.device_type !== 'switch' && node.device_type !== 'ap'">
                <svg viewBox="0 0 24 24" width="16" height="16">
                  <circle cx="12" cy="12" r="8" fill="currentColor"/>
                </svg>
              </div>
              <!-- Fault severity indicator dot -->
              <div
                v-if="node.active_fault_severity"
                :class="['fault-indicator', `fault-${node.active_fault_severity}`]"
                :title="`活跃故障: ${node.active_fault_severity}`"
              ></div>
              <span class="node-label">{{ node.device_name }}</span>
```

---

### 替换 5-C：在 `<script setup>` 中，`// Filter State` 注释之前插入 WebSocket 和 dragState 变量及逻辑

**替换前：**
```js
// Filter State
```

**替换后：**
```js
// Drag state (drag-to-reposition existing nodes)
const dragState = ref(null)

// WebSocket for real-time device status
let deviceStatusWs = null
let wsPingTimer = null

const connectDeviceStatusWs = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/device-status`
  try {
    deviceStatusWs = new WebSocket(wsUrl)

    deviceStatusWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.event === 'device_status_change') {
          handleDeviceStatusChange(msg)
        }
      } catch {}
    }

    deviceStatusWs.onclose = () => {
      if (wsPingTimer) clearInterval(wsPingTimer)
      // Reconnect after 5s
      setTimeout(connectDeviceStatusWs, 5000)
    }

    deviceStatusWs.onopen = () => {
      // Keep-alive ping every 30s
      wsPingTimer = setInterval(() => {
        if (deviceStatusWs && deviceStatusWs.readyState === WebSocket.OPEN) {
          deviceStatusWs.send('ping')
        }
      }, 30000)
    }
  } catch (e) {
    console.error('WebSocket connect failed:', e)
    setTimeout(connectDeviceStatusWs, 5000)
  }
}

const handleDeviceStatusChange = (msg) => {
  const { device_id, new_state, device_name, ip, location, device_type } = msg
  const newStatus = new_state === 'unreachable' ? 'offline' : 'online'

  // Update node status on map immediately
  const node = nodes.value.find(n => n.device_id === device_id)
  if (node) {
    node.status = newStatus
  }

  // Update stats counters
  if (new_state === 'unreachable') {
    stats.value.online = Math.max(0, (stats.value.online || 0) - 1)
    stats.value.offline = (stats.value.offline || 0) + 1
    // Add to offline alerts panel
    if (!offlineAlerts.value.find(a => a.device_id === device_id)) {
      offlineAlerts.value.unshift({
        device_id,
        device_name,
        ip,
        location,
        device_type,
        offline_hours: 0,
        offline_str: '刚刚',
        last_online: new Date().toISOString(),
      })
    }
  } else if (new_state === 'reachable') {
    stats.value.offline = Math.max(0, (stats.value.offline || 0) - 1)
    stats.value.online = (stats.value.online || 0) + 1
    // Remove from offline alerts panel
    offlineAlerts.value = offlineAlerts.value.filter(a => a.device_id !== device_id)
  }
}

// Filter State
```

---

### 替换 5-D：在 `onMounted` 之前（紧接 `// Lifecycle` 注释后）插入拖拽处理函数，同时更新 `onMounted` 和 `onUnmounted`

**替换前：**
```js
// Lifecycle
let refreshInterval = null
let timeTimerId = null
```

**替换后：**
```js
// Node drag-to-reposition
const onNodeMouseDown = (e, node) => {
  if (e.button !== 0) return
  dragState.value = {
    nodeId: node.id,
    deviceId: node.device_id,
    startClientX: e.clientX,
    startClientY: e.clientY,
    startXPercent: node.x_percent,
    startYPercent: node.y_percent,
    moved: false,
  }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

const onDragMove = (e) => {
  if (!dragState.value) return
  const dx = e.clientX - dragState.value.startClientX
  const dy = e.clientY - dragState.value.startClientY
  if (!dragState.value.moved && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) {
    dragState.value.moved = true
  }
  if (dragState.value.moved && planWrapper.value) {
    const rect = planWrapper.value.getBoundingClientRect()
    const x = Math.max(0, Math.min(100, (e.clientX - rect.left) / rect.width * 100))
    const y = Math.max(0, Math.min(100, (e.clientY - rect.top) / rect.height * 100))
    const node = nodes.value.find(n => n.id === dragState.value.nodeId)
    if (node) {
      node.x_percent = Math.round(x * 100) / 100
      node.y_percent = Math.round(y * 100) / 100
    }
  }
}

const onDragEnd = async (e) => {
  if (!dragState.value) return
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
  const state = { ...dragState.value }
  dragState.value = null

  if (!state.moved) {
    // Short press without movement → open detail dialog
    const node = nodes.value.find(n => n.id === state.nodeId)
    if (node) showNodeDetail(node)
    return
  }

  // Save new position to backend
  const node = nodes.value.find(n => n.id === state.nodeId)
  if (!node || !selectedPlanId.value) return
  try {
    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/nodes/${state.nodeId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x_percent: node.x_percent, y_percent: node.y_percent }),
    })
    if (!res.ok) {
      node.x_percent = state.startXPercent
      node.y_percent = state.startYPercent
      ElMessage.error('保存节点位置失败')
    }
  } catch {
    node.x_percent = state.startXPercent
    node.y_percent = state.startYPercent
    ElMessage.error('保存节点位置失败')
  }
}

// Lifecycle
let refreshInterval = null
let timeTimerId = null
```

---

### 替换 5-E：更新 `onMounted` 和 `onUnmounted`

**替换前：**
```js
onMounted(() => {
  refreshData()

  // Update time every second
  timeTimerId = setInterval(() => {
    currentTime.value = dayjs().format('HH:mm:ss')
  }, 1000)

  // Refresh data every 30 seconds
  refreshInterval = setInterval(() => {
    loadStats()
    loadOfflineAlerts()
    if (selectedPlanId.value) {
      loadPlanNodes(selectedPlanId.value)
    }
  }, 30000)
})

onUnmounted(() => {
  if (timeTimerId) {
    clearInterval(timeTimerId)
  }
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
```

**替换后：**
```js
onMounted(() => {
  refreshData()
  connectDeviceStatusWs()

  // Update time every second
  timeTimerId = setInterval(() => {
    currentTime.value = dayjs().format('HH:mm:ss')
  }, 1000)

  // Refresh data every 30 seconds (fallback when WebSocket is unavailable)
  refreshInterval = setInterval(() => {
    loadStats()
    loadOfflineAlerts()
    if (selectedPlanId.value) {
      loadPlanNodes(selectedPlanId.value)
    }
  }, 30000)
})

onUnmounted(() => {
  if (timeTimerId) {
    clearInterval(timeTimerId)
  }
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (wsPingTimer) {
    clearInterval(wsPingTimer)
  }
  if (deviceStatusWs) {
    deviceStatusWs.onclose = null // prevent reconnect on intentional close
    deviceStatusWs.close()
  }
  // Cleanup drag handlers if any
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
})
```

---

### 替换 5-F：CSS — 在 `.device-node.highlighted` 样式块之后追加 dragging 样式

**替换前：**
```css
.device-node.highlighted {
  transform: translate(-50%, -50%) scale(1.3);
  z-index: 10;
}
```

**替换后：**
```css
.device-node.highlighted {
  transform: translate(-50%, -50%) scale(1.3);
  z-index: 10;
}

.device-node.dragging {
  transform: translate(-50%, -50%) scale(1.2);
  z-index: 20;
  cursor: grabbing;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
  transition: none; /* disable transition while dragging for responsiveness */
}
```

---

### 替换 5-G：CSS — 在 `.node-label` 样式块之后追加故障指示点样式

**替换前：**
```css
.node-label {
  position: absolute;
  bottom: -18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: var(--text-secondary);
  background: var(--bg-card);
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}

.temp-node-marker {
```

**替换后：**
```css
.node-label {
  position: absolute;
  bottom: -18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: var(--text-secondary);
  background: var(--bg-card);
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}

/* Fault severity indicator dot */
.fault-indicator {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--bg-secondary);
  z-index: 10;
  pointer-events: none;
}

.fault-critical {
  background: #ff4757;
  animation: fault-pulse 1s infinite;
}

.fault-high {
  background: #ff6b35;
}

.fault-medium {
  background: #ffd32a;
}

.fault-low {
  background: #7efff5;
}

@keyframes fault-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0.5); }
  50% { box-shadow: 0 0 0 5px rgba(255, 71, 87, 0); }
}

.temp-node-marker {
```

---

## 验收标准

完成后确认以下内容：

1. **后端**：`python -m py_compile app/features/websocket/router.py app/services/reachability_monitor.py app/features/monitor_screen/monitor_service.py app/main.py` 无报错
2. **WebSocket 端点**：访问 `/docs`，能看到 `GET /ws/device-status` 端点（或用 wscat 连接）
3. **节点 API**：调用 `GET /api/floor-plans/{id}/nodes`，返回的每个节点包含 `reachability`、`latency_ms`、`active_fault_severity` 字段
4. **大屏行为**：
   - 短按设备图标 → 打开详情弹窗（无变化）
   - 拖动设备图标 → 图标跟随鼠标移动 → 松手后位置保存
   - 有活跃故障工单的设备右上角出现彩色小圆点
