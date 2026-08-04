import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'

describe('auth credit pricing', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('estimates image, video, text and audio credits', () => {
    const store = useAuthStore()
    store.creditPrices = [
      { media_type: 'image', model: 'gpt-image-2', specification: '2K', unit_credits: 4, freeze_credits: 4 },
      { media_type: 'video', model: 'seedance-2', specification: '', unit_credits: 26, freeze_credits: 26 },
      { media_type: 'text', model: 'gpt-5.6-sol', specification: '', unit_credits: 1, freeze_credits: 1 },
      { media_type: 'audio', model: 'seed-audio-1.0-multilingual', specification: '', unit_credits: 29, freeze_credits: 60 },
    ]

    expect(store.estimateCredits('image', 'gpt-image-2', { resolution: '2K' })).toBe(4)
    expect(store.estimateCredits('video', 'seedance-2', { duration: 5 })).toBe(130)
    expect(store.estimateCredits('text', 'gpt-5.6-sol')).toBe(1)
    expect(store.estimateCredits('audio', 'seed-audio-1.0-multilingual')).toBe(60)
  })
})
