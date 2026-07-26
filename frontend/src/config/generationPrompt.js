import { productPromptContext } from './canvas/ecommerce'

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
