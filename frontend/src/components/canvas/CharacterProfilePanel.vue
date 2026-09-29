<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { ArrowUp, Coins, FileText, Globe2, Image, LoaderCircle } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamTextGeneration } from '../../api/generations'
import { streamReversePrompt } from '../../api/reversals'
import { buildCharacterProfilePrompt, mergeCharacterProfile, parseCharacterProfile } from '../../config/canvas/character'
import { worldPromptContext, worldReady } from '../../config/canvas/drama'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'

const { t } = useI18n()

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  embedded: Boolean,
})

const store = useCanvasStore()
const capabilityStore = useModelCapabilitiesStore()
const authStore = useAuthStore()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)

const worldNode = computed(() => store.incomingNodeByHandle(props.nodeId, 'world'))
const referenceImage = computed(() => store.incomingNodeByHandle(props.nodeId, 'reference'))
const selectedModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.model) || capabilityStore.defaultTextModel)
const modelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const message = computed(() => failure.value || props.data.generationError || (!worldNode.value
  ? t('canvas.connectWorldFirst')
  : !worldReady(worldNode.value.data.world)
    ? t('canvas.completeWorldFirst')
    : !props.data.prompt?.trim()
      ? t('canvas.enterCharacterIdea')
      : insufficientCredits.value ? t('canvas.insufficientCredits', { p0: estimatedCredits.value }) : ''))
const canSubmit = computed(() => !running.value && worldReady(worldNode.value?.data.world) && props.data.prompt?.trim() && !insufficientCredits.value)

async function submitTask() {
  if (!canSubmit.value) return
  const prompt = buildCharacterProfilePrompt(worldPromptContext(worldNode.value.data), props.data, Boolean(referenceImage.value?.data.asset))
  const hasReference = Boolean(referenceImage.value?.data.asset)
  const streamer = hasReference ? streamReversePrompt : streamTextGeneration
  await runTextTask(streamer, hasReference
    ? {
        workspace_id: store.workspaceId,
        node_id: props.nodeId,
        model: selectedModel.value.id,
        media_type: 'image',
        media_url: referenceImage.value.data.asset,
        prompt,
        response_mode: 'character_profile',
      }
    : { workspace_id: store.workspaceId, node_id: props.nodeId, model: selectedModel.value.id, prompt }, {
    failureMessage: t('canvas.characterProfileFailed'),
    onSuccess: (content) => ({
      profile: mergeCharacterProfile(props.data.profile, parseCharacterProfile(content)),
      workflowStep: 'visual',
    }),
  })
}
</script>

<template>
  <section class="generation-panel character-profile-panel nodrag nowheel" :class="{ embedded }" @pointerdown.stop>
    <div class="reference-strip">
      <div class="reference-item" :class="{ optional: !worldNode }" :title="worldNode ? t('canvas.world') : t('canvas.worldDisconnected')">
        <Globe2 :size="20" /><b>{{ worldNode ? 1 : '?' }}</b>
      </div>
      <div v-if="referenceImage?.data.asset" class="reference-item" :title="t('canvas.characterReference')">
        <AppImageHoverPreview :src="referenceImage.data.asset" :preview-src="buildOssImageUrl(referenceImage.data.asset, { width: 1200, quality: 90 })" :alt="t('canvas.characterReference')">
          <img :src="buildOssImageUrl(referenceImage.data.asset)" :alt="t('canvas.characterReference')" referrerpolicy="no-referrer" />
        </AppImageHoverPreview>
        <b>1</b>
      </div>
      <div v-else class="reference-item optional" :title="t('canvas.optionalCharacterReference')">
        <Image :size="20" /><b>?</b>
      </div>
    </div>
    <AppTextarea
      :model-value="data.prompt"
      maxlength="1200"
      :placeholder="t('canvas.characterIdeaPlaceholder')"
      @input="failure = ''; updateNodeData(nodeId, { prompt: $event.target.value, generationError: '' })"
    />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer>
      <FileText :size="16" />
      <AppSelect :model-value="selectedModel.id" :options="modelOptions" :aria-label="t('canvas.textModel')" @update:model-value="updateNodeData(nodeId, { model: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />{{ t('canvas.creditCost', { p0: estimatedCredits }) }}</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? t('canvas.generating') : t('canvas.generateCharacterProfile')" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
