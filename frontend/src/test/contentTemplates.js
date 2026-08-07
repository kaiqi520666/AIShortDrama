import { useContentTemplatesStore } from '../stores/contentTemplates'

export const contentTemplatesFixture = {
  product_visual: {
    key: 'product_visual',
    version: 1,
    enabled: true,
    config: {
      groups: [
        { id: 'basic', label: '基础展示', items: [{ id: 'white-bg', label: '白底图', default_enabled: true }, { id: 'first-screen', label: '首屏主视觉', default_enabled: true }, { id: 'multi-angle', label: '多角度', default_enabled: false }, { id: 'series-show', label: '系列 SKU', default_enabled: false }] },
        { id: 'marketing', label: '营销卖点', items: [{ id: 'core-selling', label: '核心卖点', default_enabled: true }, { id: 'use-scenario', label: '使用场景', default_enabled: true }, { id: 'ambient-scene', label: '氛围场景', default_enabled: true }, { id: 'contrast-effect', label: '效果对比', default_enabled: false }] },
        { id: 'detail', label: '详情说明', items: [{ id: 'detail-zoom', label: '细节图', default_enabled: true }, { id: 'specs-info', label: '规格尺寸', default_enabled: false }, { id: 'tech-specs', label: '参数表', default_enabled: false }, { id: 'manufacturing', label: '工艺', default_enabled: false }, { id: 'ingredients', label: '成分', default_enabled: false }] },
        { id: 'trust', label: '信任保障', items: [{ id: 'brand-story', label: '品牌故事', default_enabled: false }, { id: 'freebies', label: '配件 / 赠品', default_enabled: false }, { id: 'warranty', label: '售后保障', default_enabled: false }, { id: 'usage-tips', label: '使用建议', default_enabled: false }] },
      ],
      business_instruction: '',
    },
  },
  product_storyboard: {
    key: 'product_storyboard',
    version: 1,
    enabled: true,
    config: {
      templates: [{ id: 'ugc-seeding', label: 'UGC 种草', description: '用户视角真实分享体验', enabled: true }],
      durations: [15, 30, 45, 60],
      business_instruction: '以真实用户体验分享为主，不设置复杂剧情，不使用广告腔，开头尽快出现商品并通过实际操作和试吃表达感受。',
    },
  },
}

export function seedContentTemplates() {
  useContentTemplatesStore().$patch({ templates: structuredClone(contentTemplatesFixture), error: '' })
}
