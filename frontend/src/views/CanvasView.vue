<script setup>
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import { Copy, Group, Library, Maximize2, Plus, Scan, Trash2, Ungroup } from 'lucide-vue-next'
import AssetDrawer from '../components/canvas/AssetDrawer.vue'
import CanvasHeader from '../components/canvas/CanvasHeader.vue'
import FlowEdge from '../components/canvas/FlowEdge.vue'
import GenerationPanel from '../components/canvas/GenerationPanel.vue'
import MediaNode from '../components/canvas/MediaNode.vue'
import NodeCreateMenu from '../components/canvas/NodeCreateMenu.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppMenu from '../components/ui/AppMenu.vue'
import { mediaTypes } from '../config/mediaTypes'
import { useAuthStore } from '../stores/auth'
import { useCanvasStore } from '../stores/canvas'

const store = useCanvasStore()
const authStore = useAuthStore()
const props = defineProps({ workspace: { type: Object, required: true } })
const emit = defineEmits(['back'])
const { nodes, edges, groups, saveStatus } = storeToRefs(store)
const { project, fitView, findNode, setCenter, setViewport, viewport, removeSelectedElements, addSelectedNodes } = useVueFlow()

const nodeTypes = Object.fromEntries(Object.keys(mediaTypes).map((type) => [type, markRaw(MediaNode)]))
const edgeTypes = { cinematic: markRaw(FlowEdge) }
const createMenu = ref(null)
const contextMenu = ref(null)
const connectionSource = ref(null)
const groupDrag = ref(null)
const pointerMode = ref(null)
let saveTimer = null

const minimapVisible = ref(false)
const assetsVisible = ref(false)
const activeGroupId = ref(null)
const selectedNodes = computed(() => nodes.value.filter((node) => node.selected))
const selectedNode = computed(() => selectedNodes.value.length === 1 ? selectedNodes.value[0] : null)
const selectedGroup = computed(() => groups.value.find((group) => group.id === activeGroupId.value) || groups.value.find((group) => group.nodeIds.length === selectedNodes.value.length && group.nodeIds.every((id) => selectedNodes.value.some((node) => node.id === id))))
const contextGroup = computed(() => groups.value.find((group) => group.nodeIds.includes(contextMenu.value?.nodeId)))
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
function openGlobalMenu() {
  const centerX = window.innerWidth / 2 + (assetsVisible.value ? 146 : 0)
  createMenu.value = {
    point: { x: centerX - 120, y: window.innerHeight - 390 },
    position: project({ x: centerX, y: window.innerHeight / 2 }),
    sourceId: null,
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
  if (event.target.closest('.nodrag, .selection-toolbar, .asset-drawer, .canvas-side-tools, .canvas-add-button, .node-create-menu, .generation-panel')) return
  if (event.button === 1) {
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

function ungroupSelected() {
  store.ungroupNode(selectedGroup.value.nodeIds[0])
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

function scheduleSave() {
  if (!store.ready) return
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => store.saveCanvas().catch(() => {}), 800)
}

function updateViewport(value) {
  store.setViewport(value)
}

function addAsset(asset) {
  const centerX = window.innerWidth / 2 + (assetsVisible.value ? 146 : 0)
  store.addAssetNode(asset, project({ x: centerX, y: window.innerHeight / 2 }))
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
onMounted(async () => {
  await store.loadWorkspace(props.workspace)
  await nextTick()
  setViewport(store.viewportData)
})
onBeforeUnmount(() => window.clearTimeout(saveTimer))
</script>

<template>
  <main class="canvas-page" :class="{ 'assets-open': assetsVisible, 'multi-selected': selectedNodes.length > 1, [`cursor-${pointerMode}`]: pointerMode }" @pointerdown="contextMenu = null" @pointerdown.capture="handleCanvasPointerDown" @pointerup.window="resetPointerMode" @pointercancel.window="resetPointerMode">
    <CanvasHeader :workspace-name="workspace.name" :save-status="saveStatus" :username="authStore.user.username" @back="goHome" @logout="signOut" />

    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :min-zoom="0.1"
      :max-zoom="8"
      :connection-radius="28"
      :delete-key-code="['Backspace', 'Delete']"
      class="creative-flow"
      @connect="handleConnect"
      @connect-start="handleConnectStart"
      @connect-end="handleConnectEnd"
      :selection-key-code="true"
      multi-selection-key-code="Shift"
      selection-mode="partial"
      select-nodes-on-drag
      :pan-on-drag="[1]"
      @node-context-menu="openContextMenu"
      @edge-context-menu="openEdgeContextMenu"
      @pane-click="contextMenu = null"
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
      v-if="selectedNode"
      :node-id="selectedNode.id"
      :type="selectedNode.type"
      :data="selectedNode.data"
    />

    <Transition name="asset-sidebar">
      <AssetDrawer v-if="assetsVisible" :nodes="nodes" :groups="groups" :active-group-id="selectedGroup?.id" @focus="focusNode" @focus-group="focusGroup" @rename-group="store.renameGroup" @add="addAsset" @close="assetsVisible = false" />
    </Transition>

    <aside class="canvas-side-tools">
      <AppButton class="asset-toggle-button" title="资产" @click="assetsVisible = !assetsVisible"><Library :size="17" /><span>资产</span></AppButton>
      <AppButton icon-only title="整理画布" @click="fitView({ padding: 0.24, duration: 350 })"><Scan :size="17" /></AppButton>
      <AppButton icon-only title="切换小地图" @click="minimapVisible = !minimapVisible"><Maximize2 :size="17" /></AppButton>
      <span>{{ Math.round(viewport.zoom * 100) }}%</span>
    </aside>

    <div v-if="selectedNodes.length > 1 || selectedGroup" class="selection-toolbar" :style="selectionToolbarStyle">
      <input
        v-if="selectedGroup"
        class="selection-group-title"
        :value="selectedGroup.title || '未命名编组'"
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

    <AppButton class="canvas-add-button" icon-only variant="primary" title="添加节点" @click="openGlobalMenu"><Plus :size="23" /></AppButton>

    <NodeCreateMenu
      v-if="createMenu"
      :point="createMenu.point"
      :contextual="Boolean(createMenu.sourceId)"
      :source-id="createMenu.sourceId"
      @select="createNode"
      @close="createMenu = null"
    />

    <AppMenu v-if="contextMenu" class="context-menu" :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }" @pointerdown.stop>
      <AppButton v-if="contextMenu.edgeId" variant="danger" @click="runContextAction('deleteEdge')"><Trash2 :size="15" />删除连接</AppButton>
      <template v-else>
        <AppButton @click="runContextAction('duplicateNode')"><Copy :size="15" />创建副本</AppButton>
        <AppButton v-if="selectedNodes.length > 1 && !contextGroup" @click="runContextAction('groupSelected')"><Group :size="15" />编组</AppButton>
        <AppButton v-if="contextGroup" @click="runContextAction('ungroupNode')"><Ungroup :size="15" />解组</AppButton>
        <span v-if="selectedNodes.length > 1 || contextGroup"></span>
        <AppButton variant="danger" @click="runContextAction('deleteNode')"><Trash2 :size="15" />删除</AppButton>
      </template>
    </AppMenu>
  </main>
</template>
