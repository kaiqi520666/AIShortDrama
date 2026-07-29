<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Coins, FileText, LoaderCircle } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamTextGeneration } from '../../api/generations'
import { buildWorldPrompt, parseWorldProfile, worldReady } from '../../config/canvas/drama'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const authStore = useAuthStore()
const { updateNodeData } = useVueFlow()
const notice = ref('')
const step = computed(() => props.data.workflowStep || 'setting')
const completed = computed(() => worldReady(props.data.world))
const selectedModel = computed(() => reverseModels.find((model) => model.id === props.data.model) || defaultReverseModel)
const modelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const message = computed(() => notice.value || props.data.generationError || (!props.data.prompt?.trim()
  ? '请先输入故事想法'
  : insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const canSubmit = computed(() => !running.value && props.data.prompt?.trim() && !insufficientCredits.value)

async function submitTask() {
  if (!canSubmit.value) return
  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { status: 'generating', generationError: '' })
  try {
    await streamTextGeneration({
      workspace_id: store.workspaceId,
      node_id: props.nodeId,
      model: selectedModel.value.id,
      prompt: buildWorldPrompt(props.data),
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    updateNodeData(props.nodeId, {
      status: 'ready',
      world: parseWorldProfile(content),
      workflowStep: 'result',
      generationStatus: 'succeeded',
    })
  } catch (error) {
    const messageText = error.message || '世界观生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}
</script>

<template>
  <section class="generation-panel world-creation-panel nodrag nowheel" :class="`step-${step}`" @pointerdown.stop>
    <ProductWorkflowSteps
      :step="step"
      :recognized="completed"
      first-step="setting"
      second-step="result"
      first-label="设定输入"
      second-label="世界观结果"
      aria-label="世界观创作步骤"
      @update:step="updateNodeData(nodeId, { workflowStep: $event })"
    />
    <div class="world-creation-stage">
      <AppTextarea
        :model-value="data.prompt"
        maxlength="1200"
        placeholder="输入故事的大概想法，例如：失忆记者调查一座只在雨夜出现的旅馆……"
        @input="notice = ''; updateNodeData(nodeId, { prompt: $event.target.value, generationError: '' })"
      />
      <p v-if="message" class="panel-notice">{{ message }}</p>
      <footer>
        <FileText :size="16" />
        <AppSelect :model-value="selectedModel.id" :options="modelOptions" aria-label="文本模型" @update:model-value="updateNodeData(nodeId, { model: $event })" />
        <span class="panel-divider"></span>
        <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
        <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : completed ? '重新生成世界观' : '生成世界观'" @click="submitTask">
          <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
          <ArrowUp v-else :size="18" />
        </AppButton>
      </footer>
    </div>
  </section>
</template>
