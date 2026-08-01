<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { ArrowUp, Check, ChevronDown, Clapperboard, Coins, Eye, EyeOff, FileText, Image, Images, LoaderCircle, Music2, Package, Shirt, Video as VideoIcon, WandSparkles } from 'lucide-vue-next'
import { createAudioGeneration, createImageGeneration, createVideoGeneration } from '../../api/generations'
import { streamReversePrompt } from '../../api/reversals'
import { audioFormatOptions, audioModel, audioSampleRateOptions, buildAudioRequest, getAudioReferenceError, maxAudioPromptLength, normalizeAudioSettings } from '../../config/audioModels'
import { buildStoryboardProductVideoContext, getEffectivePrompt, maxGenerationPromptLength } from '../../config/generationPrompt'
import { buildImageRequest, normalizeImageSettings } from '../../config/imageModels'
import { mergeProductProfile, parseProductProfile } from '../../config/canvas/ecommerce'
import { maxProductReferenceImages } from '../../config/canvas/connectionRules'
import { nodeDefinitions } from '../../config/canvas/nodeDefinitions'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { buildVideoRequest, getVideoModelError, getVideoReferenceError, normalizeVideoSettings, videoModels } from '../../config/videoModels'
import { useGlobalConfirm, useGlobalToast } from '../../composables/useGlobalUI'
import { useCanvasStore } from '../../stores/canvas'
import { useAuthStore } from '../../stores/auth'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
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

const modelIcons = { text: FileText, image: Image, video: VideoIcon, audio: Music2, product: FileText, outfit: Shirt }
const modelIcon = computed(() => modelIcons[props.type] || WandSparkles)

const store = useCanvasStore()
const authStore = useAuthStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
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
const storyboardPromptView = ref('image')
const running = computed(() => props.data.status === 'generating')
const isStoryboardImage = computed(() => props.type === 'image' && Boolean(props.data.storyboardSourceId && props.data.videoPrompt))
const isStoryboardSegment = computed(() => Boolean(props.data.storyboardSegmentIndex && props.data.storyboardSourceId))
const isStoryboardVideo = computed(() => props.type === 'video' && isStoryboardSegment.value)
const storyboardLocked = computed(() => isStoryboardSegment.value && props.data.segmentLocked)
const hasNextStoryboardSegment = computed(() => isStoryboardVideo.value && props.data.storyboardSegmentIndex < props.data.storyboardSegmentCount)
const connectedReferences = computed(() => store.incomingNodes(props.nodeId).map((node) => (
  props.type === 'video' && node.type === 'image' && node.data.storyboardSourceId
    ? { ...node, data: { ...node.data, providerAsset: node.data.storyboardAsset?.asset_url } }
    : node
)))
const references = computed(() => {
  const character = props.data.storyboardCharacter
  const productReferences = (props.data.storyboardProductReferences || []).map((reference) => ({
    id: `storyboard-product-${reference.id}`,
    type: 'image',
    data: { title: reference.name, asset: reference.url },
  }))
  const characterReference = character?.url ? [{
    id: `storyboard-character-${character.id}`,
    type: 'image',
    data: {
      title: character.name,
      asset: character.url,
      ...(props.type === 'video' ? { providerAsset: character.assetUrl } : {}),
    },
  }] : []
  const outfitBoard = props.data.storyboardOutfitBoard?.url ? [{
    id: 'storyboard-outfit-board',
    type: 'image',
    data: { title: '服饰穿搭参考总览', asset: props.data.storyboardOutfitBoard.url },
  }] : []
  if (isStoryboardImage.value) return [...connectedReferences.value, ...outfitBoard, ...productReferences, ...characterReference]
  return [...connectedReferences.value, ...characterReference, ...productReferences]
})
const disabledReferenceIds = computed(() => new Set(props.data.disabledReferenceIds || []))
const activeReferences = computed(() => references.value.filter((node) => !disabledReferenceIds.value.has(node.id)))
const storyboardProductNode = computed(() => isStoryboardVideo.value
  ? store.incomingNodes(props.data.storyboardSourceId).find((node) => node.type === 'product')
  : null)
