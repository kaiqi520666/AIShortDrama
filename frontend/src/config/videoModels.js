export const videoAspectRatios = ['21:9', '16:9', '4:3', '1:1', '3:4', '9:16']
const seedanceRatios = videoAspectRatios

export const videoModels = [
  {
    id: 'seedance-2',
    label: 'Seedance 2',
    resolutions: ['480p', '720p', '1080p', '4k'],
    aspectRatios: seedanceRatios,
    defaultResolution: '720p',
    defaultAspectRatio: '16:9',
    defaultDuration: 5,
    durationMin: 4,
    durationMax: 15,
    generateAudio: true,
    requiresPrivateAsset: true,
    referenceLimits: { image: 9, video: 3, audio: 3 },
  },
  {
    id: 'seedance-2-fast',
    label: 'Seedance 2 Fast',
    resolutions: ['480p', '720p'],
    aspectRatios: seedanceRatios,
    defaultResolution: '720p',
    defaultAspectRatio: '16:9',
    defaultDuration: 5,
    durationMin: 4,
    durationMax: 15,
    generateAudio: true,
    requiresPrivateAsset: true,
    referenceLimits: { image: 9, video: 3, audio: 3 },
  },
  {
    id: 'seedance-2-mini',
    label: 'Seedance 2 Mini',
    resolutions: ['480p', '720p'],
    aspectRatios: seedanceRatios,
    defaultResolution: '720p',
    defaultAspectRatio: '16:9',
    defaultDuration: 10,
    durationOptions: [4, 8, 10, 12, 15],
    generateAudio: true,
    requiresPrivateAsset: true,
    referenceLimits: { image: 9, video: 3, audio: 3 },
  },
]

export const defaultVideoModel = videoModels[0]

export function getVideoModel(modelId) {
  return videoModels.find((model) => model.id === modelId) || defaultVideoModel
}

export function normalizeVideoSettings(data = {}) {
  const model = getVideoModel(data.model)
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
    storyboardCharacter: typeof reference === 'string' ? null : reference?.data?.storyboardCharacter,
    storyboard: typeof reference === 'string' ? false : Boolean(reference?.data?.storyboardSourceId),
  }))
}

const referenceLabels = { image: '图片', video: '视频', audio: '音频' }
const referenceUnits = { image: '张', video: '条', audio: '条' }

export function getVideoModelError(data, references = []) {
  const model = getVideoModel(data.model)
  const normalized = normalizeReferences(references)
  const counts = Object.fromEntries(['image', 'video', 'audio'].map((type) => [type, normalized.filter((reference) => reference.type === type).length]))

  for (const type of ['image', 'video', 'audio']) {
    const limit = model.referenceLimits[type]
    if (counts[type] > limit) return limit ? `${model.label} 最多支持 ${limit} ${referenceUnits[type]}参考${referenceLabels[type]}` : `${model.label} 不支持参考${referenceLabels[type]}`
  }
  return ''
}

export function getVideoReferenceError(data, references = []) {
  const model = getVideoModel(data.model)
  const normalized = normalizeReferences(references, model.requiresPrivateAsset)
  const modelError = getVideoModelError(data, references)
  if (modelError) return modelError
  if (model.requiresPrivateAsset && normalized.some((reference) => reference.storyboard && reference.storyboardCharacter?.assetUrl && !reference.providerAsset)) {
    return '请先在分镜图工具栏注册虚拟人像素材'
  }
  const types = normalized.map((reference) => reference.type)
  if (types.includes('audio') && !types.some((type) => ['image', 'video'].includes(type))) return '参考音频需同时连接图片或视频'
  if (normalized.some((reference) => reference.type in referenceLabels && !reference.url)) return '请先上传已连接的参考素材'
  return ''
}

export function buildVideoRequest(data, references = []) {
  const settings = normalizeVideoSettings(data)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error('视频提示词不能为空')

  const referenceError = getVideoReferenceError(data, references)
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
    reference_images: referenceUrls('image'),
    reference_videos: referenceUrls('video'),
    reference_audios: referenceUrls('audio'),
  }
}
