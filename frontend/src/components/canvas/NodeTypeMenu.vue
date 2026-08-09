<script setup>
import { computed } from 'vue'
import { getNodeMenuGroups, resolveNodeMenuGroups } from '../../config/canvas/ecommerceWorkflows'
import { nodeDefinitions } from '../../config/canvas/nodeDefinitions'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'

const props = defineProps({
  contextual: Boolean,
  sourceId: { type: String, default: null },
})

defineEmits(['select'])

const store = useCanvasStore()
const source = computed(() => store.nodes.find((node) => node.id === props.sourceId))
const groups = computed(() => resolveNodeMenuGroups(getNodeMenuGroups(store.workspaceType, {
  contextual: props.contextual,
  sourceType: source.value?.type,
  sourceWorkflowId: source.value?.data.workflowId,
}), nodeDefinitions))
</script>

<template>
  <section v-for="group in groups" :key="group.id" class="node-menu-group">
    <p v-if="group.label">{{ group.label }}</p>
    <AppButton v-for="option in group.options" :key="`${option.kind}-${option.type}`" :class="`node-option--${option.nodeType || option.type}`" @click="$emit('select', { kind: option.kind, type: option.type })">
      <span class="menu-icon"><component :is="option.icon" :size="17" /></span>
      <strong>{{ option.label }}</strong>
    </AppButton>
  </section>
</template>
