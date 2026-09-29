import { computed, nextTick, ref } from 'vue'

const generationRuntimeFields = [
  'generationTaskId',
  'generationStatus',
  'generationProgress',
  'generationPollingPaused',
  'generationError',
]

function hasMeaningfulValue(value) {
  if (typeof value === 'string') return Boolean(value.trim())
  if (Array.isArray(value)) return value.some(hasMeaningfulValue)
  if (value && typeof value === 'object') return Object.values(value).some(hasMeaningfulValue)
  return false
}

function stabilizeGeneratingData(data) {
  const stable = { ...data }
  stable.status = ['asset', 'content', 'product', 'items', 'generatedNodeIds']
    .some((key) => hasMeaningfulValue(stable[key])) ? 'ready' : 'empty'
  generationRuntimeFields.forEach((field) => { delete stable[field] })
  return stable
}

export function useCanvasHistory({ store, activeGroupId, contextMenu, delay = 200, eventTarget = globalThis }) {
  let history = []
  const historyIndex = ref(-1)
  let timer = null
  let applying = false

  function snapshot() {
    const payload = store.canvasPayload()
    const previous = history[historyIndex.value] ? JSON.parse(history[historyIndex.value]) : null
    const previousNodes = new Map((previous?.nodes || []).map((node) => [node.id, node]))
    const skippedNodeIds = new Set()
    const nodes = payload.nodes.flatMap((node) => {
      if (node.data?.status !== 'generating') return [node]
      const previousNode = previousNodes.get(node.id)
      if (previousNode) return [{ ...node, data: previousNode.data }]
      if (!previous) return [{ ...node, data: stabilizeGeneratingData(node.data) }]
      skippedNodeIds.add(node.id)
      return []
    })
    const edges = payload.edges.filter((edge) => (
      !skippedNodeIds.has(edge.source) && !skippedNodeIds.has(edge.target)
    ))
    const groups = payload.groups
      .map((group) => ({
        ...group,
        nodeIds: group.nodeIds.filter((nodeId) => !skippedNodeIds.has(nodeId)),
      }))
      .filter((group) => group.nodeIds.length > 1)
    return JSON.stringify({ nodes, edges, groups })
  }

  function generationRunning() {
    return store.nodes.some((node) => node.data?.status === 'generating')
  }

  function commit() {
    eventTarget?.clearTimeout(timer)
    timer = null
    if (applying || !store.ready) return
    const value = snapshot()
    if (value === history[historyIndex.value]) return
    history = [...history.slice(0, historyIndex.value + 1), value].slice(-50)
    historyIndex.value = history.length - 1
  }

  function schedule() {
    if (applying || !store.ready) return
    eventTarget?.clearTimeout(timer)
    timer = eventTarget?.setTimeout(commit, delay) ?? null
  }

  function restore(value) {
    applying = true
    const state = JSON.parse(value)
    store.nodes = state.nodes
    store.edges = state.edges
    store.groups = state.groups
    activeGroupId.value = null
    contextMenu.value = null
    nextTick(() => { applying = false })
  }

  function undo() {
    if (applying || generationRunning()) return
    commit()
    if (historyIndex.value <= 0) return
    restore(history[--historyIndex.value])
  }

  function redo() {
    if (applying || generationRunning()) return
    commit()
    if (historyIndex.value >= history.length - 1) return
    restore(history[++historyIndex.value])
  }

  function initialize() {
    eventTarget?.clearTimeout(timer)
    timer = null
    history = [snapshot()]
    historyIndex.value = 0
  }

  function dispose() {
    eventTarget?.clearTimeout(timer)
    timer = null
  }

  return {
    canUndo: computed(() => !generationRunning() && historyIndex.value > 0),
    canRedo: computed(() => !generationRunning() && historyIndex.value < history.length - 1),
    snapshot,
    commit,
    schedule,
    undo,
    redo,
    initialize,
    dispose,
  }
}
