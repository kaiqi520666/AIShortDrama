import MediaNode from '../../components/canvas/MediaNode.vue'
import { nodeDefinitions } from './nodeDefinitions'

export const nodeRegistry = Object.fromEntries(Object.entries(nodeDefinitions)
  .map(([type, definition]) => [type, { ...definition, component: MediaNode }]))
