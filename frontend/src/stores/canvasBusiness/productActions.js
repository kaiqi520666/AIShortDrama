import {
  buildStoryboardReferenceManifest,
  storyboardShotCount,
} from '../../config/canvas/productStoryboard'
import { createStoryboardSegmentChain } from './sharedActions'

export function createProductChain(position, sourceId) {
  if (sourceId) return { handled: false }
  const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
  const image = this.nodes.find((node) => node.id === imageId)
  image.data = { ...image.data, title: '商品参考图', assetSource: 'upload' }
  return { handled: true, id: this.addNode('product', position, imageId) }
}

export const productActions = {
  addProductVisualNodes(plannerId, productId, referenceIds, plans, settings) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner || !plans.length) return []
    const references = (Array.isArray(referenceIds) ? referenceIds : [referenceIds]).filter(Boolean)
    const columns = Math.min(3, plans.length)
    const ids = plans.map((plan, index) => {
      const id = this.addNode('image', {
        x: planner.position.x + 500 + (index % columns) * 440,
        y: planner.position.y + Math.floor(index / columns) * 340,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: plan.label,
        prompt: plan.prompt,
        promptParts: [{ type: 'text', value: plan.prompt }],
        model: settings.model,
        aspectRatio: settings.aspectRatio,
        resolution: settings.resolution,
      }
      this.addEdge({ source: plannerId, target: id })
      references.forEach((referenceId) => this.addEdge({ source: referenceId, target: id }))
      this.addEdge({ source: productId, target: id })
      return id
    })
    this.selectNodes(ids.slice(0, 1))
    return ids
  },

  addProductStoryboardNodes(plannerId, productId, plans, settings) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner) return []
    const referenceManifest = buildStoryboardReferenceManifest(
      planner.data.characterReferences,
      planner.data.productReferences,
    )
    if (plans?.segments?.length) {
      return createStoryboardSegmentChain.call(this, {
        plannerId,
        sourceIds: [productId],
        plan: plans,
        settings,
        templateKey: planner.data.templateKey || 'product_storyboard',
        templateId: plans.templateId || 'ugc-seeding',
        fallbackTitle: '商品分镜',
        productReferences: referenceManifest.products,
        characterReferences: referenceManifest.characters,
      })
    }
    if (!plans?.length) return []
    const columns = Math.min(3, plans.length)
    const ids = plans.map((plan, index) => {
      const id = this.addNode('image', {
        x: planner.position.x + 500 + (index % columns) * 440,
        y: planner.position.y + Math.floor(index / columns) * 340,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: `${plan.label}分镜板`,
        storyboardSourceId: plannerId,
        storyboardTemplateId: 'ugc-seeding',
        storyboardTemplateLabel: plan.label,
        storyboardDuration: planner.data.duration,
        storyboardVideoAspectRatio: planner.data.videoAspectRatio,
        storyboardShotCount: storyboardShotCount(planner.data.duration),
        storyboardProductReferences: referenceManifest.products,
        storyboardCharacterReferences: referenceManifest.characters,
        videoPrompt: plan.videoPrompt,
        prompt: plan.prompt,
        promptParts: [{ type: 'text', value: plan.prompt }],
        ...settings,
      }
      this.addEdge({ source: plannerId, target: id })
      this.addEdge({ source: productId, target: id })
      return id
    })
    this.selectNodes(ids.slice(0, 1))
    return ids
  },

  syncProductStoryboardReferences(plannerId, productReferences = [], characterReferences = []) {
    const manifest = buildStoryboardReferenceManifest(characterReferences, productReferences)
    const references = manifest.products.map((reference) => ({ ...reference }))
    const characters = manifest.characters.map((reference) => ({ ...reference }))
    const storyboardImageIds = new Set(this.nodes
      .filter((node) => node.type === 'image' && node.data.storyboardSourceId === plannerId)
      .map((node) => node.id))
    this.nodes
      .filter((node) => ['image', 'video'].includes(node.type)
        && (node.data.storyboardSourceId === plannerId || storyboardImageIds.has(node.data.storyboardImageId)))
      .forEach((node) => {
        node.data.storyboardProductReferences = references.map((reference) => ({ ...reference }))
        node.data.storyboardCharacterReferences = characters.map((reference) => ({ ...reference }))
      })
  },
}
