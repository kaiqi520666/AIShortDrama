<script setup>
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import AppInput from '../ui/AppInput.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  icon: { type: [Object, Function], required: true },
  selected: Boolean,
  hasTarget: Boolean,
  hasSource: { type: Boolean, default: true },
  targetHandles: { type: Array, default: () => [] },
})

const { updateNodeData } = useVueFlow()
</script>

<template>
  <div class="media-node structured-node" :class="[`media-node--${type}`, { selected }]">
    <label class="node-title">
      <component :is="icon" :size="14" />
      <AppInput
        class="node-title-input nodrag nopan"
        :model-value="data.title"
        aria-label="节点标题"
        @input="updateNodeData(id, { title: $event.target.value })"
        @keydown.stop
      />
    </label>
    <Handle v-if="hasTarget" id="target" type="target" :position="Position.Left" />
    <template v-for="handle in targetHandles" :key="handle.id">
      <Handle
        :id="handle.id"
        type="target"
        :position="Position.Left"
        :style="{ top: handle.top }"
        :aria-label="handle.label ? `${handle.label}输入` : undefined"
      />
      <span v-if="handle.label" class="structured-node-handle-label" :style="{ top: handle.top }">{{ handle.label }}</span>
    </template>
    <div class="node-body structured-node-body"><slot /></div>
    <Handle v-if="hasSource" id="source" type="source" :position="Position.Right" />
  </div>
</template>
