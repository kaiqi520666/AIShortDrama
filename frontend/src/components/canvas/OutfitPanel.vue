<script setup>
import { computed, ref } from 'vue'
import { Shirt, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { createImageGeneration } from '../../api/generations'
import { buildImageRequest, normalizeImageSettings } from '../../config/imageModels'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppTextarea from '../ui/AppTextarea.vue'
import ImageGenerationControls from './ImageGenerationControls.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const submitting = ref(false)
const notice = ref('')

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.nodeId && item.targetHandle === handle)
  return store.nodes.find((item) => item.id === edge?.source)
}

const garmentNode = computed(() => inputNode('garment'))
const modelNode = computed(() => inputNode('model'))
const references = computed(() => [garmentNode.value, modelNode.value].filter(Boolean))
const settings = computed(() => normalizeImageSettings(props.data))
const estimatedCredits = computed(() => authStore.estimateCredits('image', settings.value.model.id, { resolution: settings.value.resolution }))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const prompt = computed(() => [
  '执行服饰穿搭图像编辑。参考图 1 是服饰，参考图 2 是模特。',
  '将参考图 1 的服饰自然穿到参考图 2 的模特身上，保持模特的身份、面部、体型、姿态和背景不变。',
  '准确保留服饰的版型、颜色、纹理、图案及细节，使穿着关系、遮挡、褶皱和光影真实自然。',
  props.data.requirements?.trim() ? `补充要求：${props.data.requirements.trim()}` : '',
].filter(Boolean).join('\n'))
const message = computed(() => notice.value || props.data.generationError || (!garmentNode.value?.data.asset
  ? '请先选择服饰参考图'
  : !modelNode.value?.data.asset
    ? '请先选择模特参考图'
    : insufficientCredits.value
      ? `积分不足，本次需要 ${estimatedCredits.value} 积分`
      : ''))
const canSubmit = computed(() => !submitting.value && garmentNode.value?.data.asset && modelNode.value?.data.asset && !insufficientCredits.value)
const sourceItems = computed(() => [
  { label: '服饰参考图', icon: Shirt, node: garmentNode.value },
  { label: '模特参考图', icon: UserRound, node: modelNode.value },
])

function updateSettings(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

function updateRequirements(event) {
  notice.value = ''
  updateNodeData(props.nodeId, { requirements: event.target.value, generationError: '' })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成穿搭效果',
    message: '将新增一张穿搭效果图，已有结果不会删除。',
    confirmText: '继续生成',
  })) return

  submitting.value = true
  notice.value = ''
  const imageSettings = {
    model: settings.value.model.id,
    aspectRatio: settings.value.aspectRatio,
    resolution: settings.value.resolution,
    googleSearch: settings.value.googleSearch,
    googleImageSearch: settings.value.googleImageSearch,
  }
  const outputId = store.addOutfitResultNode(props.nodeId, garmentNode.value.id, modelNode.value.id, prompt.value, imageSettings)
  updateNodeData(props.nodeId, { status: 'generating', generationError: '' })
  try {
    const result = await createImageGeneration({
      workspace_id: store.workspaceId,
      node_id: outputId,
      ...buildImageRequest({ ...imageSettings, prompt: prompt.value }, references.value),
    })
    if (result.code !== 0) throw new Error(result.message)
    updateNodeData(outputId, { generationTaskId: result.data.id, generationStatus: result.data.status, status: 'generating' })
    updateNodeData(props.nodeId, { status: 'ready', generatedNodeIds: [...existingGeneratedNodes.value, outputId] })
  } catch (error) {
    const messageText = error.response?.data?.message || error.message || '穿搭任务提交失败'
    notice.value = messageText
    updateNodeData(outputId, { status: 'failed', generationError: messageText })
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    store.selectNodes([outputId])
    submitting.value = false
    await authStore.refreshCredits().catch(() => {})
  }
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel outfit-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Shirt :size="16" />服饰穿搭</span>
      <small>使用服饰图和模特图生成穿搭效果</small>
    </header>

    <div class="outfit-panel-references">
      <div v-for="item in sourceItems" :key="item.label" class="outfit-panel-reference" :class="{ empty: !item.node?.data.asset }">
        <img v-if="item.node?.data.asset" :src="buildOssImageUrl(item.node.data.asset, { width: 240, quality: 80 })" :alt="item.label" referrerpolicy="no-referrer" />
        <component :is="item.icon" v-else :size="20" />
        <span><strong>{{ item.label }}</strong><small>{{ item.node?.data.asset ? item.node.data.title : '尚未选择' }}</small></span>
      </div>
    </div>

    <AppTextarea
      :model-value="data.requirements"
      maxlength="1200"
      placeholder="补充穿搭要求，例如保持站姿、使用纯色背景或突出服装版型…"
      @input="updateRequirements"
    />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <ImageGenerationControls
      :settings="data"
      :estimated-credits="estimatedCredits"
      :disabled="!canSubmit"
      :running="submitting"
      submit-label="生成穿搭效果"
      @update:settings="updateSettings"
      @submit="submitTask"
    />
  </section>
</template>