const storyboardProductContext = computed(() => buildStoryboardProductVideoContext(
  storyboardProductNode.value?.data.product,
  activeReferences.value,
  props.data.storyboardPlotGoal,
))
const allImageReferences = computed(() => references.value.filter((node) => node.type === 'image' && node.data.asset))
const imageReferences = computed(() => activeReferences.value.filter((node) => node.type === 'image' && node.data.asset))
const audioReferences = computed(() => activeReferences.value.filter((node) => node.type === 'audio' && node.data.asset))
const mentionReferences = computed(() => {
  if (props.type === 'video') return activeReferences.value.filter((node) => ['image', 'video', 'audio'].includes(node.type) && node.data.asset)
  return props.type === 'audio' ? audioReferences.value : imageReferences.value
})
const isReverseTask = computed(() => props.type === 'text' && ['image', 'video'].includes(props.data.reverseType))
const isProductRecognition = computed(() => props.type === 'product')
const isVisionTextTask = computed(() => isReverseTask.value || isProductRecognition.value)
const reverseReference = computed(() => activeReferences.value.find((node) => node.type === (isProductRecognition.value ? 'image' : props.data.reverseType) && node.data.asset))
const legacyProductPrompt = computed(() => isProductRecognition.value && props.data.prompt?.startsWith('识别图片中的商品并严格输出一个 JSON 对象'))
const effectivePrompt = computed(() => ['image', 'video', 'audio'].includes(props.type)
  ? getEffectivePrompt(props.data, activeReferences.value)
  : legacyProductPrompt.value ? '' : props.data.prompt?.trim() || '')
