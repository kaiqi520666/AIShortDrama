import { nodeCatalog } from './nodeCatalog'

export const workspaceTypes = [
  { id: 'general', label: '通用画布', description: '自由组合文本、图片、视频和音频' },
  { id: 'ecommerce', label: '电商画布', description: '用于商品内容与营销素材生产' },
]

export const nodePacks = Object.fromEntries(workspaceTypes.map(({ id }) => [id, Object.values(nodeCatalog)
  .filter((node) => node.workspaces.includes(id))
  .sort((left, right) => left.order[id] - right.order[id])
  .map((node) => node.type)]))

export function getWorkspaceType(type) {
  const definition = workspaceTypes.find((item) => item.id === type)
  if (!definition) throw new Error(`不支持的画布类型：${type}`)
  return definition
}

export function getNodeTypes(workspaceType) {
  const types = nodePacks[workspaceType]
  if (!types) throw new Error(`不支持的画布类型：${workspaceType}`)
  return types
}

export function isNodeTypeAvailable(workspaceType, nodeType) {
  if (!nodeCatalog[nodeType]) {
    if (import.meta.env.DEV) throw new Error(`节点 ${nodeType} 未在 nodeCatalog 注册`)
    return false
  }
  return getNodeTypes(workspaceType).includes(nodeType)
}
