<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { ArrowUp, ChevronDown, Coins, FileText, Image, Images, LoaderCircle, Megaphone, Music2, Package, Video as VideoIcon, WandSparkles } from 'lucide-vue-next'
import { createAudioGeneration, createImageGeneration, createVideoGeneration } from '../../api/generations'
import { streamReversePrompt } from '../../api/reversals'
import { audioFormatOptions, audioModel, audioSampleRateOptions, buildAudioRequest, getAudioReferenceError, maxAudioPromptLength, normalizeAudioSettings } from '../../config/audioModels'
import { getEffectivePrompt, maxGenerationPromptLength } from '../../config/generationPrompt'
import { buildImageRequest, normalizeImageSettings } from '../../config/imageModels'
import { mergeProductProfile, parseProductProfile } from '../../config/canvas/ecommerce'
import { nodeDefinitions } from '../../config/canvas/nodeDefinitions'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { buildVideoRequest, defaultVideoModel, getVideoModelError, getVideoReferenceError, normalizeVideoSettings, videoModels } from '../../config/videoModels'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useCanvasStore } from '../../stores/canvas'
import { useAuthStore } from '../../stores/auth'
import AppButton from '../ui/AppButton.vue'
import AppMenu from '../ui/AppMenu.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppSlider from '../ui/AppSlider.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import ImageGenerationControls from './ImageGenerationControls.vue'
import PromptReferenceEditor from './PromptReferenceEditor.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  type: { type: String, required: true },
  embedded: Boolean,
})

const modelIcons = { text: FileText, image: Image, video: VideoIcon, audio: Music2, product: Package, selling_copy: Megaphone }
const modelIcon = computed(() => modelIcons[props.type] || WandSparkles)

const store = useCanvasStore()
const authStore = useAuthStore()
const toast = useGlobalToast()
const { updateNodeData } = useVueFlow()
const settingsTrigger = ref(null)
const settingsMenu = ref(null)
const settingsOpen = ref(false)
const settingsStyle = ref({})
const modelTrigger = ref(null)
const modelMenu = ref(null)
const modelOpen = ref(false)
const modelStyle = ref({})
const notice = ref('')
const running = computed(() => props.data.status === 'generating')
const references = computed(() => store.incomingNodes(props.nodeId))
const imageReferences = computed(() => references.value.filter((node) => node.type === 'image' && node.data.asset))
const audioReferences = computed(() => references.value.filter((node) => node.type === 'audio' && node.data.asset))
const mentionReferences = computed(() => {
  if (props.type === 'video') return references.value.filter((node) => ['image', 'video', 'audio'].includes(node.type) && node.data.asset)
  return props.type === 'audio' ? audioReferences.value : imageReferences.value
})
const isReverseTask = computed(() => props.type === 'text' && ['image', 'video'].includes(props.data.reverseType))
const isProductRecognition = computed(() => props.type === 'product')
const isVisionTextTask = computed(() => isReverseTask.value || isProductRecognition.value)
const reverseReference = computed(() => references.value.find((node) => node.type === (isProductRecognition.value ? 'image' : props.data.reverseType) && node.data.asset))
const legacyProductPrompt = computed(() => isProductRecognition.value && props.data.prompt?.startsWith('识别图片中的商品并严格输出一个 JSON 对象'))
const effectivePrompt = computed(() => ['image', 'video', 'audio'].includes(props.type)
  ? getEffectivePrompt(props.data, references.value)
  : legacyProductPrompt.value ? '' : props.data.prompt?.trim() || '')
