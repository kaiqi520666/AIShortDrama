<script setup>
import { computed } from 'vue'
import { Check, Images, Package } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { productPromptContext } from '../../config/canvas/ecommerce'
import AppInput from '../ui/AppInput.vue'
import AppButton from '../ui/AppButton.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const { updateNodeData } = useVueFlow()
const product = computed(() => props.data.product || {})
const completed = computed(() => ['name', 'category', 'sellingPoints'].filter((key) => product.value[key]?.trim()).length)
const profileReady = computed(() => Boolean(productPromptContext(product.value)))
const step = computed(() => props.data.workflowStep || 'recognition')
const selectedItems = computed(() => (props.data.items || []).filter((item) => item.enabled))

function updateField(key, value) {
  updateNodeData(props.id, { product: { ...product.value, [key]: value }, status: 'ready' })
}

function setStep(value) {
  updateNodeData(props.id, { workflowStep: value })
}
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Package" :selected="selected" has-target>
    <div class="product-node-content nowheel" @keydown.stop>
      <div class="product-node-steps">
        <AppButton :class="{ active: step === 'recognition', complete: profileReady }" @click.stop="setStep('recognition')">
          <span><Check v-if="profileReady" :size="12" /><template v-else>1</template></span>商品识别
        </AppButton>
        <span></span>
        <AppButton :class="{ active: step === 'visual' }" :disabled="!profileReady" @click.stop="setStep('visual')">
          <span>2</span>出图设置
        </AppButton>
      </div>

      <template v-if="step === 'recognition'">
        <div class="structured-node-summary product-step-summary">
          <span><Package :size="15" />商品资料</span>
          <small>{{ completed }}/3 核心信息</small>
        </div>
        <div class="product-fields two-columns">
          <label><span>商品名称</span><AppInput class="nodrag nopan" :model-value="product.name" placeholder="例如：轻量冲锋衣" @input="updateField('name', $event.target.value)" /></label>
          <label><span>品牌</span><AppInput class="nodrag nopan" :model-value="product.brand" placeholder="品牌名称" @input="updateField('brand', $event.target.value)" /></label>
          <label><span>品类</span><AppInput class="nodrag nopan" :model-value="product.category" placeholder="服饰 / 美妆 / 数码" @input="updateField('category', $event.target.value)" /></label>
          <label><span>价格</span><AppInput class="nodrag nopan" :model-value="product.price" placeholder="例如：¥299" @input="updateField('price', $event.target.value)" /></label>
        </div>
        <label class="product-field-wide"><span>规格 / SKU</span><AppInput class="nodrag nopan" :model-value="product.specifications" placeholder="颜色、尺码、容量等" @input="updateField('specifications', $event.target.value)" /></label>
        <label class="product-field-wide"><span>核心卖点</span><AppTextarea class="nodrag nopan" :model-value="product.sellingPoints" maxlength="800" placeholder="用换行分隔主要卖点" @input="updateField('sellingPoints', $event.target.value)" /></label>
        <div class="product-fields product-fields--secondary two-columns">
          <label><span>目标人群</span><AppInput class="nodrag nopan" :model-value="product.audience" placeholder="目标用户" @input="updateField('audience', $event.target.value)" /></label>
          <label><span>使用场景</span><AppInput class="nodrag nopan" :model-value="product.scenario" placeholder="通勤、户外等" @input="updateField('scenario', $event.target.value)" /></label>
        </div>
        <label class="product-field-wide"><span>补充信息</span><AppTextarea class="nodrag nopan" :model-value="product.additionalInfo" maxlength="1000" placeholder="其他有效商品信息" @input="updateField('additionalInfo', $event.target.value)" /></label>
      </template>

      <template v-else>
        <div class="structured-node-summary product-step-summary">
          <span><Images :size="15" />出图方案</span>
          <small>{{ selectedItems.length }} 张</small>
        </div>
        <div class="product-visual-tags product-creation-tags">
          <span v-for="item in selectedItems" :key="item.id">{{ item.label }}</span>
          <small v-if="!selectedItems.length">尚未选择图种</small>
        </div>
        <div class="product-creation-settings-summary">
          <span>{{ data.imageModel }}</span><span>{{ data.aspectRatio }}</span><span>{{ data.resolution }}</span>
        </div>
      </template>
    </div>
  </StructuredNodeShell>
</template>
