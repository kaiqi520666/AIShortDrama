import { assignWorkflowEdges, assignWorkflowNode, createWorkflowId } from '../../config/canvas/ecommerceWorkflows'
import { useModelCapabilitiesStore } from '../modelCapabilities'
import { createCanvasEdge } from './sharedActions'

export function createApparelChain(position, sourceId) {
  if (sourceId) return { handled: false }
  const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
  const image = this.nodes.find((node) => node.id === imageId)
  image.data = { ...image.data, title: '服饰参考图', assetSource: 'upload', resourceType: 'garment' }
  return { handled: true, id: this.addNode('apparel', position, imageId) }
}

export function createOutfitChain(position, sourceId) {
  if (sourceId) return { handled: false }
  const apparelId = this.addNode('apparel', { x: position.x - 500, y: position.y - 170 })
  const modelId = this.addNode('image', { x: position.x - 500, y: position.y + 190 })
  const model = this.nodes.find((node) => node.id === modelId)
  model.data = { ...model.data, title: '模特参考图', assetSource: 'upload', resourceType: 'model' }
  const outfitId = this.addNode('outfit', position, apparelId)
  const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === outfitId)
  apparelEdge.targetHandle = 'apparel'
  this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, modelId, outfitId, 'model'))
  this.selectNodes([outfitId])
  return { handled: true, id: outfitId }
}

export function createApparelStoryboardChain(position, sourceId, skipStoryboardInputs) {
  const source = this.nodes.find((node) => node.id === sourceId)
  if (skipStoryboardInputs || (sourceId && !['apparel', 'outfit'].includes(source?.type))) return { handled: false }
  const workflowId = source?.data.workflowId || createWorkflowId('apparel')
  let outfitId = source?.type === 'outfit' ? source.id : null
  let apparelId = source?.type === 'apparel' ? source.id : null
  if (!outfitId && source?.type === 'apparel') {
    const modelId = this.addNode('image', { x: position.x - 980, y: position.y + 100 })
    const model = this.nodes.find((node) => node.id === modelId)
    model.data = { ...model.data, title: '模特参考图', assetSource: 'upload', resourceType: 'model' }
    outfitId = this.addNode('outfit', { x: position.x - 500, y: position.y - 120 }, source.id)
    const apparelEdge = this.edges.find((edge) => edge.source === source.id && edge.target === outfitId)
    if (apparelEdge) apparelEdge.targetHandle = 'apparel'
    this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, modelId, outfitId, 'model'))
  }
  if (!outfitId) {
    apparelId = this.addNode('apparel', { x: position.x - 500, y: position.y - 170 })
    const modelId = this.addNode('image', { x: position.x - 500, y: position.y + 190 })
    const model = this.nodes.find((node) => node.id === modelId)
    model.data = { ...model.data, title: '模特参考图', assetSource: 'upload', resourceType: 'model' }
    outfitId = this.addNode('outfit', position, apparelId)
    const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === outfitId)
    if (apparelEdge) apparelEdge.targetHandle = 'apparel'
    this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, modelId, outfitId, 'model'))
  }
  const outfit = this.nodes.find((node) => node.id === outfitId)
  outfit.data.title = outfit.data.title.replace('模特试穿', '服饰穿搭')
  apparelId ||= this.edges.find((edge) => edge.target === outfitId && this.nodes.find((node) => node.id === edge.source)?.type === 'apparel')?.source
  const garmentId = this.edges.find((edge) => edge.target === apparelId && this.nodes.find((node) => node.id === edge.source)?.type === 'image')?.source
  const modelId = this.edges.find((edge) => edge.target === outfitId && edge.targetHandle === 'model')?.source
  const storyboardId = this.addNode('apparel_storyboard', { x: outfit.position.x + 520, y: outfit.position.y }, outfitId, true)
  const outfitEdge = this.edges.find((edge) => edge.source === outfitId && edge.target === storyboardId)
  if (outfitEdge) outfitEdge.targetHandle = 'outfit'
  assignWorkflowNode(this.nodes.find((node) => node.id === garmentId), workflowId, 'apparel', 'garment_reference')
  assignWorkflowNode(this.nodes.find((node) => node.id === apparelId), workflowId, 'apparel', 'apparel')
  assignWorkflowNode(this.nodes.find((node) => node.id === modelId), workflowId, 'apparel', 'model_reference')
  assignWorkflowNode(outfit, workflowId, 'apparel', 'outfit', true)
  assignWorkflowNode(this.nodes.find((node) => node.id === storyboardId), workflowId, 'apparel', 'storyboard')
  assignWorkflowEdges(this.edges, workflowId, [garmentId, apparelId, modelId, outfitId, storyboardId])
  this.selectNodes([garmentId])
  return { handled: true, id: storyboardId }
}

