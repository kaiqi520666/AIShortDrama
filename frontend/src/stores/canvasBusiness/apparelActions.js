import { assignWorkflowNode } from '../../config/canvas/ecommerceWorkflows'

export function createApparelChain(position, sourceId) {
  if (sourceId) return { handled: false }
  const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
  const image = this.nodes.find((node) => node.id === imageId)
  image.data = { ...image.data, title: '服饰参考图', assetSource: 'upload', resourceType: 'garment' }
  return { handled: true, id: this.addNode('apparel', position, imageId) }
}

export function createOutfitChain(position, sourceId) {
  if (sourceId) return { handled: false }
  const apparelId = this.addNode('apparel', { x: position.x - 500, y: position.y })
  const outfitId = this.addNode('outfit', position, apparelId)
  const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === outfitId)
  apparelEdge.targetHandle = 'apparel'
  const workflowId = `workflow-apparel-${outfitId}`
  const apparel = this.nodes.find((node) => node.id === apparelId)
  const garment = this.nodes.find((node) => node.type === 'image' && this.edges.some((edge) => edge.source === node.id && edge.target === apparelId))
  const outfit = this.nodes.find((node) => node.id === outfitId)
  assignWorkflowNode(garment, workflowId, 'apparel', 'garment_reference')
  assignWorkflowNode(apparel, workflowId, 'apparel', 'apparel')
  assignWorkflowNode(outfit, workflowId, 'apparel', 'outfit', true)
  this.edges.filter((edge) => [garment?.id, apparelId, outfitId].includes(edge.source) && [garment?.id, apparelId, outfitId].includes(edge.target))
    .forEach((edge) => { edge.workflowId = workflowId })
  this.selectNodes([outfitId])
  return { handled: true, id: outfitId }
}

export const apparelActions = {
  addOutfitVisualNode(outfitId, garmentId, prompt, settings) {
    const outfit = this.nodes.find((node) => node.id === outfitId)
    if (!outfit || !prompt?.trim()) return
    const id = this.addNode('image', { x: outfit.position.x + 500, y: outfit.position.y })
    const node = this.nodes.find((item) => item.id === id)
    const workflowId = outfit.data.workflowId
    node.data = {
      ...node.data,
      title: '试穿定妆图',
      outfitSourceId: outfitId,
      resourceType: 'outfit-reference',
      requiresPrivateRegistration: true,
      prompt,
      promptParts: [{ type: 'text', value: prompt }],
      ...settings,
    }
    if (workflowId) assignWorkflowNode(node, workflowId, outfit.data.workflowType, 'outfit_reference')
    this.addEdge({ source: outfitId, target: id, ...(workflowId ? { workflowId } : {}) })
    this.addEdge({ source: garmentId, target: id, ...(workflowId ? { workflowId } : {}) })
    this.selectNodes([id])
    return id
  },

  addOutfitVideoNode(outfitId, outfitReferenceId, garmentId, prompt, settings = {}) {
    const outfit = this.nodes.find((node) => node.id === outfitId)
    if (!outfit || !outfitReferenceId || !garmentId || !prompt?.trim()) return
    const id = this.addNode('video', { x: outfit.position.x + 1040, y: outfit.position.y })
    const node = this.nodes.find((item) => item.id === id)
    const workflowId = outfit.data.workflowId
    node.data = {
      ...node.data,
      title: '服饰展示视频',
      outfitSourceId: outfitId,
      outfitReferenceId,
      outfitGarmentId: garmentId,
      outfitReferenceOrder: ['定妆图', '服饰原图'],
      prompt,
      promptParts: [{ type: 'text', value: prompt }],
      generateAudio: false,
      ...settings,
    }
    if (workflowId) assignWorkflowNode(node, workflowId, outfit.data.workflowType, 'outfit_video')
    this.addEdge({ source: outfitReferenceId, target: id, ...(workflowId ? { workflowId } : {}) })
    this.addEdge({ source: garmentId, target: id, ...(workflowId ? { workflowId } : {}) })
    outfit.data = { ...outfit.data, videoNodeId: id }
    this.selectNodes([id])
    return id
  },
}
