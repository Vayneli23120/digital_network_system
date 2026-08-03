// Monitor3D 场景构建（item 946 切片 9b）
// 从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
// 父侧单实例：读 sceneState + deps；不依赖 interaction（交互反依赖本模块）。
import * as THREE from 'three'
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'

export function useSceneBuilders(sceneState, deps) {
  // 别名：与父侧一致的对象引用共享（sceneState 不可 reactive/ref 包裹）
  const ctx = sceneState.ctx
  const plan = sceneState.plan
  const { percentToWorld, getDeviceBaseSize, STATUS_COLOR, STATUS_EMISSIVE } = sceneState
  const { nodes, devices, links, filteredDevices, devicePaths, devicePorts, topoNodes, topoEdges, isEditMode, selectedTopoEdgeId, showLabels, showDataLinks, trafficHeatItems, trafficHeatByDevice, commandSummary, deviceMappings } = deps
  const { deviceStatus, isDeviceOffline } = deviceMappings

// 计算拓扑节点的渲染坐标：port 节点需叠加「随缩放」的锚点偏移，
// 与端口锚点球、后端数据链路寻路使用同一公式，避免分支光缆/数据链路在设备端分叉
function getTopoNodeRenderPos(node) {
  if (node && node.node_kind === 'port' && node.port_id) {
    const port = devicePorts.value.find(p => p.id === node.port_id)
    const devNode = nodes.value.find(n => n.device_id === (node.device_id || (port && port.device_id)))
    if (port && devNode) {
      const scale = Number(devNode.scale) || 1
      const iconSize = 3.0 * scale
      return {
        x: parseFloat(devNode.x_percent) + (port.anchor_x - 0.5) * iconSize,
        y: parseFloat(devNode.y_percent) + (port.anchor_y - 0.5) * iconSize,
      }
    }
  }
  return { x: parseFloat(node.x_percent), y: parseFloat(node.y_percent) }
}

// 构建 TopoEdge 渲染
function buildTopoEdges() {
  const { scene } = ctx.value
  if (!scene || topoEdges.value.length === 0) return

  // 清除旧渲染
  disposeGroup('topo-edges')

  const edgeGroup = new THREE.Group()
  edgeGroup.name = 'topo-edges'

  const edgeHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
  const edgeRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
  const wpRadius = edgeRadius * 2.5  // 拐点球半径

  topoEdges.value.forEach(edge => {
    // 找两端节点坐标
    const aNode = topoNodes.value.find(n => n.id === edge.a_node_id)
    const bNode = topoNodes.value.find(n => n.id === edge.b_node_id)
    if (!aNode || !bNode) return

    // port 端点叠加随缩放的锚点偏移，使分支光缆终点与锚点球/数据链路一致
    const aPos = getTopoNodeRenderPos(aNode)
    const bPos = getTopoNodeRenderPos(bNode)
    const startX = aPos.x
    const startY = aPos.y
    const endX = bPos.x
    const endY = bPos.y

    // 解析拐点
    let waypoints = []
    try {
      if (typeof edge.waypoints === 'string') {
        waypoints = JSON.parse(edge.waypoints) || []
      } else if (Array.isArray(edge.waypoints)) {
        waypoints = edge.waypoints
      }
    } catch (e) {
      waypoints = []
    }

    // 构建所有点
    const points = [
      { x: startX, y: startY },
      ...waypoints,
      { x: endX, y: endY }
    ]

    // 颜色根据 cable_type
    let color = 0x22c55e  // 默认绿色（分支光缆）
    if (edge.cable_type === 'trunk') color = 0x3b82f6  // 主干蓝色
    if (edge.cable_type === 'trunk_to_core') color = 0xf59e0b  // 核心-主干橙色
    if (edge.cable_type === 'trunk_segment') color = 0x8b5cf6  // 主干段紫色
    if (edge.status === 'down') color = 0xff4d4f  // 断开红色

    // 选中的线：保留类型颜色，但加粗 + 不透明，便于识别
    const isSelectedEdge = isEditMode.value && selectedTopoEdgeId.value === edge.id
    const thisEdgeRadius = isSelectedEdge ? edgeRadius * 1.8 : edgeRadius

    const mat = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: isSelectedEdge ? 1.0 : 0.8,
    })

    // 绘制每段
    for (let i = 0; i < points.length - 1; i++) {
      const pt1 = points[i]
      const pt2 = points[i + 1]

      const start = percentToWorld(pt1.x, pt1.y, edgeHeight)
      const end = percentToWorld(pt2.x, pt2.y, edgeHeight)

      const direction = new THREE.Vector3().subVectors(end, start)
      const length = direction.length()

      if (length < 1e-6) continue

      const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)

      const cylinderGeo = new THREE.CylinderGeometry(thisEdgeRadius, thisEdgeRadius, length, 8)
      const cylinder = new THREE.Mesh(cylinderGeo, mat)
      cylinder.position.copy(midPoint)

      const axis = new THREE.Vector3(0, 1, 0)
      const normalizedDir = direction.clone().normalize()
      if (normalizedDir.length() < 0.5) continue
      const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, normalizedDir)
      cylinder.quaternion.copy(quaternion)

      // 存储边信息用于点击选择
      cylinder.userData.topoEdge = {
        id: edge.id,
        aNodeId: edge.a_node_id,
        bNodeId: edge.b_node_id,
        cableType: edge.cable_type,
        cableId: edge.cable_id,
        cableNo: edge.cable_no,
        cableName: edge.cable_name,
        segmentIndex: i,
      }
      cylinder.name = `topo-edge-${edge.id}-seg-${i}`
      edgeGroup.add(cylinder)
    }

    // 添加拐点球（白色，可拖拽）—— 仅当该线被选中时显示，避免多线重叠时手柄难以操控
    if (waypoints.length > 0 && isEditMode.value && selectedTopoEdgeId.value === edge.id) {
      waypoints.forEach((wp, idx) => {
        const wpWorld = percentToWorld(wp.x, wp.y, edgeHeight)
        const sphereGeo = new THREE.SphereGeometry(wpRadius, 16, 16)
        const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 1.0 })
        const sphere = new THREE.Mesh(sphereGeo, sphereMat)
        sphere.position.set(wpWorld.x, wpWorld.y, wpWorld.z)
        sphere.userData.topoEdgeWaypoint = {
          edgeId: edge.id,
          index: idx,
          x: wp.x,
          y: wp.y,
        }
        sphere.name = `topo-edge-waypoint-${edge.id}-${idx}`
        edgeGroup.add(sphere)
      })
    }
  })

  scene.add(edgeGroup)
  ctx.value.topoEdgesGroup = edgeGroup

  // 渲染 junction 节点球（分支点）
  const junctionNodes = topoNodes.value.filter(n => n.node_kind === 'junction' && n.junction_type === 'branch_point')
  if (junctionNodes.length > 0) {
    const bpHeight = edgeHeight + 1  // 分支点略高于边
    const bpRadius = edgeRadius * 3  // 分支点球比边粗

    junctionNodes.forEach(node => {
      const bpWorld = percentToWorld(node.x_percent, node.y_percent, bpHeight)
      const sphereGeo = new THREE.SphereGeometry(bpRadius, 16, 16)
      const sphereMat = new THREE.MeshBasicMaterial({
        color: 0xfbbf24,  // 黄色（分支点）
        transparent: true,
        opacity: 1.0,
      })
      const sphere = new THREE.Mesh(sphereGeo, sphereMat)
      sphere.position.set(bpWorld.x, bpWorld.y, bpWorld.z)
      sphere.userData.topoNode = node
      sphere.name = `junction-${node.id}`
      edgeGroup.add(sphere)

      // 添加分支点标签（CSS2D）
      if (node.label && isEditMode.value) {
        const labelEl = document.createElement('div')
        labelEl.className = 'topo-label junction-label'
        labelEl.textContent = node.label
        const labelObj = new CSS2DObject(labelEl)
        labelObj.position.set(bpWorld.x, bpWorld.y + bpRadius * 2, bpWorld.z)
        edgeGroup.add(labelObj)
      }
    })
  }

  // 渲染 trunk_endpoint（主干起点终点，编辑模式下可拖拽）
  if (isEditMode.value) {
    const trunkEndpoints = topoNodes.value.filter(n => n.node_kind === 'junction' && n.junction_type === 'trunk_endpoint')
    if (trunkEndpoints.length > 0) {
      const epHeight = edgeHeight + edgeRadius * 2
      const epRadius = edgeRadius * 4  // 起点终点球更大

      trunkEndpoints.forEach(node => {
        const epWorld = percentToWorld(node.x_percent, node.y_percent, epHeight)
        const sphereGeo = new THREE.SphereGeometry(epRadius, 16, 16)
        // 起点绿色，终点红色
        const isStart = node.label && node.label.includes('起点')
        const sphereMat = new THREE.MeshBasicMaterial({
          color: isStart ? 0x22c55e : 0xef4444,
          transparent: true,
          opacity: 1.0,
        })
        const sphere = new THREE.Mesh(sphereGeo, sphereMat)
        sphere.position.set(epWorld.x, epWorld.y, epWorld.z)
        sphere.userData.topoEndpoint = {
          nodeId: node.id,
          type: isStart ? 'start' : 'end',
          x: node.x_percent,
          y: node.y_percent,
        }
        sphere.name = `topo-endpoint-${node.id}`
        edgeGroup.add(sphere)
      })
    }
  }

  // 添加 cable_no 标签（只在编辑模式下显示）
  if (isEditMode.value) {
    // 按 cable_id 聚合，只在每条光缆的中点显示一个标签
    const cablesMap = new Map()
    topoEdges.value.forEach(edge => {
      if (edge.cable_id && edge.cable_no) {
        if (!cablesMap.has(edge.cable_id)) {
          cablesMap.set(edge.cable_id, { cable_no: edge.cable_no, cable_name: edge.cable_name, edges: [] })
        }
        cablesMap.get(edge.cable_id).edges.push(edge)
      }
    })

    cablesMap.forEach((cable, cableId) => {
      // 计算光缆中点位置
      const cableEdges = cable.edges
      if (cableEdges.length === 0) return

      // 取第一条边的起点作为标签位置
      const firstEdge = cableEdges[0]
      const aNode = topoNodes.value.find(n => n.id === firstEdge.a_node_id)
      if (!aNode) return

      const labelWorld = percentToWorld(aNode.x_percent, aNode.y_percent, edgeHeight + edgeRadius * 4)

      const labelEl = document.createElement('div')
      labelEl.className = 'topo-label cable-label'
      labelEl.textContent = cable.cable_no
      const labelObj = new CSS2DObject(labelEl)
      labelObj.position.set(labelWorld.x, labelWorld.y, labelWorld.z)
      edgeGroup.add(labelObj)
    })
  }
}

