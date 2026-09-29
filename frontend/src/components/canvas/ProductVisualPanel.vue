<script setup>
import { useI18n } from 'vue-i18n'
import { canvasTemplateText } from '../../i18n/canvas'
import { computed } from 'vue'
import { ArrowUp, BadgeCheck, Box, Coins, FileText, Images, LoaderCircle, Package, ScanSearch } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { maxProductReferenceImages } from '../../config/canvas/connectionRules'
import { productPromptContext } from '../../config/canvas/ecommerce'
import { buildProductVisualRequest, getProductVisualGroups, parseProductVisualPlan } from '../../config/canvas/productVisual'
import { normalizeImageSettings } from '../../config/imageModels'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { useContentTemplatesStore } from '../../stores/contentTemplates'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'

const { t } = useI18n()

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  productNodeId: { type: String, default: '' },
  embedded: Boolean,
})

const groupIcons = { basic: Box, marketing: BadgeCheck, detail: ScanSearch, trust: Package }
const store = useCanvasStore()
const capabilityStore = useModelCapabilitiesStore()
const contentTemplateStore = useContentTemplatesStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)
const productNode = computed(() => props.productNodeId
  ? store.nodes.find((node) => node.id === props.productNodeId)
  : store.incomingNodes(props.nodeId).find((node) => node.type === 'product'))
const allReferenceImages = computed(() => productNode.value
  ? store.incomingNodes(productNode.value.id).filter((node) => node.type === 'image' && node.data.asset).slice(0, maxProductReferenceImages)
  : [])
const disabledReferenceIds = computed(() => new Set(productNode.value?.data.disabledReferenceIds || []))
const referenceImages = computed(() => allReferenceImages.value.filter((node) => !disabledReferenceIds.value.has(node.id)))
const referenceImage = computed(() => referenceImages.value[0])
const productContext = computed(() => productPromptContext(productNode.value?.data.product))
const selectedImageSettings = computed(() => normalizeImageSettings({
  model: props.data.imageModel,
  aspectRatio: props.data.aspectRatio,
  resolution: props.data.resolution,
}, capabilityStore.imageModels, capabilityStore.defaultImageModel))
const selectedTextModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.textModel) || capabilityStore.defaultTextModel)
const selectedItems = computed(() => (props.data.items || []).filter((item) => item.enabled))
const template = computed(() => contentTemplateStore.templates?.product_visual)
const templateEnabled = computed(() => Boolean(template.value?.enabled))
const productVisualGroups = computed(() => templateEnabled.value ? getProductVisualGroups(template.value) : [])
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const imageModelOptions = computed(() => capabilityStore.imageModels.map(({ id, label }) => ({ value: id, label })))
const textModelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const ratioOptions = computed(() => selectedImageSettings.value.model.aspectRatios.map((value) => ({ value, label: value })))
const resolutionOptions = computed(() => selectedImageSettings.value.model.resolutions.map((value) => ({ value, label: value })))
const message = computed(() => failure.value || props.data.generationError || (!templateEnabled.value
  ? t('canvas.productVisualTemplateDisabled')
  : !productNode.value
  ? t('canvas.connectProductProfileFirst')
  : !allReferenceImages.value.length
    ? t('canvas.uploadProductFirst')
    : !referenceImage.value
      ? t('canvas.enableProductReferenceFirst')
    : !productContext.value
      ? t('canvas.fillProductFirst')
      : !selectedItems.value.length
        ? t('canvas.selectImageTypeFirst')
        : insufficientCredits.value
          ? t('canvas.insufficientCredits', { p0: estimatedCredits.value })
          : ''))
const canSubmit = computed(() => templateEnabled.value && !running.value && productNode.value && referenceImage.value && productContext.value && selectedItems.value.length && !insufficientCredits.value)

function updateItem(id, enabled) {
  failure.value = ''
  updateNodeData(props.nodeId, {
    items: props.data.items.map((item) => item.id === id ? { ...item, enabled } : item),
    generationError: '',
  })
}

