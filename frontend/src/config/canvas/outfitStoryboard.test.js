import { describe, expect, it } from 'vitest'
import { buildOutfitStoryboardRequest, parseOutfitStoryboardPlan } from './outfitStoryboard'
import { contentTemplatesFixture } from '../../test/contentTemplates'

const template = contentTemplatesFixture.apparel_showcase
const shots = Array.from({ length: 6 }, (_, index) => `镜头${index + 1}：展示动作`).join('；')

describe('apparel storyboard prompts', () => {
  it('builds a structured multi-segment request with an optional scene', () => {
    const request = buildOutfitStoryboardRequest({
      workspaceId: 'workspace-1',
      nodeId: 'storyboard-1',
      model: 'gpt-5.6-sol',
      template,
      outfitBoardUrl: 'https://example.com/board.png',
      garmentUrl: 'https://example.com/garment.png',
      modelUrl: 'https://example.com/model.png',
      sceneUrl: 'https://example.com/scene.png',
      apparelContext: '单品1：白色衬衫',
      duration: 30,
      videoAspectRatio: '9:16',
      userRequirement: '自然行走',
    })
    expect(request).not.toHaveProperty('prompt')
    expect(request.media_urls).toHaveLength(3)
    expect(request.template_context).toEqual(expect.objectContaining({ duration: 30, scene_count: 1 }))
  })

  it('parses 15-second segments with cut and extend continuity', () => {
    const plan = parseOutfitStoryboardPlan(JSON.stringify({
      templateId: 'apparel-showcase',
      title: '服饰展示',
      globalScript: '先展示整体，再展示动态细节',
      totalDuration: 30,
      segments: [
        { segmentIndex: 1, duration: 15, shotCount: 6, plotGoal: '整体造型', openingState: '模特入场', endingState: '正面定格', continuityMode: 'cut', prompt: shots, videoPrompt: shots },
        { segmentIndex: 2, duration: 15, shotCount: 6, plotGoal: '动态细节', openingState: '承接定格', endingState: '转身收尾', continuityMode: 'extend', prompt: shots, videoPrompt: shots },
      ],
    }), template)
    expect(plan.totalDuration).toBe(30)
    expect(plan.segments).toHaveLength(2)
    expect(plan.segments[1].continuityMode).toBe('extend')
  })
})