// 创建立体设备模型（基于底图比例）
function createDeviceModel(deviceType, status = 'online') {
  const group = new THREE.Group()
  const base = getDeviceBaseSize(deviceType)
  const color = STATUS_COLOR[status] || STATUS_COLOR.online
  const emissive = STATUS_EMISSIVE[status] || STATUS_EMISSIVE.online
  const bodyMat = new THREE.MeshStandardMaterial({ color, metalness: 0.4, roughness: 0.5, emissive, emissiveIntensity: 0.3 })
  const accentMat = new THREE.MeshStandardMaterial({ color: 0x1a2230, metalness: 0.6, roughness: 0.4 })

  switch (deviceType) {
    case 'ap': {
      const r = base * 0.6
      const baseMesh = new THREE.Mesh(new THREE.CylinderGeometry(r, r, base * 0.25, 24), bodyMat)
      const dome = new THREE.Mesh(
        new THREE.SphereGeometry(r * 0.7, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), bodyMat)
      dome.position.y = base * 0.15
      group.add(baseMesh, dome)
      break
    }
    case 'router': {
      const body = new THREE.Mesh(new THREE.BoxGeometry(base * 1.4, base * 0.4, base * 1.0), bodyMat)
      group.add(body)
      for (let i = -1; i <= 1; i++) {
        const ant = new THREE.Mesh(new THREE.CylinderGeometry(base * 0.04, base * 0.04, base * 0.8), accentMat)
        ant.position.set(i * base * 0.4, base * 0.6, -base * 0.4)
        group.add(ant)
      }
      break
    }
    case 'firewall': {
      const body = new THREE.Mesh(new THREE.BoxGeometry(base * 1.4, base * 0.8, base * 1.0),
        new THREE.MeshStandardMaterial({ color: 0xff4d4f, metalness: 0.4, roughness: 0.5 }))
      const panel = new THREE.Mesh(new THREE.BoxGeometry(base * 1.42, base * 0.15, base * 0.03), accentMat)
      panel.position.set(0, base * 0.1, base * 0.5)
      group.add(body, panel)
      break
    }
    default: { // switch / core_switch / server_switch / uce
      const body = new THREE.Mesh(new THREE.BoxGeometry(base * 1.6, base * 0.5, base * 1.1), bodyMat)
      const ports = new THREE.Mesh(new THREE.BoxGeometry(base * 1.4, base * 0.12, base * 0.03), accentMat)
      ports.position.set(0, -base * 0.05, base * 0.56)
      group.add(body, ports)
    }
  }

  group.userData.deviceType = deviceType
  return group
}

