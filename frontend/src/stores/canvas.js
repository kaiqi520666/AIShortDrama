import { defineStore } from 'pinia'
import { canConnect, getConnectionError, inferTargetHandle } from '../config/canvas/connectionRules'
import { createNodeData, getNodeDefinition, getReversePrompt } from '../config/canvas/nodeDefinitions'
import { isNodeTypeAvailable } from '../config/canvas/nodePacks'
import { CURRENT_CANVAS_SCHEMA_VERSION, migrateCanvas } from '../config/canvas/migrations'
import { defaultReverseModel } from '../config/reverseModels'
import { saveWorkspaceCanvas } from '../api/workspaces'
import {
  canvasBusinessActions,
  createBusinessNodeChain,
  createCanvasEdge,
  storyboardVideoData,
} from './canvasBusinessActions'

const defaultWorkspaceId = '00000000-0000-0000-0000-000000000101'
const saveQueues = new Map()

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
      canvas = migrateCanvas(canvas)
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
        schema_version: CURRENT_CANVAS_SCHEMA_VERSION,
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
      const workspaceId = this.workspaceId
      const existing = saveQueues.get(workspaceId)
      if (existing) {
        existing.payload = this.canvasPayload()
        existing.queued = true
        return existing.promise
      }
      const context = {
        payload: this.canvasPayload(),
        version: this.workspaceVersion,
        queued: false,
        promise: null,
      }
      context.promise = (async () => {
        do {
          context.queued = false
          if (this.workspaceId === workspaceId) this.saveStatus = 'saving'
          const result = await saveWorkspaceCanvas(workspaceId, {
            ...context.payload,
            version: context.version,
          })
          if (result.code !== 0) throw new Error(result.message)
          context.version = result.data.version
          if (this.workspaceId === workspaceId) {
            this.workspaceVersion = context.version
            this.saveStatus = 'saved'
          }
        } while (context.queued)
      })()
      saveQueues.set(workspaceId, context)
      try {
        await context.promise
        if (this.workspaceId === workspaceId && this.legacyImportPending) {
          localStorage.removeItem('canvas')
          this.legacyImportPending = false
        }
      } catch (error) {
        if (this.workspaceId === workspaceId && error.response?.status === 409) {
          context.queued = false
          this.saveConflict = true
          this.saveStatus = 'conflict'
        } else if (this.workspaceId === workspaceId) {
          this.saveStatus = 'failed'
        }
        throw error
      } finally {
        if (saveQueues.get(workspaceId) === context) saveQueues.delete(workspaceId)
      }
    },
    setViewport(viewport) {
      this.viewportData = { x: viewport.x, y: viewport.y, zoom: viewport.zoom }
    },
    addNode(type, position, sourceId, skipStoryboardInputs = false) {
      if (!isNodeTypeAvailable(this.workspaceType, type)) return
      const businessChain = createBusinessNodeChain.call(
        this,
        type,
        position,
        sourceId,
        skipStoryboardInputs,
      )
      if (businessChain.handled) return businessChain.id
      const source = this.nodes.find((node) => node.id === sourceId)
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
        this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, sourceId, id, defaultHandle))
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
    addProductVisualNodes(...args) {
      return canvasBusinessActions.addProductVisualNodes.apply(this, args)
    },
    addProductStoryboardNodes(...args) {
      return canvasBusinessActions.addProductStoryboardNodes.apply(this, args)
    },
    syncProductStoryboardReferences(...args) {
      return canvasBusinessActions.syncProductStoryboardReferences.apply(this, args)
    },
    addApparelStoryboardNodes(...args) {
      return canvasBusinessActions.addApparelStoryboardNodes.apply(this, args)
    },
    addOutfitStoryboardNodes(...args) {
      return canvasBusinessActions.addOutfitStoryboardNodes.apply(this, args)
    },
    addStoryboardVideoNode(...args) {
      return canvasBusinessActions.addStoryboardVideoNode.apply(this, args)
    },
    addOutfitVisualNodes(...args) {
      return canvasBusinessActions.addOutfitVisualNodes.apply(this, args)
    },
    addCharacterVisualNodes(...args) {
      return canvasBusinessActions.addCharacterVisualNodes.apply(this, args)
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
      if (mode !== 'imageReverse') return
      const mediaType = 'image'
      const mediaId = this.addNode(mediaType, { x: node.position.x - 460, y: node.position.y + 3 })
      const media = this.nodes.find((item) => item.id === mediaId)
      const mediaLabel = getNodeDefinition(mediaType).label
      media.data = { ...media.data, title: `参考${mediaLabel}`, assetSource: 'upload' }
      node.data = { ...node.data, textMode: 'task', title: `${mediaLabel}反推提示词`, model: defaultReverseModel.id, prompt: getReversePrompt(mediaType), reverseType: mediaType }
      this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, mediaId, id))
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
