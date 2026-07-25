import { getNodeDefinition } from './nodeDefinitions'
import { isNodeTypeAvailable } from './nodePacks'

export function canConnect(sourceType, targetType, workspaceType = 'general') {
  if (!isNodeTypeAvailable(workspaceType, sourceType) || !isNodeTypeAvailable(workspaceType, targetType)) return false
  const source = getNodeDefinition(sourceType)
  const target = getNodeDefinition(targetType)
  return source.outputs.includes(targetType) && target.inputs.includes(sourceType)
}

export function getConnectionError(sourceType, targetType, incomingTypes = [], workspaceType = 'general') {
  if (!canConnect(sourceType, targetType, workspaceType)) return '节点类型不能连接'
  if (targetType !== 'audio' || !['image', 'audio'].includes(sourceType)) return ''
  if (sourceType === 'image' && incomingTypes.includes('audio')) return '参考图片和参考音频不能混用'
  if (sourceType === 'audio' && incomingTypes.includes('image')) return '参考图片和参考音频不能混用'
  if (sourceType === 'image' && incomingTypes.filter((type) => type === 'image').length >= 1) return '音频节点最多连接 1 张参考图片'
  if (sourceType === 'audio' && incomingTypes.filter((type) => type === 'audio').length >= 3) return '音频节点最多连接 3 条参考音频'
  return ''
}