// 构建设备模型（独立 Group，便于单独操作）
function buildDeviceModels() {
  const { scene } = ctx.value

  // 清除旧设备组（移除所有同名组，防止重复累积）
  disposeGroup('devices')

  const group = new THREE.Group()
  group.name = 'devices'

  filteredDevices.value.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return

    const model = createDeviceModel(d.device_type, deviceStatus(d))
    const elevation = getDeviceBaseSize(d.device_type) * 0.5
    const w = percentToWorld(node.x_percent, node.y_percent, elevation)
    model.position.set(w.x, w.y, w.z)
    const userScale = Number(node.scale) || 1
    model.scale.setScalar(userScale)
    model.userData = { device: d, node, base: getDeviceBaseSize(d.device_type) }
    group.add(model)
  })

  scene.add(group)
  ctx.value.deviceGroup = group
}

// 清理组资源
function disposeGroup(name) {
  const { scene } = ctx.value
  if (!scene) return
  // 移除所有同名直接子组（防止同名组残留导致重复渲染）
  const groups = scene.children.filter(o => o.name === name)
  groups.forEach(g => {
    g.traverse(o => {
      // 清理 CSS2DObject 的 DOM 元素
      if (o.element && o.element.parentNode) {
        o.element.parentNode.removeChild(o.element)
      }
      o.geometry?.dispose?.()
      o.material?.dispose?.()
    })
    scene.remove(g)
  })
}

