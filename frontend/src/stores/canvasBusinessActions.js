import { getNodeDescriptor } from '../config/canvas/nodeCatalog'
import {
  apparelActions,
  createApparelChain,
  createOutfitChain,
} from './canvasBusiness/apparelActions'
import { createProductChain, productActions } from './canvasBusiness/productActions'
import { createCanvasEdge, sharedActions, storyboardVideoData } from './canvasBusiness/sharedActions'

const businessCreators = {
  apparel: createApparelChain,
  outfit: createOutfitChain,
  product: createProductChain,
}

export function createBusinessNodeChain(type, position, sourceId, skipStoryboardInputs) {
  const creatorName = getNodeDescriptor(type).businessCreator
  if (!creatorName) return { handled: false }
  const creator = businessCreators[creatorName]
  if (!creator) throw new Error(`节点 ${type} 的业务创建器 ${creatorName} 未注册`)
  return creator.call(this, position, sourceId, skipStoryboardInputs)
}

export const canvasBusinessActions = {
  ...productActions,
  ...apparelActions,
  ...sharedActions,
}

export { createCanvasEdge, storyboardVideoData }
