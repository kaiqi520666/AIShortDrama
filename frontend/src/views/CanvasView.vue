<script setup>
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import { ChevronRight, CircleHelp, Clipboard, Copy, Group, Hand, Image as ImageIcon, Keyboard, Library, Maximize2, MousePointer2, Plus, Redo2, Scan, Trash2, Undo2, Ungroup, Video } from 'lucide-vue-next'
import AssetDrawer from '../components/canvas/AssetDrawer.vue'
import CanvasHeader from '../components/canvas/CanvasHeader.vue'
import FlowEdge from '../components/canvas/FlowEdge.vue'
import GenerationPanel from '../components/canvas/GenerationPanel.vue'
import MediaNode from '../components/canvas/MediaNode.vue'
import NodeCreateMenu from '../components/canvas/NodeCreateMenu.vue'
import NodeTypeMenu from '../components/canvas/NodeTypeMenu.vue'
import ShortcutPanel from '../components/canvas/ShortcutPanel.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppInput from '../components/ui/AppInput.vue'
import AppMenu from '../components/ui/AppMenu.vue'
import AppTooltip from '../components/ui/AppTooltip.vue'
import { uploadMedia } from '../api/uploads'
import { canConnect } from '../config/connectionRules'
import { mediaTypes } from '../config/mediaTypes'
import { useGlobalToast } from '../composables/useGlobalUI'
import { useAuthStore } from '../stores/auth'
import { useCanvasStore } from '../stores/canvas'

const store = useCanvasStore()
const authStore = useAuthStore()
const toast = useGlobalToast()
const props = defineProps({ workspace: { type: Object, required: true } })
const emit = defineEmits(['back', 'ready'])
const { nodes, edges, groups, saveStatus } = storeToRefs(store)
const { project, screenToFlowCoordinate, fitView, findNode, setCenter, setViewport, updateNodeData, viewport, zoomIn, zoomOut, removeSelectedElements, addSelectedNodes } = useVueFlow()

const nodeTypes = Object.fromEntries(Object.keys(mediaTypes).map((type) => [type, markRaw(MediaNode)]))
const edgeTypes = { cinematic: markRaw(FlowEdge) }
const createMenu = ref(null)
const contextMenu = ref(null)
const connectionSource = ref(null)
const groupDrag = ref(null)
const pointerMode = ref(null)
const canvasTool = ref('move')
const toolMenuOpen = ref(false)
const shortcutPanelOpen = ref(false)
const flowMounted = ref(false)
const canvasDropActive = ref(false)
const uploadInput = ref(null)
const pendingUpload = ref(null)
const generationPanel = ref(null)
let saveTimer = null
let readyEmitted = false
let pastePoint = null
let history = []
const historyIndex = ref(-1)
let historyTimer = null
let historyApplying = false
let toolBeforeSpace = null
let nodeDragCopy = null

const pastedImageTypes = ['image/jpeg', 'image/png', 'image/webp']
const pastedImageMaxSize = 20 * 1024 * 1024
const uploadRules = {
  image: { accept: 'image/jpeg,image/png,image/webp', types: ['image/jpeg', 'image/png', 'image/webp'], maxSize: 20 * 1024 * 1024 },
  video: { accept: 'video/mp4,video/quicktime,video/webm', types: ['video/mp4', 'video/quicktime', 'video/webm'], maxSize: 500 * 1024 * 1024 },
}

