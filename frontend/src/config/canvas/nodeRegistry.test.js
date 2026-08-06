import { describe, expect, it } from 'vitest'
import { getNodeRegistry, nodeRegistry } from './nodeRegistry'
import { nodeCatalog } from './nodeCatalog'

describe('canvas node registry', () => {
  it('resolves registered components as lazy async components', () => {
    Object.keys(nodeCatalog).forEach((type) => {
      const entry = getNodeRegistry(type)
      expect(entry.component.__asyncLoader).toEqual(expect.any(Function))
      if (entry.panelComponent) expect(entry.panelComponent.__asyncLoader).toEqual(expect.any(Function))
    })
  })

  it('rejects unknown node types explicitly', () => {
    expect(() => getNodeRegistry('missing')).toThrow('不支持的节点类型')
    expect(nodeRegistry.missing).toBeUndefined()
  })
})
