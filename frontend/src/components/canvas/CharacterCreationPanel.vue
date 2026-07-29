<script setup>
import { computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { characterReady } from '../../config/canvas/character'
import CharacterProfilePanel from './CharacterProfilePanel.vue'
import CharacterVisualPanel from './CharacterVisualPanel.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const { updateNodeData } = useVueFlow()
const step = computed(() => props.data.workflowStep || 'profile')
const completed = computed(() => characterReady(props.data.profile))
</script>

<template>
  <section class="generation-panel product-creation-panel character-creation-panel nodrag nowheel" :class="`step-${step}`" @pointerdown.stop>
    <ProductWorkflowSteps
      :step="step"
      :recognized="completed"
      first-step="profile"
      second-step="visual"
      first-label="角色设定"
      second-label="设定图"
      aria-label="角色创作步骤"
      @update:step="updateNodeData(nodeId, { workflowStep: $event })"
    />
    <div class="product-creation-stage">
      <CharacterProfilePanel v-if="step === 'profile'" embedded :node-id="nodeId" :data="data" />
      <CharacterVisualPanel v-else embedded :node-id="nodeId" :data="data" />
    </div>
  </section>
</template>
