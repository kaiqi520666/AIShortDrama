import { defineStore } from 'pinia'
import { canConnect, getConnectionError, inferTargetHandle } from '../config/canvas/connectionRules'
import { createNodeData, getNodeDefinition, getReversePrompt } from '../config/canvas/nodeDefinitions'
import { isNodeTypeAvailable } from '../config/canvas/nodePacks'
import { storyboardShotCount } from '../config/canvas/productStoryboard'
import { defaultReverseModel } from '../config/reverseModels'
import { defaultVideoModel } from '../config/videoModels'
import { saveWorkspaceCanvas } from '../api/workspaces'

const createEdge = (id, source, target, targetHandle) => ({ id, source, target, ...(targetHandle ? { targetHandle } : {}), type: 'cinematic' })
const defaultWorkspaceId = '00000000-0000-0000-0000-000000000101'
let activeSave = null
let saveQueued = false

function storyboardVideoData(source) {
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
    storyboardCharacter: source.data.storyboardCharacter || null,
    storyboardProductReferences: source.data.storyboardProductReferences || [],
  }
}

function stripTransientNodes(nodes = [], edges = [], groups = []) {
  const transientIds = new Set(nodes.filter((node) => node.data?.status === 'uploading').map((node) => node.id))
  return {
    removed: transientIds.size > 0,
    nodes: nodes.filter((node) => !transientIds.has(node.id)),
    edges: edges.filter((edge) => !transientIds.has(edge.source) && !transientIds.has(edge.target)),
    groups: groups
      .map((group) => ({ ...group, nodeIds: group.nodeIds.filter((id) => !transientIds.has(id)) }))
      .filter((group) => group.nodeIds.length > 1),
  }
}

