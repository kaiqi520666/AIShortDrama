import { defineStore } from 'pinia'
import { canConnect } from '../config/connectionRules'
import { defaultImageModel } from '../config/imageModels'
import { mediaTypes } from '../config/mediaTypes'
import { defaultReverseModel } from '../config/reverseModels'
import { defaultVideoModel } from '../config/videoModels'
import { saveWorkspaceCanvas } from '../api/workspaces'

const createEdge = (id, source, target) => ({ id, source, target, type: 'cinematic' })
const reversePrompts = {
  image: '根据图片生成结构化中文提示词，包括主体描述、环境、光影、镜头语言、风格关键词。',
  video: '根据视频生成结构化中文提示词，包括主体与场景、动作、运镜、景别、光影色彩、节奏转场、声音氛围和风格关键词，并按时间顺序描述关键画面。',
}
const defaultWorkspaceId = '00000000-0000-0000-0000-000000000101'
let activeSave = null
let saveQueued = false

function createNodeData(type, number, source) {
  const textTask = type === 'text' && Boolean(source)
  const reverseType = type === 'text' && ['image', 'video'].includes(source?.type) ? source.type : null
  return {
    model: reverseType ? defaultReverseModel.id : textTask ? 'Qwen3-VL-Flash' : type === 'image' ? defaultImageModel.id : type === 'video' ? defaultVideoModel.id : mediaTypes[type].model,
    title: reverseType ? `${mediaTypes[reverseType].label}反推提示词` : textTask ? `AI 文本任务 ${number}` : `${mediaTypes[type].label}节点 ${number}`,
    status: 'empty',
    prompt: reverseType ? reversePrompts[reverseType] : '',
    ...(type === 'text' ? { textMode: textTask ? 'task' : null, content: '', ...(reverseType ? { reverseType } : {}) } : {}),
  }
}

export const useCanvasStore = defineStore('canvas', {
  state: () => ({
    workspaceId: null,
    nodes: [],
    edges: [],
    sequence: 1,
    groupSequence: 1,
    groups: [],
    viewportData: { x: 0, y: 0, zoom: 1 },
    saveStatus: 'saved',
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
      let canvas = workspace.canvas || {}
      const legacy = this.readLegacyCanvas()
      if (workspace.id === defaultWorkspaceId && !canvas.nodes?.length && legacy?.nodes?.length) {
        canvas = legacy
        this.legacyImportPending = true
      }
      this.nodes = JSON.parse(JSON.stringify(canvas.nodes || []))
      this.edges = JSON.parse(JSON.stringify(canvas.edges || []))
      this.groups = JSON.parse(JSON.stringify(canvas.groups || []))
      this.sequence = canvas.sequence || 1
      this.groupSequence = canvas.group_sequence || canvas.groupSequence || 1
      this.viewportData = { x: 0, y: 0, zoom: 1, ...(canvas.viewport || {}) }
      this.saveStatus = 'saved'
      this.ready = true
      if (this.legacyImportPending) await this.saveCanvas().catch(() => {})
    },
    readLegacyCanvas() {
      try {
        return JSON.parse(localStorage.getItem('canvas'))
      } catch {
        return null
      }
    },
    canvasPayload() {
      return {
        schema_version: 1,
        nodes: this.nodes.map(({ id, type, position, data }) => ({ id, type, position, data })),
        edges: this.edges.map(({ id, source, target, sourceHandle, targetHandle, type }) => ({ id, source, target, ...(sourceHandle ? { sourceHandle } : {}), ...(targetHandle ? { targetHandle } : {}), type: type || 'cinematic' })),
        groups: this.groups,
        sequence: this.sequence,
        group_sequence: this.groupSequence,
        viewport: this.viewportData,
      }
    },
    async saveCanvas(viewport) {
      if (!this.workspaceId || !this.ready) return
      if (viewport) this.viewportData = { x: viewport.x, y: viewport.y, zoom: viewport.zoom }
      if (activeSave) {
        saveQueued = true
        return activeSave
      }
      activeSave = (async () => {
        do {
          saveQueued = false
          this.saveStatus = 'saving'
          const result = await saveWorkspaceCanvas(this.workspaceId, this.canvasPayload())
          if (result.code !== 0) throw new Error(result.message)
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
        this.saveStatus = 'failed'
        throw error
      } finally {
        activeSave = null
      }
    },
    setViewport(viewport) {
      this.viewportData = { x: viewport.x, y: viewport.y, zoom: viewport.zoom }
    },
    addNode(type, position, sourceId) {
      const source = this.nodes.find((node) => node.id === sourceId)
      if (sourceId && (!source || !canConnect(source.type, type))) return
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
      if (this.edges.some((edge) => edge.source === connection.source && edge.target === connection.target)) return
      const source = this.nodes.find((node) => node.id === connection.source)
      const target = this.nodes.find((node) => node.id === connection.target)
      if (!source || !target || source.id === target.id || !canConnect(source.type, target.type)) return
      this.edges.push({ id: `edge-${crypto.randomUUID()}`, ...connection, type: 'cinematic' })
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
      media.data = { ...media.data, title: `参考${mediaTypes[mediaType].label}`, assetSource: 'upload' }
      node.data = { ...node.data, textMode: 'task', title: `${mediaTypes[mediaType].label}反推提示词`, model: defaultReverseModel.id, prompt: reversePrompts[mediaType], reverseType: mediaType }
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
      const nodeIds = this.nodes.filter((node) => node.selected).map((node) => node.id)
      if (nodeIds.length < 2) return
      this.groups = this.groups.filter((group) => !group.nodeIds.some((id) => nodeIds.includes(id)))
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
    duplicateNode(id) {
      const source = this.nodes.find((node) => node.id === id)
      if (!source) return
      const copyId = this.addNode(source.type, { x: source.position.x + 56, y: source.position.y + 56 })
      const copy = this.nodes.find((node) => node.id === copyId)
      copy.data = { ...source.data, title: `${source.data.title} 副本` }
    },
    deleteNode(id) {
      this.nodes = this.nodes.filter((node) => node.id !== id)
      this.edges = this.edges.filter((edge) => edge.source !== id && edge.target !== id)
      this.groups = this.groups
        .map((group) => ({ ...group, nodeIds: group.nodeIds.filter((nodeId) => nodeId !== id) }))
        .filter((group) => group.nodeIds.length > 1)
    },
  },
})
