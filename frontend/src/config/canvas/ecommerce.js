import { i18n } from '../../i18n/index'

const { t } = i18n.global
const productFields = [
  'name', 'brand', 'category', 'price', 'specifications', 'packagingType', 'productDimensions',
  'packageDimensions', 'packageRelation', 'scaleReference', 'sellingPoints', 'audience', 'scenario', 'additionalInfo',
]

export function parseProductProfile(content) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('{')
  const end = source.lastIndexOf('}')
  if (start < 0 || end <= start) throw new Error(t('canvas.invalidProductResult'))
  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error(t('canvas.invalidProductFormat'))
  }
  const product = Object.fromEntries(productFields.map((key) => {
    const value = Array.isArray(parsed[key]) ? parsed[key].join('\n') : parsed[key]
    return [key, typeof value === 'string' || typeof value === 'number' ? String(value).trim() : '']
  }))
  if (!Object.values(product).some(Boolean)) throw new Error(t('canvas.productNotFound'))
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

export function productVideoPromptContext(product = {}) {
  const hasPackaging = ['带包装', '套装'].includes(product.packagingType)
  const fields = [
    ['商品名称', product.name],
    ['品牌', product.brand],
    ['品类', product.category],
    ['规格 / SKU', product.specifications],
    ['商品形态', product.packagingType],
    ['主体尺寸', product.productDimensions],
    ['外包装尺寸', hasPackaging ? product.packageDimensions : ''],
    ['包装关系', hasPackaging ? product.packageRelation : ''],
    ['尺度参照', product.scaleReference],
    ['核心卖点', product.sellingPoints],
    ['外观信息', product.additionalInfo],
  ].filter(([, value]) => value?.trim())
  return fields.map(([label, value]) => `${label}：${value.trim()}`).join('\n')
}
