import { getNodeDefinition } from './nodeDefinitions'
import { isNodeTypeAvailable } from './nodePacks'

export function canConnect(sourceType, targetType, workspaceType = 'general') {
  if (!isNodeTypeAvailable(workspaceType, sourceType) || !isNodeTypeAvailable(workspaceType, targetType)) return false
  const source = getNodeDefinition(sourceType)
  const target = getNodeDefinition(targetType)
  return source.outputs.includes(targetType) && target.inputs.includes(sourceType)
}

export function getConnectionError(sourceType, targetType, incomingTypes = [], workspaceType = 'general', targetHandle = '', incomingConnections = []) {
  if (!canConnect(sourceType, targetType, workspaceType)) return '节点类型不能连接'
  if (targetType === 'product' && sourceType === 'image' && incomingTypes.filter((type) => type === 'image').length >= 9) return '商品创作节点最多连接 9 张参考图片'
  if (targetType === 'product_visual' && incomingTypes.includes('product')) return '商品出图节点只能连接 1 个商品资料'
  if (targetType === 'product_storyboard' && incomingTypes.includes('product')) return '商品分镜节点只能连接 1 个商品创作'
  if (targetType === 'outfit' && sourceType === 'apparel' && incomingTypes.includes('apparel')) return '服饰穿搭节点只能连接 1 个服饰资料'
  if (targetType === 'outfit' && sourceType === 'image' && incomingTypes.includes('image')) return '服饰穿搭节点只能连接 1 张模特图'
  if (targetType === 'apparel_storyboard') {
    if (sourceType === 'apparel') {
      if (targetHandle && targetHandle !== 'apparel') return '服饰资料请连接到服饰输入'
      if (incomingTypes.includes('apparel')) return '服饰分镜节点只能连接 1 个服饰资料'
    }
    if (sourceType === 'image' && !targetHandle) return '图片请连接到模特或场景输入'
    if (sourceType === 'image' && targetHandle) {
      if (!['model', 'scene'].includes(targetHandle)) return '图片请连接到模特或场景输入'
      if (incomingConnections.some((connection) => connection.targetHandle === targetHandle)) return `${targetHandle === 'model' ? '模特' : '场景'}图片只能连接 1 张`
    }
  }
  if (targetType === 'character' && sourceType === 'world' && incomingTypes.includes('world')) return '角色创作节点只能连接 1 个世界观'
  if (targetType === 'character' && sourceType === 'image' && incomingTypes.includes('image')) return '角色创作节点只能连接 1 张参考图'
  if (targetType !== 'audio' || !['image', 'audio'].includes(sourceType)) return ''
  if (sourceType === 'image' && incomingTypes.includes('audio')) return '参考图片和参考音频不能混用'
  if (sourceType === 'audio' && incomingTypes.includes('image')) return '参考图片和参考音频不能混用'
  if (sourceType === 'image' && incomingTypes.filter((type) => type === 'image').length >= 1) return '音频节点最多连接 1 张参考图片'
  if (sourceType === 'audio' && incomingTypes.filter((type) => type === 'audio').length >= 3) return '音频节点最多连接 3 条参考音频'
  return ''
}

export function inferTargetHandle(source, targetType, incomingConnections = []) {
  if (!source || targetType !== 'apparel_storyboard') return undefined
  if (source.type === 'apparel') return 'apparel'
  if (source.type !== 'image') return undefined
  const preferred = source.data?.inputRole === 'scene' || source.data?.resourceType === 'scene'
    ? 'scene'
    : source.data?.inputRole === 'role' || source.data?.resourceType === 'model' ? 'model' : ''
  if (preferred && !incomingConnections.some((connection) => connection.targetHandle === preferred)) return preferred
  return ['model', 'scene'].find((handle) => !incomingConnections.some((connection) => connection.targetHandle === handle))
}
