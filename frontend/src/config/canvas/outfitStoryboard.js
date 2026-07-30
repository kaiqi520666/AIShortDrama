import { videoAspectRatios } from '../videoModels'
import { storyboardDurations, storyboardSegmentCount, storyboardSegmentShotCount } from './productStoryboard'

export { storyboardDurations, videoAspectRatios }

export const outfitStoryboardTemplate = {
  id: 'outfit-showcase',
  label: '服饰展示',
  description: '连续展示版型、走动、面料与场景穿搭',
}

export function buildOutfitStoryboardPrompt(outfitContext, data = {}) {
  const duration = storyboardDurations.includes(Number(data.duration)) ? Number(data.duration) : 15
  const segments = storyboardSegmentCount(duration)
  const ratio = videoAspectRatios.includes(data.videoAspectRatio) ? data.videoAspectRatio : '9:16'
  const segmentRules = Array.from({ length: segments }, (_, index) => {
    const segmentIndex = index + 1
    return `第${segmentIndex}段（15秒）：输出 segmentIndex=${segmentIndex}、duration=15、shotCount=6、continuityMode="${segmentIndex === 1 ? 'cut' : 'extend'}"、plotGoal、openingState、endingState、prompt、videoPrompt。prompt 和 videoPrompt 必须严格写镜头1至镜头6，分别对应六格服饰分镜图。`
  }).join('\n')
  const extra = data.prompt?.trim() ? `\n用户补充要求：${data.prompt.trim()}` : ''
  return `参考图片1是一张服饰穿搭参考总览图，按从左到右、从上到下依次为正面全身、45°侧面、背面展示、转身定格、面料细节、场景穿搭。只读取总览图中的服饰、模特外观和搭配信息，不复制六格宫格布局。请为“${outfitStoryboardTemplate.label}”生成总时长 ${duration} 秒、${ratio} 画幅的连续服饰展示视频方案，拆成 ${segments} 个连续的15秒段落。\n${segmentRules}\n服饰资料：${outfitContext || '以参考图片1为准。'}${extra}\n严格输出一个 JSON 对象，不要 Markdown：{"templateId":"outfit-showcase","title":"服饰展示","globalScript":"全局脚本","segments":[{"segmentIndex":1,"duration":15,"shotCount":6,"plotGoal":"剧情目标","openingState":"开场状态","endingState":"结束状态","continuityMode":"cut","prompt":"镜头1……镜头2……镜头3……镜头4……镜头5……镜头6……","videoPrompt":"镜头1……镜头2……镜头3……镜头4……镜头5……镜头6……"}]}。segments 必须恰好 ${segments} 条且按顺序。prompt 只描述静态画面、主体动作、版型、服饰状态、场景、景别、构图和光线，禁止对白、台词、说话、口型、声音、音效、环境音、旁白和引号内容。videoPrompt 描述主体动作、场景、景别、单一运镜、光影、自然衔接和现场环境音；每个15秒段落至少安排2句简短角色口播，使用“模特说道：\"……\"”或“模特回答：\"……\"”，必须说明口型与声音同步，不要写“台词：”。面料和裙摆等纯特写镜头可延续上一镜声音。不生成背景音乐、字幕、Logo、水印、价格、二维码、乱码或额外文字。保持同一套服饰、模特身份、发型、体型、颜色、材质和搭配一致。`
}

export function parseOutfitStoryboardPlan(content, duration) {
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

  const totalDuration = Number(duration)
  const expectedSegments = storyboardSegmentCount(totalDuration)
  if (parsed.templateId !== outfitStoryboardTemplate.id || !Array.isArray(parsed.segments) || parsed.segments.length !== expectedSegments) {
    throw new Error(`服饰分镜段落数量应为 ${expectedSegments} 条`)
  }

  const segments = parsed.segments.map((segment, index) => {
    const segmentIndex = Number(segment?.segmentIndex) || index + 1
    if (segmentIndex !== index + 1 || Number(segment?.duration) !== 15 || Number(segment?.shotCount) !== storyboardSegmentShotCount || !['extend', 'cut'].includes(segment?.continuityMode)) {
      throw new Error('服饰分镜段落顺序、时长、镜头数量或衔接方式异常')
    }
    if (![segment.plotGoal, segment.openingState, segment.endingState, segment.prompt, segment.videoPrompt].every((value) => typeof value === 'string' && value.trim())) {
      throw new Error('服饰分镜段落内容不完整')
    }
    if (!hasSixShots(segment.prompt) || !hasSixShots(segment.videoPrompt)) throw new Error(`第${index + 1}段必须包含镜头1至镜头6`)
    if (hasImagePromptAudio(segment.prompt)) throw new Error(`第${index + 1}段图片提示词不得包含对白或音效`)
    if (countCharacterSpeech(segment.videoPrompt) < 2 || /台词\s*[:：]/.test(segment.videoPrompt)) throw new Error(`第${index + 1}段视频提示词至少需要 2 句角色说话，且不要使用“台词：”格式`)
    return {
      segmentIndex,
      duration: 15,
      shotCount: storyboardSegmentShotCount,
      plotGoal: segment.plotGoal.trim(),
      openingState: segment.openingState.trim(),
      endingState: segment.endingState.trim(),
      continuityMode: index === 0 ? 'cut' : segment.continuityMode,
      prompt: `${segment.prompt.trim()}\n保持指定服饰、模特身份与外观一致。\n无文字水印。`,
      videoPrompt: `${segment.videoPrompt.trim()}\n不生成背景音乐。`,
    }
  })

  return {
    templateId: outfitStoryboardTemplate.id,
    title: typeof parsed.title === 'string' && parsed.title.trim() ? parsed.title.trim() : outfitStoryboardTemplate.label,
    globalScript: typeof parsed.globalScript === 'string' ? parsed.globalScript.trim() : '',
    totalDuration,
    segments,
  }
}

function hasSixShots(value) {
  return Array.from({ length: storyboardSegmentShotCount }, (_, index) => index + 1)
    .every((number) => new RegExp(`(?:镜头|第)\\s*${number}(?:格)?`).test(value))
}

function hasImagePromptAudio(value) {
  return /(说道|说：|说“|台词|对白|口型|声音|音效|环境音|现场音|旁白)/.test(value)
}

function countCharacterSpeech(value) {
  return (value.match(/(?:说道|回答)\s*[:：]?/g) || []).length
}
