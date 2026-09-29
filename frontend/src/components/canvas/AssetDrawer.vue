<script setup>
import { useI18n } from 'vue-i18n'
import { computed, ref } from 'vue'
import { ChevronDown, ChevronRight, FileText, Folder, Image, LayoutGrid, Library, Music2, Package, Pencil, RefreshCw, Trash2, Video, Workflow, X } from 'lucide-vue-next'
import { deleteAsset, listAssets, renameAsset } from '../../api/assets'
import { useGlobalConfirm, useGlobalPrompt, useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppTabs from '../ui/AppTabs.vue'
import EmptyState from '../ui/EmptyState.vue'

const { t } = useI18n()

const props = defineProps({
  nodes: { type: Array, required: true },
  groups: { type: Array, required: true },
  activeGroupId: { type: String, default: null },
})
const emit = defineEmits(['focus', 'focus-group', 'rename-node', 'rename-group', 'delete-node', 'delete-group', 'close'])
const icons = { text: FileText, image: Image, video: Video, audio: Music2, product: Package }
const drawerTabs = computed(() => ([{ value: 'nodes', label: t('canvas.nodes'), icon: Workflow }, { value: 'assets', label: t('canvas.assets'), icon: Library }]))
const assetTypeOptions = computed(() => ([
  { value: '', label: t('canvas.all'), icon: LayoutGrid },
  { value: 'image', label: t('canvas.image'), icon: Image },
  { value: 'video', label: t('canvas.video'), icon: Video },
  { value: 'audio', label: t('canvas.audio'), icon: Music2 },
]))
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
    assetError.value = getApiErrorMessage(error, t('canvas.assetsLoadFailed'))
  } finally {
    if (requestId === assetRequestId) loadingAssets.value = false
  }
}

async function renameAssetItem(asset) {
  const name = await prompt({
    title: t('canvas.renameAsset'),
    message: t('canvas.newAssetName'),
    value: asset.name,
    placeholder: t('canvas.assetName'),
    maxLength: 255,
  })
  if (!name || name === asset.name) return
  try {
    const result = await renameAsset(asset.id, name)
    if (result.code !== 0) throw new Error(result.message)
    Object.assign(asset, result.data)
    toast.success(t('canvas.assetRenamed'))
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('canvas.assetRenameFailed')))
  }
}

async function deleteAssetItem(asset) {
  const accepted = await confirm({
    title: t('canvas.deleteAsset'),
    message: t('canvas.deleteAssetConfirm', { p0: asset.name }),
    confirmText: t('canvas.delete'),
    tone: 'danger',
  })
  if (!accepted) return
  try {
    const result = await deleteAsset(asset.id)
    if (result.code !== 0) throw new Error(result.message)
    assets.value = assets.value.filter((item) => item.id !== asset.id)
    assetOffset.value = Math.max(0, assetOffset.value - 1)
    toast.success(t('canvas.assetDeleted'))
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('canvas.assetDeleteFailed')))
  }
}

async function deleteNodeItem(node) {
  const accepted = await confirm({
    title: t('canvas.deleteNode'),
    message: t('canvas.deleteNodeConfirm', { p0: node.data.title }),
    confirmText: t('canvas.delete'),
    tone: 'danger',
  })
  if (accepted) emit('delete-node', node.id)
}

async function renameNodeItem(node) {
  const currentTitle = node.data.title || ''
  const title = await prompt({
    title: t('canvas.renameNode'),
    message: t('canvas.newNodeName'),
    value: currentTitle,
    placeholder: t('canvas.nodeName'),
    maxLength: 100,
  })
  if (!title || title.trim() === currentTitle) return
  emit('rename-node', node.id, title.trim())
}

