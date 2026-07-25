export const copyOutputTypes = [
  { value: 'title', label: '商品标题' },
  { value: 'selling_points', label: '核心卖点' },
  { value: 'detail', label: '详情页文案' },
  { value: 'voiceover', label: '短视频口播稿' },
]

export function productPromptContext(product = {}) {
  const fields = [
    ['商品名称', product.name],
    ['品牌', product.brand],
    ['品类', product.category],
    ['价格', product.price],
    ['规格 / SKU', product.specifications],
    ['核心卖点', product.sellingPoints],
    ['目标人群', product.audience],
    ['使用场景', product.scenario],
  ].filter(([, value]) => value?.trim())
  return fields.map(([label, value]) => `${label}：${value.trim()}`).join('\n')
}
