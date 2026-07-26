<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, BadgeCheck, Box, Coins, Images, LoaderCircle, Package, ScanSearch } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { productPromptContext } from '../../config/canvas/ecommerce'
import { buildProductVisualPrompt, parseProductVisualPlan, productVisualGroups } from '../../config/canvas/productVisual'
import { getImageModel, imageModels } from '../../config/imageModels'
import { defaultReverseModel } from '../../config/reverseModels'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const groupIcons = { basic: Box, marketing: BadgeCheck, detail: ScanSearch, trust: Package }
const store = useCanvasStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const notice = ref('')
const productNode = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'product'))
const referenceImage = computed(() => productNode.value && store.incomingNodes(productNode.value.id).find((node) => node.type === 'image' && node.data.asset))
const productContext = computed(() => productPromptContext(productNode.value?.data.product))
const selectedModel = computed(() => getImageModel(props.data.model))
const selectedItems = computed(() => (props.data.items || []).filter((item) => item.enabled))
const prompt = computed(() => buildProductVisualPrompt(productContext.value, selectedItems.value, props.data))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', defaultReverseModel.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const modelOptions = imageModels.map((model) => ({ value: model.id, label: model.label }))
const ratioOptions = computed(() => selectedModel.value.aspectRatios.map((value) => ({ value, label: value })))
const resolutionOptions = computed(() => selectedModel.value.resolutions.map((value) => ({ value, label: value })))
const message = computed(() => notice.value || props.data.generationError || (!productNode.value
  ? '请先连接商品资料节点'
  : !referenceImage.value
    ? '请先上传商品参考图'
    : !productContext.value
      ? '请先填写商品资料'
      : !selectedItems.value.length
        ? '至少选择一个出图类型'
        : insufficientCredits.value
          ? `积分不足，本次需要 ${estimatedCredits.value} 积分`
          : ''))
const canSubmit = computed(() => !running.value && productNode.value && referenceImage.value && productContext.value && selectedItems.value.length && !insufficientCredits.value)

function updateItem(id, enabled) {
  notice.value = ''
  updateNodeData(props.nodeId, {
    items: props.data.items.map((item) => item.id === id ? { ...item, enabled } : item),
    generationError: '',
  })
}

function updateModel(modelId) {
  const model = getImageModel(modelId)
  updateNodeData(props.nodeId, {
    model: model.id,
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

  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { status: 'generating', generationError: '' })
  try {
    await streamReversePrompt({
      workspace_id: store.workspaceId,
      node_id: props.nodeId,
      model: defaultReverseModel.id,
      media_type: 'image',
      media_url: referenceImage.value.data.asset,
      prompt: prompt.value,
      response_mode: 'product_visual_plan',
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    const plans = parseProductVisualPlan(content, selectedItems.value)
    const generatedNodeIds = store.addProductVisualNodes(
      props.nodeId,
      productNode.value.id,
      referenceImage.value.id,
      plans,
      { model: selectedModel.value.id, aspectRatio: props.data.aspectRatio, resolution: props.data.resolution },
    )
    updateNodeData(props.nodeId, {
      status: 'ready',
      generationStatus: 'succeeded',
      generatedNodeIds: [...existingGeneratedNodes.value, ...generatedNodeIds],
    })
  } catch (error) {
    const messageText = error.message || '商品出图方案生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel product-visual-panel nodrag nowheel" @pointerdown.stop>
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
      <label><span>图片模型</span><AppSelect :model-value="selectedModel.id" :options="modelOptions" aria-label="图片模型" @update:model-value="updateModel" /></label>
      <label><span>画面比例</span><AppSelect :model-value="data.aspectRatio" :options="ratioOptions" aria-label="画面比例" @update:model-value="updateNodeData(nodeId, { aspectRatio: $event })" /></label>
      <label><span>清晰度</span><AppSelect :model-value="data.resolution" :options="resolutionOptions" aria-label="清晰度" @update:model-value="updateNodeData(nodeId, { resolution: $event })" /></label>
    </div>

    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <span>已选 {{ selectedItems.length }} 张</span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成出图方案'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
