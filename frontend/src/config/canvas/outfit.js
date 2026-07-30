export const outfitMaterialGroups = [
  {
    id: 'view',
    label: '基础视角',
    items: [
      { id: 'front', label: '正面全身', description: '模特自然站立，正面全身构图，完整展示服装廓形、长度和正面设计。' },
      { id: 'side', label: '侧面轮廓', description: '模特侧身站立，完整展示侧面轮廓、腰线、肩线和垂坠感。' },
      { id: 'back', label: '背面展示', description: '模特背对镜头，完整展示服装背面版型、开合方式和后背细节。' },
    ],
  },
  {
    id: 'motion',
    label: '动态展示',
    items: [
      { id: 'turn', label: '转身定格', description: '捕捉模特自然转身的瞬间，衣摆和面料有真实动态，人物与服装主体清晰。' },
      { id: 'walk', label: '走动展示', description: '模特自然向前走动，以全身画面展示服装在步态中的版型和垂坠变化。' },
      { id: 'sit', label: '坐姿展示', description: '模特自然坐姿，展示服装在坐姿下的剪裁、舒适度和褶皱状态。' },
    ],
  },
  {
    id: 'detail',
    label: '细节卖点',
    items: [
      { id: 'fabric', label: '面料细节', description: '局部近景展示面料纹理、光泽、厚薄和触感，不改变真实材质。' },
      { id: 'tailoring', label: '剪裁工艺', description: '局部近景展示领口、肩线、袖口、腰线或缝线等关键剪裁工艺。' },
      { id: 'fit', label: '上身版型', description: '中景突出服装与身体的松紧关系、比例修饰和整体上身效果。' },
    ],
  },
  {
    id: 'lifestyle',
    label: '内容场景',
    items: [
      { id: 'mirror', label: '镜前分享', description: '自然居家或试衣间镜前分享构图，呈现真实穿搭记录感。' },
      { id: 'office', label: '通勤场景', description: '现代办公空间或商务街区，突出利落、专业的通勤穿搭效果。' },
      { id: 'street', label: '街头穿搭', description: '都市街头环境，突出日常搭配感和自然街拍质感。' },
      { id: 'date', label: '约会场景', description: '咖啡店、餐厅或城市休闲空间，呈现精致亲和的约会穿搭氛围。' },
      { id: 'travel', label: '旅行场景', description: '车站、街区或户外目的地，呈现舒展自然的旅行穿搭氛围。' },
    ],
  },
]

export const outfitMaterials = outfitMaterialGroups.flatMap((group) => group.items.map((item) => ({
  ...item,
  category: group.id,
  categoryLabel: group.label,
})))

const legacySceneMap = {
  studio: 'front',
  cafe: 'date',
  lawn: 'travel',
  beach: 'travel',
  home: 'mirror',
  party: 'date',
  gallery: 'street',
}

export function resolveOutfitMaterials(moduleIds, legacySceneIds = [], customRequirement = '') {
  const ids = moduleIds?.length ? moduleIds : legacySceneIds.map((id) => legacySceneMap[id] || id)
  const selected = outfitMaterials.filter((item) => ids.includes(item.id))
  if (selected.length) return selected
  const description = customRequirement.trim()
  return description ? [{ id: 'custom', label: '自定义素材', category: 'custom', categoryLabel: '自定义', description }] : []
}

export function buildOutfitPlanPrompt(materials, customRequirement, settings = {}) {
  const materialList = materials.map((item) => `${item.id}=${item.label}（${item.categoryLabel}）：${item.description}`).join('\n')
  const supplement = materials.some((item) => item.id === 'custom') ? '' : customRequirement.trim()
  return `参考图1是服饰，参考图2是模特。请为以下每个穿搭素材模块分别生成一条中文静态图片生成提示词，每个模块生成一张独立图片：
${materialList}
${supplement ? `统一补充要求：${supplement}\n` : ''}统一画面规格：${settings.aspectRatio || '3:4'}，${settings.resolution || '1K'}。
严格输出JSON数组，格式为[{"type":"模块ID","prompt":"图片提示词"}]。每个模块必须且只能出现一次，顺序与请求一致。每条提示词不超过260个中文字符，必须明确参考图1的服饰穿到参考图2的模特身上，保持服饰颜色、版型、材质、纹理、图案和细节，保持模特身份、面部与体型一致；根据模块准确描述静态姿态、景别、构图、背景和光线。只出现一名模特，不换款，不虚构品牌、文字或配饰，不描述说话、台词、音效、运镜或连续动作，无字幕、Logo、文字、水印，不解释，不使用Markdown。`
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
