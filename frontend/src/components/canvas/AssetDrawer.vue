<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChevronDown, ChevronRight, FileText, Folder, Image, Music2, Plus, RefreshCw, Video, X } from 'lucide-vue-next'
import { listAssets } from '../../api/assets'
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
const drawerTabs = [{ value: 'nodes', label: '节点' }, { value: 'assets', label: '资产' }]
const assetTypeOptions = [{ value: '', label: '全部' }, { value: 'image', label: '图片' }, { value: 'video', label: '视频' }, { value: 'audio', label: '音频' }]
const activeTab = ref('nodes')
const assetType = ref('')
const assets = ref([])
const loadingAssets = ref(false)
const assetError = ref('')
const collapsedGroupIds = ref([])
const editingGroupId = ref(null)
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
        <AppButton v-for="asset in assets" :key="asset.id" class="asset-item" :title="`添加 ${asset.name}`" @click="emit('add', asset)">
          <span class="asset-preview">
            <img v-if="asset.media_type === 'image'" :src="asset.url" :alt="asset.name" />
            <component v-else :is="icons[asset.media_type]" :size="20" />
          </span>
          <span>{{ asset.name }}</span>
          <Plus :size="14" />
        </AppButton>
      </div>
    </div>
  </aside>
</template>
