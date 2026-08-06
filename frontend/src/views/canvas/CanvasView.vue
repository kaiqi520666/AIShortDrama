<script setup>
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import { ChevronRight, CircleHelp, Clipboard, Copy, Group, Hand, Image as ImageIcon, Keyboard, Library, Maximize2, MousePointer2, Music2, Plus, Redo2, Scan, Trash2, Undo2, Ungroup, Video } from 'lucide-vue-next'
import AssetDrawer from '../../components/canvas/AssetDrawer.vue'
import CanvasHeader from '../../components/canvas/CanvasHeader.vue'
import FlowEdge from '../../components/canvas/FlowEdge.vue'
import NodeCreateMenu from '../../components/canvas/NodeCreateMenu.vue'
import NodeTypeMenu from '../../components/canvas/NodeTypeMenu.vue'
import ShortcutPanel from '../../components/canvas/ShortcutPanel.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppMenu from '../../components/ui/AppMenu.vue'
import AppTooltip from '../../components/ui/AppTooltip.vue'
import { canConnect, getConnectionError, inferTargetHandle } from '../../config/canvas/connectionRules'
import { nodeRegistry } from '../../config/canvas/nodeRegistry'
import { getNodeTypes } from '../../config/canvas/nodePacks'
import { useGlobalConfirm, useGlobalToast } from '../../composables/useGlobalUI'
import { useCanvasAutosave } from '../../composables/useCanvasAutosave'
import { useCanvasClipboard } from '../../composables/useCanvasClipboard'
import { useCanvasHistory } from '../../composables/useCanvasHistory'
import { stopAllGenerationPolling, stopWorkspaceGenerationPolling } from '../../services/generationPolling'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useCanvasDropUpload } from './useCanvasDropUpload'
import { useCanvasGrouping } from './useCanvasGrouping'
import { useCanvasShortcuts } from './useCanvasShortcuts'

const store = useCanvasStore()
const authStore = useAuthStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const props = defineProps({ workspace: { type: Object, required: true } })
const emit = defineEmits(['back', 'ready'])
const { nodes, edges, groups } = storeToRefs(store)
const { project, screenToFlowCoordinate, fitView, findNode, setCenter, setViewport, updateNodeData, viewport, zoomIn, zoomOut, removeSelectedElements, addSelectedNodes } = useVueFlow()

const nodeTypes = Object.fromEntries(getNodeTypes(props.workspace.workspace_type).map((type) => [type, markRaw(nodeRegistry[type].component)]))
const edgeTypes = { cinematic: markRaw(FlowEdge) }
const createMenu = ref(null)
const contextMenu = ref(null)
const connectionSource = ref(null)
const pointerMode = ref(null)
const canvasTool = ref('move')
const toolMenuOpen = ref(false)
const shortcutPanelOpen = ref(false)
const flowMounted = ref(false)
const generationPanel = ref(null)
let readyEmitted = false