export const apparelActions = {
  addApparelStoryboardNodes(plannerId, garmentId, modelId, sceneId, plan, settings = {}) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner || !plan?.storyboardPrompt?.trim() || !plan.videoPrompt?.trim()) return []
    const capabilities = useModelCapabilitiesStore()
    const defaultImageModel = capabilities.defaultImageModel
    const defaultVideoModel = capabilities.defaultVideoModel
    const imageSettings = settings.imageSettings || {
      model: defaultImageModel.id,
      aspectRatio: planner.data.videoAspectRatio,
      resolution: defaultImageModel.resolutions.includes('2K') ? '2K' : defaultImageModel.defaultResolution,
    }
    const videoSettings = settings.videoSettings || {
      model: planner.data.videoModel || defaultVideoModel.id,
      duration: planner.data.duration || defaultVideoModel.defaultDuration,
      aspectRatio: planner.data.videoAspectRatio || defaultVideoModel.defaultAspectRatio,
      resolution: planner.data.videoResolution || defaultVideoModel.defaultResolution,
      generateAudio: true,
    }
    const imageId = this.addNode('image', { x: planner.position.x + 560, y: planner.position.y })
    const image = this.nodes.find((node) => node.id === imageId)
    const workflowId = planner.data.workflowId
    image.data = {
      ...image.data,
      title: `${plan.title || '服饰展示'} · 故事板`,
      storyboardSourceId: plannerId,
      storyboardTemplateId: plan.templateId,
      storyboardTemplateLabel: plan.title,
      storyboardDuration: plan.duration,
      storyboardVideoAspectRatio: videoSettings.aspectRatio,
      storyboardShotCount: plan.shotCount,
      storyboardReferenceOrder: ['服饰参考图', '角色节点'],
      storyboardRequiresRegistration: true,
      videoPrompt: plan.videoPrompt,
      prompt: plan.storyboardPrompt,
      promptParts: [{ type: 'text', value: plan.storyboardPrompt }],
      ...imageSettings,
    }
    if (workflowId) assignWorkflowNode(image, workflowId, planner.data.workflowType, 'storyboard_image')
    this.addEdge({ source: plannerId, target: imageId, ...(workflowId ? { workflowId } : {}) })
    ;[garmentId, modelId, sceneId].filter(Boolean).forEach((source) => this.addEdge({ source, target: imageId, ...(workflowId ? { workflowId } : {}) }))
    const videoId = this.addNode('video', { x: planner.position.x + 980, y: planner.position.y })
    const video = this.nodes.find((node) => node.id === videoId)
    video.data = {
      ...video.data,
      title: `${plan.title || '服饰展示'} · 视频`,
      storyboardSourceId: plannerId,
      storyboardImageId: imageId,
      storyboardTemplateId: plan.templateId,
      storyboardTemplateLabel: plan.title,
      storyboardDuration: plan.duration,
      storyboardShotCount: plan.shotCount,
      storyboardReferenceOrder: ['分镜故事板', '服饰参考图', '角色节点'],
      videoPrompt: plan.videoPrompt,
      prompt: plan.videoPrompt,
      promptParts: [{ type: 'text', value: plan.videoPrompt }],
      ...videoSettings,
    }
    if (workflowId) assignWorkflowNode(video, workflowId, planner.data.workflowType, 'storyboard_video')
    this.addEdge({ source: imageId, target: videoId, ...(workflowId ? { workflowId } : {}) })
    ;[garmentId, modelId, sceneId].filter(Boolean).forEach((source) => this.addEdge({ source, target: videoId, ...(workflowId ? { workflowId } : {}) }))
    planner.data = {
      ...planner.data,
      generatedNodeIds: [imageId, videoId],
      storyboardImageId: imageId,
      storyboardVideoId: videoId,
      storyboardShotCount: plan.shotCount,
      storyboardPrompt: plan.storyboardPrompt,
      videoPrompt: plan.videoPrompt,
      videoModel: videoSettings.model,
      duration: videoSettings.duration,
      videoAspectRatio: videoSettings.aspectRatio,
      videoResolution: videoSettings.resolution,
      generateAudio: videoSettings.generateAudio,
    }
    this.selectNodes([imageId])
    return [imageId, videoId]
  },

  addOutfitStoryboardNodes(plannerId, outfitReferenceId, outfitReference, sceneId, plans, settings) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner || !plans?.segments?.length) return []
    const reference = outfitReference?.url
      ? { url: outfitReference.url, assetId: outfitReference.assetId || null }
      : null
    const workflowId = planner.data.workflowId
    const segmentNodeIds = []
    let previousVideoId = null
    plans.segments.forEach((segment, index) => {
      const segmentIndex = index + 1
      const imageId = this.addNode('image', {
        x: planner.position.x + 560 + index * 900,
        y: planner.position.y,
      })
      const image = this.nodes.find((node) => node.id === imageId)
      image.data = {
        ...image.data,
        title: `${plans.title || '服饰分镜'} ${segmentIndex} · 分镜`,
        storyboardSourceId: plannerId,
        storyboardTemplateId: plans.templateId,
        storyboardTemplateKey: planner.data.templateKey || 'apparel_showcase',
        storyboardTemplateLabel: plans.title,
        storyboardGlobalScript: plans.globalScript,
        storyboardSegmentIndex: segmentIndex,
        storyboardSegmentCount: plans.segments.length,
        storyboardDuration: 15,
        storyboardVideoAspectRatio: planner.data.videoAspectRatio,
        storyboardShotCount: 6,
        ...(outfitReferenceId ? {} : { storyboardOutfitReference: reference }),
        storyboardRequiresRegistration: true,
        storyboardContinuityMode: segment.continuityMode,
        storyboardPlotGoal: segment.plotGoal,
        storyboardOpeningState: segment.openingState,
        storyboardEndingState: segment.endingState,
        videoPrompt: segment.videoPrompt,
        prompt: segment.prompt,
        promptParts: [{ type: 'text', value: segment.prompt }],
        segmentLocked: segmentIndex > 1,
        ...settings,
      }
      if (workflowId) assignWorkflowNode(image, workflowId, planner.data.workflowType, 'storyboard_image')
      this.addEdge({ source: plannerId, target: imageId, ...(workflowId ? { workflowId } : {}) })
      if (outfitReferenceId) this.addEdge({ source: outfitReferenceId, target: imageId, ...(workflowId ? { workflowId } : {}) })
      if (sceneId) this.addEdge({ source: sceneId, target: imageId, ...(workflowId ? { workflowId } : {}) })
      const videoId = this.addNode('video', {
        x: planner.position.x + 1010 + index * 900,
        y: planner.position.y,
      })
      const video = this.nodes.find((node) => node.id === videoId)
      video.data = {
        ...video.data,
        title: `${plans.title || '服饰分镜'} ${segmentIndex} · 视频`,
        storyboardSourceId: plannerId,
        storyboardImageId: imageId,
        storyboardTemplateId: plans.templateId,
        storyboardTemplateKey: planner.data.templateKey || 'apparel_showcase',
        storyboardTemplateLabel: plans.title,
        storyboardGlobalScript: plans.globalScript,
        storyboardSegmentIndex: segmentIndex,
        storyboardSegmentCount: plans.segments.length,
        storyboardContinuityMode: segment.continuityMode,
        storyboardPlotGoal: segment.plotGoal,
        storyboardOpeningState: segment.openingState,
        storyboardEndingState: segment.endingState,
        storyboardRequiresRegistration: true,
        storyboardDuration: 15,
        videoPrompt: segment.videoPrompt,
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
      storyboardOutfitReference: reference,
      globalScript: plans.globalScript,
      segmentNodeIds,
      generatedNodeIds: segmentNodeIds.flatMap(({ imageId, videoId }) => [imageId, videoId]),
    }
    this.selectNodes([segmentNodeIds[0].imageId])
    return planner.data.generatedNodeIds
  },

  addOutfitVisualNode(outfitId, garmentId, modelId, prompt, settings) {
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
      prompt,
      promptParts: [{ type: 'text', value: prompt }],
      ...settings,
    }
    if (workflowId) assignWorkflowNode(node, workflowId, outfit.data.workflowType, 'outfit_reference')
    this.addEdge({ source: outfitId, target: id, ...(workflowId ? { workflowId } : {}) })
    this.addEdge({ source: garmentId, target: id, ...(workflowId ? { workflowId } : {}) })
    this.addEdge({ source: modelId, target: id, ...(workflowId ? { workflowId } : {}) })
    this.selectNodes([id])
    return id
  },
}
