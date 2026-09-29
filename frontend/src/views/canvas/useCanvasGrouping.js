import { i18n } from '../../i18n/index'
import { computed, ref } from 'vue'

const { t } = i18n.global

export function getGroupFrameStyle(nodeIds, { findNode, viewport, assetsVisible }) {
  const flowNodes = nodeIds.map((id) => findNode(id)).filter(Boolean)
  if (flowNodes.length < 2) return {}

  const zoom = viewport.value.zoom
  const left = Math.min(...flowNodes.map((node) => node.computedPosition.x))
  const top = Math.min(...flowNodes.map((node) => node.computedPosition.y))
  const right = Math.max(...flowNodes.map((node) => node.computedPosition.x + node.dimensions.width))
  const bottom = Math.max(...flowNodes.map((node) => node.computedPosition.y + node.dimensions.height))
  return {
    left: `${(assetsVisible.value ? 292 : 0) + viewport.value.x + left * zoom - 28}px`,
    top: `${viewport.value.y + top * zoom - 32}px`,
    width: `${(right - left) * zoom + 56}px`,
    height: `${(bottom - top) * zoom + 46}px`,
  }
}

export function useCanvasGrouping({
  store,
  nodes,
  groups,
  viewport,
  assetsVisible,
  contextMenu,
  pointerMode,
  canvasTool,
  findNode,
  fitView,
  setCenter,
  getPanelHeight,
  removeSelectedElements,
  addSelectedNodes,
  confirm,
}) {
  const activeGroupId = ref(null)
  const groupDrag = ref(null)
  let nodeDragCopy = null
  const selectedNodes = computed(() => nodes.value.filter((node) => node.selected))
  const selectedContainsWorkflow = computed(() => selectedNodes.value.some((node) => node.data?.workflowId))
  const selectedNode = computed(() => selectedNodes.value.length === 1 ? selectedNodes.value[0] : null)
  const selectedGroup = computed(() => groups.value.find((group) => group.id === activeGroupId.value)
    || groups.value.find((group) => group.nodeIds.length === selectedNodes.value.length
      && group.nodeIds.every((id) => selectedNodes.value.some((node) => node.id === id))))
  const selectedPartialGroup = computed(() => groups.value.find((group) => selectedNodes.value.length > 1
    && group.nodeIds.length > selectedNodes.value.length
    && selectedNodes.value.every((node) => group.nodeIds.includes(node.id))))
  const contextNodeIds = computed(() => contextMenu.value?.nodeIds || [])
  const contextWorkflowNodes = computed(() => nodes.value.filter((node) => contextNodeIds.value.includes(node.id) && node.data?.workflowId))
  const contextContainsWorkflow = computed(() => contextWorkflowNodes.value.length > 0)
  const contextWorkflowRoot = computed(() => contextNodeIds.value.length === 1 && contextWorkflowNodes.value[0]?.data.workflowRoot
    ? contextWorkflowNodes.value[0]
    : null)
  const contextCompleteGroup = computed(() => groups.value.find((group) => contextNodeIds.value.length > 1
    && group.nodeIds.length === contextNodeIds.value.length
    && group.nodeIds.every((id) => contextNodeIds.value.includes(id))))
  const contextPartialGroup = computed(() => groups.value.find((group) => contextNodeIds.value.length > 1
    && group.nodeIds.length > contextNodeIds.value.length
    && contextNodeIds.value.every((id) => group.nodeIds.includes(id))))
  const frameStyle = (nodeIds) => getGroupFrameStyle(nodeIds, { findNode, viewport, assetsVisible })
  const selectionFrameStyle = computed(() => frameStyle(selectedNodes.value.map((node) => node.id)))
  const toolbarFrameStyle = computed(() => frameStyle(selectedGroup.value?.nodeIds || selectedNodes.value.map((node) => node.id)))
  const selectionToolbarStyle = computed(() => ({
    left: toolbarFrameStyle.value.left,
    top: `${Math.max(44, Number.parseFloat(toolbarFrameStyle.value.top))}px`,
  }))
  const groupFrames = computed(() => groups.value.map((group) => ({
    id: group.id,
    nodeIds: group.nodeIds,
    active: selectedGroup.value?.id === group.id,
    style: frameStyle(group.nodeIds),
  })))
  const panelStyle = computed(() => {
    const node = selectedNode.value && findNode(selectedNode.value.id)
    if (!node) return {}
    const zoom = viewport.value.zoom
    const center = (assetsVisible.value ? 292 : 0) + viewport.value.x + (node.computedPosition.x + node.dimensions.width / 2) * zoom
    const top = viewport.value.y + (node.computedPosition.y + node.dimensions.height) * zoom + 16
    const panelTop = `clamp(16px, ${top}px, calc(100vh - ${getPanelHeight(node.type) + 84}px))`
    return {
      left: `clamp(16px, ${center - 300}px, calc(100vw - 616px))`,
      top: panelTop,
      '--canvas-panel-top': panelTop,
    }
  })

  function openContextMenu({ event, node }) {
    event.preventDefault()
    const nodeIds = node.selected && selectedNodes.value.length > 1 ? selectedNodes.value.map((item) => item.id) : [node.id]
    if (nodeIds.length === 1) {
      store.selectNodes(nodeIds)
      activeGroupId.value = null
    }
    contextMenu.value = { x: event.clientX, y: event.clientY, nodeId: node.id, nodeIds }
  }

  function openSelectionContextMenu({ event, nodes: selected }) {
    event.preventDefault()
    const nodeIds = selected.map((node) => node.id)
    contextMenu.value = { x: event.clientX, y: event.clientY, nodeId: nodeIds[0], nodeIds }
  }

  function groupContextNodes() {
    if (contextContainsWorkflow.value) return
    store.selectNodes(contextNodeIds.value)
    store.groupSelected()
    contextMenu.value = null
  }

  function ungroupContextNodes() {
    store.ungroupNode(contextCompleteGroup.value.nodeIds[0])
    activeGroupId.value = null
    contextMenu.value = null
  }

  function removeContextNodesFromGroup() {
    store.removeNodesFromGroup(contextPartialGroup.value.id, contextNodeIds.value)
    contextMenu.value = null
  }

  function duplicateContextNodes() {
    if (contextContainsWorkflow.value) return
    if (contextNodeIds.value.length > 1) store.duplicateNodes(contextNodeIds.value)
    else store.duplicateWithInputs(contextNodeIds.value[0])
    activeGroupId.value = null
    contextMenu.value = null
  }

  async function deleteNodeIds(nodeIds) {
    const workflowNodes = nodes.value.filter((node) => nodeIds.includes(node.id) && node.data?.workflowId)
    if (workflowNodes.length) {
      const root = nodeIds.length === 1 && workflowNodes[0]?.data.workflowRoot ? workflowNodes[0] : null
      if (!root || !await confirm({
        title: t('canvas.deleteNamedWorkflow', { p0: root.data.workflowType === 'product' ? t('canvas.productCreation') : t('canvas.outfit') }),
        message: t('canvas.deleteWorkflowConfirm'),
        confirmText: t('canvas.deleteWorkflow'),
        tone: 'danger',
      })) return false
      store.deleteWorkflow(root.data.workflowId)
      activeGroupId.value = null
      return true
    }
    if (nodeIds.length > 1 && !await confirm({
      title: t('canvas.deleteSelectedNodes'),
      message: t('canvas.deleteSelectedNodesConfirm', { p0: nodeIds.length }),
      confirmText: t('canvas.delete'),
      tone: 'danger',
    })) return false
    store.deleteNodes(nodeIds)
    activeGroupId.value = null
    return true
  }

  async function deleteContextNodes() {
    const nodeIds = [...contextNodeIds.value]
    contextMenu.value = null
    await deleteNodeIds(nodeIds)
  }

  async function deleteSelectedNodes() {
    if (!selectedNodes.value.length) return
    await deleteNodeIds(selectedNodes.value.map((node) => node.id))
  }

  function moveGroup(event) {
    if (!groupDrag.value) return
    const deltaX = (event.clientX - groupDrag.value.startX) / viewport.value.zoom
    const deltaY = (event.clientY - groupDrag.value.startY) / viewport.value.zoom
    groupDrag.value.positions.forEach(({ id, x, y }) => {
      const node = nodes.value.find((item) => item.id === id)
      if (node) node.position = { x: x + deltaX, y: y + deltaY }
    })
  }

  function stopGroupDrag() {
    window.removeEventListener('pointermove', moveGroup)
    window.removeEventListener('pointerup', stopGroupDrag)
    groupDrag.value = null
    pointerMode.value = null
  }

  function startGroupDrag(event, group) {
    event.preventDefault()
    event.stopPropagation()
    activeGroupId.value = group.id
    store.selectNodes([])
    groupDrag.value = {
      startX: event.clientX,
      startY: event.clientY,
      positions: group.nodeIds.map((id) => {
        const node = findNode(id)
        return { id, x: node.position.x, y: node.position.y }
      }),
    }
    window.addEventListener('pointermove', moveGroup)
    window.addEventListener('pointerup', stopGroupDrag)
  }

  function handleCanvasPointerDown(event) {
    if (event.target.closest('.nodrag, .selection-toolbar, .asset-drawer, .canvas-side-tools, .canvas-bottom-toolbar, .node-create-menu, .generation-panel')) return
    if (event.button === 1 || (event.button === 0 && canvasTool.value === 'hand')) {
      pointerMode.value = 'panning'
      return
    }
    if (event.button !== 0) return
    pointerMode.value = 'selecting'
    const nodeElement = event.target.closest('.vue-flow__node')
    if (nodeElement) {
      pointerMode.value = 'moving'
      activeGroupId.value = null
      const nodeId = nodeElement.getAttribute('data-id')
      if (!event.shiftKey && groups.value.some((group) => group.nodeIds.includes(nodeId))) {
        const node = findNode(nodeId)
        if (node) {
          removeSelectedElements()
          addSelectedNodes([node])
        }
      }
      return
    }
    const group = groupFrames.value.find(({ style }) => {
      const left = Number.parseFloat(style.left)
      const top = Number.parseFloat(style.top)
      return event.clientX >= left && event.clientX <= left + Number.parseFloat(style.width)
        && event.clientY >= top && event.clientY <= top + Number.parseFloat(style.height)
    })
    if (group) {
      activeGroupId.value = group.id
      pointerMode.value = 'moving'
      startGroupDrag(event, group)
    } else activeGroupId.value = null
  }

  function handleNodeDragStart({ event, nodes: draggedNodes }) {
    if (event.altKey) nodeDragCopy = Object.fromEntries(draggedNodes.map((node) => [node.id, { ...node.position }]))
  }

  function handleNodeDragStop() {
    if (!nodeDragCopy) return
    const ids = Object.keys(nodeDragCopy)
    const positions = Object.fromEntries(ids.map((id) => [id, { ...nodes.value.find((node) => node.id === id).position }]))
    Object.entries(nodeDragCopy).forEach(([id, position]) => { nodes.value.find((node) => node.id === id).position = position })
    store.duplicateNodes(ids, positions)
    nodeDragCopy = null
    activeGroupId.value = null
  }

  function ungroupSelected() {
    if (selectedGroup.value) store.ungroupNode(selectedGroup.value.nodeIds[0])
    else if (selectedPartialGroup.value) store.removeNodesFromGroup(selectedPartialGroup.value.id, selectedNodes.value.map((node) => node.id))
    activeGroupId.value = null
  }

  function focusGroup(id) {
    const group = groups.value.find((item) => item.id === id)
    if (!group) return
    activeGroupId.value = id
    store.selectNodes([])
    fitView({ nodes: group.nodeIds, padding: 0.3, duration: 300 })
  }

  function focusNode(id) {
    const node = findNode(id)
    activeGroupId.value = null
    nodes.value.forEach((item) => { item.selected = item.id === id })
    setCenter(node.computedPosition.x + node.dimensions.width / 2, node.computedPosition.y + node.dimensions.height / 2, { zoom: 1, duration: 300 })
  }

  return {
    activeGroupId,
    selectedNodes,
    selectedContainsWorkflow,
    selectedNode,
    selectedGroup,
    selectedPartialGroup,
    contextNodeIds,
    contextContainsWorkflow,
    contextWorkflowRoot,
    contextCompleteGroup,
    contextPartialGroup,
    selectionFrameStyle,
    selectionToolbarStyle,
    groupFrames,
    panelStyle,
    openContextMenu,
    openSelectionContextMenu,
    groupContextNodes,
    ungroupContextNodes,
    removeContextNodesFromGroup,
    duplicateContextNodes,
    deleteContextNodes,
    deleteSelectedNodes,
    handleCanvasPointerDown,
    handleNodeDragStart,
    handleNodeDragStop,
    ungroupSelected,
    focusNode,
    focusGroup,
    disposeGrouping: stopGroupDrag,
  }
}
