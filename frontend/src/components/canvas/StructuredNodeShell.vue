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
    <Handle
      v-for="handle in targetHandles"
      :id="handle.id"
      :key="handle.id"
      type="target"
      :position="Position.Left"
      :style="{ top: handle.top }"
    />
    <div class="node-body structured-node-body"><slot /></div>
    <Handle v-if="hasSource" id="source" type="source" :position="Position.Right" />
  </div>
</template>
