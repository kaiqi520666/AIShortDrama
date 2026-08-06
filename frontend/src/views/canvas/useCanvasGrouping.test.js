import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { getGroupFrameStyle, useCanvasGrouping } from './useCanvasGrouping'

function createGroupingSubject() {
  const nodes = ref([
    {
      id: 'a',
      type: 'text',
      selected: true,
      position: { x: 10, y: 20 },
      computedPosition: { x: 10, y: 20 },
      dimensions: { width: 100, height: 50 },
    },
    {
      id: 'b',
      type: 'image',
      selected: true,
      position: { x: 160, y: 100 },
      computedPosition: { x: 160, y: 100 },
      dimensions: { width: 80, height: 60 },
    },
  ])
  const groups = ref([{ id: 'group-1', title: '组合', nodeIds: ['a', 'b'] }])
  const viewport = ref({ x: 0, y: 0, zoom: 2 })
  const contextMenu = ref(null)
  const pointerMode = ref(null)
  const canvasTool = ref('select')
  const store = {
    selectNodes: vi.fn(),
    groupSelected: vi.fn(),
    ungroupNode: vi.fn(),
    removeNodesFromGroup: vi.fn(),
    duplicateNodes: vi.fn(),
    duplicateWithInputs: vi.fn(),
    deleteNodes: vi.fn(),
  }
  const findNode = (id) => nodes.value.find((node) => node.id === id)
  const subject = useCanvasGrouping({
    store,
    nodes,
    groups,
    viewport,
    assetsVisible: ref(false),
    contextMenu,
    pointerMode,
    canvasTool,
    findNode,
    fitView: vi.fn(),
    setCenter: vi.fn(),
    getPanelHeight: vi.fn(() => 300),
    removeSelectedElements: vi.fn(),
    addSelectedNodes: vi.fn(),
    confirm: vi.fn(async () => true),
  })
  return { subject, store, nodes, pointerMode }
}

function panePointerEvent() {
  return {
    button: 0,
    clientX: 0,
    clientY: 20,
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
    target: { closest: vi.fn(() => null) },
  }
}

beforeEach(() => {
  vi.stubGlobal('window', {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('canvas group frames', () => {
  it('projects grouped node bounds through the viewport', () => {
    const flowNodes = {
      a: { computedPosition: { x: 10, y: 20 }, dimensions: { width: 100, height: 50 } },
      b: { computedPosition: { x: 160, y: 100 }, dimensions: { width: 80, height: 60 } },
    }
    const style = getGroupFrameStyle(['a', 'b'], {
      findNode: (id) => flowNodes[id],
      viewport: { value: { x: 5, y: 7, zoom: 2 } },
      assetsVisible: { value: false },
    })

    expect(style).toEqual({ left: '-3px', top: '15px', width: '516px', height: '326px' })
  })

  it('does not render a frame for fewer than two available nodes', () => {
    expect(getGroupFrameStyle(['missing'], {
      findNode: () => undefined,
      viewport: { value: { x: 0, y: 0, zoom: 1 } },
      assetsVisible: { value: false },
    })).toEqual({})
  })

  it('moves every child using viewport-scaled pointer deltas', () => {
    const addListener = vi.spyOn(window, 'addEventListener')
    const removeListener = vi.spyOn(window, 'removeEventListener')
    const { subject, nodes, pointerMode } = createGroupingSubject()

    subject.handleCanvasPointerDown(panePointerEvent())
    const move = addListener.mock.calls.find(([type]) => type === 'pointermove')[1]
    const stop = addListener.mock.calls.find(([type]) => type === 'pointerup')[1]
    move({ clientX: 20, clientY: 30 })

    expect(nodes.value.map((node) => node.position)).toEqual([
      { x: 20, y: 25 },
      { x: 170, y: 105 },
    ])
    stop()
    expect(pointerMode.value).toBeNull()
    expect(removeListener).toHaveBeenCalledWith('pointermove', move)
    expect(removeListener).toHaveBeenCalledWith('pointerup', stop)
  })

  it('ungroups the complete selection and resets the active group', () => {
    const { subject, store } = createGroupingSubject()
    subject.activeGroupId.value = 'group-1'

    subject.ungroupSelected()

    expect(store.ungroupNode).toHaveBeenCalledWith('a')
    expect(subject.activeGroupId.value).toBeNull()
  })

  it('removes active drag listeners when the composable is disposed', () => {
    const addListener = vi.spyOn(window, 'addEventListener')
    const removeListener = vi.spyOn(window, 'removeEventListener')
    const { subject, pointerMode } = createGroupingSubject()

    subject.handleCanvasPointerDown(panePointerEvent())
    const move = addListener.mock.calls.find(([type]) => type === 'pointermove')[1]
    const stop = addListener.mock.calls.find(([type]) => type === 'pointerup')[1]
    subject.disposeGrouping()

    expect(pointerMode.value).toBeNull()
    expect(removeListener).toHaveBeenCalledWith('pointermove', move)
    expect(removeListener).toHaveBeenCalledWith('pointerup', stop)
  })
})
