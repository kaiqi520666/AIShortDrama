import { describe, expect, it } from 'vitest'
import { uploadRules, validateUploadFile } from './useCanvasDropUpload'

describe('canvas drop uploads', () => {
  it('accepts supported media within the configured limit', () => {
    expect(validateUploadFile('image', { type: 'image/png', size: 1024 })).toBe('')
  })

  it('rejects unsupported formats and oversized files', () => {
    expect(validateUploadFile('image', { type: 'image/gif', size: 1024 })).toContain('不支持的图片格式')
    expect(validateUploadFile('video', { type: 'video/mp4', size: uploadRules.video.maxSize + 1 })).toContain('文件不能超过')
    expect(validateUploadFile('document', { type: 'text/plain', size: 1 })).toBe('不支持的上传类型')
  })
})
