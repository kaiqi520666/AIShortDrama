import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getGenerationCapabilities } from '../api/generations'
import { modelCapabilitiesFixture } from '../test/modelCapabilities'
import { useModelCapabilitiesStore } from './modelCapabilities'

vi.mock('../api/generations', () => ({ getGenerationCapabilities: vi.fn() }))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('model capabilities store', () => {
  it('normalizes API capabilities and selects server defaults', async () => {
    getGenerationCapabilities.mockResolvedValue({ code: 0, data: modelCapabilitiesFixture })
    const store = useModelCapabilitiesStore()

    await store.load()

    expect(store.defaultImageModel.id).toBe('gpt-image-2')
    expect(store.defaultVideoModel.id).toBe('seedance-2-mini')
    expect(store.defaultVideoModel.aspectRatios).not.toContain('adaptive')
    expect(store.audioCapability.defaults.sampleRate).toBe(48000)
  })

  it('exposes an error and retries without a hardcoded fallback', async () => {
    getGenerationCapabilities
      .mockRejectedValueOnce(new Error('服务暂不可用'))
      .mockResolvedValueOnce({ code: 0, data: modelCapabilitiesFixture })
    const store = useModelCapabilitiesStore()

    await expect(store.load()).rejects.toThrow('服务暂不可用')
    expect(store.capabilities).toBeNull()
    expect(store.error).toBe('服务暂不可用')

    await store.load()
    expect(store.error).toBe('')
    expect(store.capabilities.version).toBe(1)
  })
})
