import { normalizeStoryboardCharacters } from '../../config/canvas/productStoryboard'
import { useModelCapabilitiesStore } from '../modelCapabilities'

export const createCanvasEdge = (id, source, target, targetHandle) => ({
  id,
  source,
  target,
  ...(targetHandle ? { targetHandle } : {}),
  type: 'cinematic',
})

export function storyboardVideoData(source, defaultVideoModel) {
  const prompt = source?.type === 'image' ? source.data.videoPrompt?.trim() : ''
  if (!prompt) return null
  return {
    storyboardImageId: source.id,
    prompt,
    promptParts: [{ type: 'text', value: prompt }],
    model: defaultVideoModel.id,
    duration: source.data.storyboardDuration || defaultVideoModel.defaultDuration,
    aspectRatio: source.data.storyboardVideoAspectRatio || defaultVideoModel.defaultAspectRatio,
    resolution: defaultVideoModel.defaultResolution,
    generateAudio: true,
    storyboardCharacterReferences: normalizeStoryboardCharacters(source.data.storyboardCharacterReferences),
    storyboardProductReferences: source.data.storyboardProductReferences || [],
  }
}

export const sharedActions = {
  addStoryboardVideoNode(imageId) {
    const image = this.nodes.find((node) => node.id === imageId && node.type === 'image')
    if (!image?.data.asset || !image.data.videoPrompt?.trim()) return
    const existing = this.nodes.find((node) => node.type === 'video' && node.data.storyboardImageId === imageId)
    if (existing) {
      Object.assign(existing.data, storyboardVideoData(image, useModelCapabilitiesStore().defaultVideoModel))
      this.selectNodes([existing.id])
      return existing.id
    }
    const id = this.addNode('video', { x: image.position.x + 500, y: image.position.y }, imageId)
    const node = this.nodes.find((item) => item.id === id)
    if (!node) return
    node.data.title = `${image.data.storyboardTemplateLabel || '商品分镜'}视频`
    this.selectNodes([id])
    return id
  },
}
