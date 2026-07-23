export const audioModel = {
  id: 'seed-audio-1.0-multilingual',
  label: 'Seed Audio 1.0',
}

export const audioFormatOptions = [
  { value: 'mp3', label: 'MP3' },
  { value: 'wav', label: 'WAV' },
  { value: 'ogg_opus', label: 'OGG Opus' },
]

export const audioSampleRateOptions = [8000, 16000, 24000, 32000, 44100, 48000]
  .map((value) => ({ value, label: `${value / 1000} kHz` }))

export const defaultAudioSettings = {
  model: audioModel.id,
  format: 'mp3',
  sampleRate: 48000,
  speechRate: 0,
  loudnessRate: 0,
  pitchRate: 0,
}

export const maxAudioPromptLength = 3000

const boundedInteger = (value, min, max) => Number.isInteger(value) && value >= min && value <= max ? value : 0

export function normalizeAudioSettings(data = {}) {
  return {
    model: audioModel.id,
    format: audioFormatOptions.some(({ value }) => value === data.format) ? data.format : defaultAudioSettings.format,
    sampleRate: audioSampleRateOptions.some(({ value }) => value === data.sampleRate) ? data.sampleRate : defaultAudioSettings.sampleRate,
    speechRate: boundedInteger(data.speechRate, -50, 100),
    loudnessRate: boundedInteger(data.loudnessRate, -50, 100),
    pitchRate: boundedInteger(data.pitchRate, -12, 12),
  }
}

export function getAudioReferenceError(references = []) {
  const images = references.filter((node) => node.type === 'image')
  const audios = references.filter((node) => node.type === 'audio')
  if (images.length && audios.length) return '参考图片和参考音频不能混用'
  if (images.length > 1) return '最多支持 1 张参考图片'
  if (audios.length > 3) return '最多支持 3 条参考音频'
  if ([...images, ...audios].some((node) => !node.data.asset)) return '参考资源尚未准备完成'
  if (audios.some((node) => node.data.sourceDuration > 30)) return '参考音频每条不能超过 30 秒'
  if (audios.some((node) => node.data.sourceByteSize > 10 * 1024 * 1024)) return '参考音频每条不能超过 10MB'
  if (images.some((node) => node.data.sourceByteSize > 10 * 1024 * 1024)) return '参考图片不能超过 10MB'
  return ''
}

export function buildAudioRequest(data, references = []) {
  const settings = normalizeAudioSettings(data)
  return {
    model: audioModel.id,
    prompt: data.prompt.trim(),
    format: settings.format,
    sample_rate: settings.sampleRate,
    speech_rate: settings.speechRate,
    loudness_rate: settings.loudnessRate,
    pitch_rate: settings.pitchRate,
    reference_images: references.filter((node) => node.type === 'image' && node.data.asset).map((node) => node.data.asset),
    reference_audios: references.filter((node) => node.type === 'audio' && node.data.asset).map((node) => node.data.asset),
  }
}
