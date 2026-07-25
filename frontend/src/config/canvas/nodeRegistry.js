import MediaNode from '../../components/canvas/MediaNode.vue'
import ProductNode from '../../components/canvas/ProductNode.vue'
import ProductRecognitionPanel from '../../components/canvas/ProductRecognitionPanel.vue'
import SellingCopyNode from '../../components/canvas/SellingCopyNode.vue'
import SellingCopyPanel from '../../components/canvas/SellingCopyPanel.vue'
import GenerationPanel from '../../components/canvas/GenerationPanel.vue'
import { nodeDefinitions } from './nodeDefinitions'

const components = { product: ProductNode, selling_copy: SellingCopyNode }

export const nodeRegistry = Object.fromEntries(Object.entries(nodeDefinitions).map(([type, definition]) => [type, {
  ...definition,
  component: components[type] || MediaNode,
  panelComponent: type === 'product' ? ProductRecognitionPanel : type === 'selling_copy' ? SellingCopyPanel : definition.generationPanel ? GenerationPanel : null,
}]))
