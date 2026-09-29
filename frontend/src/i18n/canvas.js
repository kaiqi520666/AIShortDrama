import { i18n } from './index'

// Only use for fixed catalog/option copy, never prompts, names or generated text.
export function canvasLabel(label) {
  const messages = i18n.global.tm('canvas.labels')
  return Object.hasOwn(messages, label) ? i18n.global.rt(messages[label]) : label
}

export function canvasOptions(options) {
  return options.map((option) => ({ ...option, label: canvasLabel(option.label) }))
}

const templateDefaults = {
  basic: ['基础展示'], marketing: ['营销卖点'], detail: ['详情说明'], trust: ['信任保障'],
  'white-bg': ['白底图'], 'first-screen': ['首屏主视觉'], 'multi-angle': ['多角度'], 'series-show': ['系列 SKU'],
  'core-selling': ['核心卖点'], 'use-scenario': ['使用场景'], 'ambient-scene': ['氛围场景'], 'contrast-effect': ['效果对比'],
  'detail-zoom': ['细节图'], 'specs-info': ['规格尺寸'], 'tech-specs': ['参数表'], manufacturing: ['工艺'], ingredients: ['成分'],
  'brand-story': ['品牌故事'], freebies: ['配件 / 赠品'], warranty: ['售后保障'], 'usage-tips': ['使用建议'],
  'ugc-seeding': ['UGC 种草', '用户视角真实分享体验'],
  'commerce-drama': ['短剧带货', '通过剧情内容完成商品植入与转化'],
}

export function canvasTemplateText(id, value, field = 'label') {
  const original = templateDefaults[id]?.[field === 'description' ? 1 : 0]
  return original !== undefined && value === original ? canvasLabel(value) : value
}
