const mediaTypes = ['text', 'image', 'video', 'audio']

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function isPositiveInteger(value) {
  return Number.isInteger(value) && value > 0
}

function isNonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0
}

function hasStringOptions(value) {
  return Array.isArray(value) && value.length > 0 && value.every(isNonEmptyString)
}

function hasPositiveIntegerOptions(value) {
  return Array.isArray(value) && value.length > 0 && value.every(isPositiveInteger)
}

function validateBaseSection(type, section) {
  if (!isRecord(section) || !isNonEmptyString(section.default_model) || !Array.isArray(section.models) || !section.models.length) {
    return `模型能力缺少 ${type} 配置`
  }
  if (!section.models.some((model) => model?.id === section.default_model)) return `${type} 默认模型不存在`
  return ''
}

function validateCommonModel(type, model) {
  return isRecord(model)
    && isNonEmptyString(model.id)
    && isNonEmptyString(model.label)
    && isPositiveInteger(model.prompt_max_length)
    ? ''
    : `${type} 模型字段不完整`
}

function validateImageModel(model) {
  if (!hasStringOptions(model.resolutions) || !hasStringOptions(model.aspect_ratios)) return '图片模型规格不完整'
  if (!model.resolutions.includes(model.default_resolution) || !model.aspect_ratios.includes(model.default_aspect_ratio)) return '图片默认规格无效'
  if (!isRecord(model.reference_limits) || !isNonNegativeInteger(model.reference_limits.image)) return '图片引用限制无效'
  return isRecord(model.search) && typeof model.search.google === 'boolean' && typeof model.search.google_image === 'boolean'
    ? ''
    : '图片搜索能力无效'
}

function validateVideoModel(model) {
  if (!hasStringOptions(model.resolutions) || !hasStringOptions(model.aspect_ratios)) return '视频模型规格不完整'
  if (!model.resolutions.includes(model.default_resolution) || !model.aspect_ratios.includes(model.default_aspect_ratio)) return '视频默认规格无效'
  if (!isRecord(model.reference_limits) || !['image', 'video', 'audio'].every((key) => isNonNegativeInteger(model.reference_limits[key]))) {
    return '视频引用限制无效'
  }
  if (![model.generate_audio, model.requires_private_asset, model.return_last_frame].every((value) => typeof value === 'boolean')) {
    return '视频能力字段无效'
  }
  if (!isPositiveInteger(model.default_duration) || !isRecord(model.duration)) return '视频时长配置无效'
  if (model.duration.options !== undefined) {
    return hasPositiveIntegerOptions(model.duration.options) && model.duration.options.includes(model.default_duration)
      ? ''
      : '视频时长选项无效'
  }
  return isPositiveInteger(model.duration.min)
    && isPositiveInteger(model.duration.max)
    && model.duration.min <= model.duration.max
    && model.default_duration >= model.duration.min
    && model.default_duration <= model.duration.max
    ? ''
    : '视频时长范围无效'
}

function validateAudioModel(model) {
  if (!hasStringOptions(model.formats) || !hasPositiveIntegerOptions(model.sample_rates) || !isRecord(model.defaults)) return '音频模型规格不完整'
  if (!model.formats.includes(model.defaults.format) || !model.sample_rates.includes(model.defaults.sample_rate)) return '音频默认规格无效'
  if (!isRecord(model.reference_limits) || !['image', 'audio'].every((key) => isNonNegativeInteger(model.reference_limits[key]))) {
    return '音频引用限制无效'
  }
  if (!isPositiveInteger(model.reference_audio_max_seconds) || !isPositiveInteger(model.reference_max_bytes)) return '音频引用边界无效'
  for (const key of ['speech_rate', 'loudness_rate', 'pitch_rate']) {
    const parameter = model.parameters?.[key]
    if (!isRecord(parameter) || !Number.isFinite(parameter.min) || !Number.isFinite(parameter.max) || !Number.isFinite(parameter.default) || parameter.min > parameter.max || parameter.default < parameter.min || parameter.default > parameter.max) {
      return '音频参数范围无效'
    }
  }
  return ''
}

export function validateModelCapabilities(payload) {
  if (!isRecord(payload)) return '模型能力响应格式错误'
  if (payload.version !== 1) return '模型能力版本不兼容'
  for (const type of mediaTypes) {
    const section = payload[type]
    const sectionError = validateBaseSection(type, section)
    if (sectionError) return sectionError
    for (const model of section.models) {
      const modelError = validateCommonModel(type, model)
      if (modelError) return modelError
      const typeError = type === 'image'
        ? validateImageModel(model)
        : type === 'video'
          ? validateVideoModel(model)
          : type === 'audio'
            ? validateAudioModel(model)
            : ''
      if (typeError) return typeError
    }
  }
  return ''
}
