const generalNodes = ['text', 'image', 'video', 'audio']

export const workspaceTypes = [
  { id: 'general', label: '通用画布', defaultName: '未命名通用项目', description: '自由组合文本、图片、视频和音频' },
  { id: 'ecommerce', label: '电商画布', defaultName: '未命名电商项目', description: '用于商品内容与营销素材生产' },
  { id: 'drama', label: '短剧画布', defaultName: '未命名短剧项目', description: '用于剧本、角色、分镜与镜头生产' },
]

export const nodePacks = {
  general: generalNodes,
  ecommerce: ['product', 'product_visual', 'product_storyboard', 'apparel', 'outfit', 'apparel_storyboard', ...generalNodes],
  drama: ['world', 'character', ...generalNodes],
}

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
  return getNodeTypes(workspaceType).includes(nodeType)
}