const videoGenerationPrompt = computed(() => {
  if (!isStoryboardVideo.value) return effectivePrompt.value
  const prompt = [storyboardProductContext.value, effectivePrompt.value].filter(Boolean).join('\n\n')
  if (props.data.storyboardSegmentIndex <= 1) return prompt
  return `${props.data.storyboardContinuityMode === 'extend' ? `向后延长视频${props.data.storyboardSegmentIndex - 1}，延续上一段视频的主体、场景、光影和运镜。` : '本段为独立换场，不继承上一段视频。'}\n${prompt}`
})
const promptLimit = computed(() => isVisionTextTask.value ? 3000 : props.type === 'audio' ? maxAudioPromptLength : maxGenerationPromptLength)
const promptError = computed(() => (props.type === 'video' ? videoGenerationPrompt.value : effectivePrompt.value).length > promptLimit.value ? `提示词不能超过 ${promptLimit.value} 个字符` : '')
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
  if (props.type === 'video') return getVideoReferenceError(props.data, activeReferences.value)
  if (props.type === 'audio') return getAudioReferenceError(activeReferences.value)
  if (isProductRecognition.value && !allImageReferences.value.length) return '请先上传商品参考图'
  if (isProductRecognition.value && !imageReferences.value.length) return '请至少启用一张商品参考图片'
  if (isProductRecognition.value && imageReferences.value.length > maxProductReferenceImages) return `商品创作最多支持 ${maxProductReferenceImages} 张参考图片`
  return props.type === 'image' && selectedImageModel.value.maxReferences && imageReferences.value.length > selectedImageModel.value.maxReferences
    ? `当前模型最多支持 ${selectedImageModel.value.maxReferences} 张参考图片`
    : ''
})
const panelMessage = computed(() => {
  if (storyboardLocked.value) return `等待第 ${props.data.storyboardSegmentIndex - 1} 段确认后解锁`
  if (running.value) return ''
  return notice.value || props.data.generationError || referenceError.value || promptError.value || (insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : '')
})
const settingLabel = computed(() => {
  if (props.type === 'video') return `${selectedAspectRatio.value} · ${selectedResolution.value} · ${selectedDuration.value}s`
  if (props.type === 'audio') return `${audioFormatOptions.find(({ value }) => value === selectedAudioSettings.value.format)?.label} · ${selectedAudioSettings.value.sampleRate / 1000} kHz`
  return nodeDefinitions[props.type].setting
})
const displayReferences = computed(() => {
  const counts = {}
  return references.value.map((node) => {
    counts[node.type] = (counts[node.type] || 0) + 1
    const enabled = !disabledReferenceIds.value.has(node.id)
    const toggleable = node.type === 'image' && node.data.asset
    return { key: node.id, node, number: counts[node.type], label: `${nodeDefinitions[node.type].label}${counts[node.type]}`, enabled, toggleable }
  })
})
const canSubmit = computed(() => {
  if (storyboardLocked.value || running.value || (!effectivePrompt.value && !isProductRecognition.value) || referenceError.value || promptError.value || insufficientCredits.value) return false
  if (isVisionTextTask.value) return Boolean(reverseReference.value)
  if (props.type !== 'text') return true
  return activeReferences.value.some((node) => node.type === 'text' ? node.data.content?.trim() : node.data.asset)
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

function toggleReference(reference) {
  if (!reference.toggleable) return
  const disabled = new Set(props.data.disabledReferenceIds || [])
  if (disabled.has(reference.node.id)) disabled.delete(reference.node.id)
  else disabled.add(reference.node.id)
  notice.value = ''
  updateNodeData(props.nodeId, { disabledReferenceIds: [...disabled], generationError: '' })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (isStoryboardSegment.value && props.data.status === 'ready' && !await confirm({
    title: `重新生成第 ${props.data.storyboardSegmentIndex} 段${props.type === 'video' ? '视频' : '分镜'}`,
    message: '当前结果会保留到历史记录，并锁定后续段落。',
    confirmText: '继续重做',
  })) return
  if (isStoryboardSegment.value && props.data.status === 'ready') store.invalidateStoryboardFrom(props.nodeId)
  if (isVisionTextTask.value) {
    const nodeId = props.nodeId
    let content = ''
    notice.value = ''
    updateNodeData(nodeId, { status: 'generating', ...(isReverseTask.value ? { content: '' } : {}), generationError: '' })
    try {
      const productImageReferences = isProductRecognition.value ? imageReferences.value.slice(0, maxProductReferenceImages) : []
      const primaryReference = productImageReferences[0] || reverseReference.value
      await streamReversePrompt({
        workspace_id: store.workspaceId,
        node_id: nodeId,
        model: selectedReverseModel.value.id,
        media_type: isProductRecognition.value ? 'image' : props.data.reverseType,
        media_url: primaryReference.data.asset,
        prompt: effectivePrompt.value,
        ...(productImageReferences.length > 1
          ? { media_urls: productImageReferences.slice(1).map((reference) => reference.data.asset) }
          : {}),
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
    ...(isStoryboardImage.value ? { storyboardAsset: null } : {}),
  })
  try {
    const createGeneration = { image: createImageGeneration, video: createVideoGeneration, audio: createAudioGeneration }[props.type]
    const requestBuilders = { image: buildImageRequest, video: buildVideoRequest, audio: buildAudioRequest }
    const generationRequest = requestBuilders[props.type](
      { ...props.data, prompt: props.type === 'video' ? videoGenerationPrompt.value : effectivePrompt.value },
      props.type === 'image' ? imageReferences.value : props.type === 'video' ? activeReferences.value : references.value,
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

function updateVideoPrompt(event) {
  updateNodeData(props.nodeId, { videoPrompt: event.target.value })
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
  if (key === 'continuityMode' && isStoryboardVideo.value) {
    store.setStoryboardContinuityMode(props.nodeId, value)
    settingsOpen.value = false
    return
  }
  updateNodeData(props.nodeId, { [key]: value })
  if (['duration', 'resolution', 'aspectRatio'].includes(key)) settingsOpen.value = false
  if (key === 'aspectRatio') nextTick(() => requestAnimationFrame(updateSettingsPosition))
}

function confirmStoryboardSegment() {
  const result = store.confirmStoryboardSegment(props.nodeId)
  if (result !== true) toast.warning('请先完成当前视频生成')
}

function updateAudioSetting(key, value) {
  updateNodeData(props.nodeId, { [key]: value })
  if (['format', 'sampleRate'].includes(key)) settingsOpen.value = false
}

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

function handleKeydown(event) {
  if (event.key !== 'Escape') return
  if (!settingsOpen.value && !modelOpen.value) return
  event.preventDefault()
  settingsOpen.value = false
  modelOpen.value = false
}

watch(() => props.nodeId, () => {
  notice.value = ''
  storyboardPromptView.value = 'image'
  if (legacyProductPrompt.value) updateNodeData(props.nodeId, { prompt: '' })
  if (isVisionTextTask.value && selectedReverseModel.value.id !== props.data.model) {
    updateNodeData(props.nodeId, { model: selectedReverseModel.value.id })
  }
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
      <div v-for="reference in displayReferences" :key="reference.key" class="reference-item" :class="{ 'is-disabled': !reference.enabled }" :title="`${reference.label} · ${reference.enabled ? '已启用' : '已禁用'}`" :aria-label="`${reference.label} · ${reference.enabled ? '已启用' : '已禁用'}`">
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
          :title="`${reference.enabled ? '禁用' : '启用'}${reference.label}`"
          :aria-label="`${reference.enabled ? '禁用' : '启用'}${reference.label}`"
          :aria-pressed="reference.enabled"
          @pointerdown.stop
          @click.stop="toggleReference(reference)"
        >
          <Eye v-if="reference.enabled" :size="12" />
          <EyeOff v-else :size="12" />
        </AppButton>
      </div>
    </div>

    <div v-if="isStoryboardImage" class="storyboard-prompt-tabs" role="tablist" aria-label="分镜提示词类型">
      <AppButton :class="{ active: storyboardPromptView === 'image' }" role="tab" :aria-selected="storyboardPromptView === 'image'" @click="storyboardPromptView = 'image'"><Clapperboard :size="14" />分镜图</AppButton>
      <AppButton :class="{ active: storyboardPromptView === 'video' }" role="tab" :aria-selected="storyboardPromptView === 'video'" @click="storyboardPromptView = 'video'"><VideoIcon :size="14" />视频脚本</AppButton>
      <span>{{ data.storyboardShotCount }} 镜头 · {{ data.storyboardDuration }}s</span>
    </div>

    <PromptReferenceEditor
      v-if="['image', 'video', 'audio'].includes(type) && (!isStoryboardImage || storyboardPromptView === 'image')"
      :model-value="promptParts"
      :references="mentionReferences"
      :reference-type="type"
      :reference-label="type === 'video' ? '素材' : type === 'audio' ? '音频' : '图片'"
      :placeholder="nodeDefinitions[type].placeholder"
      @update:model-value="updatePrompt"
      @pointerdown="settingsOpen = false; modelOpen = false"
    />
    <AppTextarea
      v-else-if="isStoryboardImage"
      class="storyboard-video-prompt nodrag nopan"
      :model-value="data.videoPrompt"
      :maxlength="maxGenerationPromptLength"
      placeholder="输入 Seedance 视频提示词…"
      aria-label="视频脚本"
      @input="updateVideoPrompt"
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
        <template v-if="isStoryboardVideo && data.storyboardSegmentIndex > 1">
          <h3>衔接方式</h3>
          <div class="video-duration-options">
            <AppButton :class="{ active: data.storyboardContinuityMode === 'extend' }" @click="updateVideoSetting('continuityMode', 'extend')">向后延长</AppButton>
            <AppButton :class="{ active: data.storyboardContinuityMode === 'cut' }" @click="updateVideoSetting('continuityMode', 'cut')">独立换场</AppButton>
          </div>
        </template>
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
            <span class="image-ratio-icon" :style="ratioIconStyle(ratio)"></span>
            <strong>{{ ratio }}</strong>
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
      <AppButton v-if="isStoryboardVideo && data.status === 'ready'" class="storyboard-confirm-button" variant="soft" @click="confirmStoryboardSegment">
        <Check :size="15" />{{ hasNextStoryboardSegment ? `继续第${data.storyboardSegmentIndex + 1}段` : '完成' }}
      </AppButton>
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