async function deleteGroupItem(group) {
  const accepted = await confirm({
    title: t('canvas.deleteGroup'),
    message: t('canvas.deleteGroupConfirm', { p0: group.title, p1: group.nodes.length }),
    confirmText: t('canvas.deleteAll'),
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
      <strong>{{ t('canvas.assets') }}</strong>
      <span>{{ activeTab === 'nodes' ? nodes.length : `${assets.length}${assetHasMore ? '+' : ''}` }}</span>
      <AppButton v-if="activeTab === 'assets'" icon-only size="sm" :title="t('canvas.refreshAssets')" @click="loadAssetItems({ reset: true })"><RefreshCw :size="15" /></AppButton>
      <AppButton icon-only size="sm" :title="t('canvas.closeAssets')" @click="emit('close')"><X :size="17" /></AppButton>
    </header>

    <AppTabs class="asset-tabs" :model-value="activeTab" :options="drawerTabs" :aria-label="t('canvas.assetPanel')" @update:model-value="selectTab" />

    <div v-if="activeTab === 'nodes'" class="asset-list" @scroll.passive="handleNodeScroll">
      <EmptyState v-if="!nodes.length" compact :title="t('canvas.noNodes')" :description="t('canvas.noNodesDescription')" />
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
        <AppButton class="asset-row-action asset-row-edit" icon-only size="sm" :title="t('canvas.renameNamed', { p0: node.data.title })" :aria-label="t('canvas.renameNamed', { p0: node.data.title })" @click.stop="renameNodeItem(node)"><Pencil :size="14" /></AppButton>
        <AppButton class="asset-row-delete" icon-only size="sm" variant="danger" :title="t('canvas.deleteNamed', { p0: node.data.title })" :aria-label="t('canvas.deleteNamed', { p0: node.data.title })" @click.stop="deleteNodeItem(node)"><Trash2 :size="14" /></AppButton>
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
              :placeholder="t('canvas.unnamedGroup')"
              :aria-label="t('canvas.groupName')"
              @click.stop
              @input="renameGroup(group.id, $event)"
              @blur="editingGroupId = null"
              @keydown.enter="editingGroupId = null"
              @keydown.esc="editingGroupId = null"
            />
            <span v-else class="asset-group-title" @dblclick.stop="startRename(group.id)">{{ group.title || t('canvas.unnamedGroup') }}</span>
            <small>{{ group.nodes.length }}</small>
          </AppButton>
          <AppButton class="asset-row-delete" icon-only size="sm" variant="danger" :title="t('canvas.deleteNamed', { p0: group.title })" :aria-label="t('canvas.deleteNamed', { p0: group.title })" @click.stop="deleteGroupItem(group)"><Trash2 :size="14" /></AppButton>
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
            <AppButton class="asset-row-action asset-row-edit" icon-only size="sm" :title="t('canvas.renameNamed', { p0: node.data.title })" :aria-label="t('canvas.renameNamed', { p0: node.data.title })" @click.stop="renameNodeItem(node)"><Pencil :size="14" /></AppButton>
            <AppButton class="asset-row-delete" icon-only size="sm" variant="danger" :title="t('canvas.deleteNamed', { p0: node.data.title })" :aria-label="t('canvas.deleteNamed', { p0: node.data.title })" @click.stop="deleteNodeItem(node)"><Trash2 :size="14" /></AppButton>
          </div>
        </div>
      </section>
      <div v-if="nodeHasMore" class="asset-list-status">{{ t('canvas.scrollToLoad') }}</div>
    </div>

    <div v-else class="asset-library">
      <AppTabs class="asset-filters" :model-value="assetType" :options="assetTypeOptions" :aria-label="t('canvas.assetType')" @update:model-value="selectAssetType" />
      <EmptyState v-if="loadingAssets && !assets.length" compact :title="t('canvas.loadingAssets')" loading />
      <EmptyState v-else-if="assetError && !assets.length" compact :title="t('canvas.assetsLoadFailed')" :description="assetError" tone="error" />
      <EmptyState v-else-if="!assets.length" compact :title="t('canvas.noAssets')" :description="t('canvas.noAssetsDescription')" />
      <div v-else class="asset-list asset-library-list" @scroll.passive="handleAssetScroll">
        <div v-for="asset in assets" :key="asset.id" class="asset-library-row">
          <AppButton class="asset-item" :class="{ dragging: draggingItem === `asset:${asset.id}` }" :title="t('canvas.dragNamed', { p0: asset.name })" draggable="true" @dragstart="startAssetDrag($event, asset)" @dragend="draggingItem = ''">
            <span class="asset-preview">
              <img v-if="asset.media_type === 'image'" :src="buildOssImageUrl(asset.url)" :alt="asset.name" draggable="false" />
              <component v-else :is="icons[asset.media_type]" :size="20" />
            </span>
            <span>{{ asset.name }}</span>
          </AppButton>
          <span class="asset-library-actions">
            <AppButton icon-only size="sm" :title="t('canvas.renameNamed', { p0: asset.name })" @click="renameAssetItem(asset)"><Pencil :size="13" /></AppButton>
            <AppButton icon-only size="sm" variant="danger" :title="t('canvas.deleteNamed', { p0: asset.name })" @click="deleteAssetItem(asset)"><Trash2 :size="13" /></AppButton>
          </span>
        </div>
        <div v-if="loadingAssets" class="asset-list-status">{{ t('canvas.loading') }}</div>
        <div v-else-if="assetError" class="asset-list-status error">{{ assetError }}</div>
        <div v-else-if="assetHasMore" class="asset-list-status">{{ t('canvas.scrollToLoad') }}</div>
      </div>
    </div>
  </aside>
</template>
