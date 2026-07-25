<script setup>
import { computed, ref } from 'vue'
import { Coins, LoaderCircle, PackageSearch, ScanSearch } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { mergeProductProfile, parseProductProfile, productRecognitionPrompt } from '../../config/canvas/ecommerce'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const authStore = useAuthStore()
const { updateNodeData } = useVueFlow()
const notice = ref('')
const imageNode = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'image'))
const imageUrl = computed(() => imageNode.value?.data.asset || '')
const model = computed(() => props.data.model || defaultReverseModel.id)
const running = computed(() => props.data.recognitionStatus === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', model.value))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const canSubmit = computed(() => imageUrl.value && !running.value && !insufficientCredits.value)
const message = computed(() => notice.value || props.data.recognitionError || (!imageNode.value
  ? '请先连接商品参考图'
  : !imageUrl.value
    ? '请先上传商品参考图'
    : insufficientCredits.value
      ? `积分不足，本次需要 ${estimatedCredits.value} 积分`
      : ''))

function setModel(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { model: value, recognitionError: '' })
}

async function recognizeProduct() {
  if (!canSubmit.value) return
  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { recognitionStatus: 'generating', recognitionError: '' })
  try {
    await streamReversePrompt({
      workspace_id: store.workspaceId,
      node_id: props.nodeId,
      model: model.value,
      media_type: 'image',
      media_url: imageUrl.value,
      prompt: productRecognitionPrompt,
      response_mode: 'product_profile',
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    const product = mergeProductProfile(props.data.product, parseProductProfile(content))
    updateNodeData(props.nodeId, {
      product,
      status: 'ready',
      recognitionStatus: 'succeeded',
      generationStatus: 'succeeded',
    })
    notice.value = '识别完成，已补充商品档案'
  } catch (error) {
    const messageText = error.message || '商品识别失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { recognitionStatus: 'failed', recognitionError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}
</script>

<template>
  <section class="generation-panel product-recognition-panel nodrag nowheel" @pointerdown.stop>
    <header class="selling-copy-panel-header">
      <span><PackageSearch :size="16" />商品识别</span>
      <small v-if="imageNode">{{ imageNode.data.title }}</small>
    </header>
    <div class="selling-copy-panel-controls">
      <label><span>识别模型</span><AppSelect :model-value="model" :options="reverseModels.map(({ id, label }) => ({ value: id, label }))" aria-label="商品识别模型" @update:model-value="setModel" /></label>
    </div>
    <p v-if="message" class="panel-notice" :class="{ 'panel-notice--success': notice.startsWith('识别完成') }">{{ message }}</p>
    <footer>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" variant="primary" :disabled="!canSubmit" @click="recognizeProduct">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="17" />
        <ScanSearch v-else :size="17" />
        {{ running ? '识别中' : 'AI 识别' }}
      </AppButton>
    </footer>
  </section>
</template>
