<script setup>
import { computed } from 'vue'
import { FileText, Image, Music2, Video } from 'lucide-vue-next'
import { mediaTypes } from '../../config/mediaTypes'
import { useCanvasStore } from '../../stores/canvas'

const props = defineProps({
  point: { type: Object, required: true },
  contextual: Boolean,
  sourceId: { type: String, default: null },
})

defineEmits(['select', 'close'])

const icons = { text: FileText, image: Image, video: Video, audio: Music2 }
const store = useCanvasStore()
const source = computed(() => store.nodes.find((node) => node.id === props.sourceId))
const options = computed(() => Object.entries(mediaTypes)
  .filter(([type]) => type !== 'text' || !props.contextual || ['text', 'image'].includes(source.value?.type))
  .map(([type, { label, hint }]) => ({ type, label, hint, icon: icons[type] })))
</script>

<template>
  <div class="menu-backdrop" @pointerdown.self="$emit('close')">
    <div class="node-create-menu" :style="{ left: `${point.x}px`, top: `${point.y}px` }">
      <p>{{ contextual ? '引用该节点生成' : '添加节点' }}</p>
      <button v-for="option in options" :key="option.type" @click="$emit('select', option.type)">
        <span class="menu-icon"><component :is="option.icon" :size="17" /></span>
        <span><strong>{{ option.label }}</strong><small>{{ option.hint }}</small></span>
      </button>
    </div>
  </div>
</template>
