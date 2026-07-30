import { describe, expect, it } from 'vitest'
import { buildOutfitStoryboardPrompt, parseOutfitStoryboardPlan } from './outfitStoryboard'

describe('outfit storyboard prompts', () => {
  it('includes structured apparel data in the Qwen prompt', () => {
    const prompt = buildOutfitStoryboardPrompt('服饰类型：整套搭配\n单品1：蕾丝衬衫（颜色：粉色；面料：蕾丝）', { duration: 15, videoAspectRatio: '9:16' })
    expect(prompt).toContain('单品1：蕾丝衬衫')
    expect(prompt).toContain('颜色：粉色')
    expect(prompt).toContain('参考图片1是一张服饰穿搭参考总览图')
  })

  it('keeps image prompts static and adds no-background-music video guidance', () => {
    const plan = parseOutfitStoryboardPlan(JSON.stringify({
      templateId: 'outfit-showcase',
      title: '服饰展示',
      globalScript: '连续展示服饰',
      segments: [{
        segmentIndex: 1,
        duration: 15,
        shotCount: 6,
        continuityMode: 'cut',
        plotGoal: '展示服饰细节',
        openingState: '正面站立',
        endingState: '场景定格',
        prompt: '镜头1正面；镜头2侧面；镜头3背面；镜头4转身；镜头5面料；镜头6场景。',
        videoPrompt: '镜头1正面；镜头2侧面；镜头3背面；镜头4转身；镜头5面料；镜头6场景。',
      }],
    }), 15)
    expect(plan.segments[0].prompt).toContain('无文字水印')
    expect(plan.segments[0].videoPrompt).toContain('不生成背景音乐')
  })
})
