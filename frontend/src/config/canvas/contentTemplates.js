const visualGroupIds = ['basic', 'marketing', 'detail', 'trust']
const visualItemIds = {
  basic: ['white-bg', 'first-screen', 'multi-angle', 'series-show'],
  marketing: ['core-selling', 'use-scenario', 'ambient-scene', 'contrast-effect'],
  detail: ['detail-zoom', 'specs-info', 'tech-specs', 'manufacturing', 'ingredients'],
  trust: ['brand-story', 'freebies', 'warranty', 'usage-tips'],
}
const apparelVisualItemIds = ['front', 'three-quarter', 'back', 'turn', 'fabric', 'lifestyle']
const allowedDurations = new Set([15, 30, 45, 60])
const dramaDurations = new Set([30, 45, 60])

function validText(value, max = 6000) {
  return typeof value === 'string' && value.trim() && value.trim().length <= max
}

export function validateProductContentTemplates(value) {
  const visual = value?.product_visual
  const storyboard = value?.product_storyboard
  const drama = value?.commerce_drama
  const apparelVisual = value?.apparel_visual
  const apparelShowcase = value?.apparel_showcase
  const records = [visual, apparelVisual, storyboard, drama, apparelShowcase]
  if (records.some((item) => !item || typeof item.version !== 'number' || typeof item.enabled !== 'boolean')) return '内容模板响应无效'
  const groups = visual.config?.groups
  if (visual.config?.schema_version !== 2 || visual.config?.output_protocol_id !== 'product-visual-v1') return '商品图种模板版本无效'
  if (!Array.isArray(groups) || groups.length !== visualGroupIds.length) return '商品图种模板无效'
  for (const group of groups) {
    if (!visualGroupIds.includes(group?.id) || !validText(group?.label, 64)) return '商品图种模板无效'
    const expected = visualItemIds[group.id]
    if (!Array.isArray(group.items) || group.items.map((item) => item?.id).join('|') !== expected.join('|')) return '商品图种模板无效'
    if (group.items.some((item) => !validText(item?.label, 64) || typeof item.default_enabled !== 'boolean')) return '商品图种模板无效'
  }
  const apparelGroups = apparelVisual.config?.groups
  if (apparelVisual.config?.schema_version !== 1 || apparelVisual.config?.output_protocol_id !== 'apparel-visual-v1') return '服饰试穿模板版本无效'
  if (!Array.isArray(apparelGroups) || apparelGroups.length !== 1 || apparelGroups[0]?.id !== 'views') return '服饰试穿视角配置无效'
  if (apparelGroups[0].items?.map((item) => item?.id).join('|') !== apparelVisualItemIds.join('|')) return '服饰试穿视角配置无效'
  if (!validText(apparelGroups[0].label, 64) || apparelGroups[0].items.some((item) => !validText(item?.label, 64) || typeof item.default_enabled !== 'boolean')) return '服饰试穿视角配置无效'
  const templates = storyboard.config?.templates
  const durations = storyboard.config?.durations
  const continuity = storyboard.config?.continuity
  if (storyboard.config?.schema_version !== 2) return '商品分镜模板版本无效'
  if (!Array.isArray(templates) || templates.length !== 1 || templates[0]?.id !== 'ugc-seeding' || !validText(templates[0]?.label, 64) || !validText(templates[0]?.description, 255)) return '商品分镜模板无效'
  if (!Array.isArray(durations) || !durations.length || durations.some((item) => !allowedDurations.has(item))) return '商品分镜时长无效'
  if (!continuity || !['cut', 'extend'].every((key) => validText(continuity[key]?.label, 32) && validText(continuity[key]?.description, 120))) return '商品分镜衔接配置无效'
  const dramaConfig = drama.config
  if (dramaConfig?.schema_version !== 2 || !validText(dramaConfig.label, 64) || !validText(dramaConfig.description, 255)) return '短剧带货模板无效'
  if (!Array.isArray(dramaConfig.durations) || !dramaConfig.durations.length || dramaConfig.durations.some((item) => !dramaDurations.has(item))) return '短剧带货时长无效'
  if (dramaConfig.output_protocol_id !== 'commerce-drama-v1') return '短剧带货输出协议无效'
  if (!dramaConfig.continuity || !['cut', 'extend'].every((key) => validText(dramaConfig.continuity[key]?.label, 32) && validText(dramaConfig.continuity[key]?.description, 120))) return '短剧带货衔接配置无效'
  const showcaseConfig = apparelShowcase.config
  if (showcaseConfig?.schema_version !== 1 || !validText(showcaseConfig.label, 64) || !validText(showcaseConfig.description, 255)) return '服饰展示模板无效'
  if (!Array.isArray(showcaseConfig.durations) || !showcaseConfig.durations.length || showcaseConfig.durations.some((item) => !allowedDurations.has(item))) return '服饰展示时长无效'
  if (showcaseConfig.output_protocol_id !== 'apparel-showcase-v1') return '服饰展示输出协议无效'
  if (!showcaseConfig.continuity || !['cut', 'extend'].every((key) => validText(showcaseConfig.continuity[key]?.label, 32) && validText(showcaseConfig.continuity[key]?.description, 120))) return '服饰展示衔接配置无效'
  return ''
}

export function requireTemplate(template, name) {
  if (!template?.enabled || !template?.config) throw new Error(`${name}未启用或尚未加载`)
  return template
}
