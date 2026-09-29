<script setup>
import { useI18n } from 'vue-i18n'
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
import { isEditableProductConnection } from '../../config/canvas/ecommerceWorkflows'
import { getNodeRegistry, nodeRegistry } from '../../config/canvas/nodeRegistry'
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

const { t } = useI18n()

const store = useCanvasStore()
const authStore = useAuthStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const props = defineProps({ workspace: { type: Object, required: true } })
const emit = defineEmits(['back', 'ready'])
const { nodes, edges, groups } = storeToRefs(store)
const { project, screenToFlowCoordinate, fitView, findNode, setCenter, setViewport, updateNodeData, viewport, zoomIn, zoomOut, removeSelectedElements, addSelectedNodes } = useVueFlow()

const nodeTypes = Object.fromEntries(getNodeTypes(props.workspace.workspace_type).map((type) => [type, getNodeRegistry(type).component]))
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

function createNode(option) {
  if (option.kind === 'workflow') store.addEcommerceWorkflow(option.type, createMenu.value.position)
  else store.addNode(option.type, createMenu.value.position, createMenu.value.sourceId)
  createMenu.value = null
}

function handleConnectStart({ nodeId, handleType }) {
  const node = nodes.value.find((item) => item.id === nodeId)
  const sourceConnectable = !node?.data.workflowId || node.data.workflowRole === 'product'
  connectionSource.value = handleType === 'source' && sourceConnectable ? nodeId : null
}

function handleConnect(connection) {
  const source = nodes.value.find((node) => node.id === connection.source)
  const target = nodes.value.find((node) => node.id === connection.target)
  if ((source?.data.workflowId || target?.data.workflowId) && !isEditableProductConnection(source, target)) {
    connectionSource.value = null
    return toast.warning(t('canvas.managedConnections'))
  }
  const incomingConnections = store.edges
    .filter((edge) => edge.target === target?.id)
    .map((edge) => ({ targetHandle: edge.targetHandle, type: nodes.value.find((node) => node.id === edge.source)?.type }))
  const targetHandle = connection.targetHandle || inferTargetHandle(source, target?.type, incomingConnections)
  const normalizedConnection = targetHandle ? { ...connection, targetHandle } : connection
  const error = source && target ? getConnectionError(source.type, target.type, incomingConnections.map(({ type }) => type).filter(Boolean), store.workspaceType, targetHandle, incomingConnections) : t('canvas.nodeMissing')
  if (error) toast.warning(error)
  else if (!store.addEdge(normalizedConnection)) toast.warning(t('canvas.alreadyConnected'))
  connectionSource.value = null
}

function connectSelected() {
  if (selectedNodes.value.length !== 2) return toast.warning(t('canvas.selectTwoNodes'))
  let [source, target] = [...selectedNodes.value].sort((a, b) => a.position.x - b.position.x)
  if (!canConnect(source.type, target.type, store.workspaceType) && canConnect(target.type, source.type, store.workspaceType)) [source, target] = [target, source]
  if ((source.data?.workflowId || target.data?.workflowId) && !isEditableProductConnection(source, target)) return toast.warning(t('canvas.managedConnections'))
  const incomingConnections = store.edges
    .filter((edge) => edge.target === target.id)
    .map((edge) => ({ targetHandle: edge.targetHandle, type: nodes.value.find((node) => node.id === edge.source)?.type }))
  const targetHandle = inferTargetHandle(source, target.type, incomingConnections)
  const error = getConnectionError(source.type, target.type, incomingConnections.map(({ type }) => type).filter(Boolean), store.workspaceType, targetHandle, incomingConnections)
  if (error) return toast.warning(error)
  if (!store.addEdge({ source: source.id, target: target.id, ...(targetHandle ? { targetHandle } : {}) })) toast.warning(t('canvas.alreadyConnected'))
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
  if (edge.workflowId) return toast.warning(t('canvas.managedConnectionDelete'))
  contextMenu.value = { x: event.clientX, y: event.clientY, edgeId: edge.id }
}

