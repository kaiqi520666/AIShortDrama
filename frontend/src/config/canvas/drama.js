import { i18n } from '../../i18n/index'

const { t } = i18n.global
const worldFields = ['overview', 'timeSpace', 'society', 'rules', 'conflict', 'visualGuide']

export const worldOptions = {
  genre: ['都市', '古装', '玄幻', '科幻', '悬疑', '校园', '爱情', '喜剧'],
  era: ['当代', '古代', '近未来', '架空时代', '民国'],
  civilization: ['现实社会', '现代科技', '近未来科技', '魔法文明', '东方仙侠', '末世文明'],
  visualStyle: ['电影写实', '现代都市', '东方美学', '古典国风', '赛博朋克', '动画质感'],
  tone: ['写实', '浪漫', '热血', '轻喜', '暗黑', '悬疑'],
}

export const emptyWorld = () => Object.fromEntries(worldFields.map((key) => [key, '']))

export function buildWorldPrompt(data) {
  const setting = data.setting || {}
  const lines = [
    ['题材', setting.genre],
    ['时代', setting.era],
    ['地域', setting.location],
    ['文明 / 科技', setting.civilization],
    ['社会规则', setting.ruleSeed],
    ['视觉风格', setting.visualStyle],
    ['故事基调', setting.tone],
    ['故事想法', data.prompt],
  ].filter(([, value]) => value?.trim()).map(([label, value]) => `${label}：${value.trim()}`)

  return `你是专业的短剧世界观策划师。根据以下创作条件，补全一套可直接用于角色、场景和分镜创作的世界观：\n${lines.join('\n')}\n\n严格输出一个 JSON 对象，不解释，不使用 Markdown。格式固定为：{"overview":"世界概述","timeSpace":"时空环境","society":"社会结构与阵营","rules":"世界运行规则、能力或科技边界","conflict":"推动故事的核心矛盾","visualGuide":"统一的建筑、服饰、色彩、光影与材质基准"}。每个字段必须是中文字符串，不得为空，不虚构具体品牌，每个字段不超过 320 个中文字符。`
}

export function parseWorldProfile(content) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('{')
  const end = source.lastIndexOf('}')
  if (start < 0 || end <= start) throw new Error(t('canvas.invalidWorldResult'))
  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error(t('canvas.invalidWorldFormat'))
  }
  const world = Object.fromEntries(worldFields.map((key) => [key, typeof parsed[key] === 'string' ? parsed[key].trim() : '']))
  if (worldFields.some((key) => !world[key])) throw new Error(t('canvas.incompleteWorldResult'))
  return world
}

export function worldReady(world = {}) {
  return worldFields.every((key) => world[key]?.trim())
}

export function worldPromptContext(data = {}) {
  const setting = data.setting || {}
  const labels = {
    overview: '世界概述', timeSpace: '时空环境', society: '社会结构与阵营',
    rules: '运行规则与边界', conflict: '核心矛盾', visualGuide: '视觉基准',
  }
  const fields = worldFields.filter((key) => data.world?.[key]?.trim()).map((key) => `${labels[key]}：${data.world[key].trim()}`)
  return [
    `题材：${setting.genre || ''}；时代：${setting.era || ''}；地域：${setting.location || ''}；视觉风格：${setting.visualStyle || ''}`,
    ...fields,
  ].join('\n')
}
