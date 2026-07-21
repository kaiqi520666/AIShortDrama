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
    requireMediaForAudio: true,
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
    requireMediaForAudio: true,
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
    maxVideos: 3,
    maxAudios: 3,
    requireMediaForAudio: true,
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
    maxVideos: 1,
    maxAudios: 0,
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
    role: reference?.role,
    url: typeof reference === 'string' ? reference : reference?.url || reference?.data?.asset,
  })).filter((reference) => reference.url)
}

export function getVideoReferenceError(data, references = []) {
  const model = getVideoModel(data.model)
  const normalized = normalizeReferences(references)
  const counts = Object.fromEntries(['image', 'video', 'audio'].map((type) => [type, normalized.filter((reference) => reference.type === type).length]))
  const maxImages = model.id === 'happyhorse-1.1' && counts.video ? 5 : model.maxImages

  if (maxImages != null && counts.image > maxImages) return `当前模型最多支持 ${maxImages} 张参考图片`
  if (model.maxVideos != null && counts.video > model.maxVideos) return model.maxVideos ? `当前模型最多支持 ${model.maxVideos} 个参考视频` : '当前模型不支持参考视频'
  if (model.maxAudios != null && counts.audio > model.maxAudios) return model.maxAudios ? `当前模型最多支持 ${model.maxAudios} 个参考音频` : '当前模型不支持参考音频'
  if (model.requireMediaForAudio && counts.audio && !counts.image && !counts.video) return '参考音频不能单独使用'
  if (model.remoteOnly && normalized.some((reference) => !/^https?:\/\//i.test(reference.url))) return '当前模型的参考素材必须是公开 URL'
  return ''
}

export function buildVideoRequest(data, references = []) {
  const settings = normalizeVideoSettings(data)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error('视频提示词不能为空')

  const referenceError = getVideoReferenceError(data, references)
  if (referenceError) throw new Error(referenceError)
  const normalized = normalizeReferences(references)
  const images = normalized.filter((reference) => reference.type === 'image')
  const videos = normalized.filter((reference) => reference.type === 'video')
  const audios = normalized.filter((reference) => reference.type === 'audio')

  if (settings.model.id === 'happyhorse-1.1') {
    const action = videos.length ? 'video-edit' : images.length > 1 || images[0]?.role === 'reference_image' ? 'reference-to-video' : images.length ? 'image-to-video' : 'text-to-video'
    return {
      model: settings.model.id,
      action,
      prompt,
      duration: settings.duration,
      resolution: settings.resolution,
      ...(['text-to-video', 'reference-to-video'].includes(action) ? { aspect_ratio: settings.aspectRatio } : {}),
      ...(action === 'image-to-video' ? { image_urls: images.map(({ url }) => url) } : {}),
      ...((action === 'reference-to-video' || action === 'video-edit') && images.length ? { reference_images: images.map(({ url }) => url) } : {}),
      ...(action === 'video-edit' ? { url: videos[0].url } : {}),
    }
  }

  const singleImageMode = images.length === 1 && !videos.length && !audios.length
  return {
    model: settings.model.id,
    prompt,
    duration: settings.duration,
    aspect_ratio: settings.aspectRatio,
    resolution: settings.resolution,
    generate_audio: settings.generateAudio,
    ...(images.length ? { image_with_roles: images.map(({ url, role }) => ({ url, role: role || (singleImageMode ? 'first_frame' : 'reference_image') })) } : {}),
    ...(videos.length ? { video_with_roles: videos.map(({ url }) => ({ url, role: 'reference_video' })) } : {}),
    ...(audios.length ? { audio_with_roles: audios.map(({ url }) => ({ url, role: 'reference_audio' })) } : {}),
  }
}
