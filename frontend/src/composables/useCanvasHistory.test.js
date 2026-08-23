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

  it('skips generating snapshots and restores the previous stable node state', async () => {
    vi.useFakeTimers()
    const state = setup()
    Object.assign(state.store.nodes[0].data, { status: 'ready', content: '旧结果' })
    const history = useCanvasHistory({ ...state, delay: 20 })
    history.initialize()

    Object.assign(state.store.nodes[0].data, {
      status: 'generating',
      content: '部分结果',
      generationTaskId: 'task-1',
      generationStatus: 'running',
    })
    history.schedule()
    await vi.advanceTimersByTimeAsync(20)
    expect(history.canUndo.value).toBe(false)

    Object.assign(state.store.nodes[0].data, {
      status: 'ready',
      content: '新结果',
      generationStatus: 'succeeded',
    })
    history.schedule()
    await vi.advanceTimersByTimeAsync(20)
    expect(history.canUndo.value).toBe(true)

    history.undo()
    await nextTick()
    expect(state.store.nodes[0].data).toEqual({ value: 1, status: 'ready', content: '旧结果' })
    vi.useRealTimers()
  })

  it('records unrelated edits without storing another node generating state', async () => {
    vi.useFakeTimers()
    const state = setup()
    state.store.nodes[0].data.status = 'ready'
    state.store.nodes.push({ id: 'node-2', data: { value: 1, status: 'ready' } })
    const history = useCanvasHistory({ ...state, delay: 20 })
    history.initialize()

    Object.assign(state.store.nodes[0].data, { status: 'generating', generationTaskId: 'task-1' })
    state.store.nodes[1].data.value = 2
    history.schedule()
    await vi.advanceTimersByTimeAsync(20)
    expect(history.canUndo.value).toBe(false)

    Object.assign(state.store.nodes[0].data, { status: 'ready', generationStatus: 'succeeded' })
    history.schedule()
    await vi.advanceTimersByTimeAsync(20)
    history.undo()
    await nextTick()
    expect(state.store.nodes[0].data.status).toBe('ready')
    expect(state.store.nodes[1].data.value).toBe(2)
    vi.useRealTimers()
  })

  it('keeps a new generating node out of history until it becomes stable', async () => {
    vi.useFakeTimers()
    const state = setup()
    const history = useCanvasHistory({ ...state, delay: 20 })
    history.initialize()

    state.store.nodes.push({ id: 'node-2', data: { status: 'generating', generationTaskId: 'task-2' } })
    state.store.edges.push({ id: 'edge-1', source: 'node-1', target: 'node-2' })
    history.schedule()
    await vi.advanceTimersByTimeAsync(20)
    expect(history.canUndo.value).toBe(false)

    Object.assign(state.store.nodes[1].data, { status: 'ready', asset: 'https://example.com/result.png' })
    history.schedule()
    await vi.advanceTimersByTimeAsync(20)
    expect(history.canUndo.value).toBe(true)

    history.undo()
    await nextTick()
    expect(state.store.nodes.map(({ id }) => id)).toEqual(['node-1'])
    expect(state.store.edges).toEqual([])
    vi.useRealTimers()
  })
})
