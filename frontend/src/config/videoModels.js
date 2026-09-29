import { i18n } from '../i18n/index'

const { t } = i18n.global
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
  if (!model) throw new Error(t('canvas.videoCapabilityMissing'))
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

const referenceLabels = { image: 'canvas.image', video: 'canvas.video', audio: 'canvas.audio' }
const referenceLimitKeys = { image: 'canvas.videoImageReferenceLimit', video: 'canvas.videoVideoReferenceLimit', audio: 'canvas.videoAudioReferenceLimit' }

export function getVideoModelError(data, references = [], models, defaultModel) {
  const model = getVideoModel(models, defaultModel, data.model)
  const normalized = normalizeReferences(references)
  const counts = Object.fromEntries(['image', 'video', 'audio'].map((type) => [type, normalized.filter((reference) => reference.type === type).length]))

  for (const type of ['image', 'video', 'audio']) {
    const limit = model.referenceLimits[type]
    if (counts[type] > limit) return limit ? t(referenceLimitKeys[type], { model: model.label, count: limit }) : t('canvas.videoReferenceUnsupported', { p0: model.label, p1: t(referenceLabels[type]) })
  }
  return ''
}

export function getVideoReferenceError(data, references = [], models, defaultModel) {
  const model = getVideoModel(models, defaultModel, data.model)
  const normalized = normalizeReferences(references, model.requiresPrivateAsset)
  const modelError = getVideoModelError(data, references, models, defaultModel)
  if (modelError) return modelError
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.privateAssetStatus === 'processing')) {
    return t('canvas.refreshCharacterReview')
  }
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.privateAssetStatus === 'failed')) {
    return t('canvas.retryCharacterRegistration')
  }
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.requiresPrivateRegistration && !reference.providerAsset)) {
    return t('canvas.registerOutfitFirst')
  }
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.type === 'image' && reference.storyboard && (reference.storyboardCharacterReferences?.some((character) => character.assetUrl) || reference.storyboardRequiresRegistration || reference.storyboardOutfitBoard) && !reference.providerAsset)) {
    return t('canvas.registerImageFirst')
  }
  const types = normalized.map((reference) => reference.type)
  if (types.includes('audio') && !types.some((type) => ['image', 'video'].includes(type))) return t('canvas.audioNeedsVisual')
  if (normalized.some((reference) => reference.type in referenceLabels && !reference.url)) return t('canvas.uploadConnectedReferences')
  return ''
}

export function buildVideoRequest(data, references = [], models, defaultModel) {
  const settings = normalizeVideoSettings(data, models, defaultModel)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error(t('canvas.videoPromptRequired'))
  if (prompt.length > settings.model.maxPromptLength) throw new Error(t('canvas.videoPromptLimit', { p0: settings.model.maxPromptLength }))

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
