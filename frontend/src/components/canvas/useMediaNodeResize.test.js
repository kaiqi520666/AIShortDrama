import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useMediaNodeResize } from './useMediaNodeResize'

function createWindowStub() {
  const listeners = new Map()
  globalThis.window = {
    addEventListener: vi.fn((type, listener) => listeners.set(type, listener)),
    removeEventListener: vi.fn((type, listener) => {
      if (listeners.get(type) === listener) listeners.delete(type)
    }),
  }
  return listeners
}

beforeEach(() => createWindowStub())
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('useMediaNodeResize', () => {
  it('converts pointer movement by viewport zoom for media nodes', () => {
    const listeners = createWindowStub()
    const updateNodeData = vi.fn()
    const subject = useMediaNodeResize({
      getId: () => 'image-1',
      getType: () => 'image',
      getData: () => ({ displayWidth: 300 }),
      getMediaWidth: () => 300,
      getDisplayAspectRatio: () => 1,
      getZoom: () => 2,
      updateNodeData,
    })

    subject.startResize({ clientX: 100, clientY: 0 })
    listeners.get('pointermove')({ clientX: 140, clientY: 0 })

    expect(updateNodeData).toHaveBeenCalledWith('image-1', { displayWidth: 320 })
    subject.stopResize()
    expect(window.removeEventListener).toHaveBeenCalledWith('pointermove', expect.any(Function))
  })

  it('removes listeners after a freeform resize ends', () => {
    const listeners = createWindowStub()
    const subject = useMediaNodeResize({
      getId: () => 'text-1',
      getType: () => 'text',
      getData: () => ({ width: 350, height: 220 }),
      getMediaWidth: () => 0,
      getDisplayAspectRatio: () => 1,
      getZoom: () => 1,
      updateNodeData: vi.fn(),
    })

    subject.startResize({ clientX: 0, clientY: 0 })
    const stop = listeners.get('pointerup')
    stop()

    expect(window.removeEventListener).toHaveBeenCalledWith('pointermove', expect.any(Function))
    expect(window.removeEventListener).toHaveBeenCalledWith('pointerup', stop)
    subject.stopResize()
  })
})
