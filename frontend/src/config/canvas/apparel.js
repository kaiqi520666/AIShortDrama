import { i18n } from '../../i18n/index'

const { t } = i18n.global
const apparelFields = ['name', 'category', 'color', 'material', 'silhouette', 'details']

function text(value) {
  if (Array.isArray(value)) return value.map(String).join('、').trim()
  return typeof value === 'string' || typeof value === 'number' ? String(value).trim() : ''
}

export function createEmptyApparelItem(id = `item-${crypto.randomUUID()}`) {
  return { id, enabled: true, name: '', category: '', color: '', material: '', silhouette: '', details: '' }
}

export function parseApparelProfile(content) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('{')
  const end = source.lastIndexOf('}')
  if (start < 0 || end <= start) throw new Error(t('canvas.invalidApparelResult'))

  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error(t('canvas.invalidApparelFormat'))
  }

  const items = (Array.isArray(parsed.items) ? parsed.items : []).slice(0, 12).map((item, index) => ({
    id: `item-${index + 1}`,
    enabled: true,
    ...Object.fromEntries(apparelFields.map((key) => [key, text(item?.[key])])),
  })).filter((item) => item.name || item.category)
  if (!items.length) throw new Error(t('canvas.apparelNotFound'))

  return {
    compositionType: parsed.compositionType === 'set' || items.length > 1 ? 'set' : 'single',
    summary: text(parsed.summary),
    items,
  }
}

export function apparelPromptContext(profile = {}) {
  const items = (profile.items || []).filter((item) => item.enabled !== false)
  if (!items.length) return ''
  const lines = items.map((item, index) => {
    const details = [
      ['品类', item.category],
      ['颜色', item.color],
      ['面料', item.material],
      ['版型', item.silhouette],
      ['细节', item.details],
    ].filter(([, value]) => value?.trim()).map(([label, value]) => `${label}：${value.trim()}`).join('；')
    return `单品${index + 1}：${item.name?.trim() || item.category?.trim()}${details ? `（${details}）` : ''}`
  })
  return [
    `服饰类型：${profile.compositionType === 'set' ? '整套搭配' : '单件服饰'}`,
    profile.summary?.trim() ? `整体搭配：${profile.summary.trim()}` : '',
    ...lines,
  ].filter(Boolean).join('\n')
}