const minimapVisible = ref(false)
const assetsVisible = ref(false)
const activeGroupId = ref(null)
const selectedNodes = computed(() => nodes.value.filter((node) => node.selected))
const selectedNode = computed(() => selectedNodes.value.length === 1 ? selectedNodes.value[0] : null)
const selectedGroup = computed(() => groups.value.find((group) => group.id === activeGroupId.value) || groups.value.find((group) => group.nodeIds.length === selectedNodes.value.length && group.nodeIds.every((id) => selectedNodes.value.some((node) => node.id === id))))
const contextGroup = computed(() => groups.value.find((group) => group.nodeIds.includes(contextMenu.value?.nodeId)))
const panelConfig = { width: 600, height: 230, gap: 16, margin: 16 }
function frameStyle(nodeIds) {
  const flowNodes = nodeIds.map((id) => findNode(id)).filter(Boolean)
  if (flowNodes.length < 2) return {}

  const zoom = viewport.value.zoom
  const paddingX = 28
  const paddingTop = 32
  const paddingBottom = 14
  const left = Math.min(...flowNodes.map((node) => node.computedPosition.x))
  const top = Math.min(...flowNodes.map((node) => node.computedPosition.y))
  const right = Math.max(...flowNodes.map((node) => node.computedPosition.x + node.dimensions.width))
  const bottom = Math.max(...flowNodes.map((node) => node.computedPosition.y + node.dimensions.height))
  const offset = assetsVisible.value ? 292 : 0

  return {
    left: `${offset + viewport.value.x + left * zoom - paddingX}px`,
    top: `${viewport.value.y + top * zoom - paddingTop}px`,
    width: `${(right - left) * zoom + paddingX * 2}px`,
    height: `${(bottom - top) * zoom + paddingTop + paddingBottom}px`,
  }
}
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
  const top = viewport.value.y + node.computedPosition.y * zoom
  const bottom = top + node.dimensions.height * zoom
  const below = bottom + panelConfig.gap
  return {
    left: `clamp(${panelConfig.margin}px, ${center - panelConfig.width / 2}px, calc(100vw - ${panelConfig.width + panelConfig.margin}px))`,
    top: `${below + panelConfig.height <= window.innerHeight - panelConfig.margin ? below : Math.max(panelConfig.margin, top - panelConfig.height - panelConfig.gap)}px`,
  }
})
function openGlobalMenu(event) {
  toolMenuOpen.value = false
  const buttonRect = event.currentTarget.getBoundingClientRect()
  const centerX = window.innerWidth / 2 + (assetsVisible.value ? 146 : 0)
  createMenu.value = {
    point: { x: buttonRect.left + buttonRect.width / 2, y: buttonRect.top - 8 },
    position: project({ x: centerX, y: window.innerHeight / 2 }),
    placement: 'anchor',
    sourceId: null,
  }
}

function openShortcutCreateMenu() {
  const centerX = window.innerWidth / 2 + (assetsVisible.value ? 146 : 0)
  shortcutPanelOpen.value = false
  createMenu.value = {
    point: { x: centerX, y: window.innerHeight - 76 },
    position: project({ x: centerX, y: window.innerHeight / 2 }),
    placement: 'anchor',
    sourceId: null,
  }
}

function openPaneCreateMenu(event) {
  event.preventDefault()
  commitHistory()
  createMenu.value = null
  contextMenu.value = {
    kind: 'pane',
    x: Math.min(Math.max(10, event.clientX), window.innerWidth - 226),
    y: Math.min(Math.max(10, event.clientY), window.innerHeight - 318),
    position: project({ x: event.clientX, y: event.clientY }),
    submenuOpen: false,
  }
}

function createNode(type) {
  store.addNode(type, createMenu.value.position, createMenu.value.sourceId)
  createMenu.value = null
}

function handleConnectStart({ nodeId, handleType }) {
  connectionSource.value = handleType === 'source' ? nodeId : null
}

function handleConnect(connection) {
  store.addEdge(connection)
  connectionSource.value = null
}

function connectSelected() {
  if (selectedNodes.value.length !== 2) return toast.warning('请选择两个节点后连接')
  let [source, target] = [...selectedNodes.value].sort((a, b) => a.position.x - b.position.x)
  if (!canConnect(source.type, target.type) && canConnect(target.type, source.type)) [source, target] = [target, source]
  if (!canConnect(source.type, target.type)) return toast.warning('所选节点类型不能连接')
  if (!store.addEdge({ source: source.id, target: target.id })) toast.warning('节点已经连接')
}

function handleConnectEnd(event) {
  if (!connectionSource.value || event.target.closest('.vue-flow__handle, .vue-flow__node')) {
    connectionSource.value = null
    return
  }
  createMenu.value = {
    point: { x: Math.min(event.clientX + 12, window.innerWidth - 260), y: Math.min(event.clientY + 12, window.innerHeight - 360) },
    position: project({ x: event.clientX, y: event.clientY }),
    sourceId: connectionSource.value,
  }
  connectionSource.value = null
}

