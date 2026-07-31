<script setup>
import { computed } from 'vue'
import { canConnect } from '../../config/canvas/connectionRules'
import { nodeDefinitions } from '../../config/canvas/nodeDefinitions'
import { getNodeTypes } from '../../config/canvas/nodePacks'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'

const props = defineProps({
  contextual: Boolean,
  sourceId: { type: String, default: null },
})

defineEmits(['select'])

const store = useCanvasStore()
const source = computed(() => store.nodes.find((node) => node.id === props.sourceId))
const options = computed(() => getNodeTypes(store.workspaceType)
  .filter((type) => !['product_visual', 'outfit'].includes(type))
  .filter((type) => !props.contextual || canConnect(source.value?.type, type, store.workspaceType))
  .map((type) => nodeDefinitions[type]))
</script>

<template>
  <AppButton v-for="option in options" :key="option.type" :class="`node-option--${option.type}`" @click="$emit('select', option.type)">
    <span class="menu-icon"><component :is="option.icon" :size="17" /></span>
    <span><strong>{{ option.label }}</strong><small>{{ option.hint }}</small></span>
  </AppButton>
</template>
