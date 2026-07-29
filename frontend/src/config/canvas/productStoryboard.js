import { defaultImageModel } from '../imageModels'

export const storyboardTemplates = [
  { id: 'ugc-seeding', label: 'UGC 种草', description: '用户视角真实分享体验' },
  { id: 'sales-drama', label: '带货短剧', description: '短剧情节植入产品' },
  { id: 'product-demo', label: '产品演示', description: '多角度展示与使用演示' },
  { id: 'product-pitch', label: '产品口播', description: '面对镜头讲解产品卖点' },
  { id: 'tvc', label: 'TVC 广告', description: '品牌广告片质感' },
  { id: 'pain-solution', label: '痛点解决', description: '痛点场景到产品解决' },
  { id: 'unboxing', label: '开箱种草', description: '第一视角拆包惊喜体验' },
  { id: 'reaction', label: '反应展示', description: '首次使用的惊喜反应' },
]

export const videoAspectRatios = ['9:16', '16:9', '1:1']

export function createStoryboardTemplates() {
  return storyboardTemplates.map((item, index) => ({ ...item, enabled: index === 0 }))
}

export function storyboardShotCount(duration) {
  const seconds = Math.min(15, Math.max(4, Number(duration) || 4))
  if (seconds <= 5) return 2
  if (seconds <= 8) return 3
  if (seconds <= 11) return 4
  return 6
}

export function storyboardGrid(duration, videoAspectRatio = '9:16') {
  const shots = storyboardShotCount(duration)
  const portrait = ratioValue(videoAspectRatio) <= 1
  const layouts = portrait
    ? { 2: [2, 1], 3: [3, 1], 4: [2, 2], 6: [3, 2] }
    : { 2: [1, 2], 3: [1, 3], 4: [2, 2], 6: [2, 3] }
  const [columns, rows] = layouts[shots]
  return { shots, columns, rows }
}

export function recommendStoryboardSettings(duration, videoAspectRatio = '9:16', model = defaultImageModel) {
  const grid = storyboardGrid(duration, videoAspectRatio)
  const targetRatio = grid.columns * ratioValue(videoAspectRatio) / grid.rows
  const aspectRatio = model.aspectRatios.reduce((best, value) => (
    Math.abs(ratioValue(value) - targetRatio) < Math.abs(ratioValue(best) - targetRatio) ? value : best
  ))
  const preferredResolution = grid.shots === 6 ? '4K' : '2K'
  const resolution = model.resolutions.includes(preferredResolution)
    ? preferredResolution
    : model.resolutions.at(-1) || model.defaultResolution
  return { ...grid, aspectRatio, resolution }
}

export function buildProductStoryboardPrompt(productContext, templates, data = {}) {
  const duration = Math.min(15, Math.max(4, Number(data.duration) || 4))
  const ratio = videoAspectRatios.includes(data.videoAspectRatio) ? data.videoAspectRatio : '9:16'
  const grid = storyboardGrid(duration, ratio)
  const types = templates.map((item) => `${item.id}=${item.label}：${item.description}`).join('\n')
  const extra = data.prompt?.trim() ? `\n用户补充要求：${data.prompt.trim()}` : ''
  const character = data.characterReference
  const characterRule = character?.url
    ? `参考图 2 是指定出镜角色“${character.name}”。每个有人物的镜头必须保持其身份、人脸、发型、体型和服装一致，videoPrompt 必须说明参考图片2用于锁定出镜角色。`
    : '所有镜头禁止出现人脸、正脸、侧脸或面部局部；人物只允许出现手部、背影或肩部以下，口播与反应改为画外音、手部动作或商品特写。'
  const prefix = `参考图 1 是商品。${character?.url ? '参考图 2 是指定出镜角色。' : ''}请为以下每种商品短视频模板同时生成“多格分镜板图片提示词”和“Seedance 2 视频提示词”：\n${types}\n总时长：${duration} 秒；每个模板 ${grid.shots} 个镜头；分镜板采用 ${grid.columns} 列 × ${grid.rows} 行；每个小格保持 ${ratio} 视频画幅。\n商品资料：\n`
  const suffix = `${extra}\n严格输出 JSON 数组，格式为 [{"type":"模板ID","prompt":"分镜板图片提示词","videoPrompt":"Seedance 2 视频提示词"}]。每个模板必须且只能出现一次，顺序与请求一致。prompt 必须描述 ${grid.shots} 个按时间顺序推进且内容不同的镜头，明确每格的主体动作、景别、场景、构图和光线，整张图是边界清楚、间距统一的专业分镜板。videoPrompt 不超过 500 个中文字符，必须以“参考图片1中的分镜图”开头，明确按从左到右、从上到下依次生成 ${ratio}、${duration} 秒视频，并按镜头顺序描述主体动作、场景、景别、单一运镜、光影和自然衔接。${characterRule}同一商品的外观、颜色、材质、包装和品牌标识必须与参考图一致；不生成标题、编号、字幕、价格、二维码、水印、乱码或额外 Logo，不虚构商品功能，不解释，不使用 Markdown。`
  return `${prefix}${productContext.slice(0, Math.max(0, 3000 - prefix.length - suffix.length))}${suffix}`
}

export function parseProductStoryboardPlan(content, templates, characterReference = null) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('[')
  const end = source.lastIndexOf(']')
  if (start < 0 || end <= start) throw new Error('未生成有效的商品分镜方案')
  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error('商品分镜方案格式异常')
  }
  if (!Array.isArray(parsed)) throw new Error('商品分镜方案格式异常')
  const results = new Map(parsed.map((item) => [item?.type, item]))
  const plans = templates.map((item) => {
    const result = results.get(item.id)
    const imageRule = characterReference?.url
      ? '参考图2为指定出镜角色，所有镜头保持其身份、人脸、发型、体型和服装一致。'
      : '禁止出现人脸、正脸、侧脸及面部局部，人物仅可出现手部、背影或肩部以下。'
    const videoRule = characterReference?.assetUrl
      ? '参考图片2为指定出镜角色，必须保持人物身份与外貌一致。'
      : '全程禁止出现人脸及面部局部。'
    return {
      ...item,
      prompt: typeof result?.prompt === 'string' ? `${result.prompt.trim()}\n${imageRule}\n无文字水印。` : '',
      videoPrompt: typeof result?.videoPrompt === 'string' ? `${result.videoPrompt.trim()}\n${videoRule}` : '',
    }
  })
  const missing = plans.filter((item) => !item.prompt || !item.videoPrompt).map((item) => item.label)
  if (missing.length) throw new Error(`商品分镜方案缺少：${missing.join('、')}`)
  return plans
}

function ratioValue(value) {
  const [width, height] = String(value).split(':').map(Number)
  return width > 0 && height > 0 ? width / height : 1
}