const minimapVisible = ref(false)
const assetsVisible = ref(false)
const {
  activeGroupId,
  selectedNodes,
  selectedNode,
  selectedGroup,
  selectedPartialGroup,
  contextNodeIds,
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
  handleCanvasPointerDown,
  handleNodeDragStart,
  handleNodeDragStop,
  ungroupSelected,
  focusNode,
  focusGroup,
  disposeGrouping,
} = useCanvasGrouping({
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
  getPanelHeight: (type) => nodeRegistry[type]?.panelHeight || 260,
  removeSelectedElements,
  addSelectedNodes,
  confirm,
})
const {
  canUndo,
  canRedo,
  snapshot: historySnapshot,
  commit: commitHistory,
  schedule: scheduleHistory,
  undo,
  redo,
  initialize: initializeHistory,
  dispose: disposeHistory,
} = useCanvasHistory({ store, activeGroupId, contextMenu })
const {
  pasteFromClipboard,
  trackPastePoint,
} = useCanvasClipboard({ store, nodes, project, updateNodeData, toast })
const {
  canvasDropActive,
  uploadInput,
  pendingUpload,
  uploadRules,
  handleCanvasDragOver,
  handleCanvasDragLeave,
  handleCanvasDrop,
  chooseUpload,
  handlePaneUpload,
} = useCanvasDropUpload({ store, nodes, contextMenu, activeGroupId, screenToFlowCoordinate, updateNodeData, toast })
const selectedNodeRegistry = computed(() => selectedNode.value && nodeRegistry[selectedNode.value.type])
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
    y: Math.min(Math.max(10, event.clientY), window.innerHeight - 351),
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
  const source = nodes.value.find((node) => node.id === connection.source)
  const target = nodes.value.find((node) => node.id === connection.target)
  const incomingConnections = store.edges
    .filter((edge) => edge.target === target?.id)
    .map((edge) => ({ targetHandle: edge.targetHandle, type: nodes.value.find((node) => node.id === edge.source)?.type }))
  const targetHandle = connection.targetHandle || inferTargetHandle(source, target?.type, incomingConnections)
  const normalizedConnection = targetHandle ? { ...connection, targetHandle } : connection
  const error = source && target ? getConnectionError(source.type, target.type, incomingConnections.map(({ type }) => type).filter(Boolean), store.workspaceType, targetHandle, incomingConnections) : '节点不存在'
  if (error) toast.warning(error)
  else if (!store.addEdge(normalizedConnection)) toast.warning('节点已经连接')
  connectionSource.value = null
}

