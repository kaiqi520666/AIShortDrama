export const mediaTypes = {
  text: {
    label: '文本',
    model: 'Qwen 3.5',
    hint: '商品资料与生成要求',
    placeholder: '输入商品信息、卖点或生成要求…',
    setting: '文本生成 · 中文',
  },
  image: {
    label: '图片',
    model: 'Lib Image',
    hint: '商品图与视觉生成',
    placeholder: '描述你想生成的商品画面，@ 引用素材…',
    setting: '16:9 · 2K',
  },
  video: {
    label: '视频',
    model: 'Seedance 2.0',
    hint: '商品展示与广告视频',
    placeholder: '描述商品动作、运镜和节奏…',
    setting: '16:9 · 720P · 5s',
  },
  audio: {
    label: '音频',
    model: 'MiniMax Speech',
    hint: '广告旁白与商品讲解',
    placeholder: '输入要合成的商品旁白…',
    setting: '自然女声 · 1.0x',
  },
}
