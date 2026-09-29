import { i18n } from '../i18n/index'

const { t } = i18n.global
const mimeExtensions = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp',
}

export function buildDownloadFilename(name, mimeType, url) {
  const safeName = (name?.trim() || '图片').replace(/[<>:"/\\|?*]/g, '_')
  if (/\.[a-z0-9]{2,5}$/i.test(safeName)) return safeName
  const pathExtension = new URL(url, globalThis.location?.origin || 'http://localhost').pathname.match(/\.([a-z0-9]{2,5})$/i)?.[1]
  return `${safeName}.${mimeExtensions[mimeType] || pathExtension || 'png'}`
}

export async function downloadUrl(url, name) {
  const response = await fetch(url, { cache: 'no-store' })
  if (!response.ok) throw new Error(t('canvas.imageDownloadStatus', { p0: response.status }))
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = buildDownloadFilename(name, blob.type, url)
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
}
