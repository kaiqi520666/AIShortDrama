import { describe, expect, it } from 'vitest'
import {
  buildProductStoryboardPrompt,
  buildStoryboardReferenceManifest,
  createStoryboardTemplates,
  getStoryboardDurations,
  getStoryboardProductLimit,
  getStoryboardTemplates,
  MAX_STORYBOARD_REFERENCES,
  parseProductStoryboardPlan,
  recommendStoryboardSettings,
  storyboardGrid,
  storyboardSegmentCount,
  storyboardShotCount,
} from './productStoryboard'
import { modelCapabilitiesFixture } from '../../test/modelCapabilities'
import { contentTemplatesFixture } from '../../test/contentTemplates'
import { normalizeImageModels } from '../imageModels'
import { normalizeVideoModels } from '../videoModels'

const imageModels = normalizeImageModels(modelCapabilitiesFixture.image)
const defaultImageModel = imageModels.find(({ id }) => id === modelCapabilitiesFixture.image.default_model)
const videoModels = normalizeVideoModels(modelCapabilitiesFixture.video)
const videoAspectRatios = videoModels.find(({ id }) => id === modelCapabilitiesFixture.video.default_model).aspectRatios
const template = contentTemplatesFixture.product_storyboard
const storyboardTemplates = getStoryboardTemplates(template)
const storyboardDurations = getStoryboardDurations(template)

const shotText = (prefix = '') => Array.from({ length: 6 }, (_, index) => `${prefix}镜头${index + 1}：具体动作`).join('；')

function planJson(overrides = {}) {
  return JSON.stringify({
    templateId: 'ugc-seeding',
    title: 'UGC 种草',
    globalScript: '真实体验分享',
    totalDuration: 15,
    segments: [{
      segmentIndex: 1,
      duration: 15,
      shotCount: 6,
      plotGoal: '开头直接展示商品',
      openingState: '人物拿起商品',
      endingState: '完成试吃分享',
      continuityMode: 'cut',
      prompt: shotText(),
      videoPrompt: `图片1是本段分镜图，图片2是角色1参考图，图片3是商品参考图。${shotText('她说道："体验分享"；')}`,
      ...overrides,
    }],
  })
}

describe('product storyboard planning', () => {
  it('only exposes the UGC seeding template', () => {
    expect(storyboardTemplates).toEqual([{ id: 'ugc-seeding', label: 'UGC 种草', description: '用户视角真实分享体验', enabled: true }])
    expect(createStoryboardTemplates(template)).toEqual(storyboardTemplates)
  })

  it('keeps the six-shot storyboard layout and supported durations', () => {
    expect([4, 6, 9, 12, 15].map(storyboardShotCount)).toEqual([2, 3, 4, 6, 6])
    expect(storyboardGrid(15, '9:16')).toEqual({ shots: 6, columns: 3, rows: 2 })
    expect(storyboardGrid(15, '16:9')).toEqual({ shots: 6, columns: 2, rows: 3 })
    expect(storyboardSegmentCount(30, storyboardDurations)).toBe(2)
    expect(videoAspectRatios).toEqual(['21:9', '16:9', '4:3', '1:1', '3:4', '9:16'])
  })

  it('caps combined character and product references at six', () => {
    const characters = [1, 2, 3].map((index) => ({ id: `character-${index}`, url: `https://example.com/character-${index}.png` }))
    const products = [1, 2, 3, 4, 5].map((index) => ({ id: `product-${index}`, url: `https://example.com/product-${index}.png` }))
    const manifest = buildStoryboardReferenceManifest(characters, products)
    expect(MAX_STORYBOARD_REFERENCES).toBe(6)
    expect(manifest.references).toHaveLength(6)
    expect(manifest.products).toHaveLength(3)
    expect(getStoryboardProductLimit(1)).toBe(5)
    expect(getStoryboardProductLimit(3)).toBe(3)
  })

  it('gives GPT-5.6 Sol the complete UGC image and video contract', () => {
    const prompt = buildProductStoryboardPrompt('商品名称：测试商品\n核心卖点：口感顺滑', {
      duration: 30,
      videoAspectRatio: '9:16',
      characterReferences: [{ url: 'https://example.com/character.png' }],
      productReferences: [{ url: 'https://example.com/product.png' }],
      prompt: '场景在家庭餐桌和办公室之间切换',
    }, videoAspectRatios, template)
    expect(prompt).toContain('只保留“UGC 种草”这一种内容')
    expect(prompt).toContain('全程由人物本人或同行者真实手持手机拍摄')
    expect(prompt).toContain('前置广角')
    expect(prompt).toContain('后置1倍主摄')
    expect(prompt).toContain('不使用三脚架、稳定器、滑轨、机械推镜')
    expect(prompt).toContain('镜头之间直接硬切')
    expect(prompt).toContain('生图prompt要求')
    expect(prompt).toContain('生视频prompt要求')
    expect(prompt).toContain('3列×2行')
    expect(prompt).toContain('每个小格保持9:16视频画幅')
    expect(prompt).toContain('图片1是角色1参考图。图片2是商品参考图。')
    expect(prompt).toContain('图片1是本段分镜图，图片2是角色1参考图，图片3是商品参考图。')
    expect(prompt).toContain('segments必须恰好2条')
    expect(prompt).toContain('templateId必须始终为“ugc-seeding”')
  })

  it('preserves GPT-generated prompts without program camera or reference rewrites', () => {
    const exactPrompt = shotText('镜头动作：')
    const exactVideo = `图片1是本段分镜图。${shotText('角色1说道："自然分享"；')}`
    const plan = parseProductStoryboardPlan(planJson({ prompt: exactPrompt, videoPrompt: exactVideo }), template)
    expect(plan.templateId).toBe('ugc-seeding')
    expect(plan.segments[0].prompt).toBe(exactPrompt)
    expect(plan.segments[0].videoPrompt).toBe(exactVideo)
  })

  it('accepts multiple ordered segments and keeps continuity from GPT', () => {
    const parsed = JSON.parse(planJson())
    parsed.totalDuration = 30
    parsed.segments.push({
      ...parsed.segments[0],
      segmentIndex: 2,
      plotGoal: '继续试吃分享',
      openingState: '上一段完成开盖',
      endingState: '结束口感评价',
      continuityMode: 'extend',
    })
    const plan = parseProductStoryboardPlan(JSON.stringify(parsed), template)
    expect(plan.segments.map((segment) => segment.continuityMode)).toEqual(['cut', 'extend'])
    expect(plan.segments).toHaveLength(2)
  })

  it('rejects non-UGC or incomplete plans', () => {
    expect(() => parseProductStoryboardPlan(JSON.stringify({ templateId: 'other', segments: [] }), template)).toThrow('UGC')
    expect(() => parseProductStoryboardPlan(planJson({ prompt: '镜头1：动作；镜头2：动作；镜头3：动作', videoPrompt: shotText() }), template)).toThrow('必须包含镜头1至镜头6')
  })

  it('recommends image settings from duration and aspect ratio', () => {
    expect(recommendStoryboardSettings(9, '9:16', defaultImageModel)).toEqual(expect.objectContaining({ shots: 4, aspectRatio: '9:16', resolution: '2K' }))
    expect(recommendStoryboardSettings(15, '9:16', defaultImageModel)).toEqual(expect.objectContaining({ shots: 6, aspectRatio: '4:5', resolution: '4K' }))
  })
})
