export const outfitScenes = [
  { id: 'studio', label: '纯色棚拍', description: '纯色或浅灰棚拍背景，突出服装整体版型、长度、肩线和垂坠感。' },
  { id: 'street', label: '都市街头', description: '都市街头环境，突出日常穿搭感和自然街拍质感。' },
  { id: 'cafe', label: '街角咖啡', description: '咖啡店或休闲空间，营造轻松、亲和的生活方式氛围。' },
  { id: 'lawn', label: '自然草坪', description: '公园草坪或自然绿地，呈现清新舒展的户外穿搭氛围。' },
  { id: 'beach', label: '度假海滩', description: '海滩或滨海步道，突出轻松通透的度假穿搭效果。' },
  { id: 'home', label: '温馨居家', description: '简洁温暖的居家环境，展示舒适自然的日常穿着状态。' },
  { id: 'gallery', label: '艺术展馆', description: '现代极简展馆空间，突出时尚感和高级质感。' },
]

export function resolveOutfitScenes(sceneIds = [], customScene = '') {
  const selected = outfitScenes.filter((scene) => sceneIds.includes(scene.id))
  if (selected.length) return selected
  const description = customScene.trim()
  return description ? [{ id: 'custom', label: '自定义场景', description }] : []
}

export function buildOutfitPlanPrompt(scenes, customScene, settings = {}) {
  const sceneList = scenes.map((scene) => `${scene.id}=${scene.label}：${scene.description}`).join('\n')
  const supplement = scenes.some((scene) => scene.id === 'custom') ? '' : customScene.trim()
  return `参考图 1 是服饰，参考图 2 是模特。请为以下每个拍摄场景分别生成一条中文图片生成提示词：
${sceneList}
${supplement ? `所有场景的补充要求：${supplement}\n` : ''}统一画面规格：${settings.aspectRatio || '3:4'}，${settings.resolution || '1K'}。
严格输出 JSON 数组，格式为 [{"type":"场景ID","prompt":"提示词"}]。每个场景必须且只能出现一次，顺序与请求一致。每条提示词不超过 260 个中文字符，必须说明参考图 1 的服饰穿到参考图 2 的模特身上，保持服饰颜色、版型、材质、纹理、图案和细节，保持模特身份、面部与体型一致；只允许按场景调整姿态、背景、构图和光影；只出现一名模特，不换款，不虚构品牌、文字或配饰，不解释，不使用 Markdown。`
}

export function parseOutfitPlan(content, scenes) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('[')
  const end = source.lastIndexOf(']')
  if (start < 0 || end <= start) throw new Error('未生成有效的穿搭出图方案')

  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error('穿搭出图方案格式异常')
  }
  if (!Array.isArray(parsed)) throw new Error('穿搭出图方案格式异常')

  const prompts = new Map(parsed.map((item) => [item?.type, typeof item?.prompt === 'string' ? item.prompt.trim() : '']))
  const plans = scenes.map((scene) => ({ ...scene, prompt: prompts.get(scene.id) || '' }))
  const missing = plans.filter((plan) => !plan.prompt).map((plan) => plan.label)
  if (missing.length) throw new Error(`穿搭出图方案缺少：${missing.join('、')}`)
  return plans
}
