import { describe, expect, it } from 'vitest'
import {
  buildProductStoryboardPrompt,
  parseProductStoryboardPlan,
  recommendStoryboardSettings,
  storyboardGrid,
  storyboardShotCount,
  storyboardSegmentCount,
  storyboardTemplateRules,
  storyboardTemplates,
  videoAspectRatios,
} from './productStoryboard'

describe('product storyboard planning', () => {
  it('maps 4 to 15 seconds to the expected shot counts', () => {
    expect([4, 6, 9, 12, 15].map(storyboardShotCount)).toEqual([2, 3, 4, 6, 6])
    expect(storyboardGrid(15, '9:16')).toEqual({ shots: 6, columns: 3, rows: 2 })
    expect(storyboardGrid(15, '16:9')).toEqual({ shots: 6, columns: 2, rows: 3 })
    expect(videoAspectRatios).toEqual(['21:9', '16:9', '4:3', '1:1', '3:4', '9:16'])
  })

  it('parses one template into ordered fifteen-second segments', () => {
    const plan = parseProductStoryboardPlan(JSON.stringify({
      templateId: 'ugc-seeding',
      title: 'UGC 种草',
      globalScript: '全局脚本',
      totalDuration: 30,
      segments: [
        { segmentIndex: 1, duration: 15, shotCount: 6, plotGoal: '开场', openingState: '未使用', endingState: '拿起商品', continuityMode: 'cut', prompt: '镜头1 镜头2 镜头3 镜头4 镜头5 镜头6', videoPrompt: '镜头1 镜头2 镜头3 镜头4 镜头5 镜头6' },
        { segmentIndex: 2, duration: 15, shotCount: 6, plotGoal: '结果', openingState: '拿起商品', endingState: '展示商品', continuityMode: 'extend', prompt: '镜头1 镜头2 镜头3 镜头4 镜头5 镜头6', videoPrompt: '镜头1 镜头2 镜头3 镜头4 镜头5 镜头6' },
      ],
    }), [storyboardTemplates[0]])

    expect(storyboardSegmentCount(30)).toBe(2)
    expect(plan.segments.map((segment) => segment.continuityMode)).toEqual(['cut', 'extend'])
    expect(plan.segments.map((segment) => segment.shotCount)).toEqual([6, 6])
    expect(plan.segments[1].videoPrompt).toContain('向后延长视频1')
  })

  it('rejects a segment with fewer than six storyboard shots', () => {
    expect(() => parseProductStoryboardPlan(JSON.stringify({
      templateId: 'ugc-seeding',
      totalDuration: 15,
      segments: [{
        segmentIndex: 1,
        duration: 15,
        shotCount: 6,
        plotGoal: '开场',
        openingState: '未使用',
        endingState: '拿起商品',
        continuityMode: 'cut',
        prompt: '镜头1 镜头2 镜头3',
        videoPrompt: '镜头1 镜头2 镜头3',
      }],
    }), [storyboardTemplates[0]])).toThrow('必须包含镜头1至镜头6')
  })

  it('rejects dialogue or audio in an image prompt', () => {
    const shots = '镜头1 镜头2 镜头3 镜头4 镜头5 镜头6'
    expect(() => parseProductStoryboardPlan(JSON.stringify({
      templateId: 'ugc-seeding',
      totalDuration: 15,
      segments: [{
        segmentIndex: 1,
        duration: 15,
        shotCount: 6,
        plotGoal: '开场',
        openingState: '未使用',
        endingState: '拿起商品',
        continuityMode: 'cut',
        prompt: `${shots}，她说道："测试"`,
        videoPrompt: shots,
      }],
    }), [storyboardTemplates[0]])).toThrow('图片提示词不得包含对白或音效')
  })

  it('recommends editable image settings from duration and video ratio', () => {
    expect(recommendStoryboardSettings(9, '9:16')).toEqual(expect.objectContaining({ shots: 4, aspectRatio: '9:16', resolution: '2K' }))
    expect(recommendStoryboardSettings(15, '9:16')).toEqual(expect.objectContaining({ shots: 6, aspectRatio: '4:5', resolution: '4K' }))
  })

  it('builds one bounded prompt for every selected template', () => {
    const prompt = buildProductStoryboardPrompt('商品名称：测试商品\n核心卖点：轻便耐用'.repeat(200), storyboardTemplates, {
      duration: 8,
      videoAspectRatio: '9:16',
      prompt: '节奏轻快',
    })
    expect(prompt.length).toBeLessThanOrEqual(3000)
    expect(prompt).toContain('ugc-seeding=UGC 种草')
    expect(prompt).toContain('reaction=反应展示')
    expect(prompt).toContain('生活化自拍视频')
    expect(prompt).toContain('首次反应')
    expect(prompt).toContain('3 个镜头')
    expect(prompt).toContain('3 列 × 1 行')
    expect(prompt).toContain('videoPrompt')
    expect(prompt).toContain('不超过 500 个中文字符')
    expect(prompt).toContain('所有镜头禁止出现人脸')
    expect(prompt).toContain('画外音说道')
    expect(prompt).toContain('禁止生成背景音乐')
    expect(Object.keys(storyboardTemplateRules)).toEqual(storyboardTemplates.map((item) => item.id))
  })

  it('requires six shots for each fifteen-second segment', () => {
    const prompt = buildProductStoryboardPrompt('商品资料', [storyboardTemplates[0]], { duration: 15 })
    expect(prompt).toContain('shotCount=6')
    expect(prompt).toContain('镜头1、镜头2、镜头3、镜头4、镜头5、镜头6')
    expect(prompt).toContain('六个镜头分别对应分镜板的六个格子')
  })

  it('orders parsed prompts by selected template order', () => {
    const plans = parseProductStoryboardPlan('[{"type":"sales-drama","prompt":"短剧分镜","videoPrompt":"短剧视频"},{"type":"ugc-seeding","prompt":"种草分镜","videoPrompt":"种草视频"}]', storyboardTemplates.slice(0, 2))
    expect(plans.map((item) => item.prompt)).toEqual([
      '种草分镜\n禁止出现人脸、正脸、侧脸及面部局部，人物仅可出现手部、背影或肩部以下。\n无文字水印。',
      '短剧分镜\n禁止出现人脸、正脸、侧脸及面部局部，人物仅可出现手部、背影或肩部以下。\n无文字水印。',
    ])
    expect(plans.map((item) => item.videoPrompt)).toEqual([
      '种草视频\n全程禁止出现人脸及面部局部；参考图片2为商品参考图。\n不生成背景音乐。',
      '短剧视频\n全程禁止出现人脸及面部局部；参考图片2为商品参考图。\n不生成背景音乐。',
    ])
  })

  it('locks a selected character in image and video prompts', () => {
    const character = { name: '测试角色', url: 'https://example.com/character.png', assetUrl: 'asset://pa_test' }
    const prompt = buildProductStoryboardPrompt('测试商品', storyboardTemplates.slice(0, 1), { characterReference: character })
    const fullPrompt = buildProductStoryboardPrompt('商品资料'.repeat(1000), storyboardTemplates, { productReferences: [{}, {}, {}], characterReference: character })
    const plans = parseProductStoryboardPlan('[{"type":"ugc-seeding","prompt":"人物分镜","videoPrompt":"人物视频"}]', storyboardTemplates.slice(0, 1), character)
    expect(fullPrompt.length).toBeLessThanOrEqual(3000)
    expect(prompt).toContain('参考图 2 是指定出镜角色')
    expect(prompt).toContain('她说道')
    expect(prompt).toContain('口型与声音同步')
    expect(prompt).toContain('禁止写成“台词：”')
    expect(plans[0].prompt).toContain('参考图2为指定出镜角色')
    expect(plans[0].videoPrompt).toContain('参考图片2为指定出镜角色')
  })

  it('labels independent product references before the character reference', () => {
    const prompt = buildProductStoryboardPrompt('测试商品', storyboardTemplates.slice(0, 1), {
      productReferences: [
        { id: 'product-1', name: '正面图', url: 'https://example.com/product-1.png' },
        { id: 'product-2', name: '细节图', url: 'https://example.com/product-2.png' },
      ],
      characterReference: { name: '测试角色', url: 'https://example.com/character.png' },
    })
    expect(prompt).toContain('图片1、图片2是商品参考图')
    expect(prompt).toContain('参考图 3 是指定出镜角色')
    const plans = parseProductStoryboardPlan('[{"type":"ugc-seeding","prompt":"分镜","videoPrompt":"视频"}]', storyboardTemplates.slice(0, 1), { url: 'https://example.com/character.png', assetUrl: 'asset://character' }, 2)
    expect(plans[0].videoPrompt).toContain('参考图片2为指定出镜角色')
    expect(plans[0].videoPrompt).toContain('参考图片3、参考图片4为商品参考图')
  })

  it('rejects incomplete template plans', () => {
    expect(() => parseProductStoryboardPlan('[{"type":"ugc-seeding","prompt":"种草分镜"}]', storyboardTemplates.slice(0, 1))).toThrow('缺少')
  })

  it('rejects duplicate and unknown template types', () => {
    expect(() => parseProductStoryboardPlan('[{"type":"ugc-seeding"},{"type":"ugc-seeding"}]', storyboardTemplates.slice(0, 2))).toThrow('类型重复')
    expect(() => parseProductStoryboardPlan('[{"type":"ugc-seeding"},{"type":"unknown"}]', storyboardTemplates.slice(0, 2))).toThrow('未知类型')
  })
})
