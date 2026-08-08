import { requireTemplate } from './contentTemplates'

function apparelVisualGroups(template) {
  return requireTemplate(template, '服饰试穿设置').config.groups
}

export function resolveOutfitMaterials(template, selectedIds = null) {
  const selected = selectedIds ? new Set(selectedIds) : null
  return apparelVisualGroups(template).flatMap((group) => group.items
    .filter((item) => selected ? selected.has(item.id) : item.default_enabled)
    .map((item) => ({
      id: item.id,
      label: item.label,
      category: group.id,
      categoryLabel: group.label,
    })))
}

export function buildApparelVisualRequest({
  workspaceId,
  nodeId,
  model,
  garmentUrl,
  modelUrl,
  apparelContext,
  selectedViewIds,
  aspectRatio,
  resolution,
  templateVersion,
  userRequirement,
}) {
  return {
    workspace_id: workspaceId,
    node_id: nodeId,
    model,
    media_type: 'image',
    media_url: garmentUrl,
    media_urls: [modelUrl],
    response_mode: 'outfit_visual_plan',
    template_key: 'apparel_visual',
    template_version: templateVersion,
    template_context: {
      apparel_context: apparelContext,
      selected_view_ids: selectedViewIds,
      aspect_ratio: aspectRatio,
      resolution,
      reference_count: 2,
      user_requirement: userRequirement || '',
    },
  }
}

export function parseOutfitPlan(content, materials) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('[')
  const end = source.lastIndexOf(']')
  if (start < 0 || end <= start) throw new Error('未生成有效的试穿素材方案')

  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error('试穿素材方案格式异常')
  }
  if (!Array.isArray(parsed)) throw new Error('试穿素材方案格式异常')

  const prompts = new Map(parsed.map((item) => [item?.id || item?.type, typeof item?.prompt === 'string' ? item.prompt.trim() : '']))
  const plans = materials.map((material) => ({ ...material, prompt: prompts.get(material.id) || '' }))
  const missing = plans.filter((plan) => !plan.prompt).map((plan) => plan.label)
  if (missing.length) throw new Error(`试穿素材方案缺少：${missing.join('、')}`)
  return plans
}
