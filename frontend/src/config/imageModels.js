const seedreamRatios = ['1:1', '4:3', '3:4', '16:9', '9:16', '3:2', '2:3', '21:9', '9:21']
const geminiProRatios = ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9']
const geminiFlashRatios = ['1:1', '3:2', '2:3', '4:3', '3:4', '16:9', '9:16', '5:4', '4:5', '21:9', '1:4', '4:1', '1:8', '8:1']
const gptImageRatios = ['1:1', '3:2', '2:3', '4:3', '3:4', '5:4', '4:5', '16:9', '9:16', '2:1', '1:2', '21:9', '9:21']

export const imageModels = [
  {
    id: 'gpt-image-2',
    label: 'GPT Image 2',
    resolutions: ['1K', '2K', '4K'],
    aspectRatios: gptImageRatios,
    defaultResolution: '1K',
    defaultAspectRatio: '1:1',
    referenceField: 'reference_images',
    resolutionField: 'resolution',
    responseFormat: true,
  },
  {
    id: 'doubao-seedream-5-0-pro',
    label: 'Seedream 5.0 Pro',
    resolutions: ['1K', '2K'],
    aspectRatios: seedreamRatios,
    defaultResolution: '2K',
    defaultAspectRatio: '16:9',
    maxReferences: 10,
    referenceField: 'image_urls',
  },
  {
    id: 'doubao-seedream-5-0',
    label: 'Seedream 5.0',
    resolutions: ['2K', '3K'],
    aspectRatios: seedreamRatios,
    defaultResolution: '2K',
    defaultAspectRatio: '16:9',
    maxReferences: 10,
    referenceField: 'image_urls',
  },
  {
    id: 'gemini-3-pro-image-preview',
    label: 'Gemini 3 Pro',
    resolutions: ['1K', '2K', '4K'],
    aspectRatios: geminiProRatios,
    defaultResolution: '1K',
    defaultAspectRatio: '16:9',
    maxReferences: 14,
    referenceField: 'image_urls',
    referenceObjects: true,
    orientation: true,
  },
  {
    id: 'gemini-3.1-flash-image-preview',
    label: 'Gemini 3.1 Flash',
    resolutions: ['0.5K', '1K', '2K', '4K'],
    aspectRatios: geminiFlashRatios,
    defaultResolution: '1K',
    defaultAspectRatio: '16:9',
    maxReferences: 14,
    referenceField: 'image_urls',
    referenceObjects: true,
    search: true,
  },
]

export const defaultImageModel = imageModels[0]

export function getImageModel(modelId) {
  return imageModels.find((model) => model.id === modelId) || defaultImageModel
}

export function normalizeImageSettings(data = {}) {
  const model = getImageModel(data.model)
  return {
    model,
    resolution: model.resolutions.includes(data.resolution) ? data.resolution : model.defaultResolution,
    aspectRatio: model.aspectRatios.includes(data.aspectRatio) ? data.aspectRatio : model.defaultAspectRatio,
    googleSearch: Boolean(model.search && data.googleSearch),
    googleImageSearch: Boolean(model.search && data.googleSearch && data.googleImageSearch),
  }
}

export function buildImageRequest(data, references = []) {
  const settings = normalizeImageSettings(data)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error('图片提示词不能为空')

  const urls = references.map((reference) => typeof reference === 'string' ? reference : reference?.data?.asset).filter(Boolean)
  if (settings.model.maxReferences && urls.length > settings.model.maxReferences) throw new Error(`参考图片不能超过 ${settings.model.maxReferences} 张`)
  if (urls.some((url) => !/^https?:\/\//i.test(url))) throw new Error('参考图片必须是公开可访问的 URL')

  const metadata = settings.model.resolutionField ? {} : { resolution: settings.resolution }
  if (settings.model.orientation) {
    const [width, height] = settings.aspectRatio.split(':').map(Number)
    if (width !== height) metadata.orientation = width > height ? 'landscape' : 'portrait'
  }
  if (settings.googleSearch) metadata.google_search = true
  if (settings.googleImageSearch) metadata.google_image_search = true

  const payload = {
    model: settings.model.id,
    prompt,
    size: settings.aspectRatio,
    n: 1,
    ...(settings.model.resolutionField ? { [settings.model.resolutionField]: settings.resolution.toLowerCase() } : {}),
    ...(settings.model.responseFormat ? { response_format: 'url' } : {}),
    ...(urls.length ? { [settings.model.referenceField]: settings.model.referenceObjects ? urls.map((url) => ({ url })) : urls } : {}),
  }
  if (Object.keys(metadata).length) payload.metadata = metadata
  return payload
}