// 重建场景（底图切换或节点变化后）
function rebuildScene() {
  disposeGroup('devices')
  disposeGroup('links')
  disposeGroup('labels')
  disposeGroup('fiber-trunks')
  disposeGroup('branch-points')
  disposeGroup('branch-links')
  disposeGroup('data-link-paths')
  disposeGroup('impact-glow')
  buildDeviceModels()
  buildLinks()
  buildTopoEdges()
  buildDataLinkPaths()
  buildLabels()
  buildOfflineGlow()
  buildImpactGlow()
}

// 构建链路（支持 waypoints 正交折线）
function buildLinks() {
  const { scene } = ctx.value

  const linkGroup = new THREE.Group()
  linkGroup.name = 'links'

  // 链路高度：比主干光缆稍微高一点，避免重叠
  const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
  const linkHeight = trunkHeight + 0.5  // 链路浮在主干上方
  // 链路圆柱半径：比主干细一点
  const linkRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001

  links.value.forEach(link => {
    const fromNode = nodes.value.find(n => n.id === link.from_node_id || n.device_id === link.from)
    const toNode = nodes.value.find(n => n.id === link.to_node_id || n.device_id === link.to)

    if (!fromNode || !toNode) return

    const a = percentToWorld(fromNode.x_percent, fromNode.y_percent, linkHeight)
    const b = percentToWorld(toNode.x_percent, toNode.y_percent, linkHeight)

    // 构建折线点（支持 waypoints）
    const points = []
    points.push(new THREE.Vector3(a.x, a.y, a.z))

    // 如果有拐点，按拐点绘制折线
    if (link.waypoints) {
      try {
        // waypoints 可能是字符串或已解析的数组
        const waypoints = typeof link.waypoints === 'string'
          ? JSON.parse(link.waypoints)
          : link.waypoints
        if (Array.isArray(waypoints)) {
          waypoints.forEach(wp => {
            const wpWorld = percentToWorld(wp.x, wp.y, linkHeight)
            points.push(new THREE.Vector3(wpWorld.x, wpWorld.y, wpWorld.z))
          })
        }
      } catch (e) {
        console.error('解析 waypoints 失败:', e)
      }
    } else if (!link.waypoints) {
      // 无拐点时，生成默认正交折线（先横后竖）
      const midX = (a.x + b.x) / 2
      const midZ = (a.z + b.z) / 2
      // 根据起点终点方向决定折线方向
      if (Math.abs(a.x - b.x) > Math.abs(a.z - b.z)) {
        // 横向为主：先横向到中点，再竖向
        points.push(new THREE.Vector3(midX, a.y, a.z))
        points.push(new THREE.Vector3(midX, a.y, b.z))
      } else {
        // 竖向为主：先竖向到中点，再横向
        points.push(new THREE.Vector3(a.x, a.y, midZ))
        points.push(new THREE.Vector3(b.x, a.y, midZ))
      }
    }

    points.push(new THREE.Vector3(b.x, b.y, b.z))

    // 链路状态颜色：正常绿色；链路本身故障或任一端设备离线时变红
    const fromDevice = devices.value.find(d => d.id === fromNode.device_id)
    const toDevice = devices.value.find(d => d.id === toNode.device_id)
    const endpointOffline =
      (fromDevice && isDeviceOffline(fromDevice)) ||
      (toDevice && isDeviceOffline(toDevice))
    const statusColor = (link.status === 'broken' || endpointOffline) ? 0xff4d4f : 0x22c55e  // 红色/绿色
    const mat = new THREE.MeshBasicMaterial({
      color: statusColor,
      transparent: true,
      opacity: 0.8,
    })
    // 标记“离线/故障链路”，供动画循环做呼吸闪烁
    mat.userData.offlineLink = (link.status === 'broken' || endpointOffline)

    // 使用圆柱体绘制每段链路（更粗、更可见）
    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i]
      const end = points[i + 1]

      const direction = new THREE.Vector3().subVectors(end, start)
      const length = direction.length()
      const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)

      const cylinderGeo = new THREE.CylinderGeometry(linkRadius, linkRadius, length, 8)
      const cylinder = new THREE.Mesh(cylinderGeo, mat)
      cylinder.position.copy(midPoint)

      const axis = new THREE.Vector3(0, 1, 0)
      const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, direction.clone().normalize())
      cylinder.quaternion.copy(quaternion)

      cylinder.userData.link = link
      cylinder.name = `link-${link.id}-seg-${i}`
      linkGroup.add(cylinder)
    }

    // 如果有拐点且在编辑模式，添加拐点标记球
    if (link.waypoints && isEditMode.value) {
      try {
        // waypoints 可能是字符串或已解析的数组
        const waypoints = typeof link.waypoints === 'string'
          ? JSON.parse(link.waypoints)
          : link.waypoints
        if (Array.isArray(waypoints)) {
          waypoints.forEach((wp, idx) => {
            const wpWorld = percentToWorld(wp.x, wp.y, linkHeight + linkRadius * 2)
            // 拐点球半径
            const wpRadius = linkRadius * 2.5
            const sphereGeo = new THREE.SphereGeometry(wpRadius, 16, 16)
            const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffc107, transparent: true, opacity: 1.0 })  // 黄色
            const sphere = new THREE.Mesh(sphereGeo, sphereMat)
            sphere.position.set(wpWorld.x, wpWorld.y, wpWorld.z)
            sphere.userData.waypoint = { linkId: link.id, index: idx, x: wp.x, y: wp.y }
            sphere.name = `waypoint-${link.id}-${idx}`
            linkGroup.add(sphere)
          })
        }
      } catch (e) {}
    }
  })

  scene.add(linkGroup)
  // 保留显隐状态（rebuild 后仍跟随“数据链路”开关）
  linkGroup.visible = showDataLinks.value
  ctx.value.linkLines = linkGroup
}

