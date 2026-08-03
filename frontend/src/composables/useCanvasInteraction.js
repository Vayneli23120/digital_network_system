// Monitor3D 画布交互（item 946 切片 9c）
// 从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
// 父侧单实例：读 sceneState + deps + builders；attach/detachSceneListeners 由父在 initScene 后/卸载时调用。
import { ref } from 'vue'
import * as THREE from 'three'
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { ElMessage } from 'element-plus'
import { authenticatedAxios as axios } from '@/api/request.js'
import { formatDateTime } from '@/utils/time'

export function useCanvasInteraction(sceneState, deps, builders) {
  // 别名：与父侧一致的对象引用共享（sceneState 不可 reactive/ref 包裹）
  const ctx = sceneState.ctx
  const plan = sceneState.plan
  const { percentToWorld, getDeviceBaseSize, raycaster, pointer, EMISSIVE_ON, EMISSIVE_OFF } = sceneState
  const { t } = deps
  const {
    isEditMode, selectedDevice, selectedNode, selectedTopoEdgeId,
    trunkCreateMode, trunkStartPoint, trunkEndPoint, branchPointCreateMode,
    connectFromBranchMode, selectedBranchPoint, selectedTopoBranchPoint,
    devices, nodes, links, fiberTrunks, fiberBranchLinks, devicePaths,
    topoNodes, topoEdges, currentPlanId,
  } = deps
  const { deviceStatus, isDeviceOffline, getStatusLabelI18n, getDeviceTypeLabelI18n } = deps.deviceMappings
  const {
    createFiberTrunk, connectDeviceFromTopoBranch, connectDeviceFromBranch,
    addBranchPointOnTopoEdge, openTopoEdgeWaypointDialog,
    loadTopoData, loadFiberData, getActiveFaultForDevice,
  } = deps

  // 连线状态（父侧无引用；端口/拓扑 refs 由父持有经 deps 共享）
  const wiringState = ref(null)  // { fromNodeId, fromWorldPos, rubberBandLine }

// 屏幕坐标 → 百分比坐标（射线求交）
function screenToPercent(e) {
  const { camera, renderer } = ctx.value
  const rect = renderer.domElement.getBoundingClientRect()
  const ndc = new THREE.Vector2(
    ((e.clientX - rect.left) / rect.width) * 2 - 1,
    -((e.clientY - rect.top) / rect.height) * 2 + 1
  )
  const ray = new THREE.Raycaster()
  ray.setFromCamera(ndc, camera)
  const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
  const hit = new THREE.Vector3()
  if (!ray.ray.intersectPlane(ground, hit)) return null
  return {
    x_percent: Math.max(0, Math.min(100, (hit.x / plan.real_width_m) * 100)),
    y_percent: Math.max(0, Math.min(100, (hit.z / plan.real_depth_m) * 100)),
  }
}

// 更新设备缩放
async function updateDeviceScale(newScale) {
  if (!selectedNode.value) return

  try {
    await axios.put(`/api/floor-plans/${currentPlanId.value}/nodes/${selectedNode.value.id}`, {
      scale: Number(newScale.toFixed(2)),
    })
    ElMessage.success(t('msgSaveSuccess'))

    // 更新本地 nodes 数据
    const node = nodes.value.find(n => n.id === selectedNode.value.id)
    if (node) {
      node.scale = newScale
      selectedNode.value = { ...node }
    }

    // 更新模型缩放
    if (selectedModel) {
      selectedModel.scale.setScalar(newScale)
    }

    // 重建端口锚点，使其偏移跟随新缩放（避免锚点脱离模型）
    if (isEditMode.value) {
      builders.buildPortAnchors()
    }

    // 分支光缆终点与数据链路寻路都依赖锚点偏移（随缩放变化），一并刷新避免分叉
    builders.buildTopoEdges()
    try {
      const res = await axios.get(`/api/floor-plans/${currentPlanId.value}/device-paths`)
      devicePaths.value = {
        ...(res.data?.paths || {}),
        ...(res.data?.neighbor_paths || {}),
      }
      builders.disposeGroup('data-link-paths')
      builders.buildDataLinkPaths()
    } catch (e) {
      // 数据链路刷新失败不阻断缩放操作
    }
  } catch (e) {
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 自定义滚轮缩放处理函数（需要保存引用以便清理）
function handleWheel(e) {
  e.preventDefault()

  // 编辑模式下禁用滚轮缩放，防止视角乱动
  if (isEditMode.value) return

  const { camera, controls } = ctx.value

  // 计算鼠标在场景中的位置
  const rect = ctx.value.renderer.domElement.getBoundingClientRect()
  const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1
  const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1

  // 射线投射到地面（y=0）
  const raycasterLocal = new THREE.Raycaster()
  raycasterLocal.setFromCamera({ x: mouseX, y: mouseY }, camera)

  // 创建一个水平面用于计算交点
  const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
  const intersectPoint = new THREE.Vector3()
  raycasterLocal.ray.intersectPlane(groundPlane, intersectPoint)

  if (intersectPoint) {
    // 缩放因子
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    const minDist = 30
    const maxDist = 3000

    // 当前相机到target的距离
    const currentDist = camera.position.distanceTo(controls.target)
    const newDist = Math.max(minDist, Math.min(maxDist, currentDist * (1 / delta)))

    // 以鼠标位置为中心缩放
    const direction = camera.position.clone().sub(controls.target).normalize()
    const offset = intersectPoint.clone().sub(controls.target)

    // 新的target位置（向鼠标位置移动）
    const factor = (newDist - currentDist) / currentDist
    controls.target.add(offset.multiplyScalar(factor * 0.5))

    // 新的相机位置
    camera.position.copy(controls.target).add(direction.multiplyScalar(newDist))
  }
}

function onPortAnchorMouseDown(anchorData) {
  if (!isEditMode.value) return

  // 如果已处于连线态，先清理，避免残留孤立的橡皮筋线
  if (wiringState.value) cancelWiring()

  // 查找该端口对应的 topoNode（直接用锚点的 portId 精确匹配）
  const topoNode = topoNodes.value.find(n =>
    n.node_kind === 'port' && n.port_id === anchorData.portId
  )

  if (!topoNode) {
    // 没有拓扑节点，需要先创建
    ElMessage.warning(t('msgUpdateFailed'))
    return
  }

  // 进入连线态
  const worldPos = percentToWorld(anchorData.anchorX, anchorData.anchorY, Math.min(plan.real_width_m, plan.real_depth_m) * 0.003)

  wiringState.value = {
    fromNodeId: topoNode.id,
    fromDeviceId: anchorData.deviceId,
    fromWorldPos: worldPos,
    fromAnchorX: anchorData.anchorX,
    fromAnchorY: anchorData.anchorY,
    rubberBandLine: null,
  }

  // 创建橡皮筋线
  const { scene, renderer } = ctx.value
  if (scene) {
    const lineMat = new THREE.LineBasicMaterial({ color: 0x22c55e, linewidth: 2 })
    const lineGeo = new THREE.BufferGeometry()
    lineGeo.setFromPoints([
      new THREE.Vector3(worldPos.x, worldPos.y, worldPos.z),
      new THREE.Vector3(worldPos.x, worldPos.y, worldPos.z),
    ])
    const line = new THREE.Line(lineGeo, lineMat)
    line.name = 'rubber-band'
    scene.add(line)
    wiringState.value.rubberBandLine = line
  }

  // 添加鼠标移动和释放监听器
  // 添加鼠标移动和释放监听器（挂在 window 上，保证在画布外松开也能结束连线）
  window.addEventListener('mousemove', onWiringMouseMove)
  window.addEventListener('mouseup', onWiringMouseUp)
}

function updateRubberBandLine(mouseWorldPos) {
  if (!wiringState.value || !wiringState.value.rubberBandLine) return

  const line = wiringState.value.rubberBandLine
  const positions = line.geometry.attributes.position.array
  positions[3] = mouseWorldPos.x
  positions[4] = mouseWorldPos.y
  positions[5] = mouseWorldPos.z
  line.geometry.attributes.position.needsUpdate = true
}

async function finishWiring(targetAnchorData) {
  if (!wiringState.value) return

  // 查找目标 topoNode（直接用锚点的 portId 精确匹配）
  const targetTopoNode = topoNodes.value.find(n =>
    n.node_kind === 'port' && n.port_id === targetAnchorData.portId
  )

  if (!targetTopoNode) {
    cancelWiring()
    return
  }

  // 不能连接到自己
  if (wiringState.value.fromDeviceId === targetAnchorData.deviceId) {
    cancelWiring()
    return
  }

  // 防止重复连线：同一对端口节点之间已存在边则拒绝
  const fromNodeId = wiringState.value.fromNodeId
  const toNodeId = targetTopoNode.id
  const duplicate = topoEdges.value.some(e =>
    (e.a_node_id === fromNodeId && e.b_node_id === toNodeId) ||
    (e.a_node_id === toNodeId && e.b_node_id === fromNodeId)
  )
  if (duplicate) {
    ElMessage.warning(t('monitor3dPortDuplicate'))
    cancelWiring()
    return
  }

  // 创建 TopoEdge
  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/topo-edges`, {
      floor_plan_id: currentPlanId.value,
      a_node_id: wiringState.value.fromNodeId,
      b_node_id: targetTopoNode.id,
      cable_type: 'fiber',
      cable_name: `${devices.value.find(d => d.id === wiringState.value.fromDeviceId)?.name || 'A'} - ${devices.value.find(d => d.id === targetAnchorData.deviceId)?.name || 'B'}`,
      status: 'up',
    })

    ElMessage.success(t('msgSaveSuccess'))

    // 重新加载拓扑数据
    await loadTopoData()
    await loadFiberData()
  } catch (e) {
    console.error('创建连接失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }

  cancelWiring()
}

function cancelWiring() {
  // 移除事件监听器
  window.removeEventListener('mousemove', onWiringMouseMove)
  window.removeEventListener('mouseup', onWiringMouseUp)

  // 清除场景中所有橡皮筋线（包括可能残留的孤立线）
  const { scene } = ctx.value
  if (scene) {
    const strays = scene.children.filter(o => o.name === 'rubber-band')
    strays.forEach(o => {
      scene.remove(o)
      o.geometry?.dispose?.()
      o.material?.dispose?.()
    })
  }

  // 恢复控制器
  if (ctx.value.controls) {
    ctx.value.controls.enabled = true
  }

  wiringState.value = null
}

// 点击拾取（独立 Group）
let selectedModel = null

// 拖动状态
const dragState = ref(null)
let isDragging = false

// 拐点拖动状态
let waypointDragState = null
let selectedWaypointSphere = null

// 主干拐点拖动状态
let trunkWaypointDragState = null
let selectedTrunkWaypointSphere = null

// 主干端点拖拽状态
let trunkEndpointDragState = null
let selectedTrunkEndpointSphere = null

// 分支点拖拽状态
let branchPointDragState = null
let selectedBranchPointSphere = null

// 分支光缆拐点拖拽状态
let branchLinkWaypointDragState = null
let selectedBranchLinkWaypointSphere = null

// 编辑模式鼠标按下 - 拖动起点（支持拐点和设备拖动）
function onCanvasMouseDown(e) {
  if (!isEditMode.value) return

  const { camera, renderer, deviceGroup, linkLines, controls, fiberTrunkGroup, branchPointGroup, branchLinkGroup } = ctx.value

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // ========== 光纤主干交互 ==========

  // 处理主干创建模式的点击
  if (trunkCreateMode.value) {
    const pos = screenToPercent(e)
    if (!pos) return

    if (!trunkStartPoint.value) {
      trunkStartPoint.value = { x: pos.x_percent, y: pos.y_percent }
      ElMessage.info(t('clickTrunkEnd'))
    } else {
      trunkEndPoint.value = { x: pos.x_percent, y: pos.y_percent }
      createFiberTrunk()
    }
    return
  }

  // 处理从分支点连接设备模式
  if (connectFromBranchMode.value) {
    // 优先检测是否点中了端口锚点 → 连到该具体锚点，避免链路与光缆分叉
    if (selectedTopoBranchPoint.value && ctx.value.portAnchors) {
      const anchorHits = raycaster.intersectObjects(ctx.value.portAnchors.children, false)
      if (anchorHits.length > 0 && anchorHits[0].object.userData.portAnchor) {
        const anchor = anchorHits[0].object.userData.portAnchor
        connectDeviceFromTopoBranch(anchor.deviceId, anchor.portId)
        return
      }
    }

    const hits = raycaster.intersectObjects(deviceGroup?.children || [], true)
    if (hits.length > 0) {
      let model = hits[0].object
      while (model && !model.userData.device) {
        model = model.parent
      }
      if (model && model.userData.device) {
        // 根据选中的分支点类型使用不同的连接函数
        if (selectedTopoBranchPoint.value) {
          connectDeviceFromTopoBranch(model.userData.device.id)
        } else if (selectedBranchPoint.value) {
          connectDeviceFromBranch(model.userData.device.id)
        }
      }
    }
    return
  }

  // ========== PNetLab 式端口连线交互 ==========

  // 检查是否处于连线态（更新橡皮筋）
  if (wiringState.value) {
    // 这是 mouseup 应该在另一个处理器中处理
    return
  }

  // 检查是否点击了端口锚点（开始连线）
  if (ctx.value.portAnchors) {
    const anchorHits = raycaster.intersectObjects(ctx.value.portAnchors.children, false)
    if (anchorHits.length > 0) {
      // 默认优先允许拖动设备；按住 Ctrl/Meta 再点击锚点才进入连线态
      // 这样在设备缩得很小时，锚点不会挡住设备拖拽
      if (e.ctrlKey || e.metaKey) {
        const sphere = anchorHits[0].object
        if (sphere.userData.portAnchor) {
          onPortAnchorMouseDown(sphere.userData.portAnchor)
          controls.enabled = false
          return
        }
      }
    }
  }

  // ========== 光纤主干交互 ==========
  if (fiberTrunkGroup) {
    const endpointSpheres = fiberTrunkGroup.children.filter(c => c.userData.trunkEndpoint)
    const epHits = raycaster.intersectObjects(endpointSpheres, false)

    if (epHits.length > 0) {
      const sphere = epHits[0].object
      const ep = sphere.userData.trunkEndpoint

      trunkEndpointDragState = {
        trunkId: ep.trunkId,
        type: ep.type,  // 'start' or 'end'
        startX: ep.x,
        startY: ep.y,
      }
      selectedTrunkEndpointSphere = sphere

      // 高亮端点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTrunkEndpointDragMove)
      renderer.domElement.addEventListener('mouseup', onTrunkEndpointDragEnd)
      return
    }
  }

  // 检查是否点击了分支点球（可拖动调整位置）- 新 topo 模型
  if (ctx.value.topoEdgesGroup) {
    const bpSpheres = ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoNode && c.userData.topoNode.junction_type === 'branch_point')
    if (bpSpheres.length > 0) {
      const bpHits = raycaster.intersectObjects(bpSpheres, false)
      if (bpHits.length > 0) {
        const sphere = bpHits[0].object
        const node = sphere.userData.topoNode

        branchPointDragState = {
          nodeId: node.id,
          startX: node.x_percent,
          startY: node.y_percent,
        }
        selectedBranchPointSphere = sphere

        // 高亮分支点球
        sphere.material.color.set(0x22d3ee)

        controls.enabled = false
        isDragging = false

        renderer.domElement.addEventListener('mousemove', onBranchPointDragMove)
        renderer.domElement.addEventListener('mouseup', onBranchPointDragEnd)
        return
      }
    }
  }

  // 检查是否点击了分支光缆拐点球
  if (branchLinkGroup) {
    const waypointSpheres = branchLinkGroup.children.filter(c => c.userData.branchLinkWaypoint)
    const wpHits = raycaster.intersectObjects(waypointSpheres, false)

    if (wpHits.length > 0) {
      const sphere = wpHits[0].object
      const wp = sphere.userData.branchLinkWaypoint

      branchLinkWaypointDragState = {
        linkId: wp.linkId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedBranchLinkWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onBranchLinkWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onBranchLinkWaypointDragEnd)
      return
    }
  }

  // 检查是否点击了 TopoEndpoint（主干起点终点）
  if (isEditMode.value && !branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const endpointSpheres = ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoEndpoint)
    const epHits = raycaster.intersectObjects(endpointSpheres, false)

    if (epHits.length > 0) {
      const sphere = epHits[0].object
      const ep = sphere.userData.topoEndpoint

      topoEndpointDragState = {
        nodeId: ep.nodeId,
        type: ep.type,
        startX: ep.x,
        startY: ep.y,
      }
      selectedTopoEndpointSphere = sphere

      // 高亮端点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTopoEndpointDragMove)
      renderer.domElement.addEventListener('mouseup', onTopoEndpointDragEnd)
      return
    }
  }

  // 检查是否点击了 TopoEdge 拐点球（优先于边管体）
  if (isEditMode.value && !branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const waypointSpheres = ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoEdgeWaypoint)
    const wpHits = raycaster.intersectObjects(waypointSpheres, false)

    if (wpHits.length > 0) {
      const sphere = wpHits[0].object
      const wp = sphere.userData.topoEdgeWaypoint

      topoEdgeWaypointDragState = {
        edgeId: wp.edgeId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedTopoEdgeWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTopoEdgeWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onTopoEdgeWaypointDragEnd)
      return
    }
  }

  // 检查是否点击了 TopoEdge（编辑模式下点击打开拐点对话框）
  if (isEditMode.value && !branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const edgeHits = raycaster.intersectObjects(ctx.value.topoEdgesGroup.children, false)
    if (edgeHits.length > 0) {
      const cylinder = edgeHits[0].object
      if (cylinder.userData.topoEdge) {
        // 找到对应的 TopoEdge 数据
        const edgeData = cylinder.userData.topoEdge
        const edge = topoEdges.value.find(e => e.id === edgeData.id)
        if (edge) {
          // 第一次点击：选中该线，仅显示其拐点手柄（避免多线重叠误操作）
          if (selectedTopoEdgeId.value !== edge.id) {
            selectedTopoEdgeId.value = edge.id
            builders.buildTopoEdges()
            return
          }
          // 再次点击已选中的线：打开拐点编辑对话框
          openTopoEdgeWaypointDialog(edge)
          return
        }
      }
    }
  }

  // 检查是否点击了主干拐点球（优先于主干管体）
  if (fiberTrunkGroup) {
    const trunkWaypointSpheres = fiberTrunkGroup.children.filter(c => c.userData.trunkWaypoint)
    const wpHits = raycaster.intersectObjects(trunkWaypointSpheres, false)

    if (wpHits.length > 0) {
      const sphere = wpHits[0].object
      const wp = sphere.userData.trunkWaypoint

      trunkWaypointDragState = {
        trunkId: wp.trunkId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedTrunkWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTrunkWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onTrunkWaypointDragEnd)
      return
    }
  }

  // 检查是否点击了主干光缆管体（添加分支点）- 需要进入分支点创建模式
  if (branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const topoEdgeHits = raycaster.intersectObjects(ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoEdge), false)
    if (topoEdgeHits.length > 0) {
      const hit = topoEdgeHits[0]
      const tube = hit.object
      const edgeData = tube.userData.topoEdge
      if (edgeData && edgeData.cableId) {
        // 直接使用射线与管体的交点坐标，而不是地面平面交点
        const worldPos = hit.point
        const x_percent = Math.max(0, Math.min(100, (worldPos.x / plan.real_width_m) * 100))
        const y_percent = Math.max(0, Math.min(100, (worldPos.z / plan.real_depth_m) * 100))
        // 使用新的 topo API 创建分支点
        addBranchPointOnTopoEdge(edgeData.cableId, { x: x_percent, y: y_percent })
        branchPointCreateMode.value = false  // 添加完成后退出模式
      }
      return
    }
  }

  // ========== 原有编辑交互 ==========

  // 先检查是否点击了拐点球
  if (linkLines) {
    const waypointSpheres = linkLines.children.filter(c => c.userData.waypoint)
    const waypointHits = raycaster.intersectObjects(waypointSpheres, false)

    if (waypointHits.length > 0) {
      const sphere = waypointHits[0].object
      const wp = sphere.userData.waypoint

      waypointDragState = {
        linkId: wp.linkId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onWaypointDragEnd)
      return
    }
  }

  // 检查设备点击
  const hits = raycaster.intersectObjects(deviceGroup?.children || [], true)

  if (hits.length > 0) {
    // 找到带 userData.device 的父级 Group
    let model = hits[0].object
    while (model && !model.userData.device) {
      model = model.parent
    }

    if (model && model.userData.device) {
      const device = model.userData.device
      const node = model.userData.node

      selectedDevice.value = device
      selectedNode.value = node
      selectedModel = model

      // 高亮选中设备
      model.traverse(child => {
        if (child.material) {
          child.material.emissive = EMISSIVE_ON
        }
      })

      // 设置拖动状态
      dragState.value = {
        nodeId: node.id,
        deviceId: device.id,
        deviceType: device.device_type,
        startClientX: e.clientX,
        startClientY: e.clientY,
      }

      // 暂停轨道控制（编辑模式下完全禁用）
      controls.enabled = false
      isDragging = false

      // 监听拖动
      renderer.domElement.addEventListener('mousemove', onDragMove)
      renderer.domElement.addEventListener('mouseup', onDragEnd)
    }
  } else if (selectedTopoEdgeId.value != null) {
    // 点击空白处：取消选中拓扑线，隐藏拐点手柄
    selectedTopoEdgeId.value = null
    builders.buildTopoEdges()
  }
}

// 拐点拖动处理
function onWaypointDragMove(e) {
  if (!waypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  waypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  waypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新拐点球位置
  if (selectedWaypointSphere) {
    const linkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002 + 2
    const w = percentToWorld(waypointDragState._lastX, waypointDragState._lastY, linkHeight)
    selectedWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

// 拐点拖动结束
async function onWaypointDragEnd(e) {
  if (!waypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { linkId, index, _lastX, _lastY } = waypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新拐点数据
      const link = links.value.find(l => l.id === linkId)
      if (link) {
        // waypoints 可能是字符串或已解析的数组
        let waypoints = []
        if (typeof link.waypoints === 'string') {
          waypoints = JSON.parse(link.waypoints) || []
        } else if (Array.isArray(link.waypoints)) {
          waypoints = link.waypoints
        }

        // 更新指定索引的拐点
        if (index < waypoints.length) {
          waypoints[index] = { x: Number(_lastX.toFixed(2)), y: Number(_lastY.toFixed(2)) }
        }

        const waypointsJson = JSON.stringify(waypoints)
        await axios.put(`/api/floor-plans/${currentPlanId.value}/links/${linkId}`, {
          waypoints: waypointsJson
        })

        // 更新本地数据
        link.waypoints = waypointsJson

        // 更新 userData
        if (selectedWaypointSphere) {
          selectedWaypointSphere.userData.waypoint.x = _lastX
          selectedWaypointSphere.userData.waypoint.y = _lastY
        }

        // 重建链路
        builders.disposeGroup('links')
        builders.buildLinks()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedWaypointSphere) {
    selectedWaypointSphere.material.color.set(0xffa116)
  }

  waypointDragState = null
  selectedWaypointSphere = null
  isDragging = false
}

// 主干拐点拖动处理
function onTrunkWaypointDragMove(e) {
  if (!trunkWaypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  trunkWaypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  trunkWaypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新主干拐点球位置
  if (selectedTrunkWaypointSphere) {
    const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const trunkRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.0015
    const w = percentToWorld(trunkWaypointDragState._lastX, trunkWaypointDragState._lastY, trunkHeight + trunkRadius * 3)
    selectedTrunkWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

// 主干拐点拖动结束
async function onTrunkWaypointDragEnd(e) {
  if (!trunkWaypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTrunkWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTrunkWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { trunkId, index, _lastX, _lastY } = trunkWaypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新主干拐点数据
      const trunk = fiberTrunks.value.find(t => t.id === trunkId)
      if (trunk) {
        // waypoints 可能是字符串或已解析的数组
        let waypoints = []
        if (typeof trunk.waypoints === 'string') {
          waypoints = JSON.parse(trunk.waypoints) || []
        } else if (Array.isArray(trunk.waypoints)) {
          waypoints = trunk.waypoints
        }

        // 更新指定索引的拐点
        if (index < waypoints.length) {
          waypoints[index] = { x: Number(_lastX.toFixed(2)), y: Number(_lastY.toFixed(2)) }
        }

        const waypointsJson = JSON.stringify(waypoints)
        await axios.put(`/api/floor-plans/${currentPlanId.value}/fiber-trunks/${trunkId}`, {
          waypoints: waypointsJson
        })

        // 更新本地数据
        trunk.waypoints = waypointsJson

        // 重新加载 topo 数据并重建渲染
        await loadTopoData()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新主干拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedTrunkWaypointSphere) {
    selectedTrunkWaypointSphere.material.color.set(0xffffff)
  }

  trunkWaypointDragState = null
  selectedTrunkWaypointSphere = null
  isDragging = false
}

// ========== TopoEdge 拐点球拖拽处理 ==========

let topoEdgeWaypointDragState = null
let selectedTopoEdgeWaypointSphere = null

// TopoEndpoint 拖拽状态
let topoEndpointDragState = null
let selectedTopoEndpointSphere = null

function onTopoEdgeWaypointDragMove(e) {
  if (!topoEdgeWaypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  topoEdgeWaypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  topoEdgeWaypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新拐点球位置
  if (selectedTopoEdgeWaypointSphere) {
    const edgeHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const w = percentToWorld(topoEdgeWaypointDragState._lastX, topoEdgeWaypointDragState._lastY, edgeHeight)
    selectedTopoEdgeWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

async function onTopoEdgeWaypointDragEnd(e) {
  if (!topoEdgeWaypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTopoEdgeWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTopoEdgeWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { edgeId, index, _lastX, _lastY } = topoEdgeWaypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新 TopoEdge 拐点数据
      const edge = topoEdges.value.find(e => e.id === edgeId)
      if (edge) {
        let waypoints = []
        if (typeof edge.waypoints === 'string') {
          waypoints = JSON.parse(edge.waypoints) || []
        } else if (Array.isArray(edge.waypoints)) {
          waypoints = [...edge.waypoints]  // 复制数组
        }

        // 更新指定索引的拐点
        if (index < waypoints.length) {
          waypoints[index] = { x: Number(_lastX.toFixed(2)), y: Number(_lastY.toFixed(2)) }
        }

        // 发送数组，不是 JSON 字符串
        await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-edges/${edgeId}`, {
          waypoints: waypoints
        })

        // 更新本地数据
        edge.waypoints = waypoints

        // 重建拓扑边
        builders.buildTopoEdges()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新 TopoEdge 拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedTopoEdgeWaypointSphere) {
    selectedTopoEdgeWaypointSphere.material.color.set(0xffffff)
  }

  topoEdgeWaypointDragState = null
  selectedTopoEdgeWaypointSphere = null
  isDragging = false
}

// ========== TopoEndpoint（主干起点终点）拖拽处理 ==========

function onTopoEndpointDragMove(e) {
  if (!topoEndpointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  topoEndpointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  topoEndpointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新端点球位置
  if (selectedTopoEndpointSphere) {
    const edgeHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const edgeRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
    const epHeight = edgeHeight + edgeRadius * 2
    const w = percentToWorld(topoEndpointDragState._lastX, topoEndpointDragState._lastY, epHeight)
    selectedTopoEndpointSphere.position.set(w.x, w.y, w.z)
  }
}

async function onTopoEndpointDragEnd(e) {
  if (!topoEndpointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTopoEndpointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTopoEndpointDragEnd)
  ctx.value.controls.enabled = true

  const { nodeId, type, _lastX, _lastY } = topoEndpointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新 TopoNode 位置
      await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-nodes/${nodeId}`, {
        x_percent: _lastX,
        y_percent: _lastY,
      })

      // 更新本地数据
      const node = topoNodes.value.find(n => n.id === nodeId)
      if (node) {
        node.x_percent = _lastX
        node.y_percent = _lastY
      }

      // 重建拓扑边渲染
      builders.buildTopoEdges()

      ElMessage.success(t('msgSaveSuccess'))
    } catch (err) {
      console.error('更新 TopoEndpoint 位置失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复端点球颜色
  if (selectedTopoEndpointSphere) {
    const isStart = selectedTopoEndpointSphere.userData.topoEndpoint.type === 'start'
    selectedTopoEndpointSphere.material.color.set(isStart ? 0x22c55e : 0xef4444)
  }

  topoEndpointDragState = null
  selectedTopoEndpointSphere = null
  isDragging = false
}

// ========== 主干端点拖动处理（旧系统） ==========
function onTrunkEndpointDragMove(e) {
  if (!trunkEndpointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  trunkEndpointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  trunkEndpointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新端点球位置
  if (selectedTrunkEndpointSphere) {
    const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const trunkRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.0015
    const w = percentToWorld(trunkEndpointDragState._lastX, trunkEndpointDragState._lastY, trunkHeight + trunkRadius * 2)
    selectedTrunkEndpointSphere.position.set(w.x, w.y, w.z)
  }
}

// 主干端点拖动结束
async function onTrunkEndpointDragEnd(e) {
  if (!trunkEndpointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTrunkEndpointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTrunkEndpointDragEnd)
  ctx.value.controls.enabled = true

  const { trunkId, type, _lastX, _lastY } = trunkEndpointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      const trunk = fiberTrunks.value.find(t => t.id === trunkId)
      if (trunk) {
        // 更新起点或终点坐标
        const updateData = {}
        if (type === 'start') {
          updateData.start_x_percent = Number(_lastX.toFixed(2))
          updateData.start_y_percent = Number(_lastY.toFixed(2))

          // 检查是否靠近某个设备（起点可以关联核心交换机）
          const nearbyNode = findNearbyDevice(_lastX, _lastY, 5)  // 5% 范围内
          if (nearbyNode) {
            updateData.start_device_id = nearbyNode.device_id
            ElMessage.success(`${t('connectedToDevice')}: ${nearbyNode.device_name || nearbyNode.name}`)
          }
        } else {
          updateData.end_x_percent = Number(_lastX.toFixed(2))
          updateData.end_y_percent = Number(_lastY.toFixed(2))
        }

        await axios.put(`/api/floor-plans/${currentPlanId.value}/fiber-trunks/${trunkId}`, updateData)

        // 更新本地数据
        if (type === 'start') {
          trunk.start_x_percent = Number(_lastX.toFixed(2))
          trunk.start_y_percent = Number(_lastY.toFixed(2))
          if (updateData.start_device_id) {
            trunk.start_device_id = updateData.start_device_id
          }
        } else {
          trunk.end_x_percent = Number(_lastX.toFixed(2))
          trunk.end_y_percent = Number(_lastY.toFixed(2))
        }

        // 重新加载 topo 数据并重建渲染
        await loadTopoData()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新主干端点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复端点球颜色
  if (selectedTrunkEndpointSphere) {
    const ep = selectedTrunkEndpointSphere.userData.trunkEndpoint
    selectedTrunkEndpointSphere.material.color.set(ep.type === 'start' ? 0x22c55e : 0xef4444)
  }

  trunkEndpointDragState = null
  selectedTrunkEndpointSphere = null
  isDragging = false
}

// 分支点拖动处理
function onBranchPointDragMove(e) {
  if (!branchPointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  branchPointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  branchPointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新分支点球位置
  if (selectedBranchPointSphere) {
    const bpHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002 + 1
    const w = percentToWorld(branchPointDragState._lastX, branchPointDragState._lastY, bpHeight)
    selectedBranchPointSphere.position.set(w.x, w.y, w.z)
  }
}

// 分支点拖动结束
async function onBranchPointDragEnd(e) {
  if (!branchPointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onBranchPointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onBranchPointDragEnd)
  ctx.value.controls.enabled = true

  const { nodeId, _lastX, _lastY } = branchPointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 使用新的 topo API 更新节点位置
      await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-nodes/${nodeId}`, {
        x_percent: Number(_lastX.toFixed(2)),
        y_percent: Number(_lastY.toFixed(2)),
      })

      // 重新加载 topo 数据并重建渲染
      await loadFiberData()

      ElMessage.success(t('msgSaveSuccess'))
    } catch (err) {
      console.error('更新分支点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复分支点球颜色
  if (selectedBranchPointSphere) {
    selectedBranchPointSphere.material.color.set(0xfbbf24)  // 黄色
  }

  branchPointDragState = null
  selectedBranchPointSphere = null
  isDragging = false
}

// 分支光缆拐点拖动处理
function onBranchLinkWaypointDragMove(e) {
  if (!branchLinkWaypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  branchLinkWaypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  branchLinkWaypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新拐点球位置
  if (selectedBranchLinkWaypointSphere) {
    const branchHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
    const branchRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
    const w = percentToWorld(branchLinkWaypointDragState._lastX, branchLinkWaypointDragState._lastY, branchHeight + branchRadius * 3)
    selectedBranchLinkWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

// 分支光缆拐点拖动结束
async function onBranchLinkWaypointDragEnd(e) {
  if (!branchLinkWaypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onBranchLinkWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onBranchLinkWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { linkId, index, _lastX, _lastY } = branchLinkWaypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      const link = fiberBranchLinks.value.find(l => l.id === linkId)
      if (link) {
        // 解析拐点
        let waypoints = []
        if (typeof link.waypoints === 'string') {
          waypoints = JSON.parse(link.waypoints) || []
        } else if (Array.isArray(link.waypoints)) {
          waypoints = link.waypoints
        }

        // 更新指定索引的拐点
        if (index < waypoints.length) {
          waypoints[index] = { x: Number(_lastX.toFixed(2)), y: Number(_lastY.toFixed(2)) }
        }

        const waypointsJson = JSON.stringify(waypoints)
        await axios.put(`/api/floor-plans/${currentPlanId.value}/links/${linkId}`, {
          waypoints: waypointsJson
        })

        // 更新本地数据
        link.waypoints = waypointsJson

        // 更新 userData
        // 重新加载 topo 数据并重建渲染
        await loadTopoData()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新分支光缆拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedBranchLinkWaypointSphere) {
    selectedBranchLinkWaypointSphere.material.color.set(0xffffff)
  }

  branchLinkWaypointDragState = null
  selectedBranchLinkWaypointSphere = null
  isDragging = false
}

// 查找附近的设备节点
function findNearbyDevice(x_percent, y_percent, threshold) {
  for (const node of nodes.value) {
    const dx = Math.abs(node.x_percent - x_percent)
    const dy = Math.abs(node.y_percent - y_percent)
    if (dx < threshold && dy < threshold) {
      // 找到对应的设备
      const device = devices.value.find(d => d.id === node.device_id)
      return {
        device_id: node.device_id,
        device_name: device ? device.name : null,
        name: device ? device.name : t('monitor3dDeviceFallbackName', { id: node.device_id })
      }
    }
  }
  return null
}

// 查找附近的核心交换机节点（用于主干起点自动关联核心）
function findNearbyCoreDevice(x_percent, y_percent, threshold) {
  for (const node of nodes.value) {
    const dx = Math.abs(node.x_percent - x_percent)
    const dy = Math.abs(node.y_percent - y_percent)
    if (dx < threshold && dy < threshold) {
      const device = devices.value.find(d => d.id === node.device_id)
      if (device && device.device_type === 'core_switch') {
        return {
          device_id: node.device_id,
          device_name: device.name,
        }
      }
    }
  }
  return null
}

// 查看模式点击选中
// ===== 悬浮 HUD 全息玻璃面板 =====
let hudObj = null          // CSS2DObject
let hudEl = null           // HUD 根 DOM
let hudDeviceId = null     // 当前悬浮设备 id（避免重复刷新）
let hudPinnedDeviceId = null
let hudAutoHideTimer = null

// SNMP 上行接口数据缓存：deviceId -> { ts, items }（Map 实例在 sceneState 共享，HUD 与 WS handler 复用）
const SNMP_IFACE_TTL = 8000   // 缓存有效期（ms），自带节流避免重复请求
const SNMP_TRAFFIC_TTL = 12000

// 拉取设备被监控接口（含上行口 oper_status 与实时流量）
async function fetchDeviceInterfaces(deviceId, force = false) {
  if (deviceId == null) return
  const cached = sceneState.snmpIfaceCache.get(deviceId)
  if (!force && cached && (Date.now() - cached.ts) < SNMP_IFACE_TTL) return
  // 先占位（保留旧 items），避免并发重复请求
  sceneState.snmpIfaceCache.set(deviceId, { ts: Date.now(), items: cached?.items || [] })
  try {
    const res = await axios.get(`/api/devices/${deviceId}/interfaces`, { params: { monitored_only: true } })
    const items = res.data?.items || []
    sceneState.snmpIfaceCache.set(deviceId, { ts: Date.now(), items })
    fetchUplinkTrafficSamples(deviceId, true)
    // 数据回来后若仍悬浮该设备，立即刷新 HUD
    if (hudDeviceId === deviceId) {
      const d = devices.value.find(x => x.id === deviceId)
      if (d) updateHudContent(d)
    }
  } catch (e) {
    // 静默失败（设备未配置 SNMP / 无接口等），保留旧缓存
    sceneState.snmpIfaceCache.set(deviceId, { ts: Date.now(), items: cached?.items || [] })
  }
}

// 取设备已标记为上行口的被监控接口
function getUplinkInterfaces(device) {
  if (!device) return []
  const cached = sceneState.snmpIfaceCache.get(device.id)
  if (!cached) return []
  return (cached.items || []).filter(i => i.is_uplink)
}

function getPrimaryTrafficInterface(device) {
  if (!device) return null
  const uplinks = getUplinkInterfaces(device)
  return uplinks.length > 0 ? uplinks[0] : null
}

// 取设备上行口的对端信息（CDP/LLDP 邻居发现结果），优先取已匹配到系统内设备的那条
function getPeerInfo(device) {
  const uplinks = getUplinkInterfaces(device)
  if (!uplinks.length) return null
  const withPeer = uplinks.filter(i => i.peer_device_name || i.peer_ip)
  if (!withPeer.length) return null
  const best = withPeer.find(i => i.peer_device_id) || withPeer[0]
  return {
    name: best.peer_device_name || best.peer_ip || '—',
    port: best.peer_if_name || '',
    source: best.neighbor_source || '',
    matched: !!best.peer_device_id,
  }
}

async function fetchUplinkTrafficSamples(deviceId, force = false) {
  if (deviceId == null) return
  const device = devices.value.find(x => x.id === deviceId)
  const iface = getPrimaryTrafficInterface(device)
  if (!iface?.if_index) return

  const cacheKey = `${deviceId}:${iface.if_index}`
  const cached = sceneState.snmpTrafficCache.get(cacheKey)
  if (!force && cached && (Date.now() - cached.ts) < SNMP_TRAFFIC_TTL) return

  sceneState.snmpTrafficCache.set(cacheKey, { ts: Date.now(), ifIndex: iface.if_index, samples: cached?.samples || [] })
  try {
    const res = await axios.get(`/api/devices/${deviceId}/interfaces/${iface.if_index}/traffic`, { params: { limit: 24 } })
    const samples = res.data?.samples || []
    sceneState.snmpTrafficCache.set(cacheKey, { ts: Date.now(), ifIndex: iface.if_index, samples })
    if (hudDeviceId === deviceId) {
      const d = devices.value.find(x => x.id === deviceId)
      if (d) updateHudContent(d)
    }
  } catch (e) {
    sceneState.snmpTrafficCache.set(cacheKey, { ts: Date.now(), ifIndex: iface.if_index, samples: cached?.samples || [] })
  }
}

// 格式化速率
function formatBps(bps) {
  if (bps == null) return '—'
  const v = Number(bps)
  if (!isFinite(v)) return '—'
  if (v >= 1e9) return (v / 1e9).toFixed(2) + ' Gbps'
  if (v >= 1e6) return (v / 1e6).toFixed(2) + ' Mbps'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + ' Kbps'
  return v.toFixed(0) + ' bps'
}

// 汇总上行口实时流量
function getUplinkTraffic(device) {
  const uplinks = getUplinkInterfaces(device)
  if (uplinks.length === 0) return null
  let inSum = 0, outSum = 0, hasData = false
  uplinks.forEach(i => {
    if (i.last_in_bps != null) { inSum += Number(i.last_in_bps); hasData = true }
    if (i.last_out_bps != null) { outSum += Number(i.last_out_bps); hasData = true }
  })
  if (!hasData) return null
  return { inBps: inSum, outBps: outSum }
}

function getUplinkTrafficSamples(device) {
  const iface = getPrimaryTrafficInterface(device)
  if (!device || !iface?.if_index) return []
  const cached = sceneState.snmpTrafficCache.get(`${device.id}:${iface.if_index}`)
  return cached?.samples || []
}

function buildSparklinePath(values, width, height, padding = 3) {
  if (!values.length) return ''
  if (values.length === 1) {
    const y = height / 2
    return `M ${padding} ${y} L ${width - padding} ${y}`
  }
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const span = Math.max(max - min, 1)
  return values.map((value, index) => {
    const x = padding + (index / (values.length - 1)) * (width - padding * 2)
    const y = height - padding - ((value - min) / span) * (height - padding * 2)
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}

function getUplinkTrendSvg(device) {
  if (getUplinkInterfaces(device).length === 0) return ''
  const samples = getUplinkTrafficSamples(device)
  if (!samples.length) return ''

  const inValues = samples.map(s => Number(s.in_bps || 0))
  const outValues = samples.map(s => Number(s.out_bps || 0))
  const width = 156
  const height = 36
  const inPath = buildSparklinePath(inValues, width, height)
  const outPath = buildSparklinePath(outValues, width, height)
  if (!inPath && !outPath) return ''

  return `
    <div class="hud-trend-wrap">
      <svg class="hud-spark" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
        <path d="M 2 ${height - 2} L ${width - 2} ${height - 2}" class="grid" />
        ${inPath ? `<path d="${inPath}" class="in" />` : ''}
        ${outPath ? `<path d="${outPath}" class="out" />` : ''}
      </svg>
      <div class="hud-trend-legend">
        <span class="in">↓ In</span>
        <span class="out">↑ Out</span>
      </div>
    </div>
  `
}

// 计算设备上行链路状态（优先 SNMP 上行口真实状态，回退寻路路径/手绘链路）
function getUplinkStatus(device) {
  if (!device) return { text: '—', cls: 'unknown' }
  if (isDeviceOffline(device)) return { text: t('hudUplinkDown'), cls: 'offline' }

  // 优先依据：SNMP 监控的上行接口真实 oper_status
  const uplinks = getUplinkInterfaces(device)
  if (uplinks.length > 0) {
    const downs = uplinks.filter(i => i.oper_status === 'down').length
    const ups = uplinks.filter(i => i.oper_status === 'up').length
    if (downs > 0 && ups === 0) return { text: t('hudUplinkDown'), cls: 'offline' }
    if (downs > 0) return { text: t('hudUplinkDegraded'), cls: 'maintenance' }
    if (ups > 0) return { text: t('hudUplinkNormal'), cls: 'online' }
    // 全部 unknown：落到下方路径判断
  }

  // 次依据：设备到核心的寻路路径（与大屏绿色数据链路同源）
  const path = devicePaths.value?.[device.id] ?? devicePaths.value?.[String(device.id)]
  if (path) {
    const reachable = Array.isArray(path) ? path.length >= 2 : path.reachable !== false
    return reachable
      ? { text: t('hudUplinkNormal'), cls: 'online' }
      : { text: t('hudUplinkDegraded'), cls: 'maintenance' }
  }

  // 回退：手动绘制的链路（编辑模式下使用）
  const touched = links.value.filter(l => {
    const fromNode = nodes.value.find(n => n.id === l.from_node_id || n.device_id === l.from)
    const toNode = nodes.value.find(n => n.id === l.to_node_id || n.device_id === l.to)
    return (fromNode && fromNode.device_id === device.id) ||
           (toNode && toNode.device_id === device.id)
  })
  if (touched.length > 0) {
    return touched.some(l => l.status === 'broken')
      ? { text: t('hudUplinkDegraded'), cls: 'maintenance' }
      : { text: t('hudUplinkNormal'), cls: 'online' }
  }
  return { text: t('hudUplinkNone'), cls: 'unknown' }
}

// 统计设备当前告警数（离线计 1，相连故障链路各计 1，SNMP 上行口 down 各计 1）
function getDeviceAlarmCount(device) {
  if (!device) return 0
  let count = isDeviceOffline(device) ? 1 : 0
  links.value.forEach(l => {
    if (l.status !== 'broken') return
    const fromNode = nodes.value.find(n => n.id === l.from_node_id || n.device_id === l.from)
    const toNode = nodes.value.find(n => n.id === l.to_node_id || n.device_id === l.to)
    if ((fromNode && fromNode.device_id === device.id) ||
        (toNode && toNode.device_id === device.id)) count++
  })
  // SNMP 上行口 down 计入告警
  count += getUplinkInterfaces(device).filter(i => i.oper_status === 'down').length
  return count
}

function formatCheckTime(ts) {
  if (!ts) return '—'
  return formatDateTime(ts)
}

function getRecommendationSummary(text) {
  if (!text) return '—'
  const firstLine = String(text).split('\n').map(item => item.trim()).find(Boolean)
  if (!firstLine) return '—'
  return firstLine.length > 42 ? `${firstLine.slice(0, 42)}...` : firstLine
}

// 创建 HUD 面板（懒加载，挂到场景，默认隐藏）
function ensureHudPanel() {
  if (hudObj) return
  const { scene } = ctx.value
  if (!scene) return
  hudEl = document.createElement('div')
  hudEl.className = 'device-hud'
  // CSS 通过 opacity:0 + visibility:hidden 控制隐藏，无需设置 display
  hudObj = new CSS2DObject(hudEl)
  hudObj.name = 'device-hud'
  hudObj.visible = false
  scene.add(hudObj)
}

function hideHudPanel() {
  if (hudObj) hudObj.visible = false
  if (hudEl) {
    hudEl.classList.remove('visible')
    hudEl.style.display = 'none'
  }
}

function positionHudForDevice(device) {
  if (!hudObj || !device) return false
  const { deviceGroup } = ctx.value
  const model = deviceGroup?.children?.find(child => child?.userData?.device?.id === device.id)
  if (model) {
    const base = getDeviceBaseSize(device.device_type)
    const topY = (model.position.y || 0) + base * 1.6
    hudObj.position.set(model.position.x, topY, model.position.z)
    return true
  }

  const node = nodes.value.find(n => n.device_id === device.id)
  if (!node) return false
  const world = percentToWorld(node.x_percent, node.y_percent, 0)
  const base = getDeviceBaseSize(device.device_type)
  hudObj.position.set(world.x, base * 1.6, world.z)
  return true
}

function showHudForDevice(device, durationMs = 0) {
  if (!device || isEditMode.value) return
  ensureHudPanel()
  if (!hudObj || !hudEl) return

  const { camera, labelRenderer, scene } = ctx.value
  hudDeviceId = device.id
  updateHudContent(device)
  if (!positionHudForDevice(device)) return

  hudObj.visible = true
  hudEl.style.display = 'block'
  if (labelRenderer && scene && camera) {
    labelRenderer.render(scene, camera)
  }
  requestAnimationFrame(() => {
    if (hudEl) hudEl.classList.add('visible')
  })

  if (hudAutoHideTimer) {
    clearTimeout(hudAutoHideTimer)
    hudAutoHideTimer = null
  }
  if (durationMs > 0) {
    hudPinnedDeviceId = device.id
    hudAutoHideTimer = setTimeout(() => {
      if (hudPinnedDeviceId === device.id) {
        hudPinnedDeviceId = null
        hideHudPanel()
      }
    }, durationMs)
  }
}

// 刷新 HUD 内容
function updateHudContent(device) {
  if (!hudEl) return
  const status = deviceStatus(device)
  const statusText = getStatusLabelI18n(status)
  const latency = device.reachability_latency_ms != null
    ? `${device.reachability_latency_ms} ms` : '—'
  const uplink = getUplinkStatus(device)
  const alarms = getDeviceAlarmCount(device)
  const traffic = getUplinkTraffic(device)
  const trendSvg = getUplinkTrendSvg(device)
  const peer = getPeerInfo(device)
  const activeFault = getActiveFaultForDevice(device)

  hudEl.innerHTML = `
    <div class="hud-scan"></div>
    <div class="hud-head">
      <span class="hud-dot ${status}"></span>
      <span class="hud-name">${device.name || '—'}</span>
    </div>
    <div class="hud-sub">${getDeviceTypeLabelI18n(device.device_type)} · ${device.ip || '—'}</div>
    <div class="hud-grid">
      <div class="hud-k">${t('hudStatus')}</div>
      <div class="hud-v ${status}">${statusText}</div>
      <div class="hud-k">${t('hudLatency')}</div>
      <div class="hud-v">${latency}</div>
      <div class="hud-k">${t('hudUplink')}</div>
      <div class="hud-v ${uplink.cls}">${uplink.text}</div>
      ${peer ? `
      <div class="hud-k">${t('hudPeer')}</div>
      <div class="hud-v hud-peer ${peer.matched ? 'online' : ''}">${peer.name}${peer.port ? ` <span class="hud-peer-port">${peer.port}</span>` : ''}${peer.source ? ` <span class="hud-peer-src">${peer.source.toUpperCase()}</span>` : ''}</div>
      ` : ''}
      ${traffic ? `
      <div class="hud-k">${t('hudTraffic')}</div>
      <div class="hud-v hud-traffic">↓ ${formatBps(traffic.inBps)}&nbsp;&nbsp;↑ ${formatBps(traffic.outBps)}</div>
      ` : ''}
      ${trendSvg ? `
      <div class="hud-k">Trend</div>
      <div class="hud-v hud-v-trend">${trendSvg}</div>
      ` : ''}
      <div class="hud-k">${t('hudAlarm')}</div>
      <div class="hud-v ${alarms > 0 ? 'offline' : 'online'}">${alarms}</div>
      <div class="hud-k">${t('hudCheck')}</div>
      <div class="hud-v hud-time">${formatCheckTime(device.last_reachability_check)}</div>
    </div>
    ${activeFault ? `
    <div class="hud-incident">
      <div class="hud-incident-head">
        <span>${activeFault.fault_no || 'INC'}</span>
        <b class="sev-${activeFault.severity || 'minor'}">${activeFault.severity || '-'}</b>
      </div>
      <div class="hud-incident-row">${t('hudStatus')}：${activeFault.status_label || activeFault.status || '-'}</div>
      <div class="hud-incident-row">${t('faultOwner')}：${activeFault.assigned_to || '-'}</div>
      <div class="hud-incident-row">${t('complianceRecommendation')}：${getRecommendationSummary(activeFault.recommendation)}</div>
    </div>
    ` : ''}
  `
}

// 悬浮检测：在设备上方显示 HUD，移开则隐藏
let lastHoverCheck = 0
let lastHudRefresh = 0
// 悬浮时定期刷新 HUD（上行口状态/流量），自带节流
function refreshHoveredHud() {
  if (hudDeviceId == null || !hudObj || !hudObj.visible) return
  const now = performance.now()
  if (now - lastHudRefresh < 2000) return   // 每 2s 刷新一次
  lastHudRefresh = now
  fetchDeviceInterfaces(hudDeviceId)        // 自带 8s TTL 节流
  fetchUplinkTrafficSamples(hudDeviceId)
  const d = devices.value.find(x => x.id === hudDeviceId)
  if (d) updateHudContent(d)
}
function onCanvasMouseMove(e) {
  if (isEditMode.value || isDragging || dragState.value) {
    hideHudPanel()
    hudDeviceId = null
    hudPinnedDeviceId = null
    return
  }
  const now = performance.now()
  if (now - lastHoverCheck < 60) return   // 节流
  lastHoverCheck = now

  const { camera, renderer, deviceGroup } = ctx.value
  if (!camera || !deviceGroup) return

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)

  const hits = raycaster.intersectObjects(deviceGroup.children, true)
  let model = hits.length ? hits[0].object : null
  while (model && !model.userData.device) model = model.parent

  if (model && model.userData.device) {
    const device = model.userData.device
    if (hudDeviceId !== device.id) {
      fetchDeviceInterfaces(device.id)   // 异步拉取 SNMP 上行口状态/流量
    }
    hudPinnedDeviceId = null
    showHudForDevice(device)
    renderer.domElement.style.cursor = 'pointer'
  } else {
    if (!hudPinnedDeviceId) {
      hudDeviceId = null
      hideHudPanel()
    }
    renderer.domElement.style.cursor = ''
  }
}

function onCanvasClick(e) {
  // 如果刚完成拖动，不处理点击
  if (isDragging) return
  if (isEditMode.value) return

  const { camera, renderer, deviceGroup } = ctx.value

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  const hits = raycaster.intersectObjects(deviceGroup?.children || [], true)

  // 清除之前的高亮
  if (selectedModel) {
    selectedModel.traverse(child => {
      if (child.material) {
        child.material.emissive = EMISSIVE_OFF
      }
    })
  }

  if (hits.length > 0) {
    // 找到带 userData.device 的父级 Group
    let model = hits[0].object
    while (model && !model.userData.device) {
      model = model.parent
    }

    if (model && model.userData.device) {
      const device = model.userData.device
      const node = model.userData.node

      selectedDevice.value = device
      selectedNode.value = node
      selectedModel = model

      // 高亮选中设备
      model.traverse(child => {
        if (child.material) {
          child.material.emissive = EMISSIVE_ON
        }
      })

      ElMessage.success(`${t('selected')}: ${device.name}`)

      // 相机聚焦到设备
      if (node) {
        const w = percentToWorld(node.x_percent, node.y_percent, 0)
        const ref = Math.min(plan.real_width_m, plan.real_depth_m)
        const lookAtHeight = ref * 0.03
        ctx.value.controls.target.set(w.x, lookAtHeight, w.z)
      }
    }
  } else {
    selectedDevice.value = null
    selectedNode.value = null
    selectedModel = null
  }
}

// 拖动处理（独立 Group 版本）
function onDragMove(e) {
  if (!dragState.value) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  dragState.value._lastX = pos.x_percent
  dragState.value._lastY = pos.y_percent

  // 计算基于底图尺寸的高度
  const deviceType = dragState.value.deviceType || 'switch'
  const base = getDeviceBaseSize(deviceType)
  const elevation = base * 0.5  // 设备离地高度
  const labelHeight = elevation + base * 1.1  // 标签在设备上方

  // 实时更新标签位置（在设备上方）
  const label = ctx.value.labels?.children.find(l => l.userData.deviceId === dragState.value.deviceId)
  if (label) {
    const w = percentToWorld(pos.x_percent, pos.y_percent, labelHeight)
    label.position.set(w.x, w.y, w.z)
  }

  // 实时更新设备模型位置
  if (selectedModel) {
    const w = percentToWorld(pos.x_percent, pos.y_percent, elevation)
    selectedModel.position.set(w.x, w.y, w.z)
  }
}

async function onDragEnd(e) {
  if (!dragState.value) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onDragEnd)
  ctx.value.controls.enabled = true

  const { nodeId, _lastX, _lastY } = dragState.value

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      await axios.put(`/api/floor-plans/${currentPlanId.value}/nodes/${nodeId}`, {
        x_percent: Number(_lastX.toFixed(2)),
        y_percent: Number(_lastY.toFixed(2)),
      })
      ElMessage.success(t('msgSaveSuccess'))

      // 更新本地nodes数据（不重建场景，保持选中状态）
      const node = nodes.value.find(n => n.id === nodeId)
      if (node) {
        node.x_percent = Number(_lastX.toFixed(2))
        node.y_percent = Number(_lastY.toFixed(2))
        // 同步 userData
        if (selectedModel && selectedModel.userData.node) {
          selectedModel.userData.node = { ...node }
        }
      }

      // 重建旧链路（兼容遗留数据）
      builders.disposeGroup('links')
      builders.buildLinks()

      // 同步重建 topo 图模型连线，避免设备拖动后需刷新页面才更新
      await loadFiberData()
      if (isEditMode.value) {
        builders.buildPortAnchors()
      }

      // 清除高亮
      if (selectedModel) {
        selectedModel.traverse(child => {
          if (child.material) {
            child.material.emissive = EMISSIVE_OFF
          }
        })
      }

    } catch (err) {
      console.error('更新节点位置失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  dragState.value = null
  isDragging = false
}

// ========== PNetLab 连线态鼠标处理器 ==========

function onWiringMouseMove(e) {
  if (!wiringState.value) return

  const { camera, renderer } = ctx.value
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // 计算鼠标在世界坐标中的位置（投射到平面）
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -Math.min(plan.real_width_m, plan.real_depth_m) * 0.003)
  const mouseWorld = new THREE.Vector3()
  raycaster.ray.intersectPlane(plane, mouseWorld)

  updateRubberBandLine(mouseWorld)
}

function onWiringMouseUp(e) {
  if (!wiringState.value) return

  window.removeEventListener('mousemove', onWiringMouseMove)
  window.removeEventListener('mouseup', onWiringMouseUp)
  ctx.value.controls.enabled = true

  const { camera, renderer } = ctx.value
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // 检查是否点击了另一个端口锚点
  if (ctx.value.portAnchors) {
    const anchorHits = raycaster.intersectObjects(ctx.value.portAnchors.children, false)
    if (anchorHits.length > 0) {
      const sphere = anchorHits[0].object
      if (sphere.userData.portAnchor && sphere.userData.portAnchor.deviceId !== wiringState.value.fromDeviceId) {
        finishWiring(sphere.userData.portAnchor)
        return
      }
    }
  }

  // 没有点击到目标锚点，取消连线
  cancelWiring()
}

  // 语言切换时刷新当前悬浮的 HUD 文案（父 watch(currentLang) 调用）
  function refreshCurrentHud() {
    if (hudDeviceId != null && hudEl && hudObj && hudObj.visible) {
      const d = devices.value.find(x => x.id === hudDeviceId)
      if (d) updateHudContent(d)
    }
  }

  // 设备可达性变化时若正悬浮该设备则刷新 HUD（父 WS handler 调用）
  function refreshHudForDevice(device) {
    if (hudDeviceId === device.id) updateHudContent(device)
  }

  // 画布交互监听接线（9c：wheel/click/mousemove/mousedown；onDragMove/onDragEnd 在拖拽中动态挂接）
  function attachSceneListeners(domElement) {
    if (!domElement) return
    domElement.addEventListener('wheel', handleWheel, { passive: false })
    domElement.addEventListener('click', onCanvasClick)
    domElement.addEventListener('mousemove', onCanvasMouseMove)
    domElement.addEventListener('mousedown', onCanvasMouseDown)
  }

  function detachSceneListeners(domElement) {
    if (!domElement) return
    domElement.removeEventListener('wheel', handleWheel)
    domElement.removeEventListener('click', onCanvasClick)
    domElement.removeEventListener('mousedown', onCanvasMouseDown)
    domElement.removeEventListener('mousemove', onCanvasMouseMove)
    domElement.removeEventListener('mousemove', onDragMove)
    domElement.removeEventListener('mouseup', onDragEnd)
  }

  function dispose() {
    if (hudAutoHideTimer) {
      clearTimeout(hudAutoHideTimer)
      hudAutoHideTimer = null
    }
    // 连线拖拽可能在卸载时进行中，直接移除其 window 监听（不只依赖 cancelWiring）
    window.removeEventListener('mousemove', onWiringMouseMove)
    window.removeEventListener('mouseup', onWiringMouseUp)
    detachSceneListeners(ctx.value.renderer?.domElement)
    // 释放 HUD（置于 three.dispose 之后：ctx 仍持有已分离的 domElement/场景引用）
    if (hudObj) {
      ctx.value.scene?.remove(hudObj)
      hudObj = null
      hudEl = null
      hudDeviceId = null
    }
  }

  return {
    updateDeviceScale, screenToPercent, findNearbyCoreDevice, cancelWiring,
    fetchDeviceInterfaces, fetchUplinkTrafficSamples, showHudForDevice,
    updateHudContent, refreshHudForDevice,
    refreshHoveredHud, refreshCurrentHud,
    attachSceneListeners, detachSceneListeners, dispose,
  }
}
