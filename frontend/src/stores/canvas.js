import { defineStore } from 'pinia'
import { mediaTypes } from '../config/mediaTypes'
import { demoEdges, demoNodes } from '../data/demoCanvas'

const createEdge = (id, source, target) => ({ id, source, target, type: 'cinematic' })

export const useCanvasStore = defineStore('canvas', {
  persist: { pick: ['nodes', 'edges', 'sequence', 'groups', 'groupSequence'] },
  state: () => ({
    nodes: demoNodes.map((node) => ({ ...node, data: { model: mediaTypes[node.type].model, ...node.data } })),
    edges: demoEdges.map((edge) => ({ ...edge })),
    sequence: 6,
    groupSequence: 1,
    groups: [],
  }),
  getters: {
    incomingNodes: (state) => (nodeId) =>
      state.edges
        .filter((edge) => edge.target === nodeId)
        .map((edge) => state.nodes.find((node) => node.id === edge.source))
        .filter(Boolean),
  },
  actions: {
    addNode(type, position, sourceId) {
      const number = this.sequence++
      const id = `${type}-${number}`
      this.nodes.forEach((node) => { node.selected = false })
      this.nodes.push({
        id,
        type,
        position,
        selected: true,
        data: {
          model: mediaTypes[type].model,
          title: `${mediaTypes[type].label}节点 ${number}`,
          status: 'empty',
          prompt: '',
        },
      })
      if (sourceId) this.edges.push(createEdge(`edge-${crypto.randomUUID()}`, sourceId, id))
      return id
    },
    addEdge(connection) {
      if (this.edges.some((edge) => edge.source === connection.source && edge.target === connection.target)) return
      this.edges.push({ id: `edge-${crypto.randomUUID()}`, ...connection, type: 'cinematic' })
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
