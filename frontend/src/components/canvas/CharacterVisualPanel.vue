<script setup>
import { useI18n } from 'vue-i18n'
import { canvasLabel } from '../../i18n/canvas'
import { computed } from 'vue'
import { ArrowUp, Coins, FileText, Globe2, Image, Images, LoaderCircle, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamTextGeneration } from '../../api/generations'
import { streamReversePrompt } from '../../api/reversals'
import { buildCharacterVisualPrompt, characterProfileContext, characterReady, characterVisualTypes, parseCharacterVisualPlan } from '../../config/canvas/character'
import { worldPromptContext, worldReady } from '../../config/canvas/drama'
import { normalizeImageSettings } from '../../config/imageModels'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppSelect from '../ui/AppSelect.vue'

const { t } = useI18n()

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  embedded: Boolean,
})

const store = useCanvasStore()
const capabilityStore = useModelCapabilitiesStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)

const worldNode = computed(() => store.incomingNodeByHandle(props.nodeId, 'world'))
const referenceImage = computed(() => store.incomingNodeByHandle(props.nodeId, 'reference'))
const selectedImageSettings = computed(() => normalizeImageSettings(
  { model: props.data.imageModel, aspectRatio: props.data.aspectRatio, resolution: props.data.resolution },
  capabilityStore.imageModels,
  capabilityStore.defaultImageModel,
))
const selectedTextModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.textModel) || capabilityStore.defaultTextModel)
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const imageModelOptions = computed(() => capabilityStore.imageModels.map(({ id, label }) => ({ value: id, label })))
const textModelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const ratioOptions = computed(() => selectedImageSettings.value.model.aspectRatios.map((value) => ({ value, label: value })))
const resolutionOptions = computed(() => selectedImageSettings.value.model.resolutions.map((value) => ({ value, label: value })))
const message = computed(() => failure.value || props.data.generationError || (!worldReady(worldNode.value?.data.world)
  ? t('canvas.completeWorldFirst')
  : !characterReady(props.data.profile)
    ? t('canvas.completeCharacterFirst')
    : insufficientCredits.value ? t('canvas.insufficientCredits', { p0: estimatedCredits.value }) : ''))
const canSubmit = computed(() => !running.value && worldReady(worldNode.value?.data.world) && characterReady(props.data.profile) && !insufficientCredits.value)

function updateData(value) {
  failure.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

function updateImageModel(imageModel) {
  const model = capabilityStore.imageModels.find(({ id }) => id === imageModel)
  updateData({
    imageModel: model.id,
    aspectRatio: model.aspectRatios.includes(props.data.aspectRatio) ? props.data.aspectRatio : model.defaultAspectRatio,
    resolution: model.resolutions.includes(props.data.resolution) ? props.data.resolution : model.defaultResolution,
  })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: t('canvas.regenerateCharacterPlan'),
    message: t('canvas.addThreeImageNodes'),
    confirmText: t('canvas.continueGeneration'),
  })) return

  const prompt = buildCharacterVisualPrompt(
    worldPromptContext(worldNode.value.data),
    characterProfileContext(props.data.profile),
    props.data,
    Boolean(referenceImage.value?.data.asset),
  )
  const hasReference = Boolean(referenceImage.value?.data.asset)
  const streamer = hasReference ? streamReversePrompt : streamTextGeneration
  await runTextTask(streamer, hasReference
    ? {
        workspace_id: store.workspaceId,
        node_id: props.nodeId,
        model: selectedTextModel.value.id,
        media_type: 'image',
        media_url: referenceImage.value.data.asset,
        prompt,
        response_mode: 'character_visual_plan',
      }
    : { workspace_id: store.workspaceId, node_id: props.nodeId, model: selectedTextModel.value.id, prompt }, {
    failureMessage: t('canvas.characterPlanFailed'),
    onSuccess: (content) => {
      const settings = selectedImageSettings.value
      const generatedNodeIds = store.addCharacterVisualNodes(
        props.nodeId,
        hasReference ? referenceImage.value.id : null,
        parseCharacterVisualPlan(content),
        { model: settings.model.id, aspectRatio: settings.aspectRatio, resolution: settings.resolution },
      )
      return { generatedNodeIds: [...existingGeneratedNodes.value, ...generatedNodeIds] }
    },
  })
}
</script>

<template>
  <section class="generation-panel product-visual-panel character-visual-panel nodrag nowheel" :class="{ embedded }" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Images :size="16" />{{ t('canvas.characterSheets') }}</span>
      <small><UserRound :size="13" />{{ data.profile?.name || t('canvas.unnamedCharacter') }}</small>
    </header>
    <div class="outfit-panel-references character-panel-references">
      <div class="outfit-panel-reference" :class="{ empty: !worldNode }">
        <Globe2 :size="20" />
        <span><strong>{{ t('canvas.world') }}</strong><small>{{ worldNode?.data.title || t('canvas.notConnected') }}</small></span>
      </div>
      <div class="outfit-panel-reference" :class="{ empty: !referenceImage?.data.asset }">
        <AppImageHoverPreview v-if="referenceImage?.data.asset" :src="referenceImage.data.asset" :preview-src="buildOssImageUrl(referenceImage.data.asset, { width: 1200, quality: 90 })" :alt="t('canvas.characterReference')">
          <img :src="buildOssImageUrl(referenceImage.data.asset, { width: 240, quality: 80 })" :alt="t('canvas.characterReference')" referrerpolicy="no-referrer" />
        </AppImageHoverPreview>
        <Image v-else :size="20" />
        <span><strong>{{ t('canvas.characterReference') }}</strong><small>{{ referenceImage?.data.asset ? referenceImage.data.title : t('canvas.optional') }}</small></span>
      </div>
    </div>
    <section class="character-visual-types">
      <div v-for="item in characterVisualTypes" :key="item.id" class="product-visual-option active">
        <span>{{ canvasLabel(item.label) }}</span>
      </div>
    </section>
    <div class="product-visual-settings">
      <label><span>{{ t('canvas.imageModel') }}</span><AppSelect :model-value="selectedImageSettings.model.id" :options="imageModelOptions" :aria-label="t('canvas.imageModel')" @update:model-value="updateImageModel" /></label>
      <label><span>{{ t('canvas.aspectRatio') }}</span><AppSelect :model-value="selectedImageSettings.aspectRatio" :options="ratioOptions" :aria-label="t('canvas.aspectRatio')" @update:model-value="updateData({ aspectRatio: $event })" /></label>
      <label><span>{{ t('canvas.resolution') }}</span><AppSelect :model-value="selectedImageSettings.resolution" :options="resolutionOptions" :aria-label="t('canvas.resolution')" @update:model-value="updateData({ resolution: $event })" /></label>
    </div>
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" :aria-label="t('canvas.textModel')" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />{{ t('canvas.creditCost', { p0: estimatedCredits }) }}</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? t('canvas.generating') : t('canvas.generateCharacterPlan')" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
