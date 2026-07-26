import { defineStore } from 'pinia'
import { canConnect, getConnectionError } from '../config/canvas/connectionRules'
import { createNodeData, getNodeDefinition, getReversePrompt } from '../config/canvas/nodeDefinitions'
import { isNodeTypeAvailable } from '../config/canvas/nodePacks'
import { defaultReverseModel } from '../config/reverseModels'
import { saveWorkspaceCanvas } from '../api/workspaces'

const createEdge = (id, source, target, targetHandle) => ({ id, source, target, ...(targetHandle ? { targetHandle } : {}), type: 'cinematic' })
const defaultWorkspaceId = '00000000-0000-0000-0000-000000000101'
let activeSave = null
let saveQueued = false

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
      if (type === 'outfit' && !sourceId) {
        const garmentId = this.addNode('image', { x: position.x - 460, y: position.y - 215 })
        const modelId = this.addNode('image', { x: position.x - 460, y: position.y + 215 })
        const garment = this.nodes.find((node) => node.id === garmentId)
        const model = this.nodes.find((node) => node.id === modelId)
        garment.data = { ...garment.data, title: '服饰参考图', assetSource: 'upload' }
        model.data = { ...model.data, title: '模特参考图', assetSource: 'upload', resourceType: 'model' }
        const outfitId = this.addNode(type, position, garmentId)
        const garmentEdge = this.edges.find((edge) => edge.source === garmentId && edge.target === outfitId)
        garmentEdge.targetHandle = 'garment'
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
      const source = this.nodes.find((node) => node.id === sourceId)
      if (sourceId && (!source || !canConnect(source.type, type, this.workspaceType))) return
      const number = this.sequence++
      const id = `${type}-${number}`
      this.nodes.forEach((node) => { node.selected = false })
      this.nodes.push({
        id,
        type,
        position,
        selected: true,
        data: createNodeData(type, number, source),
      })
      if (sourceId) this.edges.push(createEdge(`edge-${crypto.randomUUID()}`, sourceId, id))
      return id
    },
    addEdge(connection) {
      if (this.edges.some((edge) => edge.source === connection.source && edge.target === connection.target)) return false
      const source = this.nodes.find((node) => node.id === connection.source)
      const target = this.nodes.find((node) => node.id === connection.target)
      if (!source || !target || source.id === target.id || !canConnect(source.type, target.type, this.workspaceType)) return false
      const incomingTypes = this.edges
        .filter((edge) => edge.target === target.id)
        .map((edge) => this.nodes.find((node) => node.id === edge.source)?.type)
        .filter(Boolean)
      if (getConnectionError(source.type, target.type, incomingTypes, this.workspaceType)) return false
      this.edges.push({ id: `edge-${crypto.randomUUID()}`, ...connection, type: 'cinematic' })
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
    addOutfitResultNode(outfitId, garmentId, modelId, prompt, settings) {
      const outfit = this.nodes.find((node) => node.id === outfitId)
      if (!outfit) return
      const resultNumber = this.nodes.filter((node) => node.data.outfitSourceId === outfitId).length + 1
      const resultIndex = resultNumber - 1
      const id = this.addNode('image', {
        x: outfit.position.x + 500 + (resultIndex % 3) * 440,
        y: outfit.position.y + Math.floor(resultIndex / 3) * 340,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: `穿搭效果图 ${resultNumber}`,
        outfitSourceId: outfitId,
        status: 'generating',
        generationProgress: 0,
        prompt,
        promptParts: [{ type: 'text', value: prompt }],
        ...settings,
      }
      this.addEdge({ source: outfitId, target: id })
      this.addEdge({ source: garmentId, target: id })
      this.addEdge({ source: modelId, target: id })
      this.selectNodes([outfitId])
      return id
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