export const useCanvasStore = defineStore('canvas', {
  state: () => ({
    workspaceId: null,
    workspaceType: 'general',
    workspaceVersion: null,
    nodes: [],
    edges: [],
    sequence: 1,
    groupSequence: 1,
    groups: [],
    viewportData: { x: 0, y: 0, zoom: 1 },
    saveStatus: 'saved',
    saveConflict: false,
    ready: false,
    legacyImportPending: false,
  }),
  getters: {
    incomingNodes: (state) => (nodeId) =>
      state.edges
        .filter((edge) => edge.target === nodeId)
        .map((edge) => state.nodes.find((node) => node.id === edge.source))
        .filter(Boolean),
  },
  actions: {
    async loadWorkspace(workspace) {
      this.ready = false
      this.workspaceId = workspace.id
      this.workspaceType = workspace.workspace_type
      this.workspaceVersion = workspace.version
      this.saveConflict = false
      let canvas = workspace.canvas || {}
      const legacy = this.readLegacyCanvas()
      if (workspace.id === defaultWorkspaceId && !canvas.nodes?.length && legacy?.nodes?.length) {
        canvas = legacy
        this.legacyImportPending = true
      }
      const persistent = stripTransientNodes(canvas.nodes, canvas.edges, canvas.groups)
      this.nodes = JSON.parse(JSON.stringify(persistent.nodes))
      this.edges = JSON.parse(JSON.stringify(persistent.edges))
      this.groups = JSON.parse(JSON.stringify(persistent.groups))
      this.sequence = canvas.sequence || 1
      this.groupSequence = canvas.group_sequence || canvas.groupSequence || 1
      this.viewportData = { x: 0, y: 0, zoom: 1, ...(canvas.viewport || {}) }
      this.saveStatus = 'saved'
      this.ready = true
      if (this.legacyImportPending || persistent.removed) await this.saveCanvas().catch(() => {})
    },
    readLegacyCanvas() {
      try {
        return JSON.parse(localStorage.getItem('canvas'))
      } catch {
        return null
      }
    },
    canvasPayload() {
      const persistent = stripTransientNodes(this.nodes, this.edges, this.groups)
      return {
        schema_version: 1,
        nodes: persistent.nodes.map(({ id, type, position, data }) => ({ id, type, position, data })),
        edges: persistent.edges.map(({ id, source, target, sourceHandle, targetHandle, type }) => ({ id, source, target, ...(sourceHandle ? { sourceHandle } : {}), ...(targetHandle ? { targetHandle } : {}), type: type || 'cinematic' })),
        groups: persistent.groups,
        sequence: this.sequence,
        group_sequence: this.groupSequence,
        viewport: this.viewportData,
      }
    },
    async saveCanvas(viewport) {
      if (!this.workspaceId || !this.ready || this.saveConflict) return
      if (viewport) this.viewportData = { x: viewport.x, y: viewport.y, zoom: viewport.zoom }
      if (activeSave) {
        saveQueued = true
        return activeSave
      }
      activeSave = (async () => {
        do {
          saveQueued = false
          this.saveStatus = 'saving'
          const result = await saveWorkspaceCanvas(this.workspaceId, {
            ...this.canvasPayload(),
            version: this.workspaceVersion,
          })
          if (result.code !== 0) throw new Error(result.message)
          this.workspaceVersion = result.data.version
          this.saveStatus = 'saved'
        } while (saveQueued)
      })()
      try {
        await activeSave
        if (this.legacyImportPending) {
          localStorage.removeItem('canvas')
          this.legacyImportPending = false
        }
      } catch (error) {
        if (error.response?.status === 409) {
          saveQueued = false
          this.saveConflict = true
          this.saveStatus = 'conflict'
        } else {
          this.saveStatus = 'failed'
        }
        throw error
      } finally {
        activeSave = null
      }
    },
    setViewport(viewport) {
      this.viewportData = { x: viewport.x, y: viewport.y, zoom: viewport.zoom }
    },
    addNode(type, position, sourceId) {
      if (!isNodeTypeAvailable(this.workspaceType, type)) return
      const source = this.nodes.find((node) => node.id === sourceId)
      if (type === 'apparel' && !sourceId) {
        const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
        const image = this.nodes.find((node) => node.id === imageId)
        image.data = { ...image.data, title: '服饰参考图', assetSource: 'upload', resourceType: 'garment' }
        return this.addNode(type, position, imageId)
      }
      if (type === 'outfit' && !sourceId) {
        const apparelId = this.addNode('apparel', { x: position.x - 500, y: position.y - 170 })
        const modelId = this.addNode('image', { x: position.x - 500, y: position.y + 190 })
        const model = this.nodes.find((node) => node.id === modelId)
        model.data = { ...model.data, title: '模特参考图', assetSource: 'upload', resourceType: 'model' }
        const outfitId = this.addNode(type, position, apparelId)
        const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === outfitId)
        apparelEdge.targetHandle = 'apparel'
        this.edges.push(createEdge(`edge-${crypto.randomUUID()}`, modelId, outfitId, 'model'))
        this.selectNodes([outfitId])
        return outfitId
      }
      if (type === 'product' && !sourceId) {
        const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
        const image = this.nodes.find((node) => node.id === imageId)
        image.data = { ...image.data, title: '商品参考图', assetSource: 'upload' }
        return this.addNode(type, position, imageId)
      }
      if (type === 'character' && (!sourceId || source?.type === 'world')) {
        const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 210 })
        const image = this.nodes.find((node) => node.id === imageId)
        image.data = { ...image.data, title: '角色参考图', assetSource: 'upload', resourceType: 'character' }
        const characterId = this.addNode(type, position, imageId)
        if (source?.type === 'world') this.edges.push(createEdge(`edge-${crypto.randomUUID()}`, source.id, characterId, 'world'))
        this.selectNodes([characterId])
        return characterId
      }
      const incomingConnections = this.edges
        .filter((edge) => edge.target === source?.id)
        .map((edge) => ({ targetHandle: edge.targetHandle, type: this.nodes.find((node) => node.id === edge.source)?.type }))
      const targetHandle = source ? inferTargetHandle(source, type, incomingConnections) : undefined
      const connectionError = source && targetHandle
        ? getConnectionError(source.type, type, incomingConnections.map(({ type: sourceType }) => sourceType).filter(Boolean), this.workspaceType, targetHandle, incomingConnections)
        : ''
      if (sourceId && (!source || !canConnect(source.type, type, this.workspaceType) || connectionError || (type === 'apparel_storyboard' && source.type === 'image' && !targetHandle))) return
      const number = this.sequence++
      const id = `${type}-${number}`
      this.nodes.forEach((node) => { node.selected = false })
      const data = createNodeData(type, number, source)
      if (type === 'video') Object.assign(data, storyboardVideoData(source) || {})
      this.nodes.push({
        id,
        type,
        position,
        selected: true,
        data,
      })
      if (sourceId) {
        const defaultHandle = type === 'character' && source.type === 'image' ? 'reference' : targetHandle
        this.edges.push(createEdge(`edge-${crypto.randomUUID()}`, sourceId, id, defaultHandle))
      }
      return id
    },
    addEdge(connection) {
      if (this.edges.some((edge) => edge.source === connection.source && edge.target === connection.target)) return false
      const source = this.nodes.find((node) => node.id === connection.source)
      const target = this.nodes.find((node) => node.id === connection.target)
      if (!source || !target || source.id === target.id || !canConnect(source.type, target.type, this.workspaceType)) return false
      const incomingConnections = this.edges
        .filter((edge) => edge.target === target.id)
        .map((edge) => ({ targetHandle: edge.targetHandle, type: this.nodes.find((node) => node.id === edge.source)?.type }))
        .filter(({ type }) => type)
      const targetHandle = connection.targetHandle || inferTargetHandle(source, target.type, incomingConnections)
      const incomingTypes = incomingConnections.map(({ type }) => type)
      if (getConnectionError(source.type, target.type, incomingTypes, this.workspaceType, targetHandle, incomingConnections)) return false
      this.edges.push({ id: `edge-${crypto.randomUUID()}`, ...connection, ...(targetHandle ? { targetHandle } : {}), type: 'cinematic' })
      if (target.type === 'video' && !target.data.prompt?.trim()) Object.assign(target.data, storyboardVideoData(source) || {})
      return true
    },
    addProductVisualNodes(plannerId, productId, referenceId, plans, settings) {
      const planner = this.nodes.find((node) => node.id === plannerId)
      if (!planner || !plans.length) return []

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
        this.addEdge({ source: referenceId, target: id })
        this.addEdge({ source: productId, target: id })
        return id
      })
      this.selectNodes(ids.slice(0, 1))
      return ids
    },
    addProductStoryboardNodes(plannerId, productId, plans, settings) {
      const planner = this.nodes.find((node) => node.id === plannerId)
      if (!planner) return []

      if (plans?.segments?.length) {
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
            title: `${plans.title || '商品分镜'} ${segmentIndex} · 分镜`,
            storyboardSourceId: plannerId,
            storyboardTemplateId: plans.templateId,
            storyboardTemplateLabel: plans.title,
            storyboardGlobalScript: plans.globalScript,
            storyboardSegmentIndex: segmentIndex,
            storyboardSegmentCount: plans.segments.length,
            storyboardDuration: 15,
            storyboardVideoAspectRatio: planner.data.videoAspectRatio,
            storyboardShotCount: 6,
            storyboardProductReferences: planner.data.productReferences || [],
            storyboardCharacter: planner.data.characterReference || null,
            storyboardContinuityMode: segment.continuityMode,
            storyboardPlotGoal: segment.plotGoal,
            storyboardOpeningState: segment.openingState,
            storyboardEndingState: segment.endingState,
            continuityLastFrameUrl: null,
            videoPrompt: segment.videoPrompt,
            prompt: segment.prompt,
            promptParts: [{ type: 'text', value: segment.prompt }],
            segmentLocked: segmentIndex > 1,
            ...settings,
          }
          this.addEdge({ source: plannerId, target: imageId })
          this.addEdge({ source: productId, target: imageId })

          const videoId = this.addNode('video', {
            x: planner.position.x + 1010 + index * 900,
            y: planner.position.y,
          }, imageId)
          const video = this.nodes.find((node) => node.id === videoId)
          video.data = {
            ...video.data,
            title: `${plans.title || '商品分镜'} ${segmentIndex} · 视频`,
            storyboardSourceId: plannerId,
            storyboardImageId: imageId,
            storyboardTemplateId: plans.templateId,
            storyboardTemplateLabel: plans.title,
            storyboardGlobalScript: plans.globalScript,
            storyboardSegmentIndex: segmentIndex,
            storyboardSegmentCount: plans.segments.length,
            storyboardContinuityMode: segment.continuityMode,
            storyboardPlotGoal: segment.plotGoal,
            storyboardOpeningState: segment.openingState,
            storyboardEndingState: segment.endingState,
            storyboardCharacter: planner.data.characterReference || null,
            storyboardProductReferences: planner.data.productReferences || [],
            storyboardDuration: 15,
            videoPrompt: segment.videoPrompt,
            prompt: segment.videoPrompt,
            promptParts: [{ type: 'text', value: segment.videoPrompt }],
            segmentLocked: true,
            returnLastFrame: true,
          }
          if (segment.continuityMode === 'extend' && previousVideoId) {
            this.addEdge({ source: previousVideoId, target: videoId })
          }
          segmentNodeIds.push({ segmentIndex, imageId, videoId })
          previousVideoId = videoId
        })
        planner.data = {
          ...planner.data,
          globalScript: plans.globalScript,
          segmentNodeIds,
          generatedNodeIds: segmentNodeIds.flatMap(({ imageId, videoId }) => [imageId, videoId]),
        }
        this.selectNodes([segmentNodeIds[0].imageId])
        return planner.data.generatedNodeIds
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
          storyboardTemplateId: plan.id,
          storyboardTemplateLabel: plan.label,
          storyboardDuration: planner.data.duration,
          storyboardVideoAspectRatio: planner.data.videoAspectRatio,
          storyboardShotCount: storyboardShotCount(planner.data.duration),
          storyboardProductReferences: planner.data.productReferences || [],
          storyboardCharacter: planner.data.characterReference || null,
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
    addApparelStoryboardNodes(plannerId, garmentId, modelId, sceneId, plan, settings = {}) {
      const planner = this.nodes.find((node) => node.id === plannerId)
      if (!planner || !plan?.storyboardPrompt?.trim() || !plan.videoPrompt?.trim()) return []

      const imageSettings = settings.imageSettings || {
        model: 'gpt-image-2',
        aspectRatio: planner.data.videoAspectRatio,
        resolution: '2K',
      }
      const videoSettings = settings.videoSettings || {
        model: planner.data.videoModel || defaultVideoModel.id,
        duration: planner.data.duration || defaultVideoModel.defaultDuration,
        aspectRatio: planner.data.videoAspectRatio || defaultVideoModel.defaultAspectRatio,
        resolution: planner.data.videoResolution || defaultVideoModel.defaultResolution,
        generateAudio: true,
      }
      const imageId = this.addNode('image', {
        x: planner.position.x + 560,
        y: planner.position.y,
      })
      const image = this.nodes.find((node) => node.id === imageId)
      image.data = {
        ...image.data,
        title: `${plan.title || '服饰展示'} · 故事板`,
        storyboardSourceId: plannerId,
        storyboardTemplateId: plan.templateId,
        storyboardTemplateLabel: plan.title,
        storyboardDuration: plan.duration,
        storyboardVideoAspectRatio: videoSettings.aspectRatio,
        storyboardShotCount: plan.shotCount,
        storyboardReferenceOrder: ['服饰参考图', '模特参考图', '场景参考图'],
        storyboardRequiresRegistration: true,
        videoPrompt: plan.videoPrompt,
        prompt: plan.storyboardPrompt,
        promptParts: [{ type: 'text', value: plan.storyboardPrompt }],
        ...imageSettings,
      }
      this.addEdge({ source: plannerId, target: imageId })
      ;[garmentId, modelId, sceneId].filter(Boolean).forEach((source) => this.addEdge({ source, target: imageId }))

      const videoId = this.addNode('video', {
        x: planner.position.x + 980,
        y: planner.position.y,
      }, imageId)
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
        storyboardReferenceOrder: ['分镜故事板', '服饰参考图', '模特参考图', '场景参考图'],
        videoPrompt: plan.videoPrompt,
        prompt: plan.videoPrompt,
        promptParts: [{ type: 'text', value: plan.videoPrompt }],
        ...videoSettings,
      }
      ;[garmentId, modelId, sceneId].filter(Boolean).forEach((source) => this.addEdge({ source, target: videoId }))

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
    addOutfitStoryboardNodes(plannerId, outfitId, plans, settings) {
      const planner = this.nodes.find((node) => node.id === plannerId)
      if (!planner || !plans?.segments?.length) return []
      const outfit = this.nodes.find((node) => node.id === outfitId)
      const board = outfit?.data.outfitBoardAsset ? { url: outfit.data.outfitBoardAsset, assetId: outfit.data.outfitBoardAssetId || null } : null

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
          storyboardTemplateLabel: plans.title,
          storyboardGlobalScript: plans.globalScript,
          storyboardSegmentIndex: segmentIndex,
          storyboardSegmentCount: plans.segments.length,
          storyboardDuration: 15,
          storyboardVideoAspectRatio: planner.data.videoAspectRatio,
          storyboardShotCount: 6,
          storyboardOutfitBoard: board,
          storyboardRequiresRegistration: true,
          storyboardContinuityMode: segment.continuityMode,
          storyboardPlotGoal: segment.plotGoal,
          storyboardOpeningState: segment.openingState,
          storyboardEndingState: segment.endingState,
          continuityLastFrameUrl: null,
          videoPrompt: segment.videoPrompt,
          prompt: segment.prompt,
          promptParts: [{ type: 'text', value: segment.prompt }],
          segmentLocked: segmentIndex > 1,
          ...settings,
        }
        this.addEdge({ source: plannerId, target: imageId })
        this.addEdge({ source: outfitId, target: imageId })

        const videoId = this.addNode('video', {
          x: planner.position.x + 1010 + index * 900,
          y: planner.position.y,
        }, imageId)
        const video = this.nodes.find((node) => node.id === videoId)
        video.data = {
          ...video.data,
          title: `${plans.title || '服饰分镜'} ${segmentIndex} · 视频`,
          storyboardSourceId: plannerId,
          storyboardImageId: imageId,
          storyboardTemplateId: plans.templateId,
          storyboardTemplateLabel: plans.title,
          storyboardGlobalScript: plans.globalScript,
          storyboardSegmentIndex: segmentIndex,
          storyboardSegmentCount: plans.segments.length,
          storyboardContinuityMode: segment.continuityMode,
          storyboardPlotGoal: segment.plotGoal,
          storyboardOpeningState: segment.openingState,
          storyboardEndingState: segment.endingState,
          storyboardOutfitBoard: board,
          storyboardRequiresRegistration: true,
          storyboardDuration: 15,
          videoPrompt: segment.videoPrompt,
          prompt: segment.videoPrompt,
          promptParts: [{ type: 'text', value: segment.videoPrompt }],
          segmentLocked: true,
          returnLastFrame: true,
        }
        if (segment.continuityMode === 'extend' && previousVideoId) this.addEdge({ source: previousVideoId, target: videoId })
        segmentNodeIds.push({ segmentIndex, imageId, videoId })
        previousVideoId = videoId
      })
      planner.data = {
        ...planner.data,
        storyboardOutfitBoard: board,
        globalScript: plans.globalScript,
        segmentNodeIds,
        generatedNodeIds: segmentNodeIds.flatMap(({ imageId, videoId }) => [imageId, videoId]),
      }
      this.selectNodes([segmentNodeIds[0].imageId])
      return planner.data.generatedNodeIds
    },
    addStoryboardVideoNode(imageId) {
      const image = this.nodes.find((node) => node.id === imageId && node.type === 'image')
      if (!image?.data.asset || !image.data.videoPrompt?.trim()) return
      const existing = this.nodes.find((node) => node.type === 'video' && node.data.storyboardImageId === imageId)
      if (existing) {
        Object.assign(existing.data, storyboardVideoData(image))
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
    addOutfitVisualNodes(outfitId, garmentId, modelId, plans, settings) {
      const outfit = this.nodes.find((node) => node.id === outfitId)
      if (!outfit || !plans.length) return []

      const columns = Math.min(3, plans.length)
      const ids = plans.map((plan, index) => {
        const id = this.addNode('image', {
          x: outfit.position.x + 500 + (index % columns) * 440,
          y: outfit.position.y + Math.floor(index / columns) * 340,
        })
        const node = this.nodes.find((item) => item.id === id)
        node.data = {
          ...node.data,
          title: plan.label,
          outfitSourceId: outfitId,
          outfitMaterialId: plan.id,
          outfitMaterialCategory: plan.category,
          outfitMaterialCategoryLabel: plan.categoryLabel,
          resourceType: 'outfit-material',
          prompt: plan.prompt,
          promptParts: [{ type: 'text', value: plan.prompt }],
          ...settings,
        }
        this.addEdge({ source: outfitId, target: id })
        this.addEdge({ source: garmentId, target: id })
        this.addEdge({ source: modelId, target: id })
        return id
      })
      this.selectNodes(ids.slice(0, 1))
      return ids
    },
    addCharacterVisualNodes(characterId, referenceId, plans, settings) {
      const character = this.nodes.find((node) => node.id === characterId)
      if (!character || !plans.length) return []

      const ids = plans.map((plan, index) => {
        const id = this.addNode('image', { x: character.position.x + 500 + index * 440, y: character.position.y })
        const node = this.nodes.find((item) => item.id === id)
        node.data = {
          ...node.data,
          title: plan.label,
          characterSourceId: characterId,
          prompt: plan.prompt,
          promptParts: [{ type: 'text', value: plan.prompt }],
          ...settings,
        }
        this.addEdge({ source: characterId, target: id })
        if (referenceId) this.addEdge({ source: referenceId, target: id })
        return id
      })
      this.selectNodes(ids.slice(0, 1))
      return ids
    },
    addAssetNode(asset, position) {
      const id = this.addNode(asset.media_type, position)
      const node = this.nodes.find((item) => item.id === id)
      if (!node) return
      node.data = {
        ...node.data,
        title: asset.name,
        status: 'ready',
        asset: asset.url,
        assetId: asset.id,
        assetSource: 'library',
        sourceWidth: asset.width,
        sourceHeight: asset.height,
        sourceAspectRatio: asset.width && asset.height ? asset.width / asset.height : null,
        sourceByteSize: asset.byte_size,
        ...(asset.duration ? { sourceDuration: asset.duration } : {}),
      }
      return id
    },
    setTextMode(id, mode) {
      const node = this.nodes.find((item) => item.id === id)
      if (!node || node.data.textMode) return
      if (mode === 'manual') {
        node.data = { ...node.data, textMode: 'manual', status: 'ready' }
        return
      }
      const mediaType = mode === 'videoReverse' ? 'video' : 'image'
      const mediaId = this.addNode(mediaType, { x: node.position.x - 460, y: node.position.y + 3 })
      const media = this.nodes.find((item) => item.id === mediaId)
      const mediaLabel = getNodeDefinition(mediaType).label
      media.data = { ...media.data, title: `参考${mediaLabel}`, assetSource: 'upload' }
      node.data = { ...node.data, textMode: 'task', title: `${mediaLabel}反推提示词`, model: defaultReverseModel.id, prompt: getReversePrompt(mediaType), reverseType: mediaType }
      this.edges.push(createEdge(`edge-${crypto.randomUUID()}`, mediaId, id))
      this.selectNodes([id])
    },
    deleteEdge(id) {
      this.edges = this.edges.filter((edge) => edge.id !== id)
    },
    selectNodes(nodeIds) {
      this.nodes.forEach((node) => { node.selected = nodeIds.includes(node.id) })
    },
    unlockStoryboardVideo(imageId) {
      const video = this.nodes.find((node) => node.type === 'video' && node.data.storyboardImageId === imageId)
      if (video) video.data.segmentLocked = false
    },
    setStoryboardContinuityMode(videoId, mode) {
      const video = this.nodes.find((node) => node.id === videoId && node.type === 'video')
      if (!video?.data.storyboardSegmentIndex) return false
      const segmentIndex = video.data.storyboardSegmentIndex
      const sourceId = video.data.storyboardSourceId
      const previous = this.nodes.find((node) => node.type === 'video' && node.data.storyboardSourceId === sourceId && node.data.storyboardSegmentIndex === segmentIndex - 1)
      const nextMode = segmentIndex === 1 ? 'cut' : mode === 'extend' ? 'extend' : 'cut'
      video.data.storyboardContinuityMode = nextMode
      const image = this.nodes.find((node) => node.id === video.data.storyboardImageId)
      if (image) image.data.storyboardContinuityMode = nextMode
      this.edges = this.edges.filter((edge) => !(edge.target === videoId && this.nodes.find((node) => node.id === edge.source)?.type === 'video'))
      if (nextMode === 'extend' && previous) this.addEdge({ source: previous.id, target: videoId })
      return true
    },
    confirmStoryboardSegment(videoId) {
      const video = this.nodes.find((node) => node.id === videoId && node.type === 'video')
      if (!video) return 'not_found'
      if (video.data.status !== 'ready' || !video.data.storyboardSegmentIndex) return 'not_ready'
      const nextImage = this.nodes.find((node) => node.type === 'image'
        && node.data.storyboardSourceId === video.data.storyboardSourceId
        && node.data.storyboardSegmentIndex === video.data.storyboardSegmentIndex + 1)
      if (!nextImage) return true
      const nextMode = nextImage.data.storyboardContinuityMode
      if (nextMode === 'extend' && !video.data.lastFrameUrl) return 'missing_last_frame'
      nextImage.data.continuityLastFrameUrl = nextMode === 'extend' ? video.data.lastFrameUrl : null
      nextImage.data.segmentLocked = false
      video.data.segmentConfirmed = true
      return true
    },
    invalidateStoryboardFrom(nodeId) {
      const target = this.nodes.find((node) => node.id === nodeId)
      const segmentIndex = target?.data.storyboardSegmentIndex
      const sourceId = target?.data.storyboardSourceId
      if (!segmentIndex || !sourceId) return
      this.nodes
        .filter((node) => node.data.storyboardSourceId === sourceId && node.data.storyboardSegmentIndex >= segmentIndex)
        .forEach((node) => {
          const history = node.data.storyboardHistory || []
          if (node.data.asset) history.push({ asset: node.data.asset, assetId: node.data.assetId || null, status: node.data.status, savedAt: new Date().toISOString() })
          node.data.storyboardHistory = history.slice(-5)
          const isTargetVideo = node.id === nodeId && node.type === 'video'
          const keepCurrentImage = node.data.storyboardSegmentIndex === segmentIndex && node.type === 'image' && target.type === 'video'
          if (!keepCurrentImage) {
            node.data.asset = ''
            node.data.assetId = null
            node.data.lastFrameUrl = null
            node.data.status = 'empty'
          }
          node.data.generationTaskId = null
          node.data.generationStatus = ''
          node.data.generationProgress = 0
          node.data.generationError = ''
          node.data.segmentConfirmed = false
          node.data.continuityLastFrameUrl = null
          node.data.segmentLocked = node.type === 'image'
            ? node.data.storyboardSegmentIndex > segmentIndex
            : !(isTargetVideo || (node.data.storyboardSegmentIndex === segmentIndex && keepCurrentImage))
        })
      this.nodes
        .filter((node) => node.data.storyboardSourceId === sourceId && node.data.storyboardSegmentIndex === segmentIndex)
        .filter((node) => node.type === 'video' && target.type === 'image')
        .forEach((node) => { node.data.segmentLocked = true })
    },
    groupSelected() {
      const selectedIds = this.nodes.filter((node) => node.selected).map((node) => node.id)
      if (selectedIds.length < 2) return
      const touched = this.groups.filter((group) => group.nodeIds.some((id) => selectedIds.includes(id)))
      const mergedIds = new Set([...selectedIds, ...touched.flatMap((group) => group.nodeIds)])
      const nodeIds = this.nodes.filter((node) => mergedIds.has(node.id)).map((node) => node.id)
      this.groups = this.groups.filter((group) => !touched.includes(group))
      if (touched.length) {
        this.groups.push({ ...touched[0], nodeIds })
        return
      }
      while (this.groups.some((group) => group.title === `编组 ${this.groupSequence}`)) this.groupSequence += 1
      this.groups.push({ id: `group-${crypto.randomUUID()}`, title: `编组 ${this.groupSequence++}`, nodeIds })
    },
    renameGroup(id, title) {
      const group = this.groups.find((item) => item.id === id)
      if (group) group.title = title.trim() || group.title
    },
    ungroupNode(nodeId) {
      const group = this.groups.find((item) => item.nodeIds.includes(nodeId))
      if (!group) return
      this.groups = this.groups.filter((item) => item.id !== group.id)
    },
    removeNodesFromGroup(groupId, nodeIds) {
      const group = this.groups.find((item) => item.id === groupId)
      if (!group) return
      const removedIds = new Set(nodeIds)
      group.nodeIds = group.nodeIds.filter((id) => !removedIds.has(id))
      if (group.nodeIds.length < 2) this.groups = this.groups.filter((item) => item.id !== groupId)
    },
    duplicateNodes(nodeIds, positions = {}) {
      const sourceIds = new Set(nodeIds)
      const sources = this.nodes.filter((node) => sourceIds.has(node.id))
      if (!sources.length) return []
      const idMap = new Map()
      this.nodes.forEach((node) => { node.selected = false })
      const copies = sources.map((source) => {
        const id = `${source.type}-${this.sequence++}`
        idMap.set(source.id, id)
        return {
          id,
          type: source.type,
          position: positions[source.id] || { x: source.position.x + 56, y: source.position.y + 56 },
          selected: true,
          data: { ...JSON.parse(JSON.stringify(source.data)), title: `${source.data.title || getNodeDefinition(source.type).label} 副本` },
        }
      })
      this.nodes.push(...copies)
      this.edges.push(...this.edges
        .filter((edge) => sourceIds.has(edge.source) && sourceIds.has(edge.target))
        .map((edge) => ({ ...edge, id: `edge-${crypto.randomUUID()}`, source: idMap.get(edge.source), target: idMap.get(edge.target) })))
      this.groups
        .map((group) => ({ title: `${group.title} 副本`, nodeIds: group.nodeIds.filter((id) => sourceIds.has(id)).map((id) => idMap.get(id)) }))
        .filter((group) => group.nodeIds.length > 1)
        .forEach((group) => this.groups.push({ id: `group-${crypto.randomUUID()}`, ...group }))
      return copies.map((copy) => copy.id)
    },
    duplicateSelected() {
      return this.duplicateNodes(this.nodes.filter((node) => node.selected).map((node) => node.id))
    },
    duplicateWithInputs(id) {
      const copyId = this.duplicateNodes([id])[0]
      if (!copyId) return
      this.edges.push(...this.edges
        .filter((edge) => edge.target === id)
        .map((edge) => ({ ...edge, id: `edge-${crypto.randomUUID()}`, target: copyId })))
      return copyId
    },
    renameNode(id, title) {
      const node = this.nodes.find((item) => item.id === id)
      if (node && title.trim()) node.data.title = title.trim()
    },
    deleteNodes(nodeIds) {
      const removedIds = new Set(nodeIds)
      this.nodes = this.nodes.filter((node) => !removedIds.has(node.id))
      this.edges = this.edges.filter((edge) => !removedIds.has(edge.source) && !removedIds.has(edge.target))
      this.groups = this.groups
        .map((group) => ({ ...group, nodeIds: group.nodeIds.filter((nodeId) => !removedIds.has(nodeId)) }))
        .filter((group) => group.nodeIds.length > 1)
    },
    deleteNode(id) {
      this.deleteNodes([id])
    },
    deleteGroup(id) {
      const group = this.groups.find((item) => item.id === id)
      if (!group) return
      const nodeIds = new Set(group.nodeIds)
      this.nodes = this.nodes.filter((node) => !nodeIds.has(node.id))
      this.edges = this.edges.filter((edge) => !nodeIds.has(edge.source) && !nodeIds.has(edge.target))
      this.groups = this.groups.filter((item) => item.id !== id)
    },
  },
})
