import { computed, nextTick, ref } from 'vue'

export function useCanvasHistory({ store, activeGroupId, contextMenu, delay = 200, eventTarget = globalThis }) {
  let history = []
  const historyIndex = ref(-1)
  let timer = null
  let applying = false

  function snapshot() {
    const payload = store.canvasPayload()
    return JSON.stringify({ nodes: payload.nodes, edges: payload.edges, groups: payload.groups })
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
    if (applying) return
    commit()
    if (historyIndex.value <= 0) return
    restore(history[--historyIndex.value])
  }

  function redo() {
    if (applying) return
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
    canUndo: computed(() => historyIndex.value > 0),
    canRedo: computed(() => historyIndex.value < history.length - 1),
    snapshot,
    commit,
    schedule,
    undo,
    redo,
    initialize,
    dispose,
  }
}