function openContextMenu({ event, node }) {
  event.preventDefault()
  contextMenu.value = { x: event.clientX, y: event.clientY, nodeId: node.id }
}

function openEdgeContextMenu({ event, edge }) {
  event.preventDefault()
  contextMenu.value = { x: event.clientX, y: event.clientY, edgeId: edge.id }
}

function runContextAction(action) {
  if (action === 'groupSelected') store.groupSelected()
  else store[action](action === 'deleteEdge' ? contextMenu.value.edgeId : contextMenu.value.nodeId)
  contextMenu.value = null
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
    if (groups.value.some((group) => group.nodeIds.includes(nodeId))) {
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
    return event.clientX >= left && event.clientX <= left + Number.parseFloat(style.width) && event.clientY >= top && event.clientY <= top + Number.parseFloat(style.height)
  })
  if (group) {
    activeGroupId.value = group.id
    pointerMode.value = 'moving'
    startGroupDrag(event, group)
  } else {
    activeGroupId.value = null
  }
}

function resetPointerMode() {
  pointerMode.value = null
}

function handleNodeDragStart({ event, nodes: draggedNodes }) {
  if (!event.altKey) return
  nodeDragCopy = Object.fromEntries(draggedNodes.map((node) => [node.id, { ...node.position }]))
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

function selectCanvasTool(tool) {
  canvasTool.value = tool
  toolMenuOpen.value = false
  pointerMode.value = null
}

function toggleToolMenu() {
  createMenu.value = null
  contextMenu.value = null
  toolMenuOpen.value = !toolMenuOpen.value
}

function ungroupSelected() {
  const group = selectedGroup.value || groups.value.find((item) => item.nodeIds.some((id) => selectedNodes.value.some((node) => node.id === id)))
  if (!group) return
  store.ungroupNode(group.nodeIds[0])
  activeGroupId.value = null
}

function focusNode(id) {
  const node = findNode(id)
  activeGroupId.value = null
  nodes.value.forEach((item) => { item.selected = item.id === id })
  setCenter(node.computedPosition.x + node.dimensions.width / 2, node.computedPosition.y + node.dimensions.height / 2, { zoom: 1, duration: 300 })
}

function focusGroup(id) {
  const group = groups.value.find((item) => item.id === id)
  if (!group) return
  activeGroupId.value = id
  store.selectNodes([])
  fitView({ nodes: group.nodeIds, padding: 0.3, duration: 300 })
}

function createPaneNode(type) {
  store.addNode(type, contextMenu.value.position)
  contextMenu.value = null
}

function scheduleSave() {
  if (!store.ready) return
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => store.saveCanvas().catch(() => {}), 800)
}

function historySnapshot() {
  const payload = store.canvasPayload()
  return JSON.stringify({
    nodes: payload.nodes,
    edges: payload.edges,
    groups: payload.groups,
  })
}

function commitHistory() {
  window.clearTimeout(historyTimer)
  if (historyApplying || !store.ready) return
  const snapshot = historySnapshot()
  if (snapshot === history[historyIndex.value]) return
  history = [...history.slice(0, historyIndex.value + 1), snapshot].slice(-50)
  historyIndex.value = history.length - 1
}

function scheduleHistory() {
  if (historyApplying || !store.ready) return
  window.clearTimeout(historyTimer)
  historyTimer = window.setTimeout(commitHistory, 200)
}

function restoreHistory(snapshot) {
  historyApplying = true
  const state = JSON.parse(snapshot)
  store.nodes = state.nodes
  store.edges = state.edges
  store.groups = state.groups
  activeGroupId.value = null
  contextMenu.value = null
  nextTick(() => { historyApplying = false })
}

function undo() {
  if (historyApplying) return
  commitHistory()
  if (historyIndex.value <= 0) return
  restoreHistory(history[--historyIndex.value])
}

function redo() {
  if (historyApplying) return
  commitHistory()
  if (historyIndex.value >= history.length - 1) return
  restoreHistory(history[++historyIndex.value])
}

