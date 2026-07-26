export const mediaUploadRules = {
  image: { types: ['image/jpeg', 'image/png', 'image/webp'], maxSize: 20 * 1024 * 1024 },
  video: { types: ['video/mp4', 'video/quicktime', 'video/webm'], maxSize: 500 * 1024 * 1024 },
  audio: { types: ['audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp4'], maxSize: 100 * 1024 * 1024 },
}

export function validateMediaFile(type, file) {
  const rule = mediaUploadRules[type]
  const label = type === 'video' ? '视频' : type === 'audio' ? '音频' : '图片'
  if (!rule?.types.includes(file.type)) return `不支持的${label}格式`
  if (file.size > rule.maxSize) return `文件不能超过 ${rule.maxSize / 1024 / 1024}MB`
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
      if (type === 'audio') return Number.isFinite(media.duration) ? resolve({ duration: media.duration }) : reject(new Error('无法读取音频时长'))
      width && height ? resolve({ width, height, duration: media.duration || null }) : reject(new Error('无法读取媒体尺寸'))
    }
    media.onerror = () => {
      cleanup()
      reject(new Error('无法读取媒体文件'))
    }
    media.preload = 'metadata'
    media.src = url
  })
}
