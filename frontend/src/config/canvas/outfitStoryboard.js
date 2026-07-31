import { defaultImageModel } from '../imageModels'
import { defaultVideoModel, getVideoModel, videoAspectRatios } from '../videoModels'
import { storyboardGrid, storyboardShotCount } from './productStoryboard'

export { videoAspectRatios }

export const outfitStoryboardTemplate = {
  id: 'apparel-showcase',
  label: '服饰展示',
  description: '根据服饰、模特与场景参考图生成一张静态故事板和一条视频脚本',
}

export function getApparelVideoSettings(data = {}) {
  const model = getVideoModel(data.videoModel || defaultVideoModel.id)
  const duration = model.durationOptions
    ? model.durationOptions.includes(Number(data.duration)) ? Number(data.duration) : model.defaultDuration
    : Number.isInteger(Number(data.duration)) && Number(data.duration) >= model.durationMin && Number(data.duration) <= model.durationMax
      ? Number(data.duration)
      : model.defaultDuration
  const aspectRatio = model.aspectRatios.includes(data.videoAspectRatio) ? data.videoAspectRatio : model.defaultAspectRatio
  const resolution = model.resolutions.includes(data.videoResolution) ? data.videoResolution : model.defaultResolution
  return { model, duration, aspectRatio, resolution }
}

export function buildOutfitStoryboardPrompt(apparelContext, data = {}) {
  const settings = getApparelVideoSettings(data)
  const grid = storyboardGrid(settings.duration, settings.aspectRatio)
  const context = apparelContext?.trim() || '以图片1中的服饰为准，准确保持服装类别、颜色、面料、版型和细节。'
  const prefix = `图片1是服饰参考图，图片2是模特参考图，图片3是场景参考图。三张图片的引用关系固定不变：图片1只用于锁定服饰，图片2只用于锁定模特身份与外观，图片3只用于锁定环境与光线。请为服饰展示生成一条 ${settings.duration} 秒、${settings.aspectRatio} 画幅的 Seedance 2 视频方案。\n服饰资料：\n`
  const suffix = `${data.prompt?.trim() ? `\n用户补充要求：${data.prompt.trim()}` : ''}\n故事板要求：只输出一张静态 ${grid.columns} 列 × ${grid.rows} 行的分镜故事板，共 ${grid.shots} 个按时间顺序推进的镜头。每格画面要有明确的主体动作、景别、构图、服饰展示重点、场景和光线，格线清晰、间距统一、无任何文字。storyboardPrompt 只描述静态画面，禁止对白、台词、角色说话、口型、声音、音效、环境音、旁白和引号内容。\n视频脚本要求：videoPrompt 必须先写“图片1是分镜故事板，图片2是服饰参考图，图片3是模特参考图，图片4是场景参考图”，再按镜头1至镜头${grid.shots}描述动作、场景、景别、单一运镜、光影和自然衔接。禁止台词、角色说话、口播、旁白、对白、字幕和背景音乐，只保留必要的自然环境音或服装动作音；保持同一服饰、模特身份、发型、体型、颜色、材质、版型和场景一致。\n严格输出一个 JSON 对象，不要 Markdown：{"templateId":"${outfitStoryboardTemplate.id}","title":"${outfitStoryboardTemplate.label}","duration":${settings.duration},"shotCount":${grid.shots},"storyboardPrompt":"镜头1……镜头2……","videoPrompt":"图片1是分镜故事板……镜头1……镜头2……"}`
  return `${prefix}${context.slice(0, Math.max(0, 3000 - prefix.length - suffix.length))}${suffix}`
}

export function parseOutfitStoryboardPlan(content, duration, data = {}) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('{')
  const end = source.lastIndexOf('}')
  if (start < 0 || end <= start) throw new Error('未生成有效的服饰分镜方案')

  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error('服饰分镜方案格式异常')
  }

  const settings = getApparelVideoSettings({ ...data, duration })
  const shotCount = storyboardShotCount(settings.duration)
  if (!parsed || typeof parsed !== 'object' || parsed.templateId !== outfitStoryboardTemplate.id) throw new Error('服饰分镜方案模板异常')
  if (![parsed.storyboardPrompt, parsed.videoPrompt].every((value) => typeof value === 'string' && value.trim())) throw new Error('服饰分镜方案内容不完整')
  if (!hasShots(parsed.storyboardPrompt, shotCount) || !hasShots(parsed.videoPrompt, shotCount)) throw new Error(`服饰分镜必须包含镜头1至镜头${shotCount}`)
  if (hasImagePromptAudio(parsed.storyboardPrompt)) throw new Error('故事板图片提示词不得包含对白或音效')
  if (hasSpeech(parsed.videoPrompt)) throw new Error('服饰视频提示词不得包含台词或角色说话')

  return {
    templateId: outfitStoryboardTemplate.id,
    title: typeof parsed.title === 'string' && parsed.title.trim() ? parsed.title.trim() : outfitStoryboardTemplate.label,
    duration: settings.duration,
    totalDuration: settings.duration,
    shotCount,
    storyboardPrompt: `${parsed.storyboardPrompt.trim()}\n保持指定服饰、模特身份与场景外观一致。\n无文字、水印或额外 Logo。`,
    videoPrompt: `${parsed.videoPrompt.trim()}\n不生成台词、角色说话、旁白、字幕或背景音乐。`,
    imageSettings: { model: defaultImageModel.id, aspectRatio: settings.aspectRatio, resolution: '2K' },
    videoSettings: { model: settings.model.id, duration: settings.duration, aspectRatio: settings.aspectRatio, resolution: settings.resolution, generateAudio: true },
  }
}

function hasShots(value, count) {
  return Array.from({ length: count }, (_, index) => index + 1)
    .every((number) => new RegExp(`镜头\\s*${number}(?!\\d)`).test(value))
}

function hasImagePromptAudio(value) {
  return /(台词|对白|角色说话|口播|旁白|说道|回答|口型|声音|音效|环境音)/.test(value)
}

function hasSpeech(value) {
  return /(台词|对白|角色说话|口播|旁白|说道|回答|口型)/.test(value)
}
