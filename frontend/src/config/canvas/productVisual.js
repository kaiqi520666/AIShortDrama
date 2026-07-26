export const productVisualGroups = [
  {
    id: 'basic',
    label: '基础展示',
    items: [
      { id: 'white-bg', label: '白底图' },
      { id: 'first-screen', label: '首屏主视觉' },
      { id: 'multi-angle', label: '多角度' },
      { id: 'series-show', label: '系列 SKU' },
    ],
  },
  {
    id: 'marketing',
    label: '营销卖点',
    items: [
      { id: 'core-selling', label: '核心卖点' },
      { id: 'use-scenario', label: '使用场景' },
      { id: 'ambient-scene', label: '氛围场景' },
      { id: 'contrast-effect', label: '效果对比' },
    ],
  },
  {
    id: 'detail',
    label: '详情说明',
    items: [
      { id: 'detail-zoom', label: '细节图' },
      { id: 'specs-info', label: '规格尺寸' },
      { id: 'tech-specs', label: '参数表' },
      { id: 'manufacturing', label: '工艺' },
      { id: 'ingredients', label: '成分' },
    ],
  },
  {
    id: 'trust',
    label: '信任保障',
    items: [
      { id: 'brand-story', label: '品牌故事' },
      { id: 'freebies', label: '配件 / 赠品' },
      { id: 'warranty', label: '售后保障' },
      { id: 'usage-tips', label: '使用建议' },
    ],
  },
]

export const productVisualTypes = productVisualGroups.flatMap((group) => group.items)

const defaultTypeIds = new Set(['white-bg', 'first-screen', 'core-selling', 'use-scenario', 'ambient-scene', 'detail-zoom'])

export function createProductVisualItems() {
  return productVisualTypes.map((item) => ({ ...item, enabled: defaultTypeIds.has(item.id) }))
}

export function buildProductVisualPrompt(productContext, items, settings = {}) {
  const types = items.map((item) => `${item.id}=${item.label}`).join('、')
  const prefix = `请根据参考商品图片和商品资料，为以下图种分别生成一条中文图片提示词：${types}。统一画面规格：${settings.aspectRatio || '1:1'}，${settings.resolution || '1K'}。\n商品资料：\n`
  const suffix = `\n严格输出 JSON 数组，格式为 [{"type":"图种ID","prompt":"提示词"}]。每个图种必须且只能出现一次，顺序与请求一致。每条提示词不超过 100 个中文字符，只描述该图种特有的构图、场景、光线、视角与文案布局，不重复商品资料，不虚构图片和资料中没有的商品事实，不解释，不使用 Markdown。`
  return `${prefix}${productContext.slice(0, Math.max(0, 3000 - prefix.length - suffix.length))}${suffix}`
}

export function parseProductVisualPlan(content, items) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('[')
  const end = source.lastIndexOf(']')
  if (start < 0 || end <= start) throw new Error('未生成有效的商品出图方案')

  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error('商品出图方案格式异常')
  }
  if (!Array.isArray(parsed)) throw new Error('商品出图方案格式异常')

  const prompts = new Map(parsed.map((item) => [item?.type, typeof item?.prompt === 'string' ? item.prompt.trim() : '']))
  const plans = items.map((item) => ({ ...item, prompt: prompts.get(item.id) || '' }))
  const missing = plans.filter((item) => !item.prompt).map((item) => item.label)
  if (missing.length) throw new Error(`商品出图方案缺少：${missing.join('、')}`)
  return plans
}