const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < history.length - 1)
const submenuOpensLeft = computed(() => (contextMenu.value?.x || 0) + 478 > window.innerWidth)

function handleCanvasShortcut(event) {
  if (event.target instanceof Element && event.target.closest('input, textarea, [contenteditable]:not([contenteditable="false"])')) return
  const key = event.key.toLowerCase()
  const command = event.ctrlKey || event.metaKey
  if (key === 'escape' && shortcutPanelOpen.value) {
    shortcutPanelOpen.value = false
    return
  }
  if (shortcutPanelOpen.value) return
  if (event.code === 'Space' && !command && !event.altKey) {
    event.preventDefault()
    if (toolBeforeSpace === null) {
      toolBeforeSpace = canvasTool.value
      canvasTool.value = 'hand'
    }
    return
  }
  if (key === 'tab' && !command && !event.altKey) {
    event.preventDefault()
    openShortcutCreateMenu()
    return
  }
  if (!(event.ctrlKey || event.metaKey || event.altKey) && (key === 'v' || key === 'h')) {
    event.preventDefault()
    selectCanvasTool(key === 'h' ? 'hand' : 'move')
    return
  }
  if (event.altKey && event.shiftKey && key === 'f') {
    event.preventDefault()
    fitView({ padding: 0.24, duration: 350 })
    return
  }
  if (!command || event.altKey) return
  if (['z', 'y', 'g', 'd', 'l', 'enter', '0', '=', '+', '-'].includes(key)) event.preventDefault()
  if (key === 'z') return event.shiftKey ? redo() : undo()
  if (key === 'y') return redo()
  if (key === 'g') return event.shiftKey ? ungroupSelected() : (selectedNodes.value.length > 1 && store.groupSelected())
  if (key === 'd') return selectedNodes.value.length && store.duplicateSelected()
  if (key === 'l') return connectSelected()
  if (key === 'enter') return generationPanel.value?.submitTask()
  if (key === '0') return fitView({ padding: 0.24, duration: 350 })
  if (key === '=' || key === '+') return zoomIn({ duration: 180 })
  if (key === '-') zoomOut({ duration: 180 })
}

function restoreTemporaryHand() {
  if (toolBeforeSpace === null) return
  canvasTool.value = toolBeforeSpace
  toolBeforeSpace = null
  pointerMode.value = null
}

function handleCanvasKeyup(event) {
  if (event.code === 'Space') restoreTemporaryHand()
}

function updateViewport(value) {
  store.setViewport(value)
}

async function finishCanvasSetup() {
  if (readyEmitted) return
  readyEmitted = true
  setViewport(store.viewportData)
  await nextTick()
  emit('ready')
}

function handleCanvasDragOver(event) {
  if (!event.dataTransfer.types.includes('application/x-mooncut-canvas-item')) return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'copy'
  canvasDropActive.value = true
}

function handleCanvasDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) canvasDropActive.value = false
}

function handleCanvasDrop(event) {
  const raw = event.dataTransfer.getData('application/x-mooncut-canvas-item')
  canvasDropActive.value = false
  if (!raw) return
  event.preventDefault()
  try {
    const item = JSON.parse(raw)
    const position = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
    if (item.kind !== 'asset') return
    store.addAssetNode(item.asset, position)
    activeGroupId.value = null
  } catch {
    toast.error('无法添加拖拽内容')
  }
}

function trackPastePoint(event) {
  if (event.target.closest('.creative-flow') && !event.target.closest('.vue-flow__node, .generation-panel, .node-create-menu')) {
    pastePoint = { x: event.clientX, y: event.clientY }
  }
}

function pasteText(text, position) {
  const id = store.addNode('text', position)
  const node = nodes.value.find((item) => item.id === id)
  node.data = { ...node.data, textMode: 'manual', content: text, status: 'ready', pasted: true }
}

