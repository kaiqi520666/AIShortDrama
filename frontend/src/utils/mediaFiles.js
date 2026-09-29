export const mediaUploadRules = {
  image: { types: ['image/jpeg', 'image/png', 'image/webp'], maxSize: 20 * 1024 * 1024 },
  video: { types: ['video/mp4', 'video/quicktime', 'video/webm'], maxSize: 500 * 1024 * 1024 },
  audio: { types: ['audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp4'], maxSize: 100 * 1024 * 1024 },
}

export function validateMediaFile(type, file) {
  const rule = mediaUploadRules[type]
  const label = t(type === 'video' ? 'canvas.video' : type === 'audio' ? 'canvas.audio' : 'canvas.image')
  if (!rule?.types.includes(file.type)) return t('canvas.unsupportedMediaFormat', { p0: label })
  if (file.size > rule.maxSize) return t('canvas.fileSizeLimit', { p0: rule.maxSize / 1024 / 1024 })
  return ''
}

export function readMediaMetadata(type, file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const media = type === 'image' ? new Image() : document.createElement(type)
    const cleanup = () => URL.revokeObjectURL(url)
    media.onload = media.onloadedmetadata = () => {
      const width = media.naturalWidth || media.videoWidth
      const height = media.naturalHeight || media.videoHeight
      cleanup()
      if (type === 'audio') return Number.isFinite(media.duration) ? resolve({ duration: media.duration }) : reject(new Error(t('canvas.audioDurationReadFailed')))
      width && height ? resolve({ width, height, duration: media.duration || null }) : reject(new Error(t('canvas.mediaDimensionsReadFailed')))
    }
    media.onerror = () => {
      cleanup()
      reject(new Error(t('canvas.mediaReadFailed')))
    }
    media.preload = 'metadata'
    media.src = url
  })
}
import { i18n } from '../i18n'

const { t } = i18n.global
