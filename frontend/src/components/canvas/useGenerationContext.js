import { computed, ref, watch } from 'vue'
import { getAudioReferenceError } from '../../config/audioModels'
import { getEffectivePrompt } from '../../config/generationPrompt'
import { MAX_STORYBOARD_REFERENCES } from '../../config/canvas/productStoryboard'
import { maxProductReferenceImages } from '../../config/canvas/connectionRules'
import { nodeDefinitions } from '../../config/canvas/nodeDefinitions'
import { getVideoModelError, getVideoReferenceError } from '../../config/videoModels'
import { getGenerationAdapter } from '../../services/generationAdapters'
import { getApiErrorMessage } from '../../utils/apiError'

const supportedGenerationTypes = new Set(['text', 'image', 'video', 'audio'])

export function useGenerationContext({
  props,
  store,
  authStore,
  capabilityStore,
  updateNodeData,
  confirm,
  toast,
  runTextTask,
  failure,
}) {
  const notice = ref('')
  const running = computed(() => props.data.status === 'generating')
  const isStoryboardImage = computed(() => (
    props.type === 'image' && Boolean(props.data.storyboardSourceId && props.data.videoPrompt)
  ))
  const isStoryboardSegment = computed(() => Boolean(
    props.data.storyboardSegmentIndex && props.data.storyboardSourceId,
  ))
  const isStoryboardVideo = computed(() => props.type === 'video' && isStoryboardSegment.value)
  const storyboardLocked = computed(() => isStoryboardSegment.value && props.data.segmentLocked)
  const hasNextStoryboardSegment = computed(() => (
    isStoryboardVideo.value
    && props.data.storyboardSegmentIndex < props.data.storyboardSegmentCount
  ))
  const connectedReferences = computed(() => store.incomingNodes(props.nodeId).map((node) => (
    props.type === 'video' && node.type === 'image'
      ? {
          ...node,
          data: {
            ...node.data,
            providerAsset: node.data.storyboardAsset?.status === 'active'
              ? node.data.storyboardAsset.asset_url
              : node.data.providerAsset || null,
          },
        }
      : node
  )))
  const references = computed(() => {
    const characters = (props.data.storyboardCharacterReferences || []).map((character, index) => ({
      id: `storyboard-character-${character.id}`,
      type: 'image',
      data: {
        title: `角色${index + 1} · ${character.name}`,
        asset: character.url,
        ...(props.type === 'video' ? { providerAsset: character.assetUrl } : {}),
      },
    }))
    const productReferences = (props.data.storyboardProductReferences || []).map((reference) => ({
      id: `storyboard-product-${reference.id}`,
      type: 'image',
      data: { title: reference.name, asset: reference.url },
    }))
    const legacyOutfitReference = (props.data.storyboardOutfitReference || props.data.storyboardOutfitBoard)?.url ? [{
      id: 'storyboard-outfit-reference',
      type: 'image',
      data: { title: '试穿定妆图', asset: (props.data.storyboardOutfitReference || props.data.storyboardOutfitBoard).url },
    }] : []
    const outfitReferences = props.type === 'image' && props.data.outfitSourceId
      ? [props.data.outfitModelReference, props.data.outfitSceneReference]
        .filter((reference) => reference?.url)
        .map((reference, index) => ({
          id: `outfit-reference-${index}-${reference.id || reference.url}`,
          type: 'image',
          data: { title: index ? '场景参考图' : '模特参考图', asset: reference.url },
        }))
      : []
    return isStoryboardImage.value
      ? [...legacyOutfitReference, ...connectedReferences.value, ...characters, ...productReferences]
      : [...connectedReferences.value, ...outfitReferences, ...characters, ...productReferences]
  })
  const disabledReferenceIds = computed(() => new Set(props.data.disabledReferenceIds || []))
  const activeReferences = computed(() => references.value.filter(
    (node) => !disabledReferenceIds.value.has(node.id),
  ))
  const allImageReferences = computed(() => references.value.filter(
    (node) => node.type === 'image' && node.data.asset,
  ))
  const imageReferences = computed(() => activeReferences.value.filter(
    (node) => node.type === 'image' && node.data.asset,
  ))
  const audioReferences = computed(() => activeReferences.value.filter(
    (node) => node.type === 'audio' && node.data.asset,
  ))
  const mentionReferences = computed(() => {
    if (props.type === 'video') {
      return activeReferences.value.filter((node) => (
        ['image', 'video', 'audio'].includes(node.type) && node.data.asset
      ))
    }
    return props.type === 'audio' ? audioReferences.value : imageReferences.value
  })
  const isReverseTask = computed(() => props.type === 'text' && props.data.reverseType === 'image')
  const isProductRecognition = computed(() => props.type === 'product')
  const isVisionTextTask = computed(() => isReverseTask.value || isProductRecognition.value)
  const reverseReference = computed(() => activeReferences.value.find((node) => (
    node.type === (isProductRecognition.value ? 'image' : props.data.reverseType) && node.data.asset
  )))
  const legacyProductPrompt = computed(() => (
    isProductRecognition.value
    && props.data.prompt?.startsWith('识别图片中的商品并严格输出一个 JSON 对象')
  ))
  const effectivePrompt = computed(() => (
    ['image', 'video', 'audio'].includes(props.type)
      ? getEffectivePrompt(props.data, activeReferences.value)
      : legacyProductPrompt.value ? '' : props.data.prompt?.trim() || ''
  ))
  const videoGenerationPrompt = computed(() => effectivePrompt.value)
  const imageModels = computed(() => capabilityStore.imageModels)
  const videoModels = computed(() => capabilityStore.videoModels)
  const reverseModels = computed(() => capabilityStore.textModels)
  const defaultImageModel = computed(() => capabilityStore.defaultImageModel)
  const defaultVideoModel = computed(() => capabilityStore.defaultVideoModel)
  const defaultReverseModel = computed(() => capabilityStore.defaultTextModel)
  const audioCapability = computed(() => capabilityStore.audioCapability)
  const audioModel = computed(() => audioCapability.value.model)
  const audioFormatOptions = computed(() => audioCapability.value.formatOptions)
  const audioSampleRateOptions = computed(() => audioCapability.value.sampleRateOptions)
  const selectedImageSettings = computed(() => getGenerationAdapter('image').normalize({
    data: props.data,
    imageModels: imageModels.value,
    defaultImageModel: defaultImageModel.value,
  }))
  const selectedImageModel = computed(() => selectedImageSettings.value.model)
  const selectedVideoSettings = computed(() => getGenerationAdapter('video').normalize({
    data: props.data,
    videoModels: videoModels.value,
    defaultVideoModel: defaultVideoModel.value,
  }))
  const selectedVideoModel = computed(() => selectedVideoSettings.value.model)
  const selectedAudioSettings = computed(() => getGenerationAdapter('audio').normalize({
    data: props.data,
    audioCapability: audioCapability.value,
  }))
  const selectedReverseModel = computed(() => getGenerationAdapter('text').normalize({
    data: props.data,
    textModels: reverseModels.value,
    defaultTextModel: defaultReverseModel.value,
  }))
  const selectableModels = computed(() => (
    props.type === 'video' ? videoModels.value : reverseModels.value
  ))
  const selectedModel = computed(() => (
    props.type === 'video' ? selectedVideoModel.value : selectedReverseModel.value
  ))
  const promptLimit = computed(() => {
    if (props.type === 'image') return selectedImageModel.value.maxPromptLength
    if (props.type === 'video') return selectedVideoModel.value.maxPromptLength
    if (props.type === 'audio') return audioCapability.value.maxPromptLength
    return selectedReverseModel.value.maxPromptLength
  })
  const promptError = computed(() => {
    const prompt = props.type === 'video' ? videoGenerationPrompt.value : effectivePrompt.value
    return prompt.length > promptLimit.value ? `提示词不能超过 ${promptLimit.value} 个字符` : ''
  })
  const promptParts = computed(() => (
    props.data.promptParts ?? (props.data.prompt ? [{ type: 'text', value: props.data.prompt }] : [])
  ))
  const selectedResolution = computed(() => (
    props.type === 'image' ? selectedImageSettings.value.resolution : selectedVideoSettings.value.resolution
  ))
  const selectedAspectRatio = computed(() => (
    props.type === 'image' ? selectedImageSettings.value.aspectRatio : selectedVideoSettings.value.aspectRatio
  ))
  const selectedDuration = computed(() => selectedVideoSettings.value.duration)
  const estimatedCredits = computed(() => {
    if (isVisionTextTask.value) return authStore.estimateCredits('text', selectedReverseModel.value.id)
    if (!['image', 'video', 'audio'].includes(props.type)) return null
    const model = props.type === 'image'
      ? selectedImageModel.value.id
      : props.type === 'video' ? selectedVideoModel.value.id : audioModel.value.id
    return authStore.estimateCredits(props.type, model, {
      resolution: selectedResolution.value,
      duration: selectedDuration.value,
    })
  })
  const insufficientCredits = computed(() => (
    estimatedCredits.value !== null
    && (authStore.user?.credit_balance || 0) < estimatedCredits.value
  ))
  const creditLabel = computed(() => `${props.type === 'audio' ? '冻结' : '本次'} ${estimatedCredits.value} 积分`)
  const referenceError = computed(() => {
    if (props.type === 'video') {
      return getVideoReferenceError(
        props.data,
        activeReferences.value,
        videoModels.value,
        defaultVideoModel.value,
      )
    }
    if (props.type === 'audio') return getAudioReferenceError(activeReferences.value, audioCapability.value)
    if (isProductRecognition.value && !allImageReferences.value.length) return '请先上传商品参考图'
    if (isProductRecognition.value && !imageReferences.value.length) return '请至少启用一张商品参考图片'
    if (isProductRecognition.value && imageReferences.value.length > maxProductReferenceImages) {
      return `商品创作最多支持 ${maxProductReferenceImages} 张参考图片`
    }
    if (isStoryboardImage.value && imageReferences.value.length > MAX_STORYBOARD_REFERENCES) {
      return `商品分镜生图最多支持 ${MAX_STORYBOARD_REFERENCES} 张参考图片`
    }
    return props.type === 'image'
      && selectedImageModel.value.maxReferences
      && imageReferences.value.length > selectedImageModel.value.maxReferences
      ? `当前模型最多支持 ${selectedImageModel.value.maxReferences} 张参考图片`
      : ''
  })
  const panelMessage = computed(() => {
    if (storyboardLocked.value) return `等待第 ${props.data.storyboardSegmentIndex - 1} 段确认后解锁`
    if (running.value) return ''
    return notice.value
      || failure.value
      || props.data.generationError
      || referenceError.value
      || promptError.value
      || (insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : '')
  })
  const settingLabel = computed(() => {
    if (props.type === 'video') {
      return `${selectedAspectRatio.value} · ${selectedResolution.value} · ${selectedDuration.value}s`
    }
    if (props.type === 'audio') {
      const format = audioFormatOptions.value.find(({ value }) => value === selectedAudioSettings.value.format)
      return `${format?.label} · ${selectedAudioSettings.value.sampleRate / 1000} kHz`
    }
    return nodeDefinitions[props.type].setting
  })
  const displayReferences = computed(() => {
    const counts = {}
    return references.value.map((node) => {
      counts[node.type] = (counts[node.type] || 0) + 1
      const enabled = !disabledReferenceIds.value.has(node.id)
      const toggleable = node.type === 'image' && node.data.asset
      return {
        key: node.id,
        node,
        number: counts[node.type],
        label: `${nodeDefinitions[node.type].label}${counts[node.type]}`,
        enabled,
        toggleable,
      }
    })
  })
  const canSubmit = computed(() => {
    if (
      storyboardLocked.value
      || running.value
      || (!effectivePrompt.value && !isProductRecognition.value)
      || referenceError.value
      || promptError.value
      || insufficientCredits.value
    ) return false
    if (isVisionTextTask.value) return Boolean(reverseReference.value)
    if (props.type !== 'text') return true
    return activeReferences.value.some((node) => (
      node.type === 'text' ? node.data.content?.trim() : node.data.asset
    ))
  })

  function updatePrompt(parts) {
    notice.value = ''
    updateNodeData(props.nodeId, {
      promptParts: parts,
      prompt: parts.map((part) => {
        if (['image', 'video', 'audio'].includes(part.type)) {
          const number = mentionReferences.value
            .filter((node) => node.type === part.type)
            .findIndex((node) => node.id === part.nodeId) + 1
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
    updateNodeData(props.nodeId, {
      disabledReferenceIds: [...disabled],
      generationError: '',
    })
  }

  function createGenerationContext() {
    return {
      nodeId: props.nodeId,
      workspaceId: store.workspaceId,
      data: props.data,
      prompt: props.type === 'video' ? videoGenerationPrompt.value : effectivePrompt.value,
      validationError: referenceError.value || promptError.value,
      references: references.value,
      activeReferences: activeReferences.value,
      imageReferences: imageReferences.value,
      primaryReference: reverseReference.value,
      imageModels: imageModels.value,
      defaultImageModel: defaultImageModel.value,
      videoModels: videoModels.value,
      defaultVideoModel: defaultVideoModel.value,
      audioCapability: audioCapability.value,
      textModel: selectedReverseModel.value,
      mediaType: isProductRecognition.value ? 'image' : props.data.reverseType,
      operation: isProductRecognition.value ? 'productRecognition' : 'reversePrompt',
      runTextTask,
    }
  }

  async function submitTask() {
    if (!canSubmit.value) return
    if (isStoryboardSegment.value && props.data.status === 'ready' && !await confirm({
      title: `重新生成第 ${props.data.storyboardSegmentIndex} 段${props.type === 'video' ? '视频' : '分镜'}`,
      message: '当前结果会保留到历史记录，并锁定后续段落。',
      confirmText: '继续重做',
    })) return
    if (isStoryboardSegment.value && props.data.status === 'ready') {
      store.invalidateStoryboardFrom(props.nodeId)
    }
    const generationType = isVisionTextTask.value ? 'text' : props.type
    if (!supportedGenerationTypes.has(generationType) || (generationType === 'text' && !isVisionTextTask.value)) return
    const adapter = getGenerationAdapter(generationType)
    const context = createGenerationContext()
    const validationError = adapter.validate(context)
    if (validationError) {
      notice.value = validationError
      return
    }
    if (isVisionTextTask.value) {
      notice.value = ''
      if (isReverseTask.value) updateNodeData(props.nodeId, { content: '' })
      await adapter.submit(adapter.buildRequest(context), context)
      return
    }
    const nodeId = props.nodeId
    notice.value = ''
    updateNodeData(nodeId, {
      status: 'generating',
      generationProgress: 0,
      generationError: '',
      ...(props.type === 'image' ? { storyboardAsset: null } : {}),
    })
    try {
      const result = await adapter.submit(adapter.buildRequest(context), context)
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
        generationError: getApiErrorMessage(error, '任务提交失败'),
      })
    }
  }

  function updateVideoPrompt(event) {
    updateNodeData(props.nodeId, { videoPrompt: event.target.value })
  }

  function videoModelError(data, modelReferences) {
    return getVideoModelError(data, modelReferences, videoModels.value, defaultVideoModel.value)
  }

  function updateVideoModel(model) {
    const error = videoModelError({ ...props.data, model: model.id }, references.value)
    if (error) return false
    const updates = { model: model.id }
    if (!model.resolutions.includes(selectedResolution.value)) updates.resolution = model.defaultResolution
    if (!model.aspectRatios.includes(selectedAspectRatio.value)) updates.aspectRatio = model.defaultAspectRatio
    if (model.durationOptions && !model.durationOptions.includes(selectedDuration.value)) {
      updates.duration = model.defaultDuration
    } else if (!model.durationOptions && (
      selectedDuration.value < model.durationMin || selectedDuration.value > model.durationMax
    )) {
      updates.duration = model.defaultDuration
    }
    updateNodeData(props.nodeId, updates)
    return true
  }

  function updateModel(model) {
    if (props.type === 'video') return updateVideoModel(model)
    updateNodeData(props.nodeId, { model: model.id })
    return true
  }

  function updateVideoSetting(key, value) {
    if (key === 'continuityMode' && isStoryboardVideo.value) {
      store.setStoryboardContinuityMode(props.nodeId, value)
      return 'close'
    }
    updateNodeData(props.nodeId, { [key]: value })
    return ['resolution', 'aspectRatio'].includes(key) ? 'close' : ''
  }

  function updateAudioSetting(key, value) {
    updateNodeData(props.nodeId, { [key]: value })
    return ['format', 'sampleRate'].includes(key) ? 'close' : ''
  }

  function confirmStoryboardSegment() {
    const result = store.confirmStoryboardSegment(props.nodeId)
    if (result !== true) toast.warning('请先完成当前视频生成')
  }

  watch(() => props.nodeId, () => {
    notice.value = ''
    if (legacyProductPrompt.value) updateNodeData(props.nodeId, { prompt: '' })
    if (isVisionTextTask.value && selectedReverseModel.value.id !== props.data.model) {
      updateNodeData(props.nodeId, { model: selectedReverseModel.value.id })
    }
  }, { immediate: true })

  return {
    notice,
    running,
    isStoryboardImage,
    isStoryboardSegment,
    isStoryboardVideo,
    storyboardLocked,
    hasNextStoryboardSegment,
    references,
    activeReferences,
    imageReferences,
    mentionReferences,
    isReverseTask,
    isVisionTextTask,
    effectivePrompt,
    videoGenerationPrompt,
    audioModel,
    audioFormatOptions,
    audioSampleRateOptions,
    promptError,
    promptParts,
    selectedImageModel,
    selectedVideoSettings,
    selectedVideoModel,
    selectedAudioSettings,
    selectedReverseModel,
    selectableModels,
    selectedModel,
    promptLimit,
    selectedResolution,
    selectedAspectRatio,
    selectedDuration,
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
    updateModel,
    updateVideoSetting,
    updateAudioSetting,
    confirmStoryboardSegment,
  }
}
