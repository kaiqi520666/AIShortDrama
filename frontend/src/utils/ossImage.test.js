import { describe, expect, it } from 'vitest'
import { buildOssImageUrl } from './ossImage'

describe('buildOssImageUrl', () => {
  it('adds the canvas preview process by default', () => {
    expect(buildOssImageUrl('https://image.example.com/original.png')).toBe(
      'https://image.example.com/original.png?x-oss-process=image/resize,w_1024/quality,q_85/format,webp',
    )
  })

  it('preserves other parameters and replaces an existing image process', () => {
    expect(buildOssImageUrl(
      'https://image.example.com/original.png?token=abc&x-oss-process=image/resize,w_480/quality,q_80/format,webp#preview',
      { width: 480, quality: 80 },
    )).toBe(
      'https://image.example.com/original.png?token=abc&x-oss-process=image/resize,w_480/quality,q_80/format,webp#preview',
    )
  })

  it('leaves local and empty URLs unchanged', () => {
    expect(buildOssImageUrl('/api/assets/1/content')).toBe('/api/assets/1/content')
    expect(buildOssImageUrl('blob:local-preview')).toBe('blob:local-preview')
    expect(buildOssImageUrl('')).toBe('')
  })
})
