<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChevronDown, ChevronRight, FileText, Folder, Image, Music2, Plus, RefreshCw, Video, X } from 'lucide-vue-next'
import { listAssets } from '../../api/assets'

const props = defineProps({
  nodes: { type: Array, required: true },
  groups: { type: Array, required: true },
  activeGroupId: { type: String, default: null },
})
const emit = defineEmits(['focus', 'focus-group', 'rename-group', 'add', 'close'])
const icons = { text: FileText, image: Image, video: Video, audio: Music2 }
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

onMounted(loadAssetItems)
</script>

<template>
  <aside class="asset-drawer">
    <header>
      <strong>资产</strong>
      <span>{{ activeTab === 'nodes' ? nodes.length : assets.length }}</span>
      <button v-if="activeTab === 'assets'" title="刷新资产" @click="loadAssetItems"><RefreshCw :size="15" /></button>
      <button title="关闭资产" @click="emit('close')"><X :size="17" /></button>
    </header>

    <nav class="asset-tabs">
      <button :class="{ active: activeTab === 'nodes' }" @click="activeTab = 'nodes'">节点</button>
      <button :class="{ active: activeTab === 'assets' }" @click="activeTab = 'assets'; loadAssetItems()">资产</button>
    </nav>

    <div v-if="activeTab === 'nodes'" class="asset-list">
      <button
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
      </button>

      <section v-for="group in groupItems" :key="group.id" class="asset-group">
        <button class="asset-group-row" :class="{ active: group.active }" @click="emit('focus-group', group.id)">
          <span class="asset-group-toggle" @click.stop="collapsedGroupIds = collapsedGroupIds.includes(group.id) ? collapsedGroupIds.filter((id) => id !== group.id) : [...collapsedGroupIds, group.id]">
            <ChevronRight v-if="collapsedGroupIds.includes(group.id)" :size="14" />
            <ChevronDown v-else :size="14" />
          </span>
          <Folder :size="16" />
          <input
            v-if="editingGroupId === group.id"
            class="asset-group-title-input"
            :value="group.title"
            aria-label="编组名称"
            @click.stop
            @input="renameGroup(group.id, $event)"
            @blur="editingGroupId = null"
            @keydown.enter="editingGroupId = null"
            @keydown.esc="editingGroupId = null"
          />
          <span v-else class="asset-group-title" @dblclick.stop="startRename(group.id)">{{ group.title }}</span>
          <small>{{ group.nodes.length }}</small>
        </button>

        <div v-if="!collapsedGroupIds.includes(group.id)" class="asset-group-items">
          <button
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
          </button>
        </div>
      </section>
    </div>

    <div v-else class="asset-library">
      <div class="asset-filters">
        <button v-for="item in [{ value: '', label: '全部' }, { value: 'image', label: '图片' }, { value: 'video', label: '视频' }, { value: 'audio', label: '音频' }]" :key="item.value" :class="{ active: assetType === item.value }" @click="selectAssetType(item.value)">{{ item.label }}</button>
      </div>
      <p v-if="loadingAssets" class="asset-library-state">加载中…</p>
      <p v-else-if="assetError" class="asset-library-state error">{{ assetError }}</p>
      <p v-else-if="!assets.length" class="asset-library-state">暂无资产</p>
      <div v-else class="asset-list asset-library-list">
        <button v-for="asset in assets" :key="asset.id" class="asset-item" :title="`添加 ${asset.name}`" @click="emit('add', asset)">
          <span class="asset-preview">
            <img v-if="asset.media_type === 'image'" :src="asset.url" :alt="asset.name" />
            <component v-else :is="icons[asset.media_type]" :size="20" />
          </span>
          <span>{{ asset.name }}</span>
          <Plus :size="14" />
        </button>
      </div>
    </div>
  </aside>
</template>