// 构建数据链路路径（沿着光纤拓扑）- 使用后端返回的 polyline
function buildDataLinkPaths() {
  const { scene } = ctx.value
  if (!scene || !devicePaths.value || Object.keys(devicePaths.value).length === 0) return

  const pathGroup = new THREE.Group()
  pathGroup.name = 'data-link-paths'

  // 路径高度：在物理拓扑上方
  const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
  const pathHeight = trunkHeight + 0.8
  // 路径线半径（比链路稍细）
  const pathRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.0008

  Object.entries(devicePaths.value).forEach(([pathKey, pathData]) => {
    // 支持两种格式：
    // 旧格式：pathData 是数组 [{x_percent, y_percent}, ...]
    // 新格式：pathData 是对象 {reachable, polyline: [{x_percent, y_percent}, ...]}
    let polyline = pathData
    if (pathData && typeof pathData === 'object' && !Array.isArray(pathData)) {
      if (!pathData.reachable) return  // 不可达，跳过
      polyline = pathData.polyline || []
    }

    if (!Array.isArray(polyline) || polyline.length < 2) return

    // 获取设备状态（以可达性判断，unreachable 显示红色）
    const deviceId = pathData?.device_id || parseInt(pathKey)
    const device = devices.value.find(d => d.id === deviceId)
    const isNeighborPath = pathData?.path_source === 'neighbor'
    const heat = getTrafficHeatForPath(deviceId, pathData)
    const activeHeat = heat?.level === 'stale' ? null : heat
    let statusColor = device && isDeviceOffline(device) ? 0xff4d4f : 0x22c55e  // 红色/绿色
    let heatRadius = pathRadius
    if (isNeighborPath) {
      statusColor = pathData.oper_status === 'down'
        ? 0xff4d4f
        : (pathData.neighbor_source === 'lldp' ? 0x38bdf8 : 0x22c55e)
    }
    if (activeHeat && !(device && isDeviceOffline(device)) && !(isNeighborPath && pathData.oper_status === 'down')) {
      statusColor = new THREE.Color(activeHeat.color || '#22c55e').getHex()
      heatRadius = pathRadius * Math.max(1, Math.min(3, (activeHeat.width || 2) / 2))
    }

    // 直接使用 polyline 的 x_percent, y_percent（后端已去重）
    const points = polyline.map(pt => {
      if (pt.x_percent != null && pt.y_percent != null) {
        const pos = percentToWorld(pt.x_percent, pt.y_percent, pathHeight)
        return new THREE.Vector3(pos.x, pos.y, pos.z)
      }
      return null
    }).filter(p => p !== null)

    // 如果点数少于2，无法绘制路径
    if (points.length < 2) return

    // 使用圆柱体绘制路径线
    const mat = new THREE.MeshBasicMaterial({
      color: statusColor,
      transparent: true,
      opacity: 0.7,
    })

    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i]
      const end = points[i + 1]

      const direction = new THREE.Vector3().subVectors(end, start)
      const length = direction.length()

      // 零长度段防御：跳过长度过小的段
      if (length < 1e-6) continue

      const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)

      const cylinderGeo = new THREE.CylinderGeometry(heatRadius, heatRadius, length, 8)
      const cylinder = new THREE.Mesh(cylinderGeo, mat)
      cylinder.position.copy(midPoint)

      const axis = new THREE.Vector3(0, 1, 0)
      const normalizedDir = direction.clone().normalize()
      // 防止 normalize 后仍然是零向量（虽然上面已检查，但双重保险）
      if (normalizedDir.length() < 0.5) continue
      const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, normalizedDir)
      cylinder.quaternion.copy(quaternion)

      cylinder.userData.dataPath = {
        pathKey,
        deviceId,
        peerDeviceId: pathData?.peer_device_id,
        source: pathData?.path_source || 'core',
        neighborSource: pathData?.neighbor_source,
        trafficHeat: heat || null,
        segmentIndex: i,
      }
      cylinder.name = `data-path-${pathKey}-seg-${i}`
      pathGroup.add(cylinder)
    }
  })

  scene.add(pathGroup)
  ctx.value.dataLinkPaths = pathGroup
  // 保留显隐状态（rebuild 后仍跟随“数据链路”开关）
  pathGroup.visible = showDataLinks.value
}

