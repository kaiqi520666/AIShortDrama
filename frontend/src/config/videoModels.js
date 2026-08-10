export function normalizeVideoModels(section) {
  return (section?.models || []).map((model) => ({
    id: model.id,
    label: model.label,
    resolutions: model.resolutions,
    aspectRatios: model.aspect_ratios.filter((ratio) => ratio !== 'adaptive'),
    defaultResolution: model.default_resolution,
    defaultAspectRatio: model.default_aspect_ratio,
    defaultDuration: model.default_duration,
    durationMin: model.duration.min,
    durationMax: model.duration.max,
    durationOptions: model.duration.options,
    maxPromptLength: model.prompt_max_length,
    generateAudio: model.generate_audio,
    returnLastFrame: model.return_last_frame,
    requiresPrivateAsset: model.requires_private_asset,
    referenceLimits: model.reference_limits,
  }))
}

export function getVideoModel(models, defaultModel, modelId) {
  const model = models.find((item) => item.id === modelId) || defaultModel
  if (!model) throw new Error('视频模型能力尚未加载')
  return model
}

export function normalizeVideoSettings(data = {}, models, defaultModel) {
  const model = getVideoModel(models, defaultModel, data.model)
  const requestedDuration = Number(data.duration)
  const duration = model.durationOptions
    ? model.durationOptions.includes(requestedDuration) ? requestedDuration : model.defaultDuration
    : Number.isInteger(requestedDuration) && requestedDuration >= model.durationMin && requestedDuration <= model.durationMax
      ? requestedDuration
      : model.defaultDuration

  return {
    model,
    resolution: model.resolutions.includes(data.resolution) ? data.resolution : model.defaultResolution,
    aspectRatio: model.aspectRatios.includes(data.aspectRatio) ? data.aspectRatio : model.defaultAspectRatio,
    duration,
    generateAudio: Boolean(model.generateAudio && (data.generateAudio ?? true)),
  }
}

function normalizeReferences(references, usePrivateAssets = false) {
  return references.map((reference) => ({
    type: reference?.type,
    url: typeof reference === 'string' ? reference : reference?.url || (usePrivateAssets ? reference?.data?.providerAsset : null) || reference?.data?.asset,
    providerAsset: typeof reference === 'string' ? '' : reference?.data?.providerAsset || '',
    privateAssetStatus: typeof reference === 'string' ? '' : reference?.data?.storyboardAsset?.status || '',
    storyboardCharacterReferences: typeof reference === 'string' ? [] : reference?.data?.storyboardCharacterReferences || [],
    storyboard: typeof reference === 'string' ? false : Boolean(reference?.data?.storyboardSourceId),
    storyboardRequiresRegistration: typeof reference === 'string' ? false : Boolean(reference?.data?.storyboardRequiresRegistration),
    requiresPrivateRegistration: typeof reference === 'string' ? false : Boolean(reference?.data?.requiresPrivateRegistration),
    storyboardOutfitBoard: typeof reference === 'string' ? null : reference?.data?.storyboardOutfitBoard,
  }))
}

const referenceLabels = { image: '图片', video: '视频', audio: '音频' }
const referenceUnits = { image: '张', video: '条', audio: '条' }

export function getVideoModelError(data, references = [], models, defaultModel) {
  const model = getVideoModel(models, defaultModel, data.model)
  const normalized = normalizeReferences(references)
  const counts = Object.fromEntries(['image', 'video', 'audio'].map((type) => [type, normalized.filter((reference) => reference.type === type).length]))

  for (const type of ['image', 'video', 'audio']) {
    const limit = model.referenceLimits[type]
    if (counts[type] > limit) return limit ? `${model.label} 最多支持 ${limit} ${referenceUnits[type]}参考${referenceLabels[type]}` : `${model.label} 不支持参考${referenceLabels[type]}`
  }
  return ''
}

export function getVideoReferenceError(data, references = [], models, defaultModel) {
  const model = getVideoModel(models, defaultModel, data.model)
  const normalized = normalizeReferences(references, model.requiresPrivateAsset)
  const modelError = getVideoModelError(data, references, models, defaultModel)
  if (modelError) return modelError
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.privateAssetStatus === 'processing')) {
    return '人物素材审核中，请在图片节点工具栏刷新状态'
  }
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.privateAssetStatus === 'failed')) {
    return '人物素材注册失败，请在图片节点工具栏重新注册'
  }
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.requiresPrivateRegistration && !reference.providerAsset)) {
    return '请先在定妆图节点工具栏注册 Seedance 人物素材'
  }
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.storyboard && (reference.storyboardCharacterReferences?.some((character) => character.assetUrl) || reference.storyboardRequiresRegistration || reference.storyboardOutfitBoard) && !reference.providerAsset)) {
    return '请先在图片节点工具栏注册 Seedance 人物素材'
  }
  const types = normalized.map((reference) => reference.type)
  if (types.includes('audio') && !types.some((type) => ['image', 'video'].includes(type))) return '参考音频需同时连接图片或视频'
  if (normalized.some((reference) => reference.type in referenceLabels && !reference.url)) return '请先上传已连接的参考素材'
  return ''
}

export function buildVideoRequest(data, references = [], models, defaultModel) {
  const settings = normalizeVideoSettings(data, models, defaultModel)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error('视频提示词不能为空')
  if (prompt.length > settings.model.maxPromptLength) throw new Error(`视频提示词不能超过 ${settings.model.maxPromptLength} 个字符`)

  const referenceError = getVideoReferenceError(data, references, models, defaultModel)
  if (referenceError) throw new Error(referenceError)
  const normalized = normalizeReferences(references, settings.model.requiresPrivateAsset)
  const referenceUrls = (type) => normalized.filter((reference) => reference.type === type && reference.url).map(({ url }) => url)
  return {
    model: settings.model.id,
    prompt,
    duration: settings.duration,
    aspect_ratio: settings.aspectRatio,
    resolution: settings.resolution,
    ...(settings.model.generateAudio ? { generate_audio: settings.generateAudio } : {}),
    ...(settings.model.returnLastFrame && data.returnLastFrame !== false ? { return_last_frame: true } : {}),
    reference_images: referenceUrls('image'),
    reference_videos: referenceUrls('video'),
    reference_audios: referenceUrls('audio'),
  }
}
