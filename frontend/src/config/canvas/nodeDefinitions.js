import { Clapperboard, FileText, Globe2, Image, Images, Music2, Package, Shirt, UserRound, Video } from 'lucide-vue-next'
import { nodeCatalog, getNodeDescriptor } from './nodeCatalog'

const icons = { Clapperboard, FileText, Globe2, Image, Images, Music2, Package, Shirt, UserRound, Video }

export const nodeDefinitions = Object.fromEntries(Object.entries(nodeCatalog).map(([type, descriptor]) => [type, {
  ...descriptor,
  icon: icons[descriptor.iconName],
  generationPanel: descriptor.panelName === 'GenerationPanel',
}]))

export function getNodeDefinition(type) {
  const definition = nodeDefinitions[type]
  if (!definition) getNodeDescriptor(type)
  return definition
}

export { createNodeData, getReversePrompt } from './nodeCatalog'
