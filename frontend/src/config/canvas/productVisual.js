import { requireTemplate } from './contentTemplates'

export function getProductVisualGroups(template) {
  const record = requireTemplate(template, '商品图种模板')
  return record.config.groups.map((group) => ({
    ...group,
    items: group.items.map((item) => ({ ...item })),
  }))
}

export function createProductVisualItems(template) {
  return getProductVisualGroups(template).flatMap((group) => group.items.map((item) => ({
    id: item.id,
    label: item.label,
    enabled: item.default_enabled,
  })))
}

export function buildProductVisualPrompt(productContext, items, settings = {}, template) {
  const record = requireTemplate(template, '商品图种模板')
  const types = items.map((item) => `${item.id}=${item.label}`).join('、')
  const instruction = record.config.business_instruction.trim()
  const prefix = `请根据参考商品图片和商品资料，为以下图种分别生成一条中文图片提示词：${types}。统一画面规格：${settings.aspectRatio || '1:1'}，${settings.resolution || '1K'}。${instruction ? `\n业务要求：${instruction}` : ''}\n商品资料：\n`
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
