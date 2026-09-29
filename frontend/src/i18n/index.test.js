import { afterEach, describe, expect, it, vi } from 'vitest'
import { i18n, initializeLocale, LOCALE_STORAGE_KEY, resolveInitialLocale, setLocale, formatNumber } from './index'
import zhCN from './locales/zh-CN.json'
import id from './locales/id.json'

afterEach(() => {
  vi.unstubAllGlobals()
  i18n.global.locale.value = 'id'
})

function flatten(value, prefix = '') {
  return Object.fromEntries(Object.entries(value).flatMap(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof item === 'object' ? Object.entries(flatten(item, path)) : [[path, item]]
  }))
}

describe('interface languages', () => {
  it.each([
    ['zh-CN', ['id-ID'], 'zh-CN'],
    ['id', ['zh-TW'], 'id'],
    [null, ['en-US', 'zh-TW', 'id'], 'zh-CN'],
    [null, ['id-ID', 'zh-CN'], 'id'],
    [null, ['en', 'fr'], 'id'],
    ['en', ['zh-HK'], 'zh-CN'],
    [null, [], 'id'],
    [null, ['identity', 'zhang', 'zh-CN'], 'zh-CN'],
  ])('resolves %s / %j as %s', (stored, languages, expected) => {
    expect(resolveInitialLocale(stored, languages)).toBe(expected)
  })

  it('matches dictionary keys and interpolation parameters', () => {
    const chinese = flatten(zhCN)
    const indonesian = flatten(id)
    expect(Object.keys(indonesian).sort()).toEqual(Object.keys(chinese).sort())
    for (const [key, value] of Object.entries(chinese)) {
      expect(indonesian[key].trim(), key).not.toBe('')
      expect((indonesian[key].match(/\{[^}]+\}/g) || []).sort(), key).toEqual((value.match(/\{[^}]+\}/g) || []).sort())
    }
  })

  it('initializes without persisting a browser-derived preference', () => {
    const storage = { getItem: vi.fn(() => null), setItem: vi.fn() }
    vi.stubGlobal('localStorage', storage)
    vi.stubGlobal('navigator', { languages: ['en', 'zh-TW'] })
    vi.stubGlobal('document', { documentElement: { lang: '' } })
    initializeLocale()
    expect(i18n.global.locale.value).toBe('zh-CN')
    expect(document.documentElement.lang).toBe('zh-CN')
    expect(storage.setItem).not.toHaveBeenCalled()
  })

  it('persists an explicit selection and updates the document language', () => {
    const setItem = vi.fn()
    vi.stubGlobal('localStorage', { setItem })
    vi.stubGlobal('document', { documentElement: { lang: '' } })
    setLocale('zh-CN')
    expect(setItem).toHaveBeenCalledWith(LOCALE_STORAGE_KEY, 'zh-CN')
    expect(document.documentElement.lang).toBe('zh-CN')
    expect(i18n.global.t('common.save')).toBe('保存')
    setLocale('id')
    expect(i18n.global.t('common.save')).toBe('Simpan')
  })

  it('works when browser storage is blocked', () => {
    vi.stubGlobal('localStorage', {
      getItem() { throw new Error('blocked') },
      setItem() { throw new Error('blocked') },
    })
    expect(() => initializeLocale()).not.toThrow()
    expect(() => setLocale('zh-CN')).not.toThrow()
  })

  it('formats numbers with the active locale without converting values', () => {
    i18n.global.locale.value = 'id'
    expect(formatNumber(1234.5)).toBe(new Intl.NumberFormat('id').format(1234.5))
    i18n.global.locale.value = 'zh-CN'
    expect(formatNumber(1234.5)).toBe(new Intl.NumberFormat('zh-CN').format(1234.5))
  })
})
