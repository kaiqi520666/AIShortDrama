<script setup>
import { computed } from 'vue'
import { ArrowUp, BadgeCheck, Box, Coins, FileText, Images, LoaderCircle, Package, ScanSearch } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { maxProductReferenceImages } from '../../config/canvas/connectionRules'
import { productPromptContext } from '../../config/canvas/ecommerce'
import { buildProductVisualPrompt, parseProductVisualPlan, productVisualGroups } from '../../config/canvas/productVisual'
import { imageModels, normalizeImageSettings } from '../../config/imageModels'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  productNodeId: { type: String, default: '' },
  embedded: Boolean,
})

const groupIcons = { basic: Box, marketing: BadgeCheck, detail: ScanSearch, trust: Package }
const store = useCanvasStore()
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
}))
const selectedTextModel = computed(() => reverseModels.find((model) => model.id === props.data.textModel) || defaultReverseModel)
const selectedItems = computed(() => (props.data.items || []).filter((item) => item.enabled))
const prompt = computed(() => buildProductVisualPrompt(productContext.value, selectedItems.value, props.data))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const imageModelOptions = imageModels.map(({ id, label }) => ({ value: id, label }))
const textModelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const ratioOptions = computed(() => selectedImageSettings.value.model.aspectRatios.map((value) => ({ value, label: value })))
const resolutionOptions = computed(() => selectedImageSettings.value.model.resolutions.map((value) => ({ value, label: value })))
const message = computed(() => failure.value || props.data.generationError || (!productNode.value
  ? '请先连接商品资料节点'
  : !allReferenceImages.value.length
    ? '请先上传商品参考图'
    : !referenceImage.value
      ? '请至少启用一张商品参考图'
    : !productContext.value
      ? '请先填写商品资料'
      : !selectedItems.value.length
        ? '至少选择一个出图类型'
        : insufficientCredits.value
          ? `积分不足，本次需要 ${estimatedCredits.value} 积分`
          : ''))
const canSubmit = computed(() => !running.value && productNode.value && referenceImage.value && productContext.value && selectedItems.value.length && !insufficientCredits.value)

function updateItem(id, enabled) {
  failure.value = ''
  updateNodeData(props.nodeId, {
    items: props.data.items.map((item) => item.id === id ? { ...item, enabled } : item),
    generationError: '',
  })
}

function updateImageModel(imageModel) {
  const model = imageModels.find(({ id }) => id === imageModel)
  updateNodeData(props.nodeId, {
    imageModel: model.id,
    aspectRatio: model.aspectRatios.includes(props.data.aspectRatio) ? props.data.aspectRatio : model.defaultAspectRatio,
    resolution: model.resolutions.includes(props.data.resolution) ? props.data.resolution : model.defaultResolution,
  })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成出图方案',
    message: `将新增 ${selectedItems.value.length} 个图片节点，已有节点不会删除。`,
    confirmText: '继续生成',
  })) return

  await runTextTask(streamReversePrompt, {
    workspace_id: store.workspaceId,
    node_id: props.nodeId,
    model: selectedTextModel.value.id,
    media_type: 'image',
    media_url: referenceImage.value.data.asset,
    ...(referenceImages.value.length > 1
      ? { media_urls: referenceImages.value.slice(1).map((reference) => reference.data.asset) }
      : {}),
    prompt: prompt.value,
    response_mode: 'product_visual_plan',
  }, {
    failureMessage: '商品出图方案生成失败',
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
      <span><Images :size="16" />商品出图</span>
      <small v-if="productNode"><Package :size="13" />{{ productNode.data.product?.name || productNode.data.title }}</small>
    </header>

    <div class="product-visual-groups">
      <section v-for="group in productVisualGroups" :key="group.id" class="product-visual-group">
        <h3><component :is="groupIcons[group.id]" :size="14" />{{ group.label }}</h3>
        <div class="product-visual-options">
          <label v-for="item in group.items" :key="item.id" class="product-visual-option" :class="{ active: data.items.find((value) => value.id === item.id)?.enabled }">
            <input
              type="checkbox"
              :checked="data.items.find((value) => value.id === item.id)?.enabled"
              @change="updateItem(item.id, $event.target.checked)"
            />
            <span>{{ item.label }}</span>
          </label>
        </div>
      </section>
    </div>

    <div class="product-visual-settings">
      <label><span>图片模型</span><AppSelect :model-value="selectedImageSettings.model.id" :options="imageModelOptions" aria-label="图片模型" @update:model-value="updateImageModel" /></label>
      <label><span>画面比例</span><AppSelect :model-value="selectedImageSettings.aspectRatio" :options="ratioOptions" aria-label="画面比例" @update:model-value="updateNodeData(nodeId, { aspectRatio: $event })" /></label>
      <label><span>清晰度</span><AppSelect :model-value="selectedImageSettings.resolution" :options="resolutionOptions" aria-label="清晰度" @update:model-value="updateNodeData(nodeId, { resolution: $event })" /></label>
    </div>

    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" aria-label="文本模型" @update:model-value="updateNodeData(nodeId, { textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成出图方案'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
