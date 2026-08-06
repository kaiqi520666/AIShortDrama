export function normalizeAudioCapability(section) {
  const model = section?.models?.find(({ id }) => id === section.default_model)
  if (!model) return null
  return {
    model: { id: model.id, label: model.label },
    formatOptions: model.formats.map((value) => ({
      value,
      label: value === 'ogg_opus' ? 'OGG Opus' : value.toUpperCase(),
    })),
    sampleRateOptions: model.sample_rates.map((value) => ({ value, label: `${value / 1000} kHz` })),
    defaults: {
      model: model.id,
      format: model.defaults.format,
      sampleRate: model.defaults.sample_rate,
      speechRate: model.parameters.speech_rate.default,
      loudnessRate: model.parameters.loudness_rate.default,
      pitchRate: model.parameters.pitch_rate.default,
    },
    parameters: model.parameters,
    referenceLimits: model.reference_limits,
    referenceAudioMaxSeconds: model.reference_audio_max_seconds,
    referenceMaxBytes: model.reference_max_bytes,
    maxPromptLength: model.prompt_max_length,
  }
}

function requireCapability(capability) {
  if (!capability) throw new Error('音频模型能力尚未加载')
  return capability
}

function boundedInteger(value, bounds) {
  return Number.isInteger(value) && value >= bounds.min && value <= bounds.max ? value : bounds.default
}

export function normalizeAudioSettings(data = {}, audioCapability) {
  const capability = requireCapability(audioCapability)
  return {
    model: capability.model.id,
    format: capability.formatOptions.some(({ value }) => value === data.format) ? data.format : capability.defaults.format,
    sampleRate: capability.sampleRateOptions.some(({ value }) => value === data.sampleRate) ? data.sampleRate : capability.defaults.sampleRate,
    speechRate: boundedInteger(data.speechRate, capability.parameters.speech_rate),
    loudnessRate: boundedInteger(data.loudnessRate, capability.parameters.loudness_rate),
    pitchRate: boundedInteger(data.pitchRate, capability.parameters.pitch_rate),
  }
}

export function getAudioReferenceError(references = [], audioCapability) {
  const capability = requireCapability(audioCapability)
  const images = references.filter((node) => node.type === 'image')
  const audios = references.filter((node) => node.type === 'audio')
  if (images.length && audios.length) return '参考图片和参考音频不能混用'
  if (images.length > capability.referenceLimits.image) return `最多支持 ${capability.referenceLimits.image} 张参考图片`
  if (audios.length > capability.referenceLimits.audio) return `最多支持 ${capability.referenceLimits.audio} 条参考音频`
  if ([...images, ...audios].some((node) => !node.data.asset)) return '参考资源尚未准备完成'
  if (audios.some((node) => node.data.sourceDuration > capability.referenceAudioMaxSeconds)) return `参考音频每条不能超过 ${capability.referenceAudioMaxSeconds} 秒`
  if (audios.some((node) => node.data.sourceByteSize > capability.referenceMaxBytes)) return `参考音频每条不能超过 ${capability.referenceMaxBytes / 1024 / 1024}MB`
  if (images.some((node) => node.data.sourceByteSize > capability.referenceMaxBytes)) return `参考图片不能超过 ${capability.referenceMaxBytes / 1024 / 1024}MB`
  return ''
}

export function buildAudioRequest(data, references = [], audioCapability) {
  const capability = requireCapability(audioCapability)
  const settings = normalizeAudioSettings(data, capability)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error('音频提示词不能为空')
  if (prompt.length > capability.maxPromptLength) throw new Error(`音频提示词不能超过 ${capability.maxPromptLength} 个字符`)
  return {
    model: capability.model.id,
    prompt,
    format: settings.format,
    sample_rate: settings.sampleRate,
    speech_rate: settings.speechRate,
    loudness_rate: settings.loudnessRate,
    pitch_rate: settings.pitchRate,
    reference_images: references.filter((node) => node.type === 'image' && node.data.asset).map((node) => node.data.asset),
    reference_audios: references.filter((node) => node.type === 'audio' && node.data.asset).map((node) => node.data.asset),
  }
}
