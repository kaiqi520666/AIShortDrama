<script setup>
import { computed } from 'vue'
import { FileText, Image, Music2, Video } from 'lucide-vue-next'
import { canConnect } from '../../config/connectionRules'
import { mediaTypes } from '../../config/mediaTypes'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'

const props = defineProps({
  contextual: Boolean,
  sourceId: { type: String, default: null },
})

defineEmits(['select'])

const icons = { text: FileText, image: Image, video: Video, audio: Music2 }
const store = useCanvasStore()
const source = computed(() => store.nodes.find((node) => node.id === props.sourceId))
const options = computed(() => Object.entries(mediaTypes)
  .filter(([type]) => !props.contextual || canConnect(source.value?.type, type))
  .map(([type, { label, hint }]) => ({ type, label, hint, icon: icons[type] })))
</script>

<template>
  <AppButton v-for="option in options" :key="option.type" :class="`node-option--${option.type}`" @click="$emit('select', option.type)">
    <span class="menu-icon"><component :is="option.icon" :size="17" /></span>
    <span><strong>{{ option.label }}</strong><small>{{ option.hint }}</small></span>
  </AppButton>
</template>
