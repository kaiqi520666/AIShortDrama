import { i18n } from '../i18n/index'

const { t } = i18n.global
export function normalizeImageModels(section) {
  return (section?.models || []).map((model) => ({
    id: model.id,
    label: model.label,
    resolutions: model.resolutions,
    aspectRatios: model.aspect_ratios.filter((ratio) => ratio !== 'adaptive'),
    defaultResolution: model.default_resolution,
    defaultAspectRatio: model.default_aspect_ratio,
    maxPromptLength: model.prompt_max_length,
    maxReferences: model.reference_limits.image,
    search: model.search.google,
    imageSearch: model.search.google_image,
  }))
}

export function getImageModel(models, defaultModel, modelId) {
  const model = models.find((item) => item.id === modelId) || defaultModel
  if (!model) throw new Error(t('canvas.imageCapabilityMissing'))
  return model
}

export function normalizeImageSettings(data = {}, models, defaultModel) {
  const model = getImageModel(models, defaultModel, data.model)
  return {
    model,
    resolution: model.resolutions.includes(data.resolution) ? data.resolution : model.defaultResolution,
    aspectRatio: model.aspectRatios.includes(data.aspectRatio) ? data.aspectRatio : model.defaultAspectRatio,
    googleSearch: Boolean(model.search && data.googleSearch),
    googleImageSearch: Boolean(model.imageSearch && data.googleSearch && data.googleImageSearch),
  }
}

export function buildImageRequest(data, references = [], models, defaultModel) {
  const settings = normalizeImageSettings(data, models, defaultModel)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error(t('canvas.imagePromptRequired'))
  if (prompt.length > settings.model.maxPromptLength) throw new Error(t('canvas.imagePromptLimit', { p0: settings.model.maxPromptLength }))

  const urls = references.map((reference) => typeof reference === 'string' ? reference : reference?.data?.asset).filter(Boolean)
  if (urls.length > settings.model.maxReferences) throw new Error(t('canvas.imageReferenceLimit', { p0: settings.model.maxReferences }))
  if (urls.some((url) => !/^https?:\/\//i.test(url))) throw new Error(t('canvas.publicReferenceRequired'))

  return {
    model: settings.model.id,
    prompt,
    size: settings.aspectRatio,
    n: 1,
    resolution: settings.resolution,
    ...(urls.length ? { reference_images: urls } : {}),
    ...(settings.googleSearch ? { google_search: true } : {}),
    ...(settings.googleImageSearch ? { google_image_search: true } : {}),
  }
}
