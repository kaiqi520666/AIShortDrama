<script setup>
import { computed, ref } from 'vue'
import { ChevronDown, ChevronRight, FileText, Folder, Image, LayoutGrid, Library, Music2, Package, Pencil, RefreshCw, Trash2, Video, Workflow, X } from 'lucide-vue-next'
import { deleteAsset, listAssets, renameAsset } from '../../api/assets'
import { useGlobalConfirm, useGlobalPrompt, useGlobalToast } from '../../composables/useGlobalUI'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppTabs from '../ui/AppTabs.vue'
import EmptyState from '../ui/EmptyState.vue'

const props = defineProps({
  nodes: { type: Array, required: true },
  groups: { type: Array, required: true },
  activeGroupId: { type: String, default: null },
})
const emit = defineEmits(['focus', 'focus-group', 'rename-node', 'rename-group', 'delete-node', 'delete-group', 'close'])
const icons = { text: FileText, image: Image, video: Video, audio: Music2, product: Package }
const drawerTabs = [{ value: 'nodes', label: '节点', icon: Workflow }, { value: 'assets', label: '资产', icon: Library }]
const assetTypeOptions = [
  { value: '', label: '全部', icon: LayoutGrid },
  { value: 'image', label: '图片', icon: Image },
  { value: 'video', label: '视频', icon: Video },
  { value: 'audio', label: '音频', icon: Music2 },
]
const PAGE_SIZE = 30
const activeTab = ref('nodes')
const assetType = ref('')
const assets = ref([])
const loadingAssets = ref(false)
const assetError = ref('')
const assetHasMore = ref(true)
const assetLoaded = ref(false)
const assetOffset = ref(0)
const nodeLimit = ref(PAGE_SIZE)
const collapsedGroupIds = ref([])
const editingGroupId = ref(null)
const draggingItem = ref('')
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const { prompt } = useGlobalPrompt()
const sortedNodes = computed(() => props.nodes.toSorted((a, b) => a.position.x - b.position.x || a.position.y - b.position.y))
const ungroupedNodes = computed(() => sortedNodes.value.filter((node) => !props.groups.some((group) => group.nodeIds.includes(node.id))))
const groupItems = computed(() => props.groups.map((group) => ({
  ...group,
  active: group.id === props.activeGroupId,
  title: group.title || '未命名编组',
  nodes: sortedNodes.value.filter((node) => group.nodeIds.includes(node.id)),
})))
const nodeSections = computed(() => {
  let remaining = nodeLimit.value
  const ungrouped = ungroupedNodes.value.slice(0, remaining)
  remaining -= ungrouped.length
  const groups = groupItems.value.map((group) => {
    if (collapsedGroupIds.value.includes(group.id)) return { ...group, nodes: [] }
    const nodes = group.nodes.slice(0, Math.max(0, remaining))
    remaining -= nodes.length
    return { ...group, nodes }
  })
  return { ungrouped, groups }
})
const visibleNodeCount = computed(() => ungroupedNodes.value.length + groupItems.value.reduce(
  (total, group) => total + (collapsedGroupIds.value.includes(group.id) ? 0 : group.nodes.length),
  0,
))
const nodeHasMore = computed(() => visibleNodeCount.value > nodeLimit.value)
let assetRequestId = 0

function startRename(id) {
  editingGroupId.value = id
}

function renameGroup(id, event) {
  emit('rename-group', id, event.target.value)
}

function startAssetDrag(event, asset) {
  draggingItem.value = `asset:${asset.id}`
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-mooncut-canvas-item', JSON.stringify({ kind: 'asset', asset }))
}

async function loadAssetItems({ reset = false } = {}) {
  if (loadingAssets.value && !reset) return
  if (!reset && (!assetLoaded.value || !assetHasMore.value)) return
  const requestId = ++assetRequestId
  if (reset) {
    assets.value = []
    assetOffset.value = 0
    assetHasMore.value = true
    assetError.value = ''
  }
  loadingAssets.value = true
  assetError.value = ''
  try {
    const result = await listAssets(assetType.value, { limit: PAGE_SIZE, offset: assetOffset.value })
    if (result.code !== 0) throw new Error(result.message)
    if (requestId !== assetRequestId) return
    const items = result.data
    const existingIds = new Set(assets.value.map((item) => item.id))
    assets.value = [...assets.value, ...items.filter((item) => !existingIds.has(item.id))]
    assetOffset.value += items.length
    assetHasMore.value = items.length === PAGE_SIZE
    assetLoaded.value = true
  } catch (error) {
    if (requestId !== assetRequestId) return
    assetError.value = error.response?.data?.message || error.message || '资产加载失败'
  } finally {
    if (requestId === assetRequestId) loadingAssets.value = false
  }
}