// 构建端口锚点（设备上的小圆点）
function buildPortAnchors() {
  const { scene } = ctx.value
  if (!scene) return

  // 清除旧锚点
  disposeGroup('port-anchors')

  if (!isEditMode.value) return  // 只在编辑模式显示

  const anchorGroup = new THREE.Group()
  anchorGroup.name = 'port-anchors'

  const refDim = Math.min(plan.real_width_m, plan.real_depth_m)
  const anchorRadius = refDim * 0.004   // 放大，编辑模式下清晰可见
  const anchorHeight = refDim * 0.006   // 抬高，浮在设备模型上方

  // 遍历设备节点，显示端口锚点
  nodes.value.forEach(node => {
    const device = devices.value.find(d => d.id === node.device_id)
    if (!device) return

    // 获取该设备的端口
    const ports = devicePorts.value.filter(p => p.device_id === device.id)
    if (ports.length === 0) {
      // 如果没有端口数据，显示默认中心锚点
      ports.push({
        id: `auto-${node.id}`,
        device_id: device.id,
        name: 'auto',
        anchor_x: 0.5,
        anchor_y: 0.5,
        is_auto_created: true,
      })
    }

    ports.forEach(port => {
      // 计算锚点位置（设备坐标 + 锚点偏移）
      const baseX = parseFloat(node.x_percent)
      const baseY = parseFloat(node.y_percent)
      // 锚点偏移需跟随模型缩放，否则模型缩小后锚点会越离越远，连线产生分叉
      const nodeScale = Number(node.scale) || 1
      const iconSize = 3.0 * nodeScale  // 设备图标实际占地（随缩放变化）
      const offsetX = (port.anchor_x - 0.5) * iconSize
      const offsetY = (port.anchor_y - 0.5) * iconSize

      const worldPos = percentToWorld(baseX + offsetX, baseY + offsetY, anchorHeight)

      const anchorColor = port.is_auto_created ? 0x22c55e : 0x3b82f6  // 自动=绿色 手动=蓝色

      // 创建锚点球（核心，不透明、鲜亮）
      const sphereGeo = new THREE.SphereGeometry(anchorRadius, 16, 16)
      const sphereMat = new THREE.MeshBasicMaterial({
        color: anchorColor,
        transparent: false,
      })
      const sphere = new THREE.Mesh(sphereGeo, sphereMat)
      sphere.position.set(worldPos.x, worldPos.y, worldPos.z)
      sphere.userData.portAnchor = {
        portId: port.id,
        deviceId: device.id,
        deviceName: device.name,
        anchorX: baseX + offsetX,
        anchorY: baseY + offsetY,
      }
      sphere.name = `port-anchor-${device.id}-${port.id}`
      anchorGroup.add(sphere)

      // 外层发光光环（半透明，不参与射线拾取，避免遮挡核心球）
      const haloGeo = new THREE.SphereGeometry(anchorRadius * 1.4, 16, 16)
      const haloMat = new THREE.MeshBasicMaterial({
        color: anchorColor,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
      })
      const halo = new THREE.Mesh(haloGeo, haloMat)
      halo.position.set(worldPos.x, worldPos.y, worldPos.z)
      halo.raycast = () => {}
      anchorGroup.add(halo)
    })
  })

  scene.add(anchorGroup)
  ctx.value.portAnchors = anchorGroup
}

// 构建设备标签（显示在设备上方）
function buildLabels() {
  const { scene, deviceGroup } = ctx.value

  const labelGroup = new THREE.Group()
  labelGroup.name = 'labels'

  // 显示所有筛选后的设备标签
  filteredDevices.value.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return

    // 获取设备模型位置和高度
    const base = getDeviceBaseSize(d.device_type)
    const elevation = base * 0.5  // 设备离地高度
    const modelHeight = base * 0.8  // 设备模型高度估算
    const labelHeight = elevation + modelHeight + base * 0.3  // 标签在设备上方

    const w = percentToWorld(node.x_percent, node.y_percent, labelHeight)

    const el = document.createElement('div')
    el.className = `device-label ${deviceStatus(d)}`
    el.textContent = d.name
    el.style.opacity = '0'

    const label = new CSS2DObject(el)
    label.position.set(w.x, w.y, w.z)
    label.userData.deviceId = d.id
    label.userData.deviceStatus = deviceStatus(d)
    label.visible = false
    labelGroup.add(label)
  })

  scene.add(labelGroup)
  ctx.value.labels = labelGroup
}

