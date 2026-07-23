export const connectionTargets = {
  text: ['text', 'image', 'video', 'audio'],
  image: ['text', 'image', 'video', 'audio'],
  video: ['text', 'video'],
  audio: ['audio', 'video'],
}

export const canConnect = (sourceType, targetType) => connectionTargets[sourceType]?.includes(targetType) ?? false

export function getConnectionError(sourceType, targetType, incomingTypes = []) {
  if (!canConnect(sourceType, targetType)) return '节点类型不能连接'
  if (targetType !== 'audio' || !['image', 'audio'].includes(sourceType)) return ''
  if (sourceType === 'image' && incomingTypes.includes('audio')) return '参考图片和参考音频不能混用'
  if (sourceType === 'audio' && incomingTypes.includes('image')) return '参考图片和参考音频不能混用'
  if (sourceType === 'image' && incomingTypes.filter((type) => type === 'image').length >= 1) return '音频节点最多连接 1 张参考图片'
  if (sourceType === 'audio' && incomingTypes.filter((type) => type === 'audio').length >= 3) return '音频节点最多连接 3 条参考音频'
  return ''
}