function connectSelected() {
  if (selectedNodes.value.length !== 2) return toast.warning('请选择两个节点后连接')
  let [source, target] = [...selectedNodes.value].sort((a, b) => a.position.x - b.position.x)
  if (!canConnect(source.type, target.type, store.workspaceType) && canConnect(target.type, source.type, store.workspaceType)) [source, target] = [target, source]
  const incomingConnections = store.edges
    .filter((edge) => edge.target === target.id)
    .map((edge) => ({ targetHandle: edge.targetHandle, type: nodes.value.find((node) => node.id === edge.source)?.type }))
  const targetHandle = inferTargetHandle(source, target.type, incomingConnections)
  const error = getConnectionError(source.type, target.type, incomingConnections.map(({ type }) => type).filter(Boolean), store.workspaceType, targetHandle, incomingConnections)
  if (error) return toast.warning(error)
  if (!store.addEdge({ source: source.id, target: target.id, ...(targetHandle ? { targetHandle } : {}) })) toast.warning('节点已经连接')
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

function openEdgeContextMenu({ event, edge }) {
  event.preventDefault()
  contextMenu.value = { x: event.clientX, y: event.clientY, edgeId: edge.id }
}

function runContextAction(action) {
  store[action](action === 'deleteEdge' ? contextMenu.value.edgeId : contextMenu.value.nodeId)
  contextMenu.value = null
}

function resetPointerMode() { pointerMode.value = null }

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

function createPaneNode(type) {
  store.addNode(type, contextMenu.value.position)
  contextMenu.value = null
}

const submenuOpensLeft = computed(() => (contextMenu.value?.x || 0) + 478 > window.innerWidth)

useCanvasShortcuts({
  canvasTool,
  pointerMode,
  shortcutPanelOpen,
  selectedNodes,
  generationPanel,
  openCreateMenu: openShortcutCreateMenu,
  selectTool: selectCanvasTool,
  fitView,
  undo,
  redo,
  groupSelected: () => store.groupSelected(),
  ungroupSelected,
  duplicateSelected: () => store.duplicateSelected(),
  connectSelected,
  zoomIn,
  zoomOut,
})

function updateViewport(value) { store.setViewport(value) }

async function finishCanvasSetup() {
  if (readyEmitted) return
  readyEmitted = true
  setViewport(store.viewportData)
  await nextTick()
  emit('ready')
}

async function pasteFromMenu() {
  const position = contextMenu.value.position
  contextMenu.value = null
  return pasteFromClipboard(position)
}

const { enable: enableAutosave, saveBeforeLeave, retrySave, cancelScheduledSave } = useCanvasAutosave({
  store,
  getPayload: () => store.canvasPayload(),
  getViewport: () => viewport.value,
  confirm,
})

async function goHome() {
  if (await saveBeforeLeave()) emit('back')
}

async function signOut() {
  if (!(await saveBeforeLeave())) return
  stopAllGenerationPolling()
  await authStore.logout()
  store.$reset()
  emit('back')
}

defineExpose({ saveBeforeLeave })

watch(() => store.saveConflict, async (conflict) => {
  if (!conflict) return
  cancelScheduledSave()
  const shouldReload = await confirm({
    title: '画布内容已更新',
    message: '该画布已在其他页面保存。当前页面已停止自动保存，刷新后可继续编辑。',
    confirmText: '刷新画布',
    cancelText: '暂不刷新',
    tone: 'danger',
  })
  if (shouldReload) window.location.reload()
})
watch(historySnapshot, scheduleHistory)
onMounted(async () => {
  await authStore.refreshCredits().catch(() => {})
  try {
    await store.loadWorkspace(props.workspace)
  } catch (error) {
    toast.error(error.message || '画布版本不受支持')
    emit('back')
    return
  }
  initializeHistory()
  flowMounted.value = true
  await nextTick()
  if (!nodes.value.length) await finishCanvasSetup()
  enableAutosave()
})
onBeforeUnmount(() => {
  stopWorkspaceGenerationPolling(store.workspaceId)
  disposeGrouping()
  disposeHistory()
})
</script>

<template>
  <main class="canvas-page" :class="{ 'assets-open': assetsVisible, 'multi-selected': selectedNodes.length > 1, [`canvas-tool-${canvasTool}`]: canvasTool, [`cursor-${pointerMode}`]: pointerMode }" @pointermove="trackPastePoint" @pointerdown="contextMenu = null; toolMenuOpen = false" @pointerdown.capture="handleCanvasPointerDown" @pointerup.window="resetPointerMode" @pointercancel.window="resetPointerMode" @dragend="canvasDropActive = false">
    <input ref="uploadInput" type="file" :accept="pendingUpload ? uploadRules[pendingUpload.type].accept : ''" hidden @change="handlePaneUpload" />
    <CanvasHeader
      :workspace-name="workspace.name"
      :username="authStore.user?.username || '访客'"
      :credit-balance="authStore.user?.credit_balance || 0"
      :credit-frozen="authStore.user?.credit_frozen || 0"
      :save-status="store.saveStatus"
      @back="goHome"
      @logout="signOut"
      @retry-save="retrySave"
    />

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
      @selection-context-menu="openSelectionContextMenu"
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

    <component
      :is="selectedNodeRegistry?.panelComponent"
      v-if="selectedNodeRegistry?.panelComponent && !selectedNode.data.pasted"
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
      <AppButton v-if="selectedNodes.length > 1 && !selectedGroup && !selectedPartialGroup" size="sm" title="编组" @click="store.groupSelected"><Group :size="15" />编组</AppButton>
      <AppButton v-if="selectedPartialGroup" size="sm" title="移出编组" @click="ungroupSelected"><Ungroup :size="15" />移出编组</AppButton>
      <AppButton v-if="selectedGroup" size="sm" title="取消编组" @click="ungroupSelected"><Ungroup :size="15" />取消编组</AppButton>
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
        <AppButton @click="chooseUpload('audio')"><Music2 :size="15" /><span>音频</span></AppButton>
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
        <AppButton v-if="contextNodeIds.length > 1 && !contextCompleteGroup && !contextPartialGroup" @click="groupContextNodes"><Group :size="15" />编组</AppButton>
        <AppButton v-if="contextCompleteGroup" @click="ungroupContextNodes"><Ungroup :size="15" />取消编组</AppButton>
        <AppButton v-if="contextPartialGroup" @click="removeContextNodesFromGroup"><Ungroup :size="15" />移出编组</AppButton>
        <AppButton @click="duplicateContextNodes"><Copy :size="15" />创建副本</AppButton>
        <span v-if="contextNodeIds.length > 1" class="context-menu-divider"></span>
        <AppButton variant="danger" @click="deleteContextNodes"><Trash2 :size="15" />{{ contextNodeIds.length > 1 ? `删除所选（${contextNodeIds.length}）` : '删除' }}</AppButton>
      </template>
    </AppMenu>
  </main>
</template>
