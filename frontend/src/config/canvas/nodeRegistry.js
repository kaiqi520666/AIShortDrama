import MediaNode from '../../components/canvas/MediaNode.vue'
import ProductNode from '../../components/canvas/ProductNode.vue'
import ProductCreationPanel from '../../components/canvas/ProductCreationPanel.vue'
import ProductVisualNode from '../../components/canvas/ProductVisualNode.vue'
import ProductVisualPanel from '../../components/canvas/ProductVisualPanel.vue'
import SellingCopyNode from '../../components/canvas/SellingCopyNode.vue'
import SellingCopyPanel from '../../components/canvas/SellingCopyPanel.vue'
import GenerationPanel from '../../components/canvas/GenerationPanel.vue'
import { nodeDefinitions } from './nodeDefinitions'

const components = { product: ProductNode, product_visual: ProductVisualNode, selling_copy: SellingCopyNode }

export const nodeRegistry = Object.fromEntries(Object.entries(nodeDefinitions).map(([type, definition]) => [type, {
  ...definition,
  component: components[type] || MediaNode,
  panelComponent: type === 'product' ? ProductCreationPanel : type === 'product_visual' ? ProductVisualPanel : type === 'selling_copy' ? SellingCopyPanel : definition.generationPanel ? GenerationPanel : null,
  panelHeight: type === 'product' ? 440 : type === 'product_visual' ? 380 : 260,
}]))
