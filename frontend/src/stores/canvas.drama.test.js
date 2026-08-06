import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { seedModelCapabilities } from '../test/modelCapabilities'
import { useCanvasStore } from './canvas'

beforeEach(() => {
  setActivePinia(createPinia())
  seedModelCapabilities()
})

describe('canvas drama workflows', () => {
  it('creates a character workflow from world context with an optional reference input', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'drama',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const worldId = store.addNode('world', { x: 0, y: 0 })
    const characterId = store.addNode('character', { x: 500, y: 0 }, worldId)

    expect(characterId).toBe('character-3')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: worldId, type: 'world' }),
      expect.objectContaining({ id: 'image-2', data: expect.objectContaining({ title: '角色参考图', resourceType: 'character' }) }),
      expect.objectContaining({ id: characterId, data: expect.objectContaining({ workflowStep: 'profile', aspectRatio: '3:4', mainReferenceNodeId: '' }) }),
    ]))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: worldId, target: characterId, targetHandle: 'world' }),
      expect.objectContaining({ source: 'image-2', target: characterId, targetHandle: 'reference' }),
    ]))
  })

  it('creates three character image nodes with shared character and optional image references', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'drama',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const worldId = store.addNode('world', { x: 0, y: 0 })
    const characterId = store.addNode('character', { x: 500, y: 0 }, worldId)
    const ids = store.addCharacterVisualNodes(characterId, 'image-2', [
      { id: 'full-body', label: '正面全身', prompt: '全身设定' },
      { id: 'portrait', label: '半身肖像', prompt: '半身设定' },
      { id: 'turnaround', label: '角色三视图', prompt: '三视图设定' },
    ], { model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K' })

    expect(ids).toEqual(['image-4', 'image-5', 'image-6'])
    expect(store.nodes.find((node) => node.id === ids[0]).data).toEqual(expect.objectContaining({
      title: '正面全身', characterSourceId: characterId, prompt: '全身设定', model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    }))
    expect(store.edges.filter((edge) => ids.includes(edge.target))).toHaveLength(6)
  })
})