async function renameAssetItem(asset) {
  const name = await prompt({
    title: '重命名资产',
    message: '输入新的资产名称',
    value: asset.name,
    placeholder: '资产名称',
    maxLength: 255,
  })
  if (!name || name === asset.name) return
  try {
    const result = await renameAsset(asset.id, name)
    if (result.code !== 0) throw new Error(result.message)
    Object.assign(asset, result.data)
    toast.success('资产名称已更新')
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '资产重命名失败')
  }
}

async function deleteAssetItem(asset) {
  const accepted = await confirm({
    title: '删除资产',
    message: `确定删除“${asset.name}”吗？画布中已使用的节点不会被删除。`,
    confirmText: '删除',
    tone: 'danger',
  })
  if (!accepted) return
  try {
    const result = await deleteAsset(asset.id)
    if (result.code !== 0) throw new Error(result.message)
    assets.value = assets.value.filter((item) => item.id !== asset.id)
    assetOffset.value = Math.max(0, assetOffset.value - 1)
    toast.success('资产已删除')
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '资产删除失败')
  }
}

async function deleteNodeItem(node) {
  const accepted = await confirm({
    title: '删除节点',
    message: `确定删除“${node.data.title}”吗？相关连线也会一并删除。`,
    confirmText: '删除',
    tone: 'danger',
  })
  if (accepted) emit('delete-node', node.id)
}

async function renameNodeItem(node) {
  const currentTitle = node.data.title || '未命名节点'
  const title = await prompt({
    title: '重命名节点',
    message: '输入新的节点名称',
    value: currentTitle,
    placeholder: '节点名称',
    maxLength: 100,
  })
  if (!title || title.trim() === currentTitle) return
  emit('rename-node', node.id, title.trim())
}

async function deleteGroupItem(group) {
  const accepted = await confirm({
    title: '删除编组',
    message: `确定删除“${group.title}”及其中的 ${group.nodes.length} 个节点吗？相关连线也会一并删除。`,
    confirmText: '全部删除',
    tone: 'danger',
  })
  if (accepted) emit('delete-group', group.id)
}

function selectAssetType(type) {
  if (assetType.value === type && assetLoaded.value) return
  assetType.value = type
  loadAssetItems({ reset: true })
}

function selectTab(tab) {
  activeTab.value = tab
  if (tab === 'assets' && !assetLoaded.value) loadAssetItems({ reset: true })
}

function handleNodeScroll(event) {
  const target = event.currentTarget
  if (nodeHasMore.value && target.scrollHeight - target.scrollTop - target.clientHeight < 120) {
    nodeLimit.value += PAGE_SIZE
  }
}

function handleAssetScroll(event) {
  const target = event.currentTarget
  if (assetHasMore.value && target.scrollHeight - target.scrollTop - target.clientHeight < 120) {
    loadAssetItems()
  }
}
</script>

