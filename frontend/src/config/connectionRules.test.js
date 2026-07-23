import { describe, expect, it } from 'vitest'
import { canConnect, getConnectionError } from './connectionRules'

describe('audio connection rules', () => {
  it('allows audio nodes to feed audio and video generation', () => {
    expect(canConnect('audio', 'video')).toBe(true)
    expect(canConnect('audio', 'audio')).toBe(true)
    expect(canConnect('audio', 'text')).toBe(false)
    expect(canConnect('audio', 'image')).toBe(false)
  })

  it('allows supported inputs and rejects incompatible reference combinations', () => {
    expect(canConnect('text', 'audio')).toBe(true)
    expect(canConnect('image', 'audio')).toBe(true)
    expect(canConnect('video', 'audio')).toBe(false)
    expect(getConnectionError('audio', 'audio', ['image'])).toContain('不能混用')
    expect(getConnectionError('image', 'audio', ['image'])).toContain('最多连接 1 张')
    expect(getConnectionError('audio', 'audio', ['audio', 'audio', 'audio'])).toContain('最多连接 3 条')
  })
})
