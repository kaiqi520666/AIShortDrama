import { productPromptContext, productVideoPromptContext } from './canvas/ecommerce'

export const maxGenerationPromptLength = 32000

function referenceContext(node) {
  if (node?.type === 'text') return node.data?.content
  if (node?.type === 'product') return productPromptContext(node.data?.product)
  return ''
}

export function getEffectivePrompt(data = {}, references = []) {
  return [
    ...references.map(referenceContext),
    data.prompt,
  ].map((value) => value?.trim()).filter(Boolean).join('\n')
}

export function buildStoryboardProductVideoContext(product = {}, references = [], plotGoal = '') {
  const productContext = productVideoPromptContext(product)
  if (!productContext) return ''

  const referenceLines = references
    .filter((reference) => reference.type === 'image' && reference.data?.asset)
    .map((reference, index) => {
      if (reference.id?.startsWith('storyboard-character-')) return `图片${index + 1}是角色参考图，控制角色身份和外观。`
      if (reference.id?.startsWith('storyboard-product-')) return `图片${index + 1}是商品参考图，控制商品外观、包装结构和真实尺度。`
      if (reference.data?.storyboardSourceId) return `图片${index + 1}是分镜图，控制构图、动作和运镜。`
      return ''
    })
    .filter(Boolean)

  return [
    referenceLines.length ? `参考关系（以下为本次请求的实际图片顺序，优先级高于后文引用）：\n${referenceLines.join('\n')}` : '',
    `商品约束（以下用户确认资料为最终事实，优先级高于分镜中的冲突描述）：\n${productContext}`,
    plotGoal?.trim() ? `当前镜头目标：${plotGoal.trim()}` : '',
    '商品图控制资料未明确的外观细节。不得改变商品结构、数量和比例；不得重绘、替换或新增包装文字。',
  ].filter(Boolean).join('\n\n')
}