<template>
  <aside class="asset-drawer">
    <header>
      <strong>资产</strong>
      <span>{{ activeTab === 'nodes' ? nodes.length : `${assets.length}${assetHasMore ? '+' : ''}` }}</span>
      <AppButton v-if="activeTab === 'assets'" icon-only size="sm" title="刷新资产" @click="loadAssetItems({ reset: true })"><RefreshCw :size="15" /></AppButton>
      <AppButton icon-only size="sm" title="关闭资产" @click="emit('close')"><X :size="17" /></AppButton>
    </header>

    <AppTabs class="asset-tabs" :model-value="activeTab" :options="drawerTabs" aria-label="资产面板" @update:model-value="selectTab" />

    <div v-if="activeTab === 'nodes'" class="asset-list" @scroll.passive="handleNodeScroll">
      <EmptyState v-if="!nodes.length" compact title="暂无节点" description="在画布中创建节点后会显示在这里" />
      <div v-for="node in nodeSections.ungrouped" :key="node.id" class="asset-node-row">
        <AppButton
          class="asset-item"
          :class="{ active: node.selected }"
          @click="emit('focus', node.id)"
        >
          <span class="asset-preview">
            <img v-if="node.type === 'image' && node.data.asset" :src="buildOssImageUrl(node.data.asset)" :alt="node.data.title" draggable="false" />
            <img v-else-if="node.type === 'video' && node.data.poster" :src="node.data.poster" :alt="node.data.title" draggable="false" />
            <component v-else :is="icons[node.type]" :size="20" />
          </span>
          <span>{{ node.data.title }}</span>
        </AppButton>
        <AppButton class="asset-row-action asset-row-edit" icon-only size="sm" :title="`重命名 ${node.data.title}`" :aria-label="`重命名 ${node.data.title}`" @click.stop="renameNodeItem(node)"><Pencil :size="14" /></AppButton>
        <AppButton class="asset-row-delete" icon-only size="sm" variant="danger" :title="`删除 ${node.data.title}`" :aria-label="`删除 ${node.data.title}`" @click.stop="deleteNodeItem(node)"><Trash2 :size="14" /></AppButton>
      </div>

      <section v-for="group in nodeSections.groups" :key="group.id" class="asset-group">
        <div class="asset-group-header">
          <AppButton class="asset-group-row" :class="{ active: group.active }" @click="emit('focus-group', group.id)">
            <span class="asset-group-toggle" @click.stop="collapsedGroupIds = collapsedGroupIds.includes(group.id) ? collapsedGroupIds.filter((id) => id !== group.id) : [...collapsedGroupIds, group.id]">
              <ChevronRight v-if="collapsedGroupIds.includes(group.id)" :size="14" />
              <ChevronDown v-else :size="14" />
            </span>
            <Folder :size="16" />
            <AppInput
              v-if="editingGroupId === group.id"
              class="asset-group-title-input"
              :model-value="group.title"
              aria-label="编组名称"
              @click.stop
              @input="renameGroup(group.id, $event)"
              @blur="editingGroupId = null"
              @keydown.enter="editingGroupId = null"
              @keydown.esc="editingGroupId = null"
            />
            <span v-else class="asset-group-title" @dblclick.stop="startRename(group.id)">{{ group.title }}</span>
            <small>{{ group.nodes.length }}</small>
          </AppButton>
          <AppButton class="asset-row-delete" icon-only size="sm" variant="danger" :title="`删除 ${group.title}`" :aria-label="`删除 ${group.title}`" @click.stop="deleteGroupItem(group)"><Trash2 :size="14" /></AppButton>
        </div>

        <div v-if="!collapsedGroupIds.includes(group.id)" class="asset-group-items">
          <div v-for="node in group.nodes" :key="node.id" class="asset-node-row">
            <AppButton
              class="asset-item"
              :class="{ active: node.selected }"
              @click="emit('focus', node.id)"
            >
              <span class="asset-preview">
                <img v-if="node.type === 'image' && node.data.asset" :src="buildOssImageUrl(node.data.asset)" :alt="node.data.title" draggable="false" />
                <img v-else-if="node.type === 'video' && node.data.poster" :src="node.data.poster" :alt="node.data.title" draggable="false" />
                <component v-else :is="icons[node.type]" :size="20" />
              </span>
              <span>{{ node.data.title }}</span>
            </AppButton>
            <AppButton class="asset-row-action asset-row-edit" icon-only size="sm" :title="`重命名 ${node.data.title}`" :aria-label="`重命名 ${node.data.title}`" @click.stop="renameNodeItem(node)"><Pencil :size="14" /></AppButton>
            <AppButton class="asset-row-delete" icon-only size="sm" variant="danger" :title="`删除 ${node.data.title}`" :aria-label="`删除 ${node.data.title}`" @click.stop="deleteNodeItem(node)"><Trash2 :size="14" /></AppButton>
          </div>
        </div>
      </section>
      <div v-if="nodeHasMore" class="asset-list-status">继续滚动加载</div>
    </div>

    <div v-else class="asset-library">
      <AppTabs class="asset-filters" :model-value="assetType" :options="assetTypeOptions" aria-label="资产类型" @update:model-value="selectAssetType" />
      <EmptyState v-if="loadingAssets && !assets.length" compact title="正在加载资产" loading />
      <EmptyState v-else-if="assetError && !assets.length" compact title="资产加载失败" :description="assetError" tone="error" />
      <EmptyState v-else-if="!assets.length" compact title="暂无资产" description="上传或生成的媒体会显示在这里" />
      <div v-else class="asset-list asset-library-list" @scroll.passive="handleAssetScroll">
        <div v-for="asset in assets" :key="asset.id" class="asset-library-row">
          <AppButton class="asset-item" :class="{ dragging: draggingItem === `asset:${asset.id}` }" :title="`拖动 ${asset.name}`" draggable="true" @dragstart="startAssetDrag($event, asset)" @dragend="draggingItem = ''">
            <span class="asset-preview">
              <img v-if="asset.media_type === 'image'" :src="buildOssImageUrl(asset.url)" :alt="asset.name" draggable="false" />
              <component v-else :is="icons[asset.media_type]" :size="20" />
            </span>
            <span>{{ asset.name }}</span>
          </AppButton>
          <span class="asset-library-actions">
            <AppButton icon-only size="sm" :title="`重命名 ${asset.name}`" @click="renameAssetItem(asset)"><Pencil :size="13" /></AppButton>
            <AppButton icon-only size="sm" variant="danger" :title="`删除 ${asset.name}`" @click="deleteAssetItem(asset)"><Trash2 :size="13" /></AppButton>
          </span>
        </div>
        <div v-if="loadingAssets" class="asset-list-status">正在加载</div>
        <div v-else-if="assetError" class="asset-list-status error">{{ assetError }}</div>
        <div v-else-if="assetHasMore" class="asset-list-status">继续滚动加载</div>
      </div>
    </div>
  </aside>
</template>
