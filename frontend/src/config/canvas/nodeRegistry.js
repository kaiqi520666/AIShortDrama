import MediaNode from '../../components/canvas/MediaNode.vue'
import ProductNode from '../../components/canvas/ProductNode.vue'
import ProductCreationPanel from '../../components/canvas/ProductCreationPanel.vue'
import ProductVisualNode from '../../components/canvas/ProductVisualNode.vue'
import ProductVisualPanel from '../../components/canvas/ProductVisualPanel.vue'
import ProductStoryboardNode from '../../components/canvas/ProductStoryboardNode.vue'
import ProductStoryboardPanel from '../../components/canvas/ProductStoryboardPanel.vue'
import ApparelNode from '../../components/canvas/ApparelNode.vue'
import ApparelPanel from '../../components/canvas/ApparelPanel.vue'
import OutfitNode from '../../components/canvas/OutfitNode.vue'
import OutfitPanel from '../../components/canvas/OutfitPanel.vue'
import GenerationPanel from '../../components/canvas/GenerationPanel.vue'
import WorldNode from '../../components/canvas/WorldNode.vue'
import WorldCreationPanel from '../../components/canvas/WorldCreationPanel.vue'
import CharacterNode from '../../components/canvas/CharacterNode.vue'
import CharacterCreationPanel from '../../components/canvas/CharacterCreationPanel.vue'
import { nodeDefinitions } from './nodeDefinitions'

const components = { product: ProductNode, product_visual: ProductVisualNode, product_storyboard: ProductStoryboardNode, apparel: ApparelNode, outfit: OutfitNode, world: WorldNode, character: CharacterNode }
const panels = { product: ProductCreationPanel, product_visual: ProductVisualPanel, product_storyboard: ProductStoryboardPanel, apparel: ApparelPanel, outfit: OutfitPanel, world: WorldCreationPanel, character: CharacterCreationPanel }
const panelHeights = { product: 440, product_visual: 380, product_storyboard: 590, apparel: 440, outfit: 470, world: 250, character: 440 }

export const nodeRegistry = Object.fromEntries(Object.entries(nodeDefinitions).map(([type, definition]) => [type, {
  ...definition,
  component: components[type] || MediaNode,
  panelComponent: panels[type] || (definition.generationPanel ? GenerationPanel : null),
  panelHeight: panelHeights[type] || 260,
}]))
