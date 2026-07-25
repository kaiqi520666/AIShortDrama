import { describe, expect, it } from 'vitest'
import { canConnect, getConnectionError } from './connectionRules'
import { getNodeTypes, getWorkspaceType } from './nodePacks'

describe('canvas node packs', () => {
  it.each(['general', 'ecommerce', 'drama'])('provides core nodes for %s', (workspaceType) => {
    expect(getNodeTypes(workspaceType)).toEqual(['text', 'image', 'video', 'audio'])
    expect(getWorkspaceType(workspaceType).id).toBe(workspaceType)
  })

  it('keeps existing media connection rules', () => {
    expect(canConnect('image', 'video', 'ecommerce')).toBe(true)
    expect(canConnect('video', 'image', 'drama')).toBe(false)
    expect(getConnectionError('audio', 'audio', ['image'], 'general')).toBe('参考图片和参考音频不能混用')
    expect(canConnect('audio', 'video')).toBe(true)
    expect(canConnect('audio', 'audio')).toBe(true)
    expect(canConnect('audio', 'text')).toBe(false)
    expect(canConnect('audio', 'image')).toBe(false)
    expect(canConnect('text', 'audio')).toBe(true)
    expect(canConnect('image', 'audio')).toBe(true)
    expect(canConnect('video', 'audio')).toBe(false)
    expect(getConnectionError('image', 'audio', ['image'])).toContain('最多连接 1 张')
    expect(getConnectionError('audio', 'audio', ['audio', 'audio', 'audio'])).toContain('最多连接 3 条')
  })
})
