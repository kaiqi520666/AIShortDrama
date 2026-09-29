<script setup>
import { useI18n } from 'vue-i18n'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { ArrowUp, Check, ChevronDown, Clapperboard, Coins, Eye, EyeOff, FileText, Image, Images, LoaderCircle, Music2, Package, Shirt, Video as VideoIcon, WandSparkles } from 'lucide-vue-next'
import { nodeDefinitions } from '../../config/canvas/nodeDefinitions'
import { canvasLabel } from '../../i18n/canvas'
import { useGlobalConfirm, useGlobalToast } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useCanvasStore } from '../../stores/canvas'
import { useAuthStore } from '../../stores/auth'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { buildOssImageUrl } from '../../utils/ossImage'
import { useGenerationContext } from './useGenerationContext'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppMenu from '../ui/AppMenu.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import AudioGenerationSettings from './AudioGenerationSettings.vue'
import ImageGenerationControls from './ImageGenerationControls.vue'
import PromptReferenceEditor from './PromptReferenceEditor.vue'
import TextGenerationControls from './TextGenerationControls.vue'
import VideoGenerationSettings from './VideoGenerationSettings.vue'

const { t } = useI18n()

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  type: { type: String, required: true },
  embedded: Boolean,
})

const modelIcons = { text: FileText, image: Image, video: VideoIcon, audio: Music2, product: FileText, outfit: Shirt }
const modelIcon = computed(() => modelIcons[props.type] || WandSparkles)

const store = useCanvasStore()
const authStore = useAuthStore()
const capabilityStore = useModelCapabilitiesStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)
const settingsTrigger = ref(null)
const settingsMenu = ref(null)
const settingsOpen = ref(false)
const settingsStyle = ref({})
const modelTrigger = ref(null)
const modelMenu = ref(null)
const modelOpen = ref(false)
const modelStyle = ref({})
const storyboardPromptView = ref('image')

const context = useGenerationContext({
  props,
  store,
  authStore,
  capabilityStore,
  updateNodeData,
  confirm,
  toast,
  runTextTask,
  failure,
})
const {
  running,
  isStoryboardImage,
  isStoryboardVideo,
  isVisionTextTask,
  hasNextStoryboardSegment,
  references,
  mentionReferences,
  promptParts,
  selectedVideoSettings,
  selectedVideoModel,
  selectedAudioSettings,
  selectableModels,
  selectedModel,
  selectedResolution,
  selectedAspectRatio,
  selectedDuration,
  audioModel,
  audioFormatOptions,
  audioSampleRateOptions,
  promptLimit,
  estimatedCredits,
  creditLabel,
  panelMessage,
  settingLabel,
  displayReferences,
  canSubmit,
  updatePrompt,
  updateTextPrompt,
  toggleReference,
  submitTask,
  updateVideoPrompt,
  videoModelError,
  updateModel: applyModel,
  updateVideoSetting: applyVideoSetting,
  updateAudioSetting: applyAudioSetting,
  confirmStoryboardSegment,
} = context

function updateModel(model) {
  if (applyModel(model)) modelOpen.value = false
}

function updateVideoSetting(key, value) {
  if (applyVideoSetting(key, value) === 'close') settingsOpen.value = false
  if (key === 'aspectRatio') nextTick(() => requestAnimationFrame(updateSettingsPosition))
}

function updateAudioSetting(key, value) {
  if (applyAudioSetting(key, value) === 'close') settingsOpen.value = false
}

defineExpose({ submitTask })

function getElement(target) {
  let element = target
  while (element?.element || element?.$el) {
    const next = element.element || element.$el
    if (next === element) break
    element = next
  }
  return element
}

function updateMenuPosition(trigger, menu, style) {
  const triggerElement = getElement(trigger)
  const menuElement = getElement(menu)
  if (!triggerElement || !menuElement) return
  const panelRect = triggerElement.closest('.generation-panel').getBoundingClientRect()
  const triggerRect = triggerElement.getBoundingClientRect()
  const menuHeight = menuElement.offsetHeight
  const menuWidth = menuElement.offsetWidth
  const gap = 8
  const centeredLeft = triggerRect.left - panelRect.left + (triggerRect.width - menuWidth) / 2
  const left = Math.min(Math.max(0, centeredLeft), Math.max(0, panelRect.width - menuWidth))
  const top = triggerRect.top - menuHeight - gap >= 12
    ? triggerRect.top - panelRect.top - menuHeight - gap
    : triggerRect.bottom - panelRect.top + gap
  style.value = { left: left + 'px', top: top + 'px' }
}

function updateSettingsPosition() {
  updateMenuPosition(settingsTrigger.value, settingsMenu.value, settingsStyle)
}

