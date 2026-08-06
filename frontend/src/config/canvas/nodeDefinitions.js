import { Clapperboard, FileText, Globe2, Image, Images, Music2, Package, Shirt, UserRound, Video } from 'lucide-vue-next'
import { createProductVisualItems } from './productVisual'
import { createStoryboardTemplates } from './productStoryboard'
import { emptyWorld } from './drama'
import { emptyCharacterProfile } from './character'

const reversePrompts = {
  image: '根据图片生成结构化中文提示词，包括主体描述、环境、光影、镜头语言、风格关键词。',
}

function createTextData(number, source, models) {
  const reverseType = source?.type === 'image' ? 'image' : null
  const textTask = Boolean(source)
  return {
    model: models.text.id,
    title: reverseType ? `${nodeDefinitions[reverseType].label}反推提示词` : textTask ? `AI 文本任务 ${number}` : `文本节点 ${number}`,
    status: 'empty',
    prompt: reverseType ? reversePrompts[reverseType] : '',
    textMode: textTask ? 'task' : null,
    content: '',
    ...(reverseType ? { reverseType } : {}),
  }
}

export const nodeDefinitions = {
  text: {
    type: 'text', label: '文本', model: '', hint: '商品资料与生成要求',
    placeholder: '输入商品信息、卖点或生成要求…', setting: '多模态文本 · 中文', icon: FileText,
    generationPanel: true, inputs: ['text', 'image'], outputs: ['text', 'image', 'video', 'audio'],
    createData: ({ number, source, models }) => createTextData(number, source, models),
  },
  image: {
    type: 'image', label: '图片', model: 'Moon Image', hint: '商品图与视觉生成',
    placeholder: '描述你想生成的商品画面，@ 引用素材…', setting: '16:9 · 2K', icon: Image,
    generationPanel: true, inputs: ['text', 'image', 'product', 'product_visual', 'product_storyboard', 'outfit', 'apparel_storyboard', 'character'], outputs: ['text', 'image', 'video', 'audio', 'product', 'apparel', 'outfit', 'apparel_storyboard', 'character'],
    createData: ({ number, models }) => ({ model: models.image.id, title: `图片节点 ${number}`, status: 'empty', prompt: '' }),
  },
  video: {
    type: 'video', label: '视频', model: 'Seedance 2 Mini', hint: '商品展示与广告视频',
    placeholder: '描述商品动作、运镜和节奏…', setting: '16:9 · 720P · 10s', icon: Video,
    generationPanel: true, inputs: ['text', 'image', 'video', 'audio', 'product'], outputs: ['text', 'video'],
    createData: ({ number, models }) => ({ model: models.video.id, title: `视频节点 ${number}`, status: 'empty', prompt: '', generateAudio: true, returnLastFrame: true }),
  },
  audio: {
    type: 'audio', label: '音频', model: 'seed-audio-1.0-multilingual', hint: '广告旁白与商品讲解',
    placeholder: '描述旁白、音效或声音氛围，@ 引用音频…', setting: 'MP3 · 48 kHz', icon: Music2,
    generationPanel: true, inputs: ['text', 'image', 'audio'], outputs: ['audio', 'video'],
    createData: ({ number, models }) => ({ model: models.audio.model.id, title: `音频节点 ${number}`, status: 'empty', prompt: '' }),
  },
  product: {
    type: 'product', label: '商品创作', model: '', hint: '识别商品并创建整套商品图',
    placeholder: '可选：补充识别要求，例如重点读取容量、材质或包装文字…', setting: '', icon: Package,
    generationPanel: true, inputs: ['image'], outputs: ['product_visual', 'product_storyboard', 'image', 'video'],
    createData: ({ number, models }) => ({
      title: `商品创作 ${number}`,
      status: 'empty',
      workflowStep: 'recognition',
      model: models.text.id,
      textModel: models.text.id,
      imageModel: models.image.id,
      aspectRatio: models.image.defaultAspectRatio,
      resolution: models.image.defaultResolution,
      items: createProductVisualItems(),
      prompt: '',
      product: {
        name: '', brand: '', category: '', price: '', specifications: '', packagingType: '', productDimensions: '',
        packageDimensions: '', packageRelation: '', scaleReference: '', sellingPoints: '', audience: '', scenario: '', additionalInfo: '',
      },
    }),
  },
  product_visual: {
    type: 'product_visual', label: '商品出图', model: '', hint: '批量规划商品套图与详情图',
    setting: '17 类商品图', icon: Images,
    inputs: ['product'], outputs: ['image'],
    createData: ({ number, models }) => ({
      title: `商品出图 ${number}`,
      status: 'empty',
      textModel: models.text.id,
      imageModel: models.image.id,
      aspectRatio: models.image.defaultAspectRatio,
      resolution: models.image.defaultResolution,
      items: createProductVisualItems(),
    }),
  },
  product_storyboard: {
    type: 'product_storyboard', label: '商品分镜', model: '', hint: '生成 UGC 种草多格分镜板与视频脚本',
    setting: 'UGC 种草 · 15/30/45/60 秒', icon: Clapperboard,
    inputs: ['product'], outputs: ['image'],
    createData: ({ number, models }) => ({
      title: `商品分镜 ${number}`,
      status: 'empty',
      textModel: models.text.id,
      duration: 30,
      videoAspectRatio: '9:16',
      templateId: 'ugc-seeding',
      templates: createStoryboardTemplates(),
      productReferences: [],
      characterReferences: [],
      prompt: '',
      generatedNodeIds: [],
    }),
  },
  apparel: {
    type: 'apparel', label: '服饰资料', model: '', hint: '识别并编辑单品与整套搭配资料',
    placeholder: '补充识别重点，例如重点区分配饰、鞋履或面料…', setting: '服饰图 + AI 识别', icon: Shirt,
    inputs: ['image'], outputs: ['outfit', 'apparel_storyboard'],
    createData: ({ number, models }) => ({
      title: `服饰资料 ${number}`,
      status: 'empty',
      model: models.text.id,
      compositionType: 'single',
      summary: '',
      items: [],
      prompt: '',
    }),
  },
  outfit: {
    type: 'outfit', label: '服饰穿搭', model: '', hint: '生成固定六格 9:16 / 1K 穿搭参考图板',
    setting: '服饰资料 + 模特图 · 6 格 9:16 / 1K', icon: Shirt,
    inputs: ['apparel', 'image'], outputs: ['image', 'apparel_storyboard'],
    createData: ({ number, models }) => ({
      title: `服饰穿搭 ${number}`,
      status: 'empty',
      textModel: models.text.id,
      imageModel: models.image.id,
      aspectRatio: '9:16',
      resolution: '1K',
      moduleIds: ['front', 'three-quarter', 'back', 'turn', 'fabric', 'lifestyle'],
      customRequirement: '',
      generatedNodeIds: [],
    }),
  },
  apparel_storyboard: {
    type: 'apparel_storyboard', label: '服饰分镜', model: '', hint: '自动创建服饰、角色和场景输入，生成故事板',
    setting: '自动创建 3 个输入节点', icon: Clapperboard,
    inputs: ['apparel', 'image'], outputs: ['image'],
    createData: ({ number, models }) => ({
      title: `服饰分镜 ${number}`,
      status: 'empty',
      textModel: models.text.id,
      videoModel: models.video.id,
      duration: models.video.defaultDuration,
      videoAspectRatio: models.video.defaultAspectRatio,
      videoResolution: models.video.defaultResolution,
      generateAudio: true,
      prompt: '',
      generatedNodeIds: [],
    }),
  },
  world: {
    type: 'world', label: '世界观创作', model: '', hint: '生成统一的短剧世界设定',
    setting: '设定输入 + 世界观结果', icon: Globe2,
    inputs: [], outputs: ['character'],
    createData: ({ number, models }) => ({
      title: `世界观创作 ${number}`,
      status: 'empty',
      workflowStep: 'setting',
      model: models.text.id,
      prompt: '',
      setting: {
        genre: '都市',
        era: '当代',
        location: '',
        civilization: '现实社会',
        ruleSeed: '',
        visualStyle: '电影写实',
        tone: '写实',
      },
      world: emptyWorld(),
    }),
  },
  character: {
    type: 'character', label: '角色创作', model: '', hint: '生成角色档案与统一设定图',
    setting: '角色设定 + 3 张设定图', icon: UserRound,
    inputs: ['world', 'image'], outputs: ['image'],
    createData: ({ number, models }) => ({
      title: `角色创作 ${number}`,
      status: 'empty',
      workflowStep: 'profile',
      model: models.text.id,
      textModel: models.text.id,
      imageModel: models.image.id,
      aspectRatio: '3:4',
      resolution: models.image.defaultResolution,
      prompt: '',
      setting: { roleType: '主角', gender: '女', ageStage: '青年', visualStyle: '电影写实' },
      profile: emptyCharacterProfile(),
      generatedNodeIds: [],
      mainReferenceNodeId: '',
    }),
  },
}

export function getNodeDefinition(type) {
  const definition = nodeDefinitions[type]
  if (!definition) throw new Error(`不支持的节点类型：${type}`)
  return definition
}

export function createNodeData(type, number, source, models) {
  if (!models?.text || !models.image || !models.video || !models.audio) throw new Error('模型能力尚未加载')
  return getNodeDefinition(type).createData({ number, source, models })
}

export function getReversePrompt(type) {
  return reversePrompts[type]
}