async function pasteImage(file, position) {
  if (!pastedImageTypes.includes(file.type)) return toast.warning('仅支持粘贴 JPG、PNG 或 WebP 图片')
  if (file.size > pastedImageMaxSize) return toast.warning('粘贴图片不能超过 20MB')

  const id = store.addNode('image', position)
  const node = nodes.value.find((item) => item.id === id)
  node.data = { ...node.data, status: 'uploading', assetSource: 'clipboard', pasted: true }
  try {
    const bitmap = await createImageBitmap(file)
    const metadata = { width: bitmap.width, height: bitmap.height }
    bitmap.close()
    const result = await uploadMedia('image', file, { workspaceId: store.workspaceId, nodeId: id, timeout: 60_000, ...metadata })
    if (result.code !== 0) throw new Error(result.message)
    updateNodeData(id, {
      asset: result.data.url,
      assetId: result.data.id,
      status: 'ready',
      sourceWidth: metadata.width,
      sourceHeight: metadata.height,
      sourceAspectRatio: metadata.width / metadata.height,
    })
    toast.success('图片已粘贴到画布')
  } catch (error) {
    store.deleteNode(id)
    toast.error(error.code === 'ECONNABORTED' ? '图片上传超时，请重试' : error.response?.data?.message || error.message || '图片粘贴失败')
  }
}

function readMediaMetadata(type, file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const media = type === 'image' ? new Image() : document.createElement('video')
    const cleanup = () => URL.revokeObjectURL(url)
    media.onload = media.onloadedmetadata = () => {
      const width = media.naturalWidth || media.videoWidth
      const height = media.naturalHeight || media.videoHeight
      cleanup()
      width && height ? resolve({ width, height, duration: media.duration || null }) : reject(new Error('无法读取媒体尺寸'))
    }
    media.onerror = () => {
      cleanup()
      reject(new Error('无法读取媒体文件'))
    }
    media.preload = 'metadata'
    media.src = url
  })
}

function chooseUpload(type) {
  pendingUpload.value = { type, position: contextMenu.value.position }
  contextMenu.value = null
  nextTick(() => uploadInput.value?.click())
}

async function handlePaneUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  const upload = pendingUpload.value
  pendingUpload.value = null
  if (!file || !upload) return
  const rule = uploadRules[upload.type]
  if (!rule.types.includes(file.type)) return toast.warning(`不支持的${upload.type === 'video' ? '视频' : '图片'}格式`)
  if (file.size > rule.maxSize) return toast.warning(`文件不能超过 ${rule.maxSize / 1024 / 1024}MB`)

  const id = store.addNode(upload.type, upload.position)
  const node = nodes.value.find((item) => item.id === id)
  node.data = { ...node.data, status: 'uploading', assetSource: 'upload', pasted: true }
  try {
    const metadata = await readMediaMetadata(upload.type, file)
    const result = await uploadMedia(upload.type, file, { workspaceId: store.workspaceId, nodeId: id, timeout: 60_000, ...metadata })
    if (result.code !== 0) throw new Error(result.message)
    updateNodeData(id, {
      asset: result.data.url,
      assetId: result.data.id,
      status: 'ready',
      sourceWidth: metadata.width,
      sourceHeight: metadata.height,
      sourceAspectRatio: metadata.width / metadata.height,
      ...(metadata.duration ? { sourceDuration: metadata.duration } : {}),
    })
  } catch (error) {
    store.deleteNode(id)
    toast.error(error.code === 'ECONNABORTED' ? '上传超时，请重试' : error.response?.data?.message || error.message || '上传失败')
  }
}

async function pasteFromMenu() {
  const position = contextMenu.value.position
  contextMenu.value = null
  try {
    if (!navigator.clipboard?.read) {
      const text = (await navigator.clipboard.readText()).trim()
      return text ? pasteText(text, position) : toast.warning('剪贴板中没有可粘贴内容')
    }
    const items = await navigator.clipboard.read()
    for (const item of items) {
      const imageType = item.types.find((type) => type.startsWith('image/'))
      if (imageType) {
        const blob = await item.getType(imageType)
        return pasteImage(new File([blob], 'clipboard-image', { type: imageType }), position)
      }
    }
    const textItem = items.find((item) => item.types.includes('text/plain'))
    const text = textItem ? (await (await textItem.getType('text/plain')).text()).trim() : ''
    return text ? pasteText(text, position) : toast.warning('剪贴板中没有可粘贴内容')
  } catch {
    toast.error('无法读取剪贴板，请允许浏览器访问剪贴板')
  }
}

