export const demoNodes = [
  {
    id: 'text-1',
    type: 'text',
    position: { x: 60, y: 180 },
    data: {
      title: '主图生成要求',
      status: 'ready',
      content: '产品居中，白色影棚背景，柔和侧光，突出金属质感，不添加文字。',
      prompt: '将商品卖点整理为简洁的电商主图提示词。',
    },
  },
  {
    id: 'image-1',
    type: 'image',
    position: { x: 600, y: 120 },
    data: {
      title: '商品原图',
      status: 'ready',
      asset: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=85',
      prompt: '保留产品造型和材质，清理背景。',
    },
  },
  {
    id: 'image-2',
    type: 'image',
    position: { x: 600, y: 500 },
    data: {
      title: '场景参考',
      status: 'ready',
      asset: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=1000&q=85',
      prompt: '简洁商业摄影，明亮背景，保留充足留白。',
    },
  },
  {
    id: 'video-1',
    type: 'video',
    position: { x: 1130, y: 240 },
    data: { title: '商品展示视频', status: 'empty', prompt: '' },
  },
  {
    id: 'audio-1',
    type: 'audio',
    position: { x: 1130, y: 590 },
    data: { title: '广告旁白', status: 'empty', prompt: '' },
  },
]

export const demoEdges = [
  { id: 'edge-1', source: 'text-1', target: 'image-1', type: 'cinematic' },
  { id: 'edge-2', source: 'image-1', target: 'video-1', type: 'cinematic' },
  { id: 'edge-3', source: 'image-2', target: 'video-1', type: 'cinematic' },
  { id: 'edge-4', source: 'text-1', target: 'audio-1', type: 'cinematic' },
]
