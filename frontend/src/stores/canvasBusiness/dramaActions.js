import { createCanvasEdge } from './sharedActions'

export function createCharacterChain(position, sourceId) {
  const source = this.nodes.find((node) => node.id === sourceId)
  if (sourceId && source?.type !== 'world') return { handled: false }
  const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 210 })
  const image = this.nodes.find((node) => node.id === imageId)
  image.data = { ...image.data, title: '角色参考图', assetSource: 'upload', resourceType: 'character' }
  const characterId = this.addNode('character', position, imageId)
  if (source?.type === 'world') {
    this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, source.id, characterId, 'world'))
  }
  this.selectNodes([characterId])
  return { handled: true, id: characterId }
}

export const dramaActions = {
  addCharacterVisualNodes(characterId, referenceId, plans, settings) {
    const character = this.nodes.find((node) => node.id === characterId)
    if (!character || !plans.length) return []
    const ids = plans.map((plan, index) => {
      const id = this.addNode('image', {
        x: character.position.x + 500 + index * 440,
        y: character.position.y,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: plan.label,
        characterSourceId: characterId,
        prompt: plan.prompt,
        promptParts: [{ type: 'text', value: plan.prompt }],
        ...settings,
      }
      this.addEdge({ source: characterId, target: id })
      if (referenceId) this.addEdge({ source: referenceId, target: id })
      return id
    })
    this.selectNodes(ids.slice(0, 1))
    return ids
  },
}
