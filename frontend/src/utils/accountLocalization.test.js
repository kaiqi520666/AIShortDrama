import { afterEach, expect, it } from 'vitest'
import { computed } from 'vue'
import { readFileSync } from 'node:fs'
import { i18n } from '../i18n'
import { localizeAccountText } from './accountLocalization'

afterEach(() => { i18n.global.locale.value = 'id' })

it('updates API labels and system notes when the locale changes', () => {
  const label = computed(() => localizeAccountText('视频生成'))
  i18n.global.locale.value = 'zh-CN'
  expect(label.value).toBe('视频生成')
  i18n.global.locale.value = 'id'
  expect(label.value).toBe('Pembuatan video')
  expect(localizeAccountText('参考图片')).toBe('Gambar referensi')
  expect(localizeAccountText('是')).toBe('Ya')
  expect(localizeAccountText('15 秒')).toBe('15 detik')
  expect(localizeAccountText('每日免费积分补足')).toBe('Pengisian ulang kredit gratis harian')
  expect(localizeAccountText('结算 seedance 生成积分')).toBe('Penyelesaian kredit pembuatan seedance')
  expect(localizeAccountText('冻结 seedance 生成积分')).toBe('Penahanan kredit pembuatan seedance')
  expect(localizeAccountText('充值 IDR 1200，赠送 10 积分')).toBe('Isi ulang IDR 1200, bonus 10 kredit')
  expect(localizeAccountText('管理员自定义备注')).toBe('管理员自定义备注')
  expect(localizeAccountText(null)).toBe(null)
})

it.each([
  '../views/dashboard/GenerationHistoryView.vue',
  '../components/account/CreditLedgerPanel.vue',
  '../components/account/BillingStandardsPanel.vue',
])('has translations for every page key in %s', (file) => {
  const source = readFileSync(new URL(file, import.meta.url), 'utf8')
  const keys = [...source.matchAll(/\bt\('([^']+)'/g)].map((match) => match[1])
  expect(keys.length).toBeGreaterThan(0)
  for (const locale of ['zh-CN', 'id']) {
    for (const key of keys) expect(i18n.global.te(key, locale), key).toBe(true)
  }
})
