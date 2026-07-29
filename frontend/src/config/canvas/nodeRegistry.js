import MediaNode from '../../components/canvas/MediaNode.vue'
import ProductNode from '../../components/canvas/ProductNode.vue'
import ProductCreationPanel from '../../components/canvas/ProductCreationPanel.vue'
import ProductVisualNode from '../../components/canvas/ProductVisualNode.vue'
import ProductVisualPanel from '../../components/canvas/ProductVisualPanel.vue'
import OutfitNode from '../../components/canvas/OutfitNode.vue'
import OutfitPanel from '../../components/canvas/OutfitPanel.vue'
import GenerationPanel from '../../components/canvas/GenerationPanel.vue'
import WorldNode from '../../components/canvas/WorldNode.vue'
import WorldCreationPanel from '../../components/canvas/WorldCreationPanel.vue'
import { nodeDefinitions } from './nodeDefinitions'

const components = { product: ProductNode, product_visual: ProductVisualNode, outfit: OutfitNode, world: WorldNode }

export const nodeRegistry = Object.fromEntries(Object.entries(nodeDefinitions).map(([type, definition]) => [type, {
  ...definition,
  component: components[type] || MediaNode,
  panelComponent: type === 'product' ? ProductCreationPanel : type === 'product_visual' ? ProductVisualPanel : type === 'outfit' ? OutfitPanel : type === 'world' ? WorldCreationPanel : definition.generationPanel ? GenerationPanel : null,
  panelHeight: type === 'product' ? 440 : type === 'product_visual' ? 380 : type === 'outfit' ? 470 : type === 'world' ? 250 : 260,
}]))
