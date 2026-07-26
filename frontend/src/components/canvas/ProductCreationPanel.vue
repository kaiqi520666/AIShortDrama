<script setup>
import { computed } from 'vue'
import { Check, Images, ScanSearch } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { productPromptContext } from '../../config/canvas/ecommerce'
import AppButton from '../ui/AppButton.vue'
import GenerationPanel from './GenerationPanel.vue'
import ProductVisualPanel from './ProductVisualPanel.vue'

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
  <section class="generation-panel product-creation-panel nodrag nowheel" @pointerdown.stop>
    <nav class="product-creation-steps" aria-label="商品创作步骤">
      <AppButton :class="{ active: step === 'recognition', complete: recognized }" @click="setStep('recognition')">
        <span class="product-step-number"><Check v-if="recognized" :size="13" /><template v-else>1</template></span>
        <span><strong>商品识别</strong><small>{{ recognized ? '资料已生成，可继续修改' : '从参考图提取商品资料' }}</small></span>
      </AppButton>
      <span class="product-step-line" :class="{ complete: recognized }"></span>
      <AppButton :class="{ active: step === 'visual' }" :disabled="!recognized" @click="setStep('visual')">
        <span class="product-step-number">2</span>
        <span><strong>出图设置</strong><small>选择图种与统一生成参数</small></span>
      </AppButton>
    </nav>

    <div class="product-creation-stage">
      <GenerationPanel v-if="step === 'recognition'" embedded :node-id="nodeId" :type="type" :data="data" />
      <ProductVisualPanel v-else embedded :node-id="nodeId" :data="data" :product-node-id="nodeId" />
    </div>
  </section>
</template>