// 离线设备呼吸动画（独立 Group 版本）
let pulseTime = 0
let lastPulseUpdate = 0
const PULSE_UPDATE_INTERVAL = 50

function pulseOfflineDevices() {
  const { deviceGroup } = ctx.value
  if (!deviceGroup) return

  const now = performance.now()
  if (now - lastPulseUpdate < PULSE_UPDATE_INTERVAL) return
  lastPulseUpdate = now

  pulseTime += 0.1
  const pulse = Math.sin(pulseTime) * 0.3 + 0.7

  deviceGroup.children.forEach(model => {
    const device = model.userData.device
    if (device && isDeviceOffline(device)) {
      model.traverse(child => {
        if (child.material && child.material.color) {
          const baseColor = STATUS_COLOR.offline
          child.material.color.set(baseColor)
          child.material.color.multiplyScalar(pulse)
        }
      })
    }
  })
}

// ===== 离线设备红色径向渐变光晕（以设备为中心向外渐变浅红，不覆盖整图）=====
const OFFLINE_GLOW_RADIUS_FACTOR = 7   // 光晕半径 = 设备基准尺寸 × 系数
const IMPACT_GLOW_RADIUS_FACTOR = 5.5

function createRadialGlowTexture() {
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const c = canvas.getContext('2d')
  const grad = c.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  // 中心较浓红 → 边缘完全透明，形成淡淡一层向外渐变
  grad.addColorStop(0.0, 'rgba(255, 70, 70, 0.55)')
  grad.addColorStop(0.35, 'rgba(255, 40, 40, 0.30)')
  grad.addColorStop(0.7, 'rgba(255, 20, 20, 0.10)')
  grad.addColorStop(1.0, 'rgba(255, 0, 0, 0)')
  c.fillStyle = grad
  c.fillRect(0, 0, size, size)
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

function createImpactGlowTexture() {
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const c = canvas.getContext('2d')
  const grad = c.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  grad.addColorStop(0.0, 'rgba(251, 191, 36, 0.45)')
  grad.addColorStop(0.38, 'rgba(245, 158, 11, 0.26)')
  grad.addColorStop(0.72, 'rgba(217, 119, 6, 0.10)')
  grad.addColorStop(1.0, 'rgba(217, 119, 6, 0)')
  c.fillStyle = grad
  c.fillRect(0, 0, size, size)
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

function getImpactDevices() {
  const impacted = commandSummary.value?.impact_scope?.impacted_devices || []
  if (!Array.isArray(impacted) || impacted.length === 0) return []
  const impactedIds = new Set(impacted.map(d => d.device_id).filter(Boolean))
  return filteredDevices.value.filter(d => impactedIds.has(d.id) && !isDeviceOffline(d))
}

// 构建离线设备地面光晕（独立 Group，便于单独清理/重建）
function buildOfflineGlow() {
  disposeGroup('offline-glow')
  const { scene } = ctx.value
  if (!scene) return

  const offline = filteredDevices.value.filter(isDeviceOffline)
  if (offline.length === 0) return

  if (!sceneState.offlineGlowTexture) sceneState.offlineGlowTexture = createRadialGlowTexture()

  const group = new THREE.Group()
  group.name = 'offline-glow'

  offline.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return
    const w = percentToWorld(node.x_percent, node.y_percent, 0)
    const radius = getDeviceBaseSize(d.device_type) * OFFLINE_GLOW_RADIUS_FACTOR
    const geo = new THREE.PlaneGeometry(radius * 2, radius * 2)
    const mat = new THREE.MeshBasicMaterial({
      map: sceneState.offlineGlowTexture,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
      blending: THREE.NormalBlending,
    })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.rotation.x = -Math.PI / 2          // 平铺在地面
    mesh.position.set(w.x, 0.2, w.z)        // 略高于底图避免 z-fighting
    mesh.renderOrder = 2
    mesh.userData = { deviceId: d.id }
    group.add(mesh)
  })

  scene.add(group)
}

// 离线光晕呼吸动画（透明度+缩放轻微脉动）
function updateOfflineGlow() {
  const { scene } = ctx.value
  if (!scene) return
  const group = scene.getObjectByName('offline-glow')
  if (!group || group.children.length === 0) return

  const breath = Math.sin(pulseTime * 1.2) * 0.18 + 0.82  // 0.64 ~ 1.0
  group.children.forEach(mesh => {
    if (mesh.material) mesh.material.opacity = 0.9 * breath
    const s = 0.92 + (breath - 0.82) * 0.6
    mesh.scale.setScalar(s)
  })
}

