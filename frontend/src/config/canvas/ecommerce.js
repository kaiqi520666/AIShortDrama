const productFields = [
  'name', 'brand', 'category', 'price', 'specifications', 'packagingType', 'productDimensions',
  'packageDimensions', 'packageRelation', 'scaleReference', 'sellingPoints', 'audience', 'scenario', 'additionalInfo',
]

export function parseProductProfile(content) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('{')
  const end = source.lastIndexOf('}')
  if (start < 0 || end <= start) throw new Error('未识别到有效的商品档案')
  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error('商品档案识别结果格式异常')
  }
  const product = Object.fromEntries(productFields.map((key) => {
    const value = Array.isArray(parsed[key]) ? parsed[key].join('\n') : parsed[key]
    return [key, typeof value === 'string' || typeof value === 'number' ? String(value).trim() : '']
  }))
  if (!Object.values(product).some(Boolean)) throw new Error('图片中未识别到商品信息')
  return product
}

export function mergeProductProfile(current = {}, recognized = {}) {
  return Object.fromEntries(productFields.map((key) => [key, current[key]?.trim() || recognized[key] || '']))
}

export function productPromptContext(product = {}) {
  const hasPackaging = ['带包装', '套装'].includes(product.packagingType)
  const fields = [
    ['商品名称', product.name],
    ['品牌', product.brand],
    ['品类', product.category],
    ['价格', product.price],
    ['规格 / SKU', product.specifications],
    ['商品形态', product.packagingType],
    ['主体尺寸', product.productDimensions],
    ['外包装尺寸', hasPackaging ? product.packageDimensions : ''],
    ['包装关系', hasPackaging ? product.packageRelation : ''],
    ['尺度参照', product.scaleReference],
    ['核心卖点', product.sellingPoints],
    ['目标人群', product.audience],
    ['使用场景', product.scenario],
    ['补充信息', product.additionalInfo],
  ].filter(([, value]) => value?.trim())
  return fields.map(([label, value]) => `${label}：${value.trim()}`).join('\n')
}
