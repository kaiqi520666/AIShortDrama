import { describe, expect, it } from 'vitest'
import { buildOutfitStoryboardPrompt, getApparelVideoSettings, outfitStoryboardTemplate, parseOutfitStoryboardPlan } from './outfitStoryboard'

describe('apparel storyboard prompts', () => {
  it('names the three apparel references and uses the selected video duration', () => {
    const prompt = buildOutfitStoryboardPrompt('服饰类型：整套搭配\n单品1：蕾丝衬衫（颜色：粉色；面料：蕾丝）', { duration: 8, videoAspectRatio: '9:16' })
    expect(prompt).toContain('图片1是服饰参考图，图片2是角色（模特）参考图，图片3是场景参考图')
    expect(prompt).toContain('单品1：蕾丝衬衫')
    expect(prompt).toContain('一张静态 3 列 × 1 行')
    expect(prompt).toContain('严格输出一个 JSON 对象')
  })

  it('parses one static storyboard prompt and one speech-free video prompt', () => {
    const plan = parseOutfitStoryboardPlan(JSON.stringify({
      templateId: outfitStoryboardTemplate.id,
      title: '服饰展示',
      duration: 5,
      shotCount: 2,
      storyboardPrompt: '镜头1正面站姿，展示版型；镜头2侧面走动，展示垂坠。',
      videoPrompt: '图片1是分镜故事板，图片2是服饰参考图，图片3是模特参考图，图片4是场景参考图。镜头1固定镜头展示正面版型，镜头2缓慢跟拍展示走动效果，保留脚步声。',
    }), 5)
    expect(plan.duration).toBe(5)
    expect(plan.shotCount).toBe(2)
    expect(plan.storyboardPrompt).toContain('无文字')
    expect(plan.videoPrompt).toContain('不生成台词')
    expect(getApparelVideoSettings({ duration: 5 }).duration).toBe(5)
  })
})
