const visualGroupIds = ['basic', 'marketing', 'detail', 'trust']
const visualItemIds = {
  basic: ['white-bg', 'first-screen', 'multi-angle', 'series-show'],
  marketing: ['core-selling', 'use-scenario', 'ambient-scene', 'contrast-effect'],
  detail: ['detail-zoom', 'specs-info', 'tech-specs', 'manufacturing', 'ingredients'],
  trust: ['brand-story', 'freebies', 'warranty', 'usage-tips'],
}
const allowedDurations = new Set([15, 30, 45, 60])

function validText(value, max = 6000) {
  return typeof value === 'string' && value.trim() && value.trim().length <= max
}

export function validateProductContentTemplates(value) {
  const visual = value?.product_visual
  const storyboard = value?.product_storyboard
  if (!visual || !storyboard || typeof visual.version !== 'number' || typeof storyboard.version !== 'number') return '商品模板响应无效'
  const groups = visual.config?.groups
  if (!Array.isArray(groups) || groups.length !== visualGroupIds.length) return '商品图种模板无效'
  for (const group of groups) {
    if (!visualGroupIds.includes(group?.id) || !validText(group?.label, 64)) return '商品图种模板无效'
    const expected = visualItemIds[group.id]
    if (!Array.isArray(group.items) || group.items.map((item) => item?.id).join('|') !== expected.join('|')) return '商品图种模板无效'
    if (group.items.some((item) => !validText(item?.label, 64) || typeof item.default_enabled !== 'boolean')) return '商品图种模板无效'
  }
  if (typeof visual.config.business_instruction !== 'string' || visual.config.business_instruction.length > 6000) return '商品图种业务指令无效'
  const templates = storyboard.config?.templates
  const durations = storyboard.config?.durations
  const continuity = storyboard.config?.continuity
  if (storyboard.config?.schema_version !== 2) return '商品分镜模板版本无效'
  if (!Array.isArray(templates) || templates.length !== 1 || templates[0]?.id !== 'ugc-seeding' || !validText(templates[0]?.label, 64) || !validText(templates[0]?.description, 255)) return '商品分镜模板无效'
  if (!Array.isArray(durations) || !durations.length || durations.some((item) => !allowedDurations.has(item))) return '商品分镜时长无效'
  if (!continuity || !['cut', 'extend'].every((key) => validText(continuity[key]?.label, 32) && validText(continuity[key]?.description, 120))) return '商品分镜衔接配置无效'
  return ''
}

export function requireTemplate(template, name) {
  if (!template?.enabled || !template?.config) throw new Error(`${name}未启用或尚未加载`)
  return template
}
