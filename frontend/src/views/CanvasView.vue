<script setup>
import { computed, markRaw, ref } from 'vue'
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
import { mediaTypes } from '../config/mediaTypes'
import { useCanvasStore } from '../stores/canvas'

const store = useCanvasStore()
const { nodes, edges, groups } = storeToRefs(store)
const { project, fitView, findNode, setCenter, viewport, removeSelectedElements, addSelectedNodes } = useVueFlow()

const nodeTypes = Object.fromEntries(Object.keys(mediaTypes).map((type) => [type, markRaw(MediaNode)]))
const edgeTypes = { cinematic: markRaw(FlowEdge) }
const createMenu = ref(null)
const contextMenu = ref(null)
const connectionSource = ref(null)
const groupDrag = ref(null)
const pointerMode = ref(null)

const minimapVisible = ref(false)
const assetsVisible = ref(false)
const activeGroupId = ref(null)
const selectedNodes = computed(() => nodes.value.filter((node) => node.selected))
const selectedNode = computed(() => selectedNodes.value.length === 1 ? selectedNodes.value[0] : null)
const selectedGroup = computed(() => groups.value.find((group) => group.id === activeGroupId.value) || groups.value.find((group) => group.nodeIds.length === selectedNodes.value.length && group.nodeIds.every((id) => selectedNodes.value.some((node) => node.id === id))))
const contextGroup = computed(() => groups.value.find((group) => group.nodeIds.includes(contextMenu.value?.nodeId)))
const panelConfig = { width: 520, gap: 16, margin: 16 }
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
  return {
    left: `clamp(${panelConfig.margin}px, ${center - panelConfig.width / 2}px, calc(100vw - ${panelConfig.width + panelConfig.margin}px))`,
    top: `${bottom + panelConfig.gap}px`,
  }
})

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

function handleConnectEnd(event) {
  if (!connectionSource.value || event.target.closest('.vue-flow__handle')) {
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

function runContextAction(action) {
  action === 'groupSelected' ? store.groupSelected() : store[action](contextMenu.value.nodeId)
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
  if (event.target.closest('.selection-toolbar, .asset-drawer, .canvas-side-tools, .canvas-add-button, .node-create-menu, .generation-panel')) return
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
</script>

<template>
  <main class="canvas-page" :class="{ 'assets-open': assetsVisible, 'multi-selected': selectedNodes.length > 1, [`cursor-${pointerMode}`]: pointerMode }" @pointerdown="contextMenu = null" @pointerdown.capture="handleCanvasPointerDown" @pointerup.window="resetPointerMode" @pointercancel.window="resetPointerMode">
    <CanvasHeader />

    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :min-zoom="0.25"
      :max-zoom="1.5"
      :connection-radius="28"
      :delete-key-code="null"
      fit-view-on-init
      class="creative-flow"
      @connect="store.addEdge"
      @connect-start="handleConnectStart"
      @connect-end="handleConnectEnd"
      :selection-key-code="true"
      multi-selection-key-code="Shift"
      selection-mode="partial"
      select-nodes-on-drag
      :pan-on-drag="[1]"
      @node-context-menu="openContextMenu"
      @pane-click="contextMenu = null"
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
      :style="panelStyle"
    />

    <Transition name="asset-sidebar">
      <AssetDrawer v-if="assetsVisible" :nodes="nodes" :groups="groups" :active-group-id="selectedGroup?.id" @focus="focusNode" @focus-group="focusGroup" @rename-group="store.renameGroup" @close="assetsVisible = false" />
    </Transition>

    <aside class="canvas-side-tools">
      <button class="asset-toggle-button" title="资产" @click="assetsVisible = !assetsVisible"><Library :size="17" /><span>资产</span></button>
      <button title="整理画布" @click="fitView({ padding: 0.24, duration: 350 })"><Scan :size="17" /></button>
      <button title="切换小地图" @click="minimapVisible = !minimapVisible"><Maximize2 :size="17" /></button>
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
      <button v-if="selectedNodes.length > 1 && !selectedGroup" title="编组" @click="store.groupSelected"><Group :size="15" />编组</button>
      <button v-if="selectedGroup" title="解组" @click="ungroupSelected"><Ungroup :size="15" />解组</button>
    </div>

    <button class="canvas-add-button" title="添加节点" @click="openGlobalMenu"><Plus :size="24" /></button>

    <NodeCreateMenu
      v-if="createMenu"
      :point="createMenu.point"
      :contextual="Boolean(createMenu.sourceId)"
      @select="createNode"
      @close="createMenu = null"
    />

    <div v-if="contextMenu" class="context-menu" :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }" @pointerdown.stop>
      <button @click="runContextAction('duplicateNode')"><Copy :size="15" />创建副本</button>
      <button v-if="selectedNodes.length > 1 && !contextGroup" @click="runContextAction('groupSelected')"><Group :size="15" />编组</button>
      <button v-if="contextGroup" @click="runContextAction('ungroupNode')"><Ungroup :size="15" />解组</button>
      <span v-if="selectedNodes.length > 1 || contextGroup"></span>
      <button class="danger" @click="runContextAction('deleteNode')"><Trash2 :size="15" />删除</button>
    </div>
  </main>
</template>