function handleNodeContextMenu(payload) {
  if (payload.node.data?.workflowId) {
    payload.event.preventDefault()
    if (!payload.node.data.workflowRoot) return
    store.selectNodes([payload.node.id])
  }
  openContextMenu(payload)
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

function createPaneNode(option) {
  if (option.kind === 'workflow') store.addEcommerceWorkflow(option.type, contextMenu.value.position)
  else store.addNode(option.type, contextMenu.value.position)
  contextMenu.value = null
}

async function deleteAssetNode(id) {
  const node = nodes.value.find((item) => item.id === id)
  if (!node?.data.workflowId) return store.deleteNode(id)
  if (!node.data.workflowRoot) return toast.warning(t('canvas.deleteFromWorkflowRoot'))
  const approved = await confirm({
    title: t('canvas.deleteNamedWorkflow', { p0: node.data.workflowType === 'product' ? t('canvas.productCreation') : t('canvas.outfit') }),
    message: t('canvas.deleteWorkflowConfirm'),
    confirmText: t('canvas.deleteWorkflow'),
    tone: 'danger',
  })
  if (approved) store.deleteWorkflow(node.data.workflowId)
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
  deleteSelected: deleteSelectedNodes,
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

const { enable: enableAutosave, saveBeforeLeave, cancelScheduledSave } = useCanvasAutosave({
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
    title: t('canvas.canvasUpdated'),
    message: t('canvas.canvasConflictDescription'),
    confirmText: t('canvas.refreshCanvas'),
    cancelText: t('canvas.notNow'),
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
    toast.error(error.message || t('canvas.unsupportedCanvasVersion'))
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
      :username="authStore.user?.username || t('canvas.guest')"
      :credit-balance="authStore.user?.credit_balance || 0"
      :credit-frozen="authStore.user?.credit_frozen || 0"
      @back="goHome"
      @logout="signOut"
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
      :delete-key-code="null"
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
      @node-context-menu="handleNodeContextMenu"
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
      <AssetDrawer v-if="assetsVisible" :nodes="nodes" :groups="groups" :active-group-id="selectedGroup?.id" @focus="focusNode" @focus-group="focusGroup" @rename-node="store.renameNode" @rename-group="store.renameGroup" @delete-node="deleteAssetNode" @delete-group="store.deleteGroup" @close="assetsVisible = false" />
    </Transition>

    <aside class="canvas-side-tools">
      <AppButton class="asset-toggle-button" :title="t('canvas.assets')" @click="assetsVisible = !assetsVisible"><Library :size="17" /><span>{{ t('canvas.assets') }}</span></AppButton>
      <AppTooltip :text="t('canvas.arrangeCanvas')"><AppButton icon-only :aria-label="t('canvas.arrangeCanvas')" @click="fitView({ padding: 0.24, duration: 350 })"><Scan :size="17" /></AppButton></AppTooltip>
      <AppTooltip :text="t('canvas.toggleMinimap')"><AppButton icon-only :aria-label="t('canvas.toggleMinimap')" @click="minimapVisible = !minimapVisible"><Maximize2 :size="17" /></AppButton></AppTooltip>
      <span>{{ Math.round(viewport.zoom * 100) }}%</span>
    </aside>

    <div v-if="selectedNodes.length > 1 || selectedGroup" class="selection-toolbar" :style="selectionToolbarStyle">
      <AppInput
        v-if="selectedGroup"
        class="selection-group-title"
        :model-value="selectedGroup.title"
        :placeholder="t('canvas.unnamedGroup')"
        :aria-label="t('canvas.groupTitle')"
        @input="store.renameGroup(selectedGroup.id, $event.target.value)"
        @blur="store.renameGroup(selectedGroup.id, $event.target.value)"
        @keydown.enter="$event.target.blur()"
        @keydown.stop
      />
      <span>{{ t('canvas.nodeCount', { p0: selectedGroup ? selectedGroup.nodeIds.length : selectedNodes.length }) }}</span>
      <AppButton v-if="selectedNodes.length > 1 && !selectedGroup && !selectedPartialGroup && !selectedContainsWorkflow" size="sm" :title="t('canvas.group')" @click="store.groupSelected"><Group :size="15" />{{ t('canvas.group') }}</AppButton>
      <AppButton v-if="selectedPartialGroup" size="sm" :title="t('canvas.removeFromGroup')" @click="ungroupSelected"><Ungroup :size="15" />{{ t('canvas.removeFromGroup') }}</AppButton>
      <AppButton v-if="selectedGroup" size="sm" :title="t('canvas.ungroup')" @click="ungroupSelected"><Ungroup :size="15" />{{ t('canvas.ungroup') }}</AppButton>
    </div>

    <nav class="canvas-bottom-toolbar" :aria-label="t('canvas.canvasTools')">
      <AppTooltip :text="t('canvas.newNode')">
        <AppButton class="canvas-add-button" icon-only variant="primary" :aria-label="t('canvas.newNode')" @click="openGlobalMenu"><Plus :size="19" /></AppButton>
      </AppTooltip>
      <div class="canvas-tool-picker" @pointerdown.stop>
        <AppTooltip :text="canvasTool === 'move' ? t('canvas.moveToolShortcut') : t('canvas.handToolShortcut')">
          <AppButton class="canvas-tool-button" :class="{ active: toolMenuOpen }" icon-only :aria-label="t('canvas.switchTool')" aria-haspopup="menu" :aria-expanded="toolMenuOpen" @click="toggleToolMenu">
            <MousePointer2 v-if="canvasTool === 'move'" :size="18" />
            <Hand v-else :size="18" />
          </AppButton>
        </AppTooltip>
        <AppMenu v-if="toolMenuOpen" class="canvas-tool-menu" @pointerdown.stop>
          <AppButton :class="{ active: canvasTool === 'move' }" @click="selectCanvasTool('move')"><MousePointer2 :size="17" /><strong>{{ t('canvas.move') }}</strong><kbd>V</kbd></AppButton>
          <AppButton :class="{ active: canvasTool === 'hand' }" @click="selectCanvasTool('hand')"><Hand :size="17" /><strong>{{ t('canvas.handTool') }}</strong><kbd>H</kbd></AppButton>
        </AppMenu>
      </div>
      <span class="canvas-bottom-divider"></span>
      <AppTooltip :text="t('canvas.shortcuts')">
        <AppButton class="canvas-bottom-secondary shortcut-toggle" icon-only :aria-label="t('canvas.shortcuts')" :aria-pressed="shortcutPanelOpen" @click="shortcutPanelOpen = !shortcutPanelOpen"><Keyboard :size="18" /></AppButton>
      </AppTooltip>
      <AppTooltip :text="t('canvas.tutorialSoon')">
        <AppButton class="canvas-bottom-secondary" icon-only :aria-label="t('canvas.tutorialSoon')"><CircleHelp :size="18" /></AppButton>
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
      <AppButton v-if="contextMenu.edgeId" variant="danger" @click="runContextAction('deleteEdge')"><Trash2 :size="15" />{{ t('canvas.deleteConnection') }}</AppButton>
      <template v-else-if="contextMenu.kind === 'pane'">
        <p class="context-menu-label">{{ t('canvas.upload') }}</p>
        <AppButton @click="chooseUpload('image')"><ImageIcon :size="15" /><span>{{ t('canvas.image') }}</span></AppButton>
        <AppButton @click="chooseUpload('video')"><Video :size="15" /><span>{{ t('canvas.video') }}</span></AppButton>
        <AppButton @click="chooseUpload('audio')"><Music2 :size="15" /><span>{{ t('canvas.audio') }}</span></AppButton>
        <span class="context-menu-divider"></span>
        <div class="context-submenu-trigger" @mouseenter="contextMenu.submenuOpen = true" @mouseleave="contextMenu.submenuOpen = false">
          <AppButton @click="contextMenu.submenuOpen = true"><Plus :size="15" /><span>{{ t('canvas.addNode') }}</span><ChevronRight class="context-menu-chevron" :size="14" /></AppButton>
          <AppMenu v-if="contextMenu.submenuOpen" class="context-submenu" :class="{ 'context-submenu--left': submenuOpensLeft }" @pointerdown.stop>
            <NodeTypeMenu @select="createPaneNode" />
          </AppMenu>
        </div>
        <span class="context-menu-divider"></span>
        <AppButton :disabled="!canUndo" @click="undo"><Undo2 :size="15" /><span>{{ t('canvas.undo') }}</span><kbd>Ctrl+Z</kbd></AppButton>
        <AppButton :disabled="!canRedo" @click="redo"><Redo2 :size="15" /><span>{{ t('canvas.redo') }}</span><kbd>Ctrl+Y</kbd></AppButton>
        <span class="context-menu-divider"></span>
        <AppButton @click="pasteFromMenu"><Clipboard :size="15" /><span>{{ t('canvas.paste') }}</span><kbd>Ctrl+V</kbd></AppButton>
      </template>
      <template v-else>
        <AppButton v-if="contextNodeIds.length > 1 && !contextCompleteGroup && !contextPartialGroup && !contextContainsWorkflow" @click="groupContextNodes"><Group :size="15" />{{ t('canvas.group') }}</AppButton>
        <AppButton v-if="contextCompleteGroup" @click="ungroupContextNodes"><Ungroup :size="15" />{{ t('canvas.ungroup') }}</AppButton>
        <AppButton v-if="contextPartialGroup" @click="removeContextNodesFromGroup"><Ungroup :size="15" />{{ t('canvas.removeFromGroup') }}</AppButton>
        <AppButton v-if="!contextContainsWorkflow" @click="duplicateContextNodes"><Copy :size="15" />{{ t('canvas.duplicate') }}</AppButton>
        <span v-if="contextNodeIds.length > 1" class="context-menu-divider"></span>
        <AppButton v-if="!contextContainsWorkflow || contextWorkflowRoot" variant="danger" @click="deleteContextNodes"><Trash2 :size="15" />{{ contextWorkflowRoot ? t('canvas.deleteWorkflow') : contextNodeIds.length > 1 ? t('canvas.deleteSelectedCount', { p0: contextNodeIds.length }) : t('canvas.delete') }}</AppButton>
      </template>
    </AppMenu>
  </main>
</template>