function updateImageModel(imageModel) {
  const model = capabilityStore.imageModels.find(({ id }) => id === imageModel)
  updateNodeData(props.nodeId, {
    imageModel: model.id,
    aspectRatio: model.aspectRatios.includes(props.data.aspectRatio) ? props.data.aspectRatio : model.defaultAspectRatio,
    resolution: model.resolutions.includes(props.data.resolution) ? props.data.resolution : model.defaultResolution,
  })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: t('canvas.regenerateImagePlan'),
    message: t('canvas.addImageNodes', { p0: selectedItems.value.length }),
    confirmText: t('canvas.continueGeneration'),
  })) return

  updateNodeData(props.nodeId, { templateVersion: template.value.version })
  await runTextTask(streamReversePrompt, buildProductVisualRequest({
    workspaceId: store.workspaceId,
    nodeId: props.nodeId,
    model: selectedTextModel.value.id,
    referenceUrls: referenceImages.value.map((reference) => reference.data.asset),
    productContext: productContext.value,
    selectedTypeIds: selectedItems.value.map((item) => item.id),
    aspectRatio: selectedImageSettings.value.aspectRatio,
    resolution: selectedImageSettings.value.resolution,
    templateVersion: template.value.version,
  }), {
    failureMessage: t('canvas.productImagePlanFailed'),
    onSuccess: (content) => {
      const settings = selectedImageSettings.value
      const generatedNodeIds = store.addProductVisualNodes(
        props.nodeId,
        productNode.value.id,
        referenceImages.value.map((reference) => reference.id),
        parseProductVisualPlan(content, selectedItems.value),
        { model: settings.model.id, aspectRatio: settings.aspectRatio, resolution: settings.resolution },
      )
      return { generatedNodeIds: [...existingGeneratedNodes.value, ...generatedNodeIds] }
    },
  })
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel product-visual-panel nodrag nowheel" :class="{ embedded }" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Images :size="16" />{{ t('canvas.productVisual') }}</span>
      <small v-if="productNode"><Package :size="13" />{{ productNode.data.product?.name || productNode.data.title }}</small>
    </header>

    <div class="product-visual-groups">
      <section v-for="group in productVisualGroups" :key="group.id" class="product-visual-group">
        <h3><component :is="groupIcons[group.id]" :size="14" />{{ canvasTemplateText(group.id, group.label) }}</h3>
        <div class="product-visual-options">
          <label v-for="item in group.items" :key="item.id" class="product-visual-option" :class="{ active: data.items.find((value) => value.id === item.id)?.enabled }">
            <input
              type="checkbox"
              :checked="data.items.find((value) => value.id === item.id)?.enabled"
              @change="updateItem(item.id, $event.target.checked)"
            />
            <span>{{ canvasTemplateText(item.id, item.label) }}</span>
          </label>
        </div>
      </section>
    </div>

    <div class="product-visual-settings">
      <label><span>{{ t('canvas.imageModel') }}</span><AppSelect :model-value="selectedImageSettings.model.id" :options="imageModelOptions" :aria-label="t('canvas.imageModel')" @update:model-value="updateImageModel" /></label>
      <label><span>{{ t('canvas.aspectRatio') }}</span><AppSelect :model-value="selectedImageSettings.aspectRatio" :options="ratioOptions" :aria-label="t('canvas.aspectRatio')" @update:model-value="updateNodeData(nodeId, { aspectRatio: $event })" /></label>
      <label><span>{{ t('canvas.resolution') }}</span><AppSelect :model-value="selectedImageSettings.resolution" :options="resolutionOptions" :aria-label="t('canvas.resolution')" @update:model-value="updateNodeData(nodeId, { resolution: $event })" /></label>
    </div>

    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" :aria-label="t('canvas.textModel')" @update:model-value="updateNodeData(nodeId, { textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />{{ t('canvas.creditCost', { p0: estimatedCredits }) }}</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? t('canvas.generating') : t('canvas.generateImagePlan')" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
