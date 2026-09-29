<script setup>
import { useI18n } from 'vue-i18n'
import { canvasTemplateText } from '../../i18n/canvas'
import { computed } from 'vue'
import { Images, Package } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { productPromptContext } from '../../config/canvas/ecommerce'
import AppInput from '../ui/AppInput.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'
import StructuredNodeShell from './StructuredNodeShell.vue'

const { t } = useI18n()

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
const packagingOptions = computed(() => ([
  { value: '无包装', label: t('canvas.unpackaged') },
  { value: '带包装', label: t('canvas.packaged') },
  { value: '套装', label: t('canvas.packageSet') },
]))
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
          <span><Package :size="15" />{{ t('canvas.productProfile') }}</span>
          <small>{{ t('canvas.coreInfoCount', { p0: completed }) }}</small>
        </div>
        <div class="product-fields two-columns">
          <label><span>{{ t('canvas.productName') }}</span><AppInput class="nodrag nopan" :model-value="product.name" :placeholder="t('canvas.productNamePlaceholder')" @input="updateField('name', $event.target.value)" /></label>
          <label><span>{{ t('canvas.brand') }}</span><AppInput class="nodrag nopan" :model-value="product.brand" :placeholder="t('canvas.brandName')" @input="updateField('brand', $event.target.value)" /></label>
          <label><span>{{ t('canvas.category') }}</span><AppInput class="nodrag nopan" :model-value="product.category" :placeholder="t('canvas.categoryPlaceholder')" @input="updateField('category', $event.target.value)" /></label>
          <label><span>{{ t('canvas.price') }}</span><AppInput class="nodrag nopan" :model-value="product.price" :placeholder="t('canvas.pricePlaceholder')" @input="updateField('price', $event.target.value)" /></label>
        </div>
        <label class="product-field-wide"><span>{{ t('canvas.specifications') }}</span><AppInput class="nodrag nopan" :model-value="product.specifications" :placeholder="t('canvas.specificationsPlaceholder')" @input="updateField('specifications', $event.target.value)" /></label>
        <section class="product-scale-section">
          <div class="structured-node-summary"><span>{{ t('canvas.scaleInfo') }}</span><small>{{ t('canvas.optionalField') }}</small></div>
          <div class="product-fields two-columns">
            <label><span>{{ t('canvas.packagingType') }}</span><AppSelect class="nodrag nopan" :model-value="product.packagingType" :options="packagingOptions" :aria-label="t('canvas.packagingType')" @update:model-value="updateField('packagingType', $event)" /></label>
            <label><span>{{ t('canvas.productDimensions') }}</span><AppInput class="nodrag nopan" :model-value="product.productDimensions" :placeholder="t('canvas.productDimensionsPlaceholder')" @input="updateField('productDimensions', $event.target.value)" /></label>
          </div>
          <div v-if="hasPackaging" class="product-fields product-fields--secondary two-columns">
            <label><span>{{ t('canvas.packageDimensions') }}</span><AppInput class="nodrag nopan" :model-value="product.packageDimensions" :placeholder="t('canvas.packageDimensionsPlaceholder')" @input="updateField('packageDimensions', $event.target.value)" /></label>
            <label><span>{{ t('canvas.packageRelation') }}</span><AppInput class="nodrag nopan" :model-value="product.packageRelation" :placeholder="t('canvas.packageRelationPlaceholder')" @input="updateField('packageRelation', $event.target.value)" /></label>
          </div>
          <label class="product-field-wide"><span>{{ t('canvas.scaleReference') }}</span><AppInput class="nodrag nopan" :model-value="product.scaleReference" :placeholder="t('canvas.scaleReferencePlaceholder')" @input="updateField('scaleReference', $event.target.value)" /></label>
        </section>
        <label class="product-field-wide"><span>{{ t('canvas.sellingPoints') }}</span><AppTextarea class="nodrag nopan" :model-value="product.sellingPoints" maxlength="800" :placeholder="t('canvas.sellingPointsPlaceholder')" @input="updateField('sellingPoints', $event.target.value)" /></label>
        <div class="product-fields product-fields--secondary two-columns">
          <label><span>{{ t('canvas.audience') }}</span><AppInput class="nodrag nopan" :model-value="product.audience" :placeholder="t('canvas.targetUser')" @input="updateField('audience', $event.target.value)" /></label>
          <label><span>{{ t('canvas.scenario') }}</span><AppInput class="nodrag nopan" :model-value="product.scenario" :placeholder="t('canvas.scenarioPlaceholder')" @input="updateField('scenario', $event.target.value)" /></label>
        </div>
        <label class="product-field-wide"><span>{{ t('canvas.additionalInfo') }}</span><AppTextarea class="nodrag nopan" :model-value="product.additionalInfo" maxlength="1000" :placeholder="t('canvas.additionalInfoPlaceholder')" @input="updateField('additionalInfo', $event.target.value)" /></label>
      </template>

      <template v-else>
        <div class="structured-node-summary product-step-summary">
          <span><Images :size="15" />{{ t('canvas.imagePlan') }}</span>
          <small>{{ t('canvas.imageCount', { p0: selectedItems.length }) }}</small>
        </div>
        <div class="product-visual-tags product-creation-tags">
          <span v-for="item in selectedItems" :key="item.id">{{ canvasTemplateText(item.id, item.label) }}</span>
          <small v-if="!selectedItems.length">{{ t('canvas.noImageTypes') }}</small>
        </div>
        <div class="product-creation-settings-summary">
          <span>{{ data.imageModel }}</span><span>{{ data.aspectRatio }}</span><span>{{ data.resolution }}</span>
        </div>
      </template>
    </div>
  </StructuredNodeShell>
</template>
