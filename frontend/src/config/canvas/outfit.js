export const outfitMaterialGroups = [{
  id: 'fixed-board',
  label: '固定六格参考图板',
  items: [
    { id: 'front', label: '正面全身', description: '模特自然站立，正面全身构图，完整展示服装廓形、长度和正面设计。' },
    { id: 'three-quarter', label: '45°侧面', description: '模特以45度侧身站立，展示肩线、腰线、侧面轮廓和垂坠感。' },
    { id: 'back', label: '背面展示', description: '模特背对镜头，完整展示服装背面版型、开合方式和后背细节。' },
    { id: 'turn', label: '转身定格', description: '模特转身后的自然定格姿态，展示衣摆、面料和整体比例。' },
    { id: 'fabric', label: '面料细节', description: '局部近景展示面料纹理、光泽、厚薄和关键工艺，不改变真实材质。' },
    { id: 'lifestyle', label: '场景穿搭', description: '自然生活场景中景，展示服饰整体搭配、比例和适用氛围。' },
  ],
}]

export const outfitMaterials = outfitMaterialGroups.flatMap((group) => group.items.map((item) => ({
  ...item,
  category: group.id,
  categoryLabel: group.label,
})))

export function resolveOutfitMaterials() {
  return outfitMaterials
}

export function buildOutfitPlanPrompt(materials, customRequirement, settings = {}, apparelContext = '') {
  const materialList = materials.map((item) => `${item.id}=${item.label}（${item.categoryLabel}）：${item.description}`).join('\n')
  const supplement = customRequirement.trim()
  return `参考图1是服饰，参考图2是模特。服饰资料如下：
${apparelContext}
请严格为固定六格参考图板生成以下 6 条中文静态图片提示词，每条对应一张独立参考图：
${materialList}
${supplement ? `统一补充要求：${supplement}\n` : ''}统一画面规格：9:16，1K。严格输出JSON数组，格式为[{"type":"模块ID","prompt":"图片提示词"}]。每个模块必须且只能出现一次，顺序与请求一致。每条提示词不超过260个中文字符，必须明确参考图1的服饰穿到参考图2的模特身上，保持服饰颜色、版型、材质、纹理、图案和细节，保持模特身份、面部与体型一致；根据模块准确描述静态姿态、景别、构图、背景和光线。只出现一名模特，不换款，不虚构品牌、文字或配饰，不描述说话、台词、音效、运镜或连续动作，无字幕、Logo、文字、水印，不解释，不使用Markdown。`
}

export function parseOutfitPlan(content, materials) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('[')
  const end = source.lastIndexOf(']')
  if (start < 0 || end <= start) throw new Error('未生成有效的穿搭素材方案')

  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error('穿搭素材方案格式异常')
  }
  if (!Array.isArray(parsed)) throw new Error('穿搭素材方案格式异常')

  const prompts = new Map(parsed.map((item) => [item?.type, typeof item?.prompt === 'string' ? item.prompt.trim() : '']))
  const plans = materials.map((material) => ({ ...material, prompt: prompts.get(material.id) || '' }))
  const missing = plans.filter((plan) => !plan.prompt).map((plan) => plan.label)
  if (missing.length) throw new Error(`穿搭素材方案缺少：${missing.join('、')}`)
  return plans
}
