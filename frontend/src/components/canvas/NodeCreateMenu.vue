<script setup>
import AppMenu from '../ui/AppMenu.vue'
import NodeTypeMenu from './NodeTypeMenu.vue'

const props = defineProps({
  point: { type: Object, required: true },
  placement: { type: String, default: 'cursor' },
  contextual: Boolean,
  sourceId: { type: String, default: null },
})

defineEmits(['select', 'close'])
</script>

<template>
  <div class="menu-backdrop" @pointerdown.self="$emit('close')">
    <AppMenu class="node-create-menu" :class="{ 'node-create-menu--anchor': placement === 'anchor' }" :style="{ left: `${point.x}px`, top: `${point.y}px` }">
      <p>{{ contextual ? '引用该节点生成' : '添加节点' }}</p>
      <NodeTypeMenu :contextual="contextual" :source-id="sourceId" @select="$emit('select', $event)" />
    </AppMenu>
  </div>
</template>
