<script setup>
import { computed, ref } from 'vue'
import { ChevronDown, ChevronRight, FileText, Folder, Image, Music2, Video, X } from 'lucide-vue-next'

const props = defineProps({
  nodes: { type: Array, required: true },
  groups: { type: Array, required: true },
  activeGroupId: { type: String, default: null },
})
const emit = defineEmits(['focus', 'focus-group', 'rename-group', 'close'])
const icons = { text: FileText, image: Image, video: Video, audio: Music2 }
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
</script>

<template>
  <aside class="asset-drawer">
    <header>
      <strong>资产</strong>
      <span>{{ nodes.length }}</span>
      <button title="关闭资产" @click="emit('close')"><X :size="17" /></button>
    </header>

    <div class="asset-list">
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
  </aside>
</template>
