<script setup>
import { computed } from 'vue'
import { Images, Package } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { productPromptContext } from '../../config/canvas/ecommerce'
import AppInput from '../ui/AppInput.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'
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
const packagingOptions = [
  { value: '无包装', label: '无包装' },
  { value: '带包装', label: '带包装' },
  { value: '套装', label: '套装 / 组合' },
]
const hasPackaging = computed(() => ['带包装', '套装'].includes(product.value.packagingType))

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
      <ProductWorkflowSteps :step="step" :recognized="profileReady" @update:step="setStep" />

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
        <section class="product-scale-section">
          <div class="structured-node-summary"><span>尺度信息</span><small>选填</small></div>
          <div class="product-fields two-columns">
            <label><span>商品形态</span><AppSelect class="nodrag nopan" :model-value="product.packagingType" :options="packagingOptions" aria-label="商品形态" @update:model-value="updateField('packagingType', $event)" /></label>
            <label><span>主体尺寸</span><AppInput class="nodrag nopan" :model-value="product.productDimensions" placeholder="如：高8.5cm，直径6cm" @input="updateField('productDimensions', $event.target.value)" /></label>
          </div>
          <div v-if="hasPackaging" class="product-fields product-fields--secondary two-columns">
            <label><span>外包装尺寸</span><AppInput class="nodrag nopan" :model-value="product.packageDimensions" placeholder="如：28×20×8cm" @input="updateField('packageDimensions', $event.target.value)" /></label>
            <label><span>包装关系</span><AppInput class="nodrag nopan" :model-value="product.packageRelation" placeholder="如：6瓶/盒，竖直排列" @input="updateField('packageRelation', $event.target.value)" /></label>
          </div>
          <label class="product-field-wide"><span>尺度参照</span><AppInput class="nodrag nopan" :model-value="product.scaleReference" placeholder="如：成人单手可握，瓶身约为掌长80%" @input="updateField('scaleReference', $event.target.value)" /></label>
        </section>
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
