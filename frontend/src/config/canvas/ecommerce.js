export const copyOutputTypes = [
  { value: 'title', label: '商品标题' },
  { value: 'selling_points', label: '核心卖点' },
  { value: 'detail', label: '详情页文案' },
  { value: 'voiceover', label: '短视频口播稿' },
]

const productFields = ['name', 'brand', 'category', 'price', 'specifications', 'sellingPoints', 'audience', 'scenario']

export const productRecognitionPrompt = `识别图片中的商品并严格输出一个 JSON 对象，不要解释，不要使用 Markdown。字段固定为：
{"name":"商品名称","brand":"品牌","category":"品类","price":"图片中可见的价格","specifications":"规格、型号、颜色、尺寸或容量","sellingPoints":["核心卖点1","核心卖点2"],"audience":"目标人群","scenario":"适用场景"}
无法从图片确认的字段填写空字符串，不要猜测品牌、价格和规格。`

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
