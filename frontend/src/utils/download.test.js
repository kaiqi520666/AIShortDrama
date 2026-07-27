import { describe, expect, it } from 'vitest'
import { buildDownloadFilename } from './download'

describe('download filename', () => {
  it('keeps a valid extension and sanitizes invalid filename characters', () => {
    expect(buildDownloadFilename('商品/主图.png', 'image/webp', 'https://example.com/image.webp')).toBe('商品_主图.png')
  })

  it('uses the response mime type before the source URL extension', () => {
    expect(buildDownloadFilename('商品主图', 'image/webp', 'https://example.com/image.png')).toBe('商品主图.webp')
  })
})
