<script setup>
import { computed } from 'vue'
import { getBezierPath } from '@vue-flow/core'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  sourceX: { type: Number, required: true },
  sourceY: { type: Number, required: true },
  targetX: { type: Number, required: true },
  targetY: { type: Number, required: true },
  sourcePosition: { type: String, required: true },
  targetPosition: { type: String, required: true },
})

const path = computed(() => getBezierPath({
  sourceX: props.sourceX,
  sourceY: props.sourceY,
  targetX: props.targetX,
  targetY: props.targetY,
  sourcePosition: props.sourcePosition,
  targetPosition: props.targetPosition,
  curvature: 0.32,
})[0])
</script>

<template>
  <path class="flow-edge-hit" :d="path" />
  <path class="flow-edge-base" :d="path" />
  <path class="flow-edge-pulse" :d="path" pathLength="1" />
</template>
