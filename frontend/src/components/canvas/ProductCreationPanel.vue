<script setup>
import { computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { productPromptContext } from '../../config/canvas/ecommerce'
import GenerationPanel from './GenerationPanel.vue'
import ProductVisualPanel from './ProductVisualPanel.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  type: { type: String, required: true },
})

const { updateNodeData } = useVueFlow()
const step = computed(() => props.data.workflowStep || 'recognition')
const recognized = computed(() => Boolean(productPromptContext(props.data.product)))

function setStep(value) {
  updateNodeData(props.nodeId, { workflowStep: value })
}
</script>

<template>
  <section class="generation-panel product-creation-panel nodrag nowheel" :class="`step-${step}`" @pointerdown.stop>
    <ProductWorkflowSteps :step="step" :recognized="recognized" @update:step="setStep" />

    <div class="product-creation-stage">
      <GenerationPanel v-if="step === 'recognition'" embedded :node-id="nodeId" :type="type" :data="data" />
      <ProductVisualPanel v-else embedded :node-id="nodeId" :data="data" :product-node-id="nodeId" />
    </div>
  </section>
</template>
