import { describe, expect, it } from 'vitest'
import { getGroupFrameStyle } from './useCanvasGrouping'

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
})
