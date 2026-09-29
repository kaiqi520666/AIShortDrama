<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { ArrowUp, Coins, FileText, LoaderCircle } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamTextGeneration } from '../../api/generations'
import { buildWorldPrompt, parseWorldProfile, worldReady } from '../../config/canvas/drama'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'

const { t } = useI18n()

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const capabilityStore = useModelCapabilitiesStore()
const authStore = useAuthStore()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)
const step = computed(() => props.data.workflowStep || 'setting')
const completed = computed(() => worldReady(props.data.world))
const selectedModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.model) || capabilityStore.defaultTextModel)
const modelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const message = computed(() => failure.value || props.data.generationError || (!props.data.prompt?.trim()
  ? t('canvas.enterStoryIdea')
  : insufficientCredits.value ? t('canvas.insufficientCredits', { p0: estimatedCredits.value }) : ''))
const canSubmit = computed(() => !running.value && props.data.prompt?.trim() && !insufficientCredits.value)

async function submitTask() {
  if (!canSubmit.value) return
  await runTextTask(streamTextGeneration, {
    workspace_id: store.workspaceId,
    node_id: props.nodeId,
    model: selectedModel.value.id,
    prompt: buildWorldPrompt(props.data),
  }, {
    failureMessage: t('canvas.worldGenerationFailed'),
    onSuccess: (content) => ({ world: parseWorldProfile(content), workflowStep: 'result' }),
  })
}
</script>

<template>
  <section class="generation-panel world-creation-panel nodrag nowheel" :class="`step-${step}`" @pointerdown.stop>
    <ProductWorkflowSteps
      :step="step"
      :recognized="completed"
      first-step="setting"
      second-step="result"
      :first-label="t('canvas.settingInput')"
      :second-label="t('canvas.worldResult')"
      :aria-label="t('canvas.worldSteps')"
      @update:step="updateNodeData(nodeId, { workflowStep: $event })"
    />
    <div class="world-creation-stage">
      <AppTextarea
        :model-value="data.prompt"
        maxlength="1200"
        :placeholder="t('canvas.worldIdeaPlaceholder')"
        @input="failure = ''; updateNodeData(nodeId, { prompt: $event.target.value, generationError: '' })"
      />
      <p v-if="message" class="panel-notice">{{ message }}</p>
      <footer>
        <FileText :size="16" />
        <AppSelect :model-value="selectedModel.id" :options="modelOptions" :aria-label="t('canvas.textModel')" @update:model-value="updateNodeData(nodeId, { model: $event })" />
        <span class="panel-divider"></span>
        <span class="task-credit-cost"><Coins :size="14" />{{ t('canvas.creditCost', { p0: estimatedCredits }) }}</span>
        <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? t('canvas.generating') : completed ? t('canvas.regenerateWorld') : t('canvas.generateWorld')" @click="submitTask">
          <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
          <ArrowUp v-else :size="18" />
        </AppButton>
      </footer>
    </div>
  </section>
</template>