function buildImpactGlow() {
  disposeGroup('impact-glow')
  const { scene } = ctx.value
  if (!scene) return

  const impacted = getImpactDevices()
  if (impacted.length === 0) return

  if (!sceneState.impactGlowTexture) sceneState.impactGlowTexture = createImpactGlowTexture()

  const group = new THREE.Group()
  group.name = 'impact-glow'

  impacted.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return
    const w = percentToWorld(node.x_percent, node.y_percent, 0)
    const radius = getDeviceBaseSize(d.device_type) * IMPACT_GLOW_RADIUS_FACTOR
    const geo = new THREE.PlaneGeometry(radius * 2, radius * 2)
    const mat = new THREE.MeshBasicMaterial({
      map: sceneState.impactGlowTexture,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
      blending: THREE.NormalBlending,
    })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.rotation.x = -Math.PI / 2
    mesh.position.set(w.x, 0.25, w.z)
    mesh.renderOrder = 3
    mesh.userData = { deviceId: d.id }
    group.add(mesh)
  })

  scene.add(group)
}

function updateImpactGlow() {
  const { scene } = ctx.value
  if (!scene) return
  const group = scene.getObjectByName('impact-glow')
  if (!group || group.children.length === 0) return

  const breath = Math.sin(pulseTime * 1.35) * 0.16 + 0.84
  group.children.forEach(mesh => {
    if (mesh.material) mesh.material.opacity = 0.72 * breath
    const s = 0.94 + (breath - 0.84) * 0.7
    mesh.scale.setScalar(s)
  })
}

// 离线/故障链路呼吸闪烁（与设备/光晕同相，红色透明度脉动）
function pulseOfflineLinks() {
  const { linkLines } = ctx.value
  if (!linkLines) return
  // 与设备呼吸同相：pulse 0.4 ~ 1.0
  const pulse = Math.sin(pulseTime) * 0.3 + 0.7
  const seen = new Set()
  linkLines.children.forEach(child => {
    const mat = child.material
    if (!mat || !mat.userData || !mat.userData.offlineLink) return
    if (seen.has(mat)) return   // 同一链路多段共享材质，仅设置一次
    seen.add(mat)
    mat.opacity = 0.4 + 0.5 * pulse   // 0.6 ~ 0.9 区间脉动
  })
}

// 根据相机距离更新标签可见性
const LABEL_SHOW_DISTANCE = 200 // 相机距离小于200米时显示标签
function updateLabelVisibility() {
  const { camera, labels } = ctx.value
  if (!labels || !showLabels.value) return

  const cameraPos = camera.position
  const cameraHeight = cameraPos.y

  // 标签可见性：相机高度低于阈值时显示
  const shouldShowLabels = cameraHeight < LABEL_SHOW_DISTANCE

  labels.children.forEach(label => {
    // 计算标签与相机的距离
    const labelPos = label.position
    const dist = cameraPos.distanceTo(labelPos)

    // 近距离显示，远距离隐藏
    label.visible = shouldShowLabels && dist < LABEL_SHOW_DISTANCE * 2

    // 更新标签样式（近处更清晰）
    if (label.element) {
      const opacity = dist < LABEL_SHOW_DISTANCE ? 1 : 0.5
      label.element.style.opacity = opacity
    }
  })
}

// 数据链路流量热力（buildDataLinkPaths 共享）
function getTrafficHeatForPath(deviceId, pathData = {}) {
  const pathDeviceId = Number(pathData?.device_id || deviceId)
  const pathIfIndex = pathData?.if_index != null ? Number(pathData.if_index) : null

  if (pathIfIndex != null) {
    const exact = trafficHeatItems.value.find(item =>
      Number(item.device_id) === pathDeviceId && Number(item.if_index) === pathIfIndex
    )
    if (exact) return exact
  }

  if (trafficHeatByDevice.value.has(deviceId)) return trafficHeatByDevice.value.get(deviceId)
  if (pathData.peer_device_id && trafficHeatByDevice.value.has(pathData.peer_device_id)) {
    return trafficHeatByDevice.value.get(pathData.peer_device_id)
  }
  return null
}

// ===== 设备状态实时刷新（仅重建设备/标签/数据链路，状态变化时调用）=====
function refreshDeviceVisuals() {
  disposeGroup('devices')
  disposeGroup('labels')
  disposeGroup('links')
  disposeGroup('data-link-paths')
  buildDeviceModels()
  buildLabels()
  buildLinks()
  buildDataLinkPaths()
  buildOfflineGlow()
}

  return {
    getTopoNodeRenderPos,
    createDeviceModel,
    buildDeviceModels,
    buildLinks,
    buildTopoEdges,
    buildDataLinkPaths,
    buildLabels,
    buildPortAnchors,
    buildOfflineGlow,
    updateOfflineGlow,
    buildImpactGlow,
    updateImpactGlow,
    pulseOfflineDevices,
    pulseOfflineLinks,
    updateLabelVisibility,
    disposeGroup,
    rebuildScene,
    refreshDeviceVisuals,
    getTrafficHeatForPath,
  }
}
