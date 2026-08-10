import { getNodeDescriptor } from './nodeCatalog'
import { isNodeTypeAvailable } from './nodePacks'

export const maxProductReferenceImages = getNodeDescriptor('product').inputLimits.image.max

export function canConnect(sourceType, targetType, workspaceType = 'general') {
  if (!isNodeTypeAvailable(workspaceType, sourceType) || !isNodeTypeAvailable(workspaceType, targetType)) return false
  const source = getNodeDescriptor(sourceType)
  const target = getNodeDescriptor(targetType)
  return source.outputs.includes(targetType) && target.inputs.includes(sourceType)
}

export function getConnectionError(sourceType, targetType, incomingTypes = [], workspaceType = 'general', targetHandle = '', incomingConnections = []) {
  if (!canConnect(sourceType, targetType, workspaceType)) return '节点类型不能连接'
  const limit = getNodeDescriptor(targetType).inputLimits?.[sourceType]
  if (limit && incomingTypes.filter((type) => type === sourceType).length >= limit.max) return limit.message
  if (targetType !== 'audio' || !['image', 'audio'].includes(sourceType)) return ''
  if (sourceType === 'image' && incomingTypes.includes('audio')) return '参考图片和参考音频不能混用'
  if (sourceType === 'audio' && incomingTypes.includes('image')) return '参考图片和参考音频不能混用'
  return ''
}

export function inferTargetHandle() {
  return undefined
}
