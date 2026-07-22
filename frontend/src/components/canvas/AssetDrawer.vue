<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChevronDown, ChevronRight, FileText, Folder, Image, LayoutGrid, Library, Music2, Pencil, Plus, RefreshCw, Trash2, Video, Workflow, X } from 'lucide-vue-next'
import { deleteAsset, listAssets, renameAsset } from '../../api/assets'
import { useGlobalConfirm, useGlobalPrompt, useGlobalToast } from '../../composables/useGlobalUI'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppTabs from '../ui/AppTabs.vue'
import EmptyState from '../ui/EmptyState.vue'

const props = defineProps({
  nodes: { type: Array, required: true },
  groups: { type: Array, required: true },
  activeGroupId: { type: String, default: null },
})
const emit = defineEmits(['focus', 'focus-group', 'rename-group', 'add', 'close'])
const icons = { text: FileText, image: Image, video: Video, audio: Music2 }
const drawerTabs = [{ value: 'nodes', label: '节点', icon: Workflow }, { value: 'assets', label: '资产', icon: Library }]
const assetTypeOptions = [
  { value: '', label: '全部', icon: LayoutGrid },
  { value: 'image', label: '图片', icon: Image },
  { value: 'video', label: '视频', icon: Video },
  { value: 'audio', label: '音频', icon: Music2 },
]
const activeTab = ref('nodes')
const assetType = ref('')
const assets = ref([])
const loadingAssets = ref(false)
const assetError = ref('')
const collapsedGroupIds = ref([])
const editingGroupId = ref(null)
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

function startRename(id) {
  editingGroupId.value = id
}

function renameGroup(id, event) {
  emit('rename-group', id, event.target.value)
}

async function loadAssetItems() {
  loadingAssets.value = true
  assetError.value = ''
  try {
    const result = await listAssets(assetType.value)
    if (result.code !== 0) throw new Error(result.message)
    assets.value = result.data
  } catch (error) {
    assetError.value = error.response?.data?.message || error.message || '资产加载失败'
  } finally {
    loadingAssets.value = false
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
    toast.success('资产已删除')
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '资产删除失败')
  }
}

function selectAssetType(type) {
  assetType.value = type
  loadAssetItems()
}

function selectTab(tab) {
  activeTab.value = tab
  if (tab === 'assets') loadAssetItems()
}

onMounted(loadAssetItems)
</script>

<template>
  <aside class="asset-drawer">
    <header>
      <strong>资产</strong>
      <span>{{ activeTab === 'nodes' ? nodes.length : assets.length }}</span>
      <AppButton v-if="activeTab === 'assets'" icon-only size="sm" title="刷新资产" @click="loadAssetItems"><RefreshCw :size="15" /></AppButton>
      <AppButton icon-only size="sm" title="关闭资产" @click="emit('close')"><X :size="17" /></AppButton>
    </header>

    <AppTabs class="asset-tabs" :model-value="activeTab" :options="drawerTabs" aria-label="资产面板" @update:model-value="selectTab" />

    <div v-if="activeTab === 'nodes'" class="asset-list">
      <EmptyState v-if="!nodes.length" compact title="暂无节点" description="在画布中创建节点后会显示在这里" />
      <AppButton
        v-for="node in ungroupedNodes"
        :key="node.id"
        class="asset-item"
        :class="{ active: node.selected }"
        @click="emit('focus', node.id)"
      >
        <span class="asset-preview">
          <img v-if="node.type === 'image' && node.data.asset" :src="node.data.asset" :alt="node.data.title" />
          <img v-else-if="node.type === 'video' && node.data.poster" :src="node.data.poster" :alt="node.data.title" />
          <component v-else :is="icons[node.type]" :size="20" />
        </span>
        <span>{{ node.data.title }}</span>
      </AppButton>

      <section v-for="group in groupItems" :key="group.id" class="asset-group">
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

        <div v-if="!collapsedGroupIds.includes(group.id)" class="asset-group-items">
          <AppButton
            v-for="node in group.nodes"
            :key="node.id"
            class="asset-item"
            :class="{ active: node.selected }"
            @click="emit('focus', node.id)"
          >
            <span class="asset-preview">
              <img v-if="node.type === 'image' && node.data.asset" :src="node.data.asset" :alt="node.data.title" />
              <img v-else-if="node.type === 'video' && node.data.poster" :src="node.data.poster" :alt="node.data.title" />
              <component v-else :is="icons[node.type]" :size="20" />
            </span>
            <span>{{ node.data.title }}</span>
          </AppButton>
        </div>
      </section>
    </div>

    <div v-else class="asset-library">
      <AppTabs class="asset-filters" :model-value="assetType" :options="assetTypeOptions" aria-label="资产类型" @update:model-value="selectAssetType" />
      <EmptyState v-if="loadingAssets" compact title="正在加载资产" loading />
      <EmptyState v-else-if="assetError" compact title="资产加载失败" :description="assetError" tone="error" />
      <EmptyState v-else-if="!assets.length" compact title="暂无资产" description="上传或生成的媒体会显示在这里" />
      <div v-else class="asset-list asset-library-list">
        <div v-for="asset in assets" :key="asset.id" class="asset-library-row">
          <AppButton class="asset-item" :title="`添加 ${asset.name}`" @click="emit('add', asset)">
            <span class="asset-preview">
              <img v-if="asset.media_type === 'image'" :src="asset.url" :alt="asset.name" />
              <component v-else :is="icons[asset.media_type]" :size="20" />
            </span>
            <span>{{ asset.name }}</span>
            <Plus :size="14" />
          </AppButton>
          <span class="asset-library-actions">
            <AppButton icon-only size="sm" :title="`重命名 ${asset.name}`" @click="renameAssetItem(asset)"><Pencil :size="13" /></AppButton>
            <AppButton icon-only size="sm" variant="danger" :title="`删除 ${asset.name}`" @click="deleteAssetItem(asset)"><Trash2 :size="13" /></AppButton>
          </span>
        </div>
      </div>
    </div>
  </aside>
</template>