function toggleModelMenu() {
  modelOpen.value = !modelOpen.value
  settingsOpen.value = false
  if (modelOpen.value) nextTick(() => updateMenuPosition(modelTrigger.value, modelMenu.value, modelStyle))
}

function toggleSettings() {
  settingsOpen.value = !settingsOpen.value
  modelOpen.value = false
  if (settingsOpen.value) nextTick(updateSettingsPosition)
}

function closeSettings(event) {
  if (!event.target.closest('.media-settings-menu, .media-settings-trigger')) settingsOpen.value = false
  if (!event.target.closest('.model-menu, .model-select-trigger')) modelOpen.value = false
}

function handleKeydown(event) {
  if (event.key !== 'Escape') return
  if (!settingsOpen.value && !modelOpen.value) return
  event.preventDefault()
  settingsOpen.value = false
  modelOpen.value = false
}

watch(() => props.nodeId, () => {
  storyboardPromptView.value = 'image'
}, { immediate: true })

onMounted(() => {
  window.addEventListener('pointerdown', closeSettings)
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', closeSettings)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <section v-if="!data.assetSource && (type !== 'text' || data.textMode === 'task')" class="generation-panel nodrag nowheel" :class="{ embedded }" @pointerdown.stop>
    <div v-if="displayReferences.length" class="reference-strip">
      <div v-for="reference in displayReferences" :key="reference.key" class="reference-item" :class="{ 'is-disabled': !reference.enabled }" :title="`${reference.label} · ${reference.enabled ? t('canvas.enabled') : t('canvas.disabled')}`" :aria-label="`${reference.label} · ${reference.enabled ? t('canvas.enabled') : t('canvas.disabled')}`">
        <AppImageHoverPreview v-if="reference.node.type === 'image' && reference.node.data.asset" :src="reference.node.data.asset" :preview-src="buildOssImageUrl(reference.node.data.asset, { width: 1200, quality: 90 })" :alt="reference.label">
          <img :src="buildOssImageUrl(reference.node.data.asset)" alt="" />
        </AppImageHoverPreview>
        <FileText v-else-if="reference.node.type === 'text'" :size="20" />
        <Image v-else-if="reference.node.type === 'image'" :size="20" />
        <VideoIcon v-else-if="reference.node.type === 'video'" :size="20" />
        <Music2 v-else-if="reference.node.type === 'audio'" :size="20" />
        <Package v-else-if="reference.node.type === 'product'" :size="20" />
        <Images v-else-if="reference.node.type === 'product_visual'" :size="20" />
        <Shirt v-else-if="reference.node.type === 'outfit'" :size="20" />
        <WandSparkles v-else :size="20" />
        <b>{{ reference.number }}</b>
        <AppButton
          v-if="reference.toggleable"
          class="reference-toggle"
          icon-only
          size="sm"
          variant="ghost"
          :title="`${reference.enabled ? t('canvas.disable') : t('canvas.enable')} ${reference.label}`"
          :aria-label="`${reference.enabled ? t('canvas.disable') : t('canvas.enable')} ${reference.label}`"
          :aria-pressed="reference.enabled"
          @pointerdown.stop
          @click.stop="toggleReference(reference)"
        >
          <Eye v-if="reference.enabled" :size="12" />
          <EyeOff v-else :size="12" />
        </AppButton>
      </div>
    </div>

    <div v-if="isStoryboardImage" class="storyboard-prompt-tabs" role="tablist" :aria-label="t('canvas.storyboardPromptType')">
      <AppButton :class="{ active: storyboardPromptView === 'image' }" role="tab" :aria-selected="storyboardPromptView === 'image'" @click="storyboardPromptView = 'image'"><Clapperboard :size="14" />{{ t('canvas.storyboardImage') }}</AppButton>
      <AppButton :class="{ active: storyboardPromptView === 'video' }" role="tab" :aria-selected="storyboardPromptView === 'video'" @click="storyboardPromptView = 'video'"><VideoIcon :size="14" />{{ t('canvas.videoScript') }}</AppButton>
      <span>{{ t('canvas.shotDuration', { p0: data.storyboardShotCount, p1: data.storyboardDuration }) }}</span>
    </div>

    <PromptReferenceEditor
      v-if="['image', 'video', 'audio'].includes(type) && (!isStoryboardImage || storyboardPromptView === 'image')"
      :model-value="promptParts"
      :references="mentionReferences"
      :reference-type="type"
      :reference-label="type === 'video' ? t('canvas.media') : type === 'audio' ? t('canvas.audio') : t('canvas.image')"
      :placeholder="canvasLabel(nodeDefinitions[type].placeholder)"
      @update:model-value="updatePrompt"
      @pointerdown="settingsOpen = false; modelOpen = false"
    />
    <AppTextarea
      v-else-if="isStoryboardImage"
      class="storyboard-video-prompt nodrag nopan"
      :model-value="data.videoPrompt"
      :maxlength="promptLimit"
      :placeholder="t('canvas.seedancePlaceholder')"
      :aria-label="t('canvas.videoScript')"
      @input="updateVideoPrompt"
      @pointerdown="settingsOpen = false; modelOpen = false"
    />
    <AppTextarea
      v-else
      :model-value="data.prompt"
      :placeholder="canvasLabel(nodeDefinitions[type].placeholder)"
      :maxlength="promptLimit"
      @input="updateTextPrompt"
      @pointerdown="settingsOpen = false; modelOpen = false"
    />

    <AppMenu v-if="modelOpen && (type === 'video' || isVisionTextTask)" ref="modelMenu" class="model-menu" :style="modelStyle" @pointerdown.stop>
      <AppButton v-for="model in selectableModels" :key="model.id" :class="{ active: selectedModel.id === model.id }" :disabled="type === 'video' && Boolean(videoModelError({ ...data, model: model.id }, references))" :title="type === 'video' ? videoModelError({ ...data, model: model.id }, references) : ''" @click="updateModel(model)">
        <component :is="modelIcon" :size="15" />
        <span>{{ model.label }}</span>
      </AppButton>
    </AppMenu>

    <AppMenu v-if="settingsOpen && ['video', 'audio'].includes(type)" ref="settingsMenu" class="image-settings-menu media-settings-menu" :class="{ 'audio-settings-menu': type === 'audio' }" :style="settingsStyle" @pointerdown.stop>
      <VideoGenerationSettings
        v-if="type === 'video'"
        :model="selectedVideoModel"
        :settings="selectedVideoSettings"
        :selected-duration="selectedDuration"
        :selected-resolution="selectedResolution"
        :selected-aspect-ratio="selectedAspectRatio"
        :storyboard="isStoryboardVideo"
        :segment-index="data.storyboardSegmentIndex"
        :continuity-mode="data.storyboardContinuityMode"
        @update="updateVideoSetting"
      />
      <AudioGenerationSettings
        v-else
        :settings="selectedAudioSettings"
        :format-options="audioFormatOptions"
        :sample-rate-options="audioSampleRateOptions"
        @update="updateAudioSetting"
      />
    </AppMenu>

    <p v-if="panelMessage" class="panel-notice">{{ panelMessage }}</p>

    <ImageGenerationControls
      v-if="type === 'image'"
      :settings="data"
      :estimated-credits="estimatedCredits"
      :disabled="!canSubmit"
      :running="running"
      @update:settings="updateNodeData(nodeId, $event)"
      @submit="submitTask"
    />
    <footer v-else-if="['text', 'product'].includes(type)">
      <TextGenerationControls
        ref="modelTrigger"
        :model="selectedModel"
        :model-icon="modelIcon"
        :model-selectable="isVisionTextTask"
        :model-open="modelOpen"
        :estimated-credits="estimatedCredits"
        :credit-label="creditLabel"
        :running="running"
        :disabled="!canSubmit"
        @toggle-model="toggleModelMenu"
        @submit="submitTask"
      />
    </footer>
    <footer v-else>
      <AppButton v-if="isStoryboardVideo && data.status === 'ready'" class="storyboard-confirm-button" variant="soft" @click="confirmStoryboardSegment">
        <Check :size="15" />{{ hasNextStoryboardSegment ? t('canvas.continueSegment', { p0: data.storyboardSegmentIndex + 1 }) : t('canvas.done') }}
      </AppButton>
      <AppButton v-if="type === 'video'" ref="modelTrigger" class="model-select model-select-trigger" @click="toggleModelMenu">
        <component :is="modelIcon" :size="16" />{{ selectedModel.label }}<ChevronDown :size="14" :class="{ rotated: modelOpen }" />
      </AppButton>
      <span v-else class="model-select"><component :is="modelIcon" :size="16" />{{ type === 'audio' ? audioModel.label : data.model }}</span>
      <span class="panel-divider"></span>
      <AppButton v-if="['video', 'audio'].includes(type)" ref="settingsTrigger" class="image-settings-trigger media-settings-trigger" @click="toggleSettings">
        <component :is="type === 'video' ? VideoIcon : type === 'audio' ? Music2 : Image" :size="16" />{{ settingLabel }}<ChevronDown :size="14" :class="{ rotated: settingsOpen }" />
      </AppButton>
      <span v-else class="setting-select"><Image :size="16" />{{ settingLabel }}</span>
      <span v-if="estimatedCredits !== null" class="task-credit-cost"><Coins :size="14" />{{ creditLabel }}</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? t('canvas.running') : t('canvas.run')" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="20" />
        <ArrowUp v-else :size="20" />
      </AppButton>
    </footer>
  </section>
</template>