const promptLimit = computed(() => isVisionTextTask.value ? 3000 : props.type === 'audio' ? maxAudioPromptLength : maxGenerationPromptLength)
const promptError = computed(() => effectivePrompt.value.length > promptLimit.value ? `提示词不能超过 ${promptLimit.value} 个字符` : '')
const promptParts = computed(() => props.data.promptParts ?? (props.data.prompt ? [{ type: 'text', value: props.data.prompt }] : []))
const selectedImageSettings = computed(() => normalizeImageSettings(props.data))
const selectedImageModel = computed(() => selectedImageSettings.value.model)
const selectedVideoSettings = computed(() => normalizeVideoSettings(props.data))
const selectedVideoModel = computed(() => selectedVideoSettings.value.model)
const selectedAudioSettings = computed(() => normalizeAudioSettings(props.data))
const selectedReverseModel = computed(() => reverseModels.find((model) => model.id === props.data.model) || defaultReverseModel)
const selectableModels = computed(() => props.type === 'video' ? videoModels : reverseModels)
const selectedModel = computed(() => props.type === 'video' ? selectedVideoModel.value : selectedReverseModel.value)
const selectedResolution = computed(() => props.type === 'image' ? selectedImageSettings.value.resolution : selectedVideoSettings.value.resolution)
const selectedAspectRatio = computed(() => props.type === 'image' ? selectedImageSettings.value.aspectRatio : selectedVideoSettings.value.aspectRatio)
const selectedDuration = computed(() => selectedVideoSettings.value.duration)
const estimatedCredits = computed(() => {
  if (isVisionTextTask.value) return authStore.estimateCredits('text', selectedReverseModel.value.id)
  if (!['image', 'video', 'audio'].includes(props.type)) return null
  const model = props.type === 'image' ? selectedImageModel.value.id : props.type === 'video' ? selectedVideoModel.value.id : audioModel.id
  return authStore.estimateCredits(props.type, model, {
    resolution: selectedResolution.value,
    duration: selectedDuration.value,
  })
})
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const creditLabel = computed(() => `${props.type === 'audio' ? '冻结' : '本次'} ${estimatedCredits.value} 积分`)
const referenceError = computed(() => {
  if (props.type === 'video') return getVideoReferenceError(props.data, references.value)
  if (props.type === 'audio') return getAudioReferenceError(references.value)
  return props.type === 'image' && selectedImageModel.value.maxReferences && imageReferences.value.length > selectedImageModel.value.maxReferences
    ? `当前模型最多支持 ${selectedImageModel.value.maxReferences} 张参考图片`
    : ''
})
const panelMessage = computed(() => notice.value || props.data.generationError || referenceError.value || promptError.value || (insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const settingLabel = computed(() => {
  if (props.type === 'video') return `${selectedAspectRatio.value === 'adaptive' ? '自适应' : selectedAspectRatio.value} · ${selectedResolution.value} · ${selectedDuration.value}s`
  if (props.type === 'audio') return `${audioFormatOptions.find(({ value }) => value === selectedAudioSettings.value.format)?.label} · ${selectedAudioSettings.value.sampleRate / 1000} kHz`
  return nodeDefinitions[props.type].setting
})
const displayReferences = computed(() => {
  const counts = {}
  return references.value.map((node) => {
    counts[node.type] = (counts[node.type] || 0) + 1
    return { key: node.id, node, number: counts[node.type], label: `${nodeDefinitions[node.type].label}${counts[node.type]}` }
  })
})
const canSubmit = computed(() => {
  if (running.value || (!effectivePrompt.value && !isProductRecognition.value) || referenceError.value || promptError.value || insufficientCredits.value) return false
  if (isVisionTextTask.value) return Boolean(reverseReference.value)
  if (props.type !== 'text') return true
  return references.value.some((node) => node.type === 'text' ? node.data.content?.trim() : node.data.asset)
})

function updatePrompt(parts) {
  notice.value = ''
  updateNodeData(props.nodeId, {
    promptParts: parts,
    prompt: parts.map((part) => {
      if (['image', 'video', 'audio'].includes(part.type)) {
        const number = mentionReferences.value.filter((node) => node.type === part.type).findIndex((node) => node.id === part.nodeId) + 1
        return `${props.type === 'image' ? '' : '@'}${nodeDefinitions[part.type].label}${number}`
      }
      return part.value
    }).join(''),
  })
}

function updateTextPrompt(event) {
  notice.value = ''
  updateNodeData(props.nodeId, { prompt: event.target.value })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (isVisionTextTask.value) {
    const nodeId = props.nodeId
    let content = ''
    notice.value = ''
    updateNodeData(nodeId, { status: 'generating', ...(isReverseTask.value ? { content: '' } : {}), generationError: '' })
    try {
      await streamReversePrompt({
        workspace_id: store.workspaceId,
        node_id: nodeId,
        model: selectedReverseModel.value.id,
        media_type: isProductRecognition.value ? 'image' : props.data.reverseType,
        media_url: reverseReference.value.data.asset,
        prompt: effectivePrompt.value,
        ...(isProductRecognition.value ? { response_mode: 'product_profile' } : {}),
      }, (delta) => {
        content += delta
        if (isReverseTask.value) updateNodeData(nodeId, { content })
      }, (taskId) => {
        updateNodeData(nodeId, { generationTaskId: taskId, generationStatus: 'running' })
      })
      updateNodeData(nodeId, isProductRecognition.value
        ? { status: 'ready', product: mergeProductProfile(props.data.product, parseProductProfile(content)), generationStatus: 'succeeded', workflowStep: 'visual' }
        : { status: 'ready', content })
    } catch (error) {
      const message = error.message || (isProductRecognition.value ? '商品识别失败' : '反推生成失败')
      notice.value = message
      updateNodeData(nodeId, { status: 'failed', ...(isReverseTask.value ? { content } : {}), generationError: message })
    } finally {
      await authStore.refreshCredits().catch(() => {})
    }
    return
  }
  if (!['image', 'video', 'audio'].includes(props.type)) {
    return
  }
  const nodeId = props.nodeId
  notice.value = ''
  updateNodeData(nodeId, {
    status: 'generating',
    generationProgress: 0,
    generationError: '',
  })
  try {
    const createGeneration = { image: createImageGeneration, video: createVideoGeneration, audio: createAudioGeneration }[props.type]
    const requestBuilders = { image: buildImageRequest, video: buildVideoRequest, audio: buildAudioRequest }
    const generationRequest = requestBuilders[props.type](
      { ...props.data, prompt: effectivePrompt.value },
      props.type === 'image' ? imageReferences.value : references.value,
    )
    const result = await createGeneration({
      workspace_id: store.workspaceId,
      node_id: nodeId,
      ...generationRequest,
    })
    if (result.code !== 0) throw new Error(result.message)
    updateNodeData(nodeId, {
      generationTaskId: result.data.id,
      generationStatus: result.data.status,
      status: 'generating',
    })
    await authStore.refreshCredits().catch(() => {})
  } catch (error) {
    updateNodeData(nodeId, {
      status: 'failed',
      generationError: error.response?.data?.message || error.message || '任务提交失败',
    })
  }
}

defineExpose({ submitTask })

function ratioIconStyle(value) {
  const [width, height] = value.split(':').map(Number)
  const scale = Math.min(16 / width, 16 / height)
  return { width: `${Math.round(width * scale)}px`, height: `${Math.round(height * scale)}px` }
}

function updateVideoModel(model) {
  const error = getVideoModelError({ ...props.data, model: model.id }, references.value)
  if (error) return
  const updates = { model: model.id }
  if (!model.resolutions.includes(selectedResolution.value)) updates.resolution = model.defaultResolution
  if (!model.aspectRatios.includes(selectedAspectRatio.value)) updates.aspectRatio = model.defaultAspectRatio
  if (model.durationOptions && !model.durationOptions.includes(selectedDuration.value)) updates.duration = model.defaultDuration
  else if (!model.durationOptions && (selectedDuration.value < model.durationMin || selectedDuration.value > model.durationMax)) updates.duration = model.defaultDuration
  updateNodeData(props.nodeId, updates)
  modelOpen.value = false
}

function updateModel(model) {
  if (props.type === 'video') updateVideoModel(model)
  else {
    updateNodeData(props.nodeId, { model: model.id })
    modelOpen.value = false
  }
}

function updateVideoSetting(key, value) {
  updateNodeData(props.nodeId, { [key]: value })
  if (key === 'aspectRatio') nextTick(() => requestAnimationFrame(updateSettingsPosition))
}

function updateAudioSetting(key, value) {
  updateNodeData(props.nodeId, { [key]: value })
}

watch(() => `${props.type}:${props.data.model}:${references.value.map((node) => node.type).join(',')}`, () => {
  if (props.type !== 'video' || props.data.model !== 'happyhorse-1.1') return
  if (!references.value.some((node) => ['audio', 'video'].includes(node.type))) return
  updateVideoModel(defaultVideoModel)
  toast.info('HappyHorse 不支持音频或视频参考，已切换为 Seedance 2')
}, { immediate: true })

function getElement(target) {
  return target?.element || target?.$el || target
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
  style.value = { left: `${left}px`, top: `${top}px` }
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

watch(() => props.nodeId, () => {
  notice.value = ''
  if (legacyProductPrompt.value) updateNodeData(props.nodeId, { prompt: '' })
  if (isVisionTextTask.value && selectedReverseModel.value.id !== props.data.model) {
    updateNodeData(props.nodeId, { model: selectedReverseModel.value.id })
  }
}, { immediate: true })
onMounted(() => window.addEventListener('pointerdown', closeSettings))
onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', closeSettings)
})
</script>

<template>
  <section v-if="!data.assetSource && (type !== 'text' || data.textMode === 'task')" class="generation-panel nodrag nowheel" :class="{ embedded }" @pointerdown.stop>
    <div v-if="displayReferences.length" class="reference-strip">
      <div v-for="reference in displayReferences" :key="reference.key" class="reference-item" :title="reference.label" :aria-label="reference.label">
        <img v-if="reference.node.type === 'image' && reference.node.data.asset" :src="reference.node.data.asset" alt="" />
        <FileText v-else-if="reference.node.type === 'text'" :size="20" />
        <Image v-else-if="reference.node.type === 'image'" :size="20" />
        <VideoIcon v-else-if="reference.node.type === 'video'" :size="20" />
        <Music2 v-else-if="reference.node.type === 'audio'" :size="20" />
        <Package v-else-if="reference.node.type === 'product'" :size="20" />
        <Images v-else-if="reference.node.type === 'product_visual'" :size="20" />
        <Megaphone v-else :size="20" />
        <b>{{ reference.number }}</b>
      </div>
    </div>

    <PromptReferenceEditor
      v-if="['image', 'video', 'audio'].includes(type)"
      :model-value="promptParts"
      :references="mentionReferences"
      :reference-type="type"
      :reference-label="type === 'video' ? '素材' : type === 'audio' ? '音频' : '图片'"
      :placeholder="nodeDefinitions[type].placeholder"
      @update:model-value="updatePrompt"
      @pointerdown="settingsOpen = false; modelOpen = false"
    />
    <AppTextarea
      v-else
      :model-value="data.prompt"
      :placeholder="nodeDefinitions[type].placeholder"
      :maxlength="promptLimit"
      @input="updateTextPrompt"
      @pointerdown="settingsOpen = false; modelOpen = false"
    />

    <AppMenu v-if="modelOpen && (type === 'video' || isVisionTextTask)" ref="modelMenu" class="model-menu" :style="modelStyle" @pointerdown.stop>
      <AppButton v-for="model in selectableModels" :key="model.id" :class="{ active: selectedModel.id === model.id }" :disabled="type === 'video' && Boolean(getVideoModelError({ ...data, model: model.id }, references))" :title="type === 'video' ? getVideoModelError({ ...data, model: model.id }, references) : ''" @click="updateModel(model)">
        <component :is="modelIcon" :size="15" />
        <span>{{ model.label }}</span>
      </AppButton>
    </AppMenu>

    <AppMenu v-if="settingsOpen && ['video', 'audio'].includes(type)" ref="settingsMenu" class="image-settings-menu media-settings-menu" :class="{ 'audio-settings-menu': type === 'audio' }" :style="settingsStyle" @pointerdown.stop>
      <template v-if="type === 'video'">
        <h3>时长</h3>
        <div v-if="selectedVideoModel.durationOptions" class="video-duration-options">
          <AppButton v-for="duration in selectedVideoModel.durationOptions" :key="duration" :class="{ active: selectedDuration === duration }" @click="updateVideoSetting('duration', duration)">{{ duration }}s</AppButton>
        </div>
        <div v-else class="video-duration-slider">
          <input type="range" :min="selectedVideoModel.durationMin" :max="selectedVideoModel.durationMax" step="1" :value="selectedDuration" aria-label="视频时长" @input="updateVideoSetting('duration', Number($event.target.value))" />
          <span>{{ selectedDuration }}s</span>
        </div>

        <h3>清晰度</h3>
        <div class="image-resolution-options">
          <AppButton v-for="resolution in selectedVideoModel.resolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="updateVideoSetting('resolution', resolution)">{{ resolution === '4k' ? '4K' : resolution }}</AppButton>
        </div>

        <h3>比例</h3>
        <div class="image-ratio-grid video-ratio-grid">
          <AppButton v-for="ratio in selectedVideoModel.aspectRatios" :key="ratio" :class="{ active: selectedAspectRatio === ratio }" @click="updateVideoSetting('aspectRatio', ratio)">
            <span v-if="ratio !== 'adaptive'" class="image-ratio-icon" :style="ratioIconStyle(ratio)"></span>
            <span v-else class="adaptive-ratio-icon">A</span>
            <strong>{{ ratio === 'adaptive' ? '自适应' : ratio }}</strong>
          </AppButton>
        </div>

        <template v-if="selectedVideoModel.generateAudio">
          <h3>输出</h3>
          <label class="setting-toggle-row">
            <span>生成同步音频</span>
            <input type="checkbox" :checked="selectedVideoSettings.generateAudio" @change="updateVideoSetting('generateAudio', $event.target.checked)" />
          </label>
        </template>
      </template>

      <template v-else>
        <div class="audio-setting-grid">
          <div>
            <span>格式</span>
            <AppSelect :model-value="selectedAudioSettings.format" :options="audioFormatOptions" aria-label="音频格式" @update:model-value="updateAudioSetting('format', $event)" />
          </div>
          <div>
            <span>采样率</span>
            <AppSelect class="audio-sample-select" :model-value="selectedAudioSettings.sampleRate" :options="audioSampleRateOptions" aria-label="音频采样率" @update:model-value="updateAudioSetting('sampleRate', $event)" />
          </div>
        </div>
        <h3>声音调整</h3>
        <div class="audio-slider-list">
          <AppSlider :model-value="selectedAudioSettings.speechRate" :min="-50" :max="100" label="语速" @update:model-value="updateAudioSetting('speechRate', $event)" />
          <AppSlider :model-value="selectedAudioSettings.loudnessRate" :min="-50" :max="100" label="音量" @update:model-value="updateAudioSetting('loudnessRate', $event)" />
          <AppSlider :model-value="selectedAudioSettings.pitchRate" :min="-12" :max="12" label="音调" @update:model-value="updateAudioSetting('pitchRate', $event)" />
        </div>
      </template>
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
    <footer v-else>
      <AppButton v-if="type === 'video' || isVisionTextTask" ref="modelTrigger" class="model-select model-select-trigger" @click="toggleModelMenu">
        <component :is="modelIcon" :size="16" />{{ selectedModel.label }}<ChevronDown :size="14" :class="{ rotated: modelOpen }" />
      </AppButton>
      <span v-else class="model-select"><component :is="modelIcon" :size="16" />{{ type === 'audio' ? audioModel.label : data.model }}</span>
      <span v-if="!['text', 'product'].includes(type)" class="panel-divider"></span>
      <AppButton v-if="['video', 'audio'].includes(type)" ref="settingsTrigger" class="image-settings-trigger media-settings-trigger" @click="toggleSettings">
        <component :is="type === 'video' ? VideoIcon : type === 'audio' ? Music2 : Image" :size="16" />{{ settingLabel }}<ChevronDown :size="14" :class="{ rotated: settingsOpen }" />
      </AppButton>
      <span v-else-if="!['text', 'product'].includes(type)" class="setting-select"><Image :size="16" />{{ settingLabel }}</span>
      <span v-if="estimatedCredits !== null" class="task-credit-cost"><Coins :size="14" />{{ creditLabel }}</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '执行中' : '执行'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="20" />
        <ArrowUp v-else :size="20" />
      </AppButton>
    </footer>
  </section>
</template>
