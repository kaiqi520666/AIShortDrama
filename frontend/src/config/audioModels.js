import { i18n } from '../i18n/index'

const { t } = i18n.global
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
  if (!capability) throw new Error(t('canvas.audioCapabilityMissing'))
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
  if (images.length && audios.length) return t('canvas.mixedAudioImage')
  if (images.length > capability.referenceLimits.image) return t('canvas.audioImageLimit', { p0: capability.referenceLimits.image })
  if (audios.length > capability.referenceLimits.audio) return t('canvas.audioReferenceLimit', { p0: capability.referenceLimits.audio })
  if ([...images, ...audios].some((node) => !node.data.asset)) return t('canvas.referencesNotReady')
  if (audios.some((node) => node.data.sourceDuration > capability.referenceAudioMaxSeconds)) return t('canvas.referenceAudioDuration', { p0: capability.referenceAudioMaxSeconds })
  if (audios.some((node) => node.data.sourceByteSize > capability.referenceMaxBytes)) return t('canvas.referenceAudioSize', { p0: capability.referenceMaxBytes / 1024 / 1024 })
  if (images.some((node) => node.data.sourceByteSize > capability.referenceMaxBytes)) return t('canvas.referenceImageSize', { p0: capability.referenceMaxBytes / 1024 / 1024 })
  return ''
}

export function buildAudioRequest(data, references = [], audioCapability) {
  const capability = requireCapability(audioCapability)
  const settings = normalizeAudioSettings(data, capability)
  const prompt = data.prompt?.trim()
  if (!prompt) throw new Error(t('canvas.audioPromptRequired'))
  if (prompt.length > capability.maxPromptLength) throw new Error(t('canvas.audioPromptLimit', { p0: capability.maxPromptLength }))
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
