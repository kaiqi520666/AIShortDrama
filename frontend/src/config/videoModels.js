const seedanceRatios = ['21:9', '16:9', '4:3', '1:1', '3:4', '9:16', 'adaptive']
const happyHorseRatios = ['16:9', '9:16', '1:1', '4:3', '3:4']

export const videoModels = [
  {
    id: 'seedance-2',
    label: 'Seedance 2',
    resolutions: ['480p', '720p', '1080p', '4k'],
    aspectRatios: seedanceRatios,
    defaultResolution: '720p',
    defaultAspectRatio: '16:9',
    defaultDuration: 0,
    durationMin: 4,
    durationMax: 15,
    durationAuto: true,
    generateAudio: true,
    maxImages: 9,
  },
  {
    id: 'seedance-2-fast',
    label: 'Seedance 2 Fast',
    resolutions: ['480p', '720p'],
    aspectRatios: seedanceRatios,
    defaultResolution: '720p',
    defaultAspectRatio: '16:9',
    defaultDuration: 0,
    durationMin: 4,
    durationMax: 15,
    durationAuto: true,
    generateAudio: true,
    maxImages: 9,
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
    maxImages: 9,
  },
  {
    id: 'happyhorse-1.1',
    label: 'HappyHorse 1.1',
    resolutions: ['720P', '1080P'],
    aspectRatios: happyHorseRatios,
    defaultResolution: '1080P',
    defaultAspectRatio: '16:9',
    defaultDuration: 5,
    durationMin: 3,
    durationMax: 15,
    maxImages: 9,
    remoteOnly: true,
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
    : model.durationAuto && [0, -1].includes(requestedDuration)
      ? 0
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

function normalizeReferences(references) {
  return references.map((reference) => ({
    type: reference?.type,
    url: typeof reference === 'string' ? reference : reference?.url || reference?.data?.asset,
  })).filter((reference) => reference.url)
}

export function getVideoReferenceError(data, references = []) {
  const model = getVideoModel(data.model)
  const normalized = normalizeReferences(references)
  const counts = Object.fromEntries(['image', 'video', 'audio'].map((type) => [type, normalized.filter((reference) => reference.type === type).length]))

  if (counts.image > model.maxImages) return `当前模型最多支持 ${model.maxImages} 张参考图片`
  if (counts.video || counts.audio) return '当前仅支持图片作为视频参考素材'
  if (model.remoteOnly && normalized.some((reference) => !/^https?:\/\//i.test(reference.url))) return '当前模型的参考素材必须是公开 URL'
  return ''
}

export function buildVideoRequest(data, references = []) {
  const settings = normalizeVideoSettings(data)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error('视频提示词不能为空')

  const referenceError = getVideoReferenceError(data, references)
  if (referenceError) throw new Error(referenceError)
  const referenceImages = normalizeReferences(references)
    .filter((reference) => reference.type === 'image')
    .map(({ url }) => url)
  return {
    model: settings.model.id,
    prompt,
    duration: settings.duration,
    aspect_ratio: settings.aspectRatio,
    resolution: settings.resolution,
    ...(settings.model.generateAudio ? { generate_audio: settings.generateAudio } : {}),
    reference_images: referenceImages,
  }
}
