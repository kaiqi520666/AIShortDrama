import { describe, expect, it } from 'vitest'
import { canConnect } from './connectionRules'

describe('audio connection rules', () => {
  it('only allows audio nodes to connect to video nodes', () => {
    expect(canConnect('audio', 'video')).toBe(true)
    expect(canConnect('audio', 'text')).toBe(false)
    expect(canConnect('audio', 'image')).toBe(false)
    expect(canConnect('audio', 'audio')).toBe(false)
  })

  it('does not allow incoming connections to audio nodes', () => {
    expect(['text', 'image', 'video', 'audio'].every((type) => !canConnect(type, 'audio'))).toBe(true)
  })
})
