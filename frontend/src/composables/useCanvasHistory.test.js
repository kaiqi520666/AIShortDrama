import { describe, expect, it, vi } from 'vitest'
import { nextTick, reactive, ref } from 'vue'
import { useCanvasHistory } from './useCanvasHistory'

function setup() {
  const store = reactive({
    ready: true,
    nodes: [{ id: 'node-1', data: { value: 1 } }],
    edges: [],
    groups: [],
    canvasPayload() {
      return { nodes: this.nodes, edges: this.edges, groups: this.groups }
    },
  })
  const activeGroupId = ref('group-1')
  const contextMenu = ref({ kind: 'node' })
  return { store, activeGroupId, contextMenu }
}

describe('canvas history', () => {
  it('restores undo and redo snapshots while clearing transient selection UI', async () => {
    vi.useFakeTimers()
    const state = setup()
    const history = useCanvasHistory({ ...state, delay: 20 })
    history.initialize()
    state.store.nodes[0].data.value = 2
    history.schedule()
    await vi.advanceTimersByTimeAsync(20)

    expect(history.canUndo.value).toBe(true)
    history.undo()
    await nextTick()
    expect(state.store.nodes[0].data.value).toBe(1)
    expect(state.activeGroupId.value).toBe(null)
    expect(state.contextMenu.value).toBe(null)

    history.redo()
    await nextTick()
    expect(state.store.nodes[0].data.value).toBe(2)
    vi.useRealTimers()
  })

  it('drops redo history after a new edit', async () => {
    vi.useFakeTimers()
    const state = setup()
    const history = useCanvasHistory({ ...state, delay: 20 })
    history.initialize()
    state.store.nodes[0].data.value = 2
    history.commit()
    history.undo()
    await nextTick()
    state.store.nodes[0].data.value = 3
    history.commit()

    expect(history.canRedo.value).toBe(false)
    vi.useRealTimers()
  })
})
