import { describe, expect, it } from 'vitest'

import { buildStoryboardProductVideoContext, getEffectivePrompt } from './generationPrompt'

describe('getEffectivePrompt', () => {
  it('merges upstream text while preserving media reference tokens', () => {
    const prompt = getEffectivePrompt({ prompt: '让 @图片1 跟随 @视频1 的运镜，并参考 @音频1' }, [
      { type: 'text', data: { content: '保持产品主体清晰' } },
      { type: 'image', data: { asset: 'image.png' } },
    ])

    expect(prompt).toBe('保持产品主体清晰\n让 @图片1 跟随 @视频1 的运镜，并参考 @音频1')
  })
})

describe('buildStoryboardProductVideoContext', () => {
  it('uses current product data and numbers active references by their actual order', () => {
    const context = buildStoryboardProductVideoContext({
      name: '用户修正名称',
      category: '即食花胶',
      packagingType: '带包装',
      productDimensions: '高8.5cm，直径6cm',
      packageRelation: '6瓶装礼盒',
      sellingPoints: '鲜炖工艺',
      additionalInfo: '玫瑰金瓶盖、蓝色云朵标签',
    }, [
      { id: 'image-1', type: 'image', data: { asset: 'storyboard.png', storyboardSourceId: 'planner-1' } },
      { id: 'storyboard-character-role-1', type: 'image', data: { asset: 'role.png' } },
      { id: 'storyboard-product-product-1', type: 'image', data: { asset: 'product.png' } },
    ], '表现送礼体面')

    expect(context).toContain('图片1是分镜图')
    expect(context).toContain('图片2是角色参考图')
    expect(context).toContain('图片3是商品参考图')
    expect(context).toContain('本次请求的实际图片顺序')
    expect(context).toContain('商品名称：用户修正名称')
    expect(context).toContain('主体尺寸：高8.5cm，直径6cm')
    expect(context).toContain('当前镜头目标：表现送礼体面')
    expect(context).not.toContain('价格：')
  })

  it('renumbers product images when no character reference is active', () => {
    const context = buildStoryboardProductVideoContext({ name: '面霜' }, [
      { id: 'image-1', type: 'image', data: { asset: 'storyboard.png', storyboardSourceId: 'planner-1' } },
      { id: 'storyboard-product-product-1', type: 'image', data: { asset: 'product.png' } },
    ])

    expect(context).toContain('图片2是商品参考图')
    expect(context).not.toContain('角色参考图')
  })
})