function handlePaste(event) {
  const editable = event.target instanceof Element && event.target.closest('input, textarea, [contenteditable]:not([contenteditable="false"])')
  if (editable || !pastePoint) return

  const imageItem = Array.from(event.clipboardData?.items || []).find((item) => item.kind === 'file' && item.type.startsWith('image/'))
  const text = event.clipboardData?.getData('text/plain')?.trim()
  if (!imageItem && !text) return

  event.preventDefault()
  const position = project(pastePoint)
  const imageFile = imageItem?.getAsFile()
  if (imageItem && !imageFile) return toast.error('无法读取剪贴板图片')
  if (imageFile) pasteImage(imageFile, position)
  else pasteText(text, position)
}

async function goHome() {
  window.clearTimeout(saveTimer)
  try {
    await store.saveCanvas(viewport.value)
    emit('back')
  } catch {}
}

async function signOut() {
  window.clearTimeout(saveTimer)
  await store.saveCanvas(viewport.value).catch(() => {})
  await authStore.logout()
  store.$reset()
  emit('back')
}

watch(() => store.canvasPayload(), scheduleSave, { deep: true })
watch(historySnapshot, scheduleHistory)
onMounted(async () => {
  window.addEventListener('paste', handlePaste)
  window.addEventListener('keydown', handleCanvasShortcut)
  window.addEventListener('keyup', handleCanvasKeyup)
  window.addEventListener('blur', restoreTemporaryHand)
  await store.loadWorkspace(props.workspace)
  window.clearTimeout(historyTimer)
  history = [historySnapshot()]
  historyIndex.value = 0
  flowMounted.value = true
  await nextTick()
  if (!nodes.value.length) await finishCanvasSetup()
})
onBeforeUnmount(() => {
  window.clearTimeout(saveTimer)
  window.clearTimeout(historyTimer)
  window.removeEventListener('paste', handlePaste)
  window.removeEventListener('keydown', handleCanvasShortcut)
  window.removeEventListener('keyup', handleCanvasKeyup)
  window.removeEventListener('blur', restoreTemporaryHand)
})
</script>

