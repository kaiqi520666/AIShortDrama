import { beforeEach, describe, expect, it, vi } from 'vitest'
import { initializeTheme, useTheme } from './useTheme'

let stored
let systemListener
let prefersDark

beforeEach(() => {
  stored = new Map()
  systemListener = null
  prefersDark = false
  globalThis.localStorage = {
    getItem: (key) => stored.get(key) ?? null,
    setItem: (key, value) => stored.set(key, value),
  }
  globalThis.document = { documentElement: { dataset: {}, style: {} } }
  globalThis.window = {
    location: { pathname: '/workspaces/test-id' },
    matchMedia: vi.fn(() => ({
      get matches() { return prefersDark },
      addEventListener: (_, listener) => { systemListener = listener },
      removeEventListener: vi.fn(),
    })),
  }
})

describe('theme', () => {
  it('defaults to the current system theme', () => {
    prefersDark = true
    initializeTheme()

    expect(useTheme().mode.value).toBe('system')
    expect(useTheme().resolvedTheme.value).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('persists manual choices and ignores invalid stored values', () => {
    stored.set('mooncut-theme', 'invalid')
    initializeTheme()
    expect(useTheme().mode.value).toBe('system')

    useTheme().setTheme('light')
    expect(stored.get('mooncut-theme')).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('reacts to system changes only in system mode', () => {
    initializeTheme()
    systemListener({ matches: true })
    expect(document.documentElement.dataset.theme).toBe('dark')

    useTheme().setTheme('light')
    systemListener({ matches: false })
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('restores the saved theme on the workspace list', () => {
    window.location.pathname = '/workspaces'
    stored.set('mooncut-theme', 'light')
    initializeTheme()

    expect(useTheme().mode.value).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('keeps public pages on the fixed dark theme', () => {
    window.location.pathname = '/login'
    stored.set('mooncut-theme', 'light')
    initializeTheme()

    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})
