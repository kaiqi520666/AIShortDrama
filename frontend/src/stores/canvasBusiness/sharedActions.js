import { normalizeStoryboardCharacters } from '../../config/canvas/productStoryboard'
import { assignWorkflowNode } from '../../config/canvas/ecommerceWorkflows'
import { useModelCapabilitiesStore } from '../modelCapabilities'

export const createCanvasEdge = (id, source, target, targetHandle, workflowId) => ({
  id,
  source,
  target,
  ...(targetHandle ? { targetHandle } : {}),
  ...(workflowId ? { workflowId } : {}),
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

export function createStoryboardSegmentChain({
  plannerId,
  sourceIds = [],
  plan,
  settings = {},
  templateKey,
  templateId,
  fallbackTitle = '分镜',
  productReferences = [],
  characterReferences = [],
}) {
  const planner = this.nodes.find((node) => node.id === plannerId)
  if (!planner || !plan?.segments?.length) return []
  const workflowId = planner.data.workflowId
  const segmentNodeIds = []
  let previousVideoId = null
  plan.segments.forEach((segment, index) => {
    const segmentIndex = index + 1
    const sharedData = {
      storyboardSourceId: plannerId,
      storyboardTemplateKey: templateKey,
      storyboardTemplateId: templateId,
      storyboardTemplateLabel: plan.title,
      storyboardGlobalScript: plan.globalScript,
      storyboardSegmentIndex: segmentIndex,
      storyboardSegmentCount: plan.segments.length,
      storyboardDuration: segment.duration || 15,
      storyboardContinuityMode: segment.continuityMode,
      storyboardPlotGoal: segment.plotGoal,
      storyboardDramaticBeat: segment.dramaticBeat,
      storyboardProductPlacement: segment.productPlacement,
      storyboardOpeningState: segment.openingState,
      storyboardEndingState: segment.endingState,
      storyboardCharacterReferences: characterReferences,
      storyboardProductReferences: productReferences,
      videoPrompt: segment.videoPrompt,
    }
    const imageId = this.addNode('image', {
      x: planner.position.x + 560 + index * 900,
      y: planner.position.y,
    })
    const image = this.nodes.find((node) => node.id === imageId)
    image.data = {
      ...image.data,
      ...sharedData,
      title: `${plan.title || fallbackTitle} ${segmentIndex} · 分镜`,
      storyboardVideoAspectRatio: planner.data.videoAspectRatio,
      storyboardShotCount: segment.shotCount || 6,
      prompt: segment.prompt,
      promptParts: [{ type: 'text', value: segment.prompt }],
      segmentLocked: segmentIndex > 1,
      ...settings,
    }
    if (workflowId) assignWorkflowNode(image, workflowId, planner.data.workflowType, 'storyboard_image')
    this.addEdge({ source: plannerId, target: imageId, ...(workflowId ? { workflowId } : {}) })
    sourceIds.forEach((sourceId) => this.addEdge({ source: sourceId, target: imageId, ...(workflowId ? { workflowId } : {}) }))

    const videoId = this.addNode('video', {
      x: planner.position.x + 1010 + index * 900,
      y: planner.position.y,
    })
    const video = this.nodes.find((node) => node.id === videoId)
    video.data = {
      ...video.data,
      ...sharedData,
      title: `${plan.title || fallbackTitle} ${segmentIndex} · 视频`,
      storyboardImageId: imageId,
      prompt: segment.videoPrompt,
      promptParts: [{ type: 'text', value: segment.videoPrompt }],
      segmentLocked: true,
    }
    if (workflowId) assignWorkflowNode(video, workflowId, planner.data.workflowType, 'storyboard_video')
    this.addEdge({ source: imageId, target: videoId, ...(workflowId ? { workflowId } : {}) })
    if (segment.continuityMode === 'extend' && previousVideoId) {
      this.addEdge({ source: previousVideoId, target: videoId, ...(workflowId ? { workflowId } : {}) })
    }
    segmentNodeIds.push({ segmentIndex, imageId, videoId })
    previousVideoId = videoId
  })
  planner.data = {
    ...planner.data,
    globalScript: plan.globalScript,
    segmentNodeIds,
    generatedNodeIds: segmentNodeIds.flatMap(({ imageId, videoId }) => [imageId, videoId]),
  }
  this.selectNodes([segmentNodeIds[0].imageId])
  return planner.data.generatedNodeIds
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
    const id = this.addNode('video', { x: image.position.x + 500, y: image.position.y })
    const node = this.nodes.find((item) => item.id === id)
    if (!node) return
    const workflowId = image.data.workflowId
    if (workflowId) assignWorkflowNode(node, workflowId, image.data.workflowType, 'storyboard_video')
    this.addEdge({ source: imageId, target: id, ...(workflowId ? { workflowId } : {}) })
    Object.assign(node.data, storyboardVideoData(image, useModelCapabilitiesStore().defaultVideoModel))
    node.data.title = `${image.data.storyboardTemplateLabel || '商品分镜'}视频`
    this.selectNodes([id])
    return id
  },
}
