import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN.json'
import id from './locales/id.json'

export const LOCALE_STORAGE_KEY = 'mooncut-locale'
export const SUPPORTED_LOCALES = ['zh-CN', 'id']

function normalizeLocale(value) {
  if (typeof value !== 'string') return ''
  const locale = value.toLowerCase()
  if (/^zh(?:-|$)/.test(locale)) return 'zh-CN'
  if (/^id(?:-|$)/.test(locale)) return 'id'
  return ''
}

export function resolveInitialLocale(stored, browserLocales = []) {
  if (SUPPORTED_LOCALES.includes(stored)) return stored
  return browserLocales.map(normalizeLocale).find(Boolean) || 'id'
}

export const i18n = createI18n({
  legacy: false,
  locale: 'id',
  fallbackLocale: 'id',
  messages: { 'zh-CN': zhCN, id },
})

export function setLocale(locale) {
  const nextLocale = SUPPORTED_LOCALES.includes(locale) ? locale : 'id'
  i18n.global.locale.value = nextLocale
  try { globalThis.localStorage?.setItem(LOCALE_STORAGE_KEY, nextLocale) } catch { /* Storage can be blocked by browser policy. */ }
  if (globalThis.document) document.documentElement.lang = nextLocale
}

export function initializeLocale() {
  let stored
  try { stored = globalThis.localStorage?.getItem(LOCALE_STORAGE_KEY) } catch { /* Use browser preferences when storage is unavailable. */ }
  const browser = globalThis.navigator
  const languages = browser?.languages?.length ? browser.languages : [browser?.language]
  const locale = resolveInitialLocale(stored, languages)
  i18n.global.locale.value = locale
  if (globalThis.document) document.documentElement.lang = locale
}

export function formatDateTime(value, options = {}) {
  return new Intl.DateTimeFormat(i18n.global.locale.value, options).format(new Date(value))
}

export function formatNumber(value, options = {}) {
  return new Intl.NumberFormat(i18n.global.locale.value, options).format(value)
}
