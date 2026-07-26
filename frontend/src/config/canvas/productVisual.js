export const productVisualGroups = [
  {
    id: 'basic',
    label: '基础展示',
    items: [
      { id: 'white-bg', label: '白底图' },
      { id: 'first-screen', label: '首屏主视觉' },
      { id: 'multi-angle', label: '多角度' },
      { id: 'series-show', label: '系列 SKU' },
    ],
  },
  {
    id: 'marketing',
    label: '营销卖点',
    items: [
      { id: 'core-selling', label: '核心卖点' },
      { id: 'use-scenario', label: '使用场景' },
      { id: 'ambient-scene', label: '氛围场景' },
      { id: 'contrast-effect', label: '效果对比' },
    ],
  },
  {
    id: 'detail',
    label: '详情说明',
    items: [
      { id: 'detail-zoom', label: '细节图' },
      { id: 'specs-info', label: '规格尺寸' },
      { id: 'tech-specs', label: '参数表' },
      { id: 'manufacturing', label: '工艺' },
      { id: 'ingredients', label: '成分' },
    ],
  },
  {
    id: 'trust',
    label: '信任保障',
    items: [
      { id: 'brand-story', label: '品牌故事' },
      { id: 'freebies', label: '配件 / 赠品' },
      { id: 'warranty', label: '售后保障' },
      { id: 'usage-tips', label: '使用建议' },
    ],
  },
]

export const productVisualTypes = productVisualGroups.flatMap((group) => group.items)

const defaultTypeIds = new Set(['white-bg', 'first-screen', 'core-selling', 'use-scenario', 'ambient-scene', 'detail-zoom'])

export function createProductVisualItems() {
  return productVisualTypes.map((item) => ({ ...item, enabled: defaultTypeIds.has(item.id), count: 1 }))
}