<template>
  <main class="canvas-page" :class="{ 'assets-open': assetsVisible, 'multi-selected': selectedNodes.length > 1, [`canvas-tool-${canvasTool}`]: canvasTool, [`cursor-${pointerMode}`]: pointerMode }" @pointermove="trackPastePoint" @pointerdown="contextMenu = null; toolMenuOpen = false" @pointerdown.capture="handleCanvasPointerDown" @pointerup.window="resetPointerMode" @pointercancel.window="resetPointerMode" @dragend="canvasDropActive = false">
    <input ref="uploadInput" type="file" :accept="pendingUpload ? uploadRules[pendingUpload.type].accept : ''" hidden @change="handlePaneUpload" />
    <CanvasHeader :workspace-name="workspace.name" :save-status="saveStatus" :username="authStore.user?.username || '访客'" @back="goHome" @logout="signOut" />

    <VueFlow
      v-if="flowMounted"
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :min-zoom="0.1"
      :max-zoom="8"
      :connection-radius="28"
      :delete-key-code="['Backspace', 'Delete']"
      class="creative-flow"
      :class="{ 'drop-active': canvasDropActive }"
      @dragover="handleCanvasDragOver"
      @dragleave="handleCanvasDragLeave"
      @drop="handleCanvasDrop"
      @connect="handleConnect"
      @connect-start="handleConnectStart"
      @connect-end="handleConnectEnd"
      @node-drag-start="handleNodeDragStart"
      @node-drag-stop="handleNodeDragStop"
      :selection-key-code="canvasTool === 'move' ? true : null"
      multi-selection-key-code="Shift"
      selection-mode="partial"
      :nodes-draggable="canvasTool === 'move'"
      :select-nodes-on-drag="canvasTool === 'move'"
      :pan-on-drag="canvasTool === 'hand' ? [0, 1] : [1]"
      @node-context-menu="openContextMenu"
      @edge-context-menu="openEdgeContextMenu"
      @pane-context-menu="openPaneCreateMenu"
      @pane-click="contextMenu = null"
      @nodes-initialized="finishCanvasSetup"
      @viewport-change-end="updateViewport"
    >
      <Background :gap="22" :size="1" pattern-color="#303238" />
      <MiniMap v-if="minimapVisible" position="bottom-right" :pannable="true" :zoomable="true" />
    </VueFlow>

    <div
      v-for="group in groupFrames"
      :key="group.id"
      class="selection-frame"
      :class="{ active: group.active }"
      :style="group.style"
    ></div>
    <div v-if="selectedNodes.length > 1 && !selectedGroup" class="selection-frame active" :style="selectionFrameStyle"></div>

    <GenerationPanel
      v-if="selectedNode && !selectedNode.data.pasted"
      ref="generationPanel"
      :node-id="selectedNode.id"
      :type="selectedNode.type"
      :data="selectedNode.data"
      :style="panelStyle"
    />

    <Transition name="asset-sidebar">
      <AssetDrawer v-if="assetsVisible" :nodes="nodes" :groups="groups" :active-group-id="selectedGroup?.id" @focus="focusNode" @focus-group="focusGroup" @rename-node="store.renameNode" @rename-group="store.renameGroup" @delete-node="store.deleteNode" @delete-group="store.deleteGroup" @close="assetsVisible = false" />
    </Transition>

    <aside class="canvas-side-tools">
      <AppButton class="asset-toggle-button" title="资产" @click="assetsVisible = !assetsVisible"><Library :size="17" /><span>资产</span></AppButton>
      <AppTooltip text="整理画布"><AppButton icon-only aria-label="整理画布" @click="fitView({ padding: 0.24, duration: 350 })"><Scan :size="17" /></AppButton></AppTooltip>
      <AppTooltip text="切换小地图"><AppButton icon-only aria-label="切换小地图" @click="minimapVisible = !minimapVisible"><Maximize2 :size="17" /></AppButton></AppTooltip>
      <span>{{ Math.round(viewport.zoom * 100) }}%</span>
    </aside>

    <div v-if="selectedNodes.length > 1 || selectedGroup" class="selection-toolbar" :style="selectionToolbarStyle">
      <AppInput
        v-if="selectedGroup"
        class="selection-group-title"
        :model-value="selectedGroup.title || '未命名编组'"
        aria-label="编组标题"
        @input="store.renameGroup(selectedGroup.id, $event.target.value)"
        @blur="store.renameGroup(selectedGroup.id, $event.target.value)"
        @keydown.enter="$event.target.blur()"
        @keydown.stop
      />
      <span>{{ selectedGroup ? selectedGroup.nodeIds.length : selectedNodes.length }} 个节点</span>
      <AppButton v-if="selectedNodes.length > 1 && !selectedGroup" size="sm" title="编组" @click="store.groupSelected"><Group :size="15" />编组</AppButton>
      <AppButton v-if="selectedGroup" size="sm" title="解组" @click="ungroupSelected"><Ungroup :size="15" />解组</AppButton>
    </div>

    <nav class="canvas-bottom-toolbar" aria-label="画布快捷工具">
      <AppTooltip text="新增节点">
        <AppButton class="canvas-add-button" icon-only variant="primary" aria-label="新增节点" @click="openGlobalMenu"><Plus :size="19" /></AppButton>
      </AppTooltip>
      <div class="canvas-tool-picker" @pointerdown.stop>
        <AppTooltip :text="canvasTool === 'move' ? '移动工具 (V)' : '抓手工具 (H)'">
          <AppButton class="canvas-tool-button" :class="{ active: toolMenuOpen }" icon-only aria-label="切换画布工具" aria-haspopup="menu" :aria-expanded="toolMenuOpen" @click="toggleToolMenu">
            <MousePointer2 v-if="canvasTool === 'move'" :size="18" />
            <Hand v-else :size="18" />
          </AppButton>
        </AppTooltip>
        <AppMenu v-if="toolMenuOpen" class="canvas-tool-menu" @pointerdown.stop>
          <AppButton :class="{ active: canvasTool === 'move' }" @click="selectCanvasTool('move')"><MousePointer2 :size="17" /><strong>移动</strong><kbd>V</kbd></AppButton>
          <AppButton :class="{ active: canvasTool === 'hand' }" @click="selectCanvasTool('hand')"><Hand :size="17" /><strong>抓手工具</strong><kbd>H</kbd></AppButton>
        </AppMenu>
      </div>
      <span class="canvas-bottom-divider"></span>
      <AppTooltip text="快捷键">
        <AppButton class="canvas-bottom-secondary shortcut-toggle" icon-only aria-label="快捷键" :aria-pressed="shortcutPanelOpen" @click="shortcutPanelOpen = !shortcutPanelOpen"><Keyboard :size="18" /></AppButton>
      </AppTooltip>
      <AppTooltip text="教程（即将上线）">
        <AppButton class="canvas-bottom-secondary" icon-only aria-label="教程（即将上线）"><CircleHelp :size="18" /></AppButton>
      </AppTooltip>
    </nav>

    <ShortcutPanel v-if="shortcutPanelOpen" @close="shortcutPanelOpen = false" />

    <NodeCreateMenu
      v-if="createMenu"
      :point="createMenu.point"
      :placement="createMenu.placement"
      :contextual="Boolean(createMenu.sourceId)"
      :source-id="createMenu.sourceId"
      @select="createNode"
      @close="createMenu = null"
    />

    <AppMenu v-if="contextMenu" class="context-menu" :class="{ 'context-menu--pane': contextMenu.kind === 'pane' }" :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }" @pointerdown.stop>
      <AppButton v-if="contextMenu.edgeId" variant="danger" @click="runContextAction('deleteEdge')"><Trash2 :size="15" />删除连接</AppButton>
      <template v-else-if="contextMenu.kind === 'pane'">
        <p class="context-menu-label">上传</p>
        <AppButton @click="chooseUpload('image')"><ImageIcon :size="15" /><span>图片</span></AppButton>
        <AppButton @click="chooseUpload('video')"><Video :size="15" /><span>视频</span></AppButton>
        <span class="context-menu-divider"></span>
        <div class="context-submenu-trigger" @mouseenter="contextMenu.submenuOpen = true" @mouseleave="contextMenu.submenuOpen = false">
          <AppButton @click="contextMenu.submenuOpen = true"><Plus :size="15" /><span>添加节点</span><ChevronRight class="context-menu-chevron" :size="14" /></AppButton>
          <AppMenu v-if="contextMenu.submenuOpen" class="context-submenu" :class="{ 'context-submenu--left': submenuOpensLeft }" @pointerdown.stop>
            <NodeTypeMenu @select="createPaneNode" />
          </AppMenu>
        </div>
        <span class="context-menu-divider"></span>
        <AppButton :disabled="!canUndo" @click="undo"><Undo2 :size="15" /><span>撤销</span><kbd>Ctrl+Z</kbd></AppButton>
        <AppButton :disabled="!canRedo" @click="redo"><Redo2 :size="15" /><span>重做</span><kbd>Ctrl+Y</kbd></AppButton>
        <span class="context-menu-divider"></span>
        <AppButton @click="pasteFromMenu"><Clipboard :size="15" /><span>粘贴</span><kbd>Ctrl+V</kbd></AppButton>
      </template>
      <template v-else>
        <AppButton @click="runContextAction('duplicateWithInputs')"><Copy :size="15" />创建副本</AppButton>
        <AppButton v-if="selectedNodes.length > 1 && !contextGroup" @click="runContextAction('groupSelected')"><Group :size="15" />编组</AppButton>
        <AppButton v-if="contextGroup" @click="runContextAction('ungroupNode')"><Ungroup :size="15" />解组</AppButton>
        <span v-if="selectedNodes.length > 1 || contextGroup"></span>
        <AppButton variant="danger" @click="runContextAction('deleteNode')"><Trash2 :size="15" />删除</AppButton>
      </template>
    </AppMenu>
  </main>
</template>
