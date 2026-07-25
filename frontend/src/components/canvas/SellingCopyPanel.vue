<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Coins, LoaderCircle, Megaphone, Package } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamTextGeneration } from '../../api/generations'
import { copyOutputTypes, productPromptContext } from '../../config/canvas/ecommerce'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const authStore = useAuthStore()
const { updateNodeData } = useVueFlow()
const notice = ref('')
const references = computed(() => store.incomingNodes(props.nodeId))
const productNode = computed(() => references.value.find((node) => node.type === 'product'))
const productContext = computed(() => productPromptContext(productNode.value?.data.product))
const textContext = computed(() => references.value.filter((node) => node.type === 'text').map((node) => node.data.content?.trim()).filter(Boolean).join('\n'))
const outputType = computed(() => props.data.outputType || 'selling_points')
const outputLabel = computed(() => copyOutputTypes.find((item) => item.value === outputType.value)?.label || '核心卖点')
const model = computed(() => props.data.model || defaultReverseModel.id)
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', model.value))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const prompt = computed(() => [
  `请根据以下商品资料生成${outputLabel.value}。`,
  productContext.value,
  textContext.value ? `补充素材：\n${textContext.value}` : '',
  props.data.requirements?.trim() ? `额外要求：\n${props.data.requirements.trim()}` : '',
  '只输出可直接使用的中文文案，不解释生成过程，不使用 Markdown。',
].filter(Boolean).join('\n\n'))
const canSubmit = computed(() => !running.value && productContext.value && prompt.value.length <= 3000 && !insufficientCredits.value)
const message = computed(() => notice.value || props.data.generationError || (!productNode.value
  ? '请先连接商品资料节点'
  : !productContext.value
    ? '请先填写商品资料'
    : prompt.value.length > 3000
      ? '输入内容不能超过 3000 个字符'
      : insufficientCredits.value
        ? `积分不足，本次需要 ${estimatedCredits.value} 积分`
        : ''))

function updateSetting(key, value) {
  notice.value = ''
  updateNodeData(props.nodeId, { [key]: value, generationError: '' })
}

async function submitTask() {
  if (!canSubmit.value) return
  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { status: 'generating', content: '', generationError: '' })
  try {
    await streamTextGeneration({
      workspace_id: store.workspaceId,
      node_id: props.nodeId,
      model: model.value,
      prompt: prompt.value,
    }, (delta) => {
      content += delta
      updateNodeData(props.nodeId, { content })
    }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    updateNodeData(props.nodeId, { status: 'ready', content, generationStatus: 'succeeded' })
  } catch (error) {
    const messageText = error.message || '文案生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', content, generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel selling-copy-panel nodrag nowheel" @pointerdown.stop>
    <header class="selling-copy-panel-header">
      <span><Megaphone :size="16" />电商文案</span>
      <small v-if="productNode"><Package :size="13" />{{ productNode.data.product?.name || productNode.data.title }}</small>
    </header>
    <div class="selling-copy-panel-controls">
      <label><span>输出类型</span><AppSelect :model-value="outputType" :options="copyOutputTypes" aria-label="文案输出类型" @update:model-value="updateSetting('outputType', $event)" /></label>
      <label><span>文本模型</span><AppSelect :model-value="model" :options="reverseModels.map(({ id, label }) => ({ value: id, label }))" aria-label="文本模型" @update:model-value="updateSetting('model', $event)" /></label>
    </div>
    <AppTextarea
      :model-value="data.requirements"
      maxlength="1000"
      placeholder="补充语气、平台、字数或表达要求…"
      aria-label="文案补充要求"
      @input="updateSetting('requirements', $event.target.value)"
      @keydown.stop
    />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" variant="primary" icon-only :disabled="!canSubmit" aria-label="生成文案" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="17" />
        <ArrowUp v-else :size="17" />
      </AppButton>
    </footer>
  </section>
</template>
