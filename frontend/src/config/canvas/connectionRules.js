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
  if (targetType === 'apparel_storyboard') {
    if (sourceType === 'outfit') {
      if (targetHandle && targetHandle !== 'outfit') return '模特试穿请连接到试穿输入'
      if (incomingTypes.includes('outfit')) return '服饰分镜节点只能连接 1 个模特试穿'
    }
    if (sourceType === 'apparel') {
      if (targetHandle && targetHandle !== 'apparel') return '服饰资料请连接到服饰输入'
      if (incomingTypes.includes('apparel')) return '服饰分镜节点只能连接 1 个服饰资料'
    }
    if (sourceType === 'image' && !targetHandle) return '图片请连接到场景输入'
    if (sourceType === 'image' && targetHandle) {
      if (targetHandle !== 'scene') return '图片请连接到场景输入'
      if (incomingConnections.some((connection) => connection.targetHandle === targetHandle)) return `${targetHandle === 'model' ? '模特' : '场景'}图片只能连接 1 张`
    }
  }
  if (targetType !== 'audio' || !['image', 'audio'].includes(sourceType)) return ''
  if (sourceType === 'image' && incomingTypes.includes('audio')) return '参考图片和参考音频不能混用'
  if (sourceType === 'audio' && incomingTypes.includes('image')) return '参考图片和参考音频不能混用'
  return ''
}

export function inferTargetHandle(source, targetType, incomingConnections = []) {
  if (!source || targetType !== 'apparel_storyboard') return undefined
  if (source.type === 'outfit') return 'outfit'
  if (source.type === 'apparel') return 'apparel'
  if (source.type !== 'image') return undefined
  return incomingConnections.some((connection) => connection.targetHandle === 'scene') ? undefined : 'scene'
}
