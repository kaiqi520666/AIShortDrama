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

export function buildProductVisualRequest({
  workspaceId,
  nodeId,
  model,
  referenceUrls,
  productContext,
  selectedTypeIds,
  aspectRatio,
  resolution,
  templateVersion,
}) {
  const [mediaUrl, ...mediaUrls] = referenceUrls
  return {
    workspace_id: workspaceId,
    node_id: nodeId,
    model,
    media_type: 'image',
    media_url: mediaUrl,
    ...(mediaUrls.length ? { media_urls: mediaUrls } : {}),
    response_mode: 'product_visual_plan',
    template_key: 'product_visual',
    template_version: templateVersion,
    template_context: {
      product_context: productContext,
      selected_type_ids: selectedTypeIds,
      aspect_ratio: aspectRatio,
      resolution,
      reference_count: referenceUrls.length,
    },
  }
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
