import { FileText, Globe2, Image, Images, Music2, Package, Shirt, Video } from 'lucide-vue-next'
import { defaultImageModel } from '../imageModels'
import { defaultReverseModel } from '../reverseModels'
import { defaultVideoModel } from '../videoModels'
import { createProductVisualItems } from './productVisual'
import { emptyWorld } from './drama'

const reversePrompts = {
  image: '根据图片生成结构化中文提示词，包括主体描述、环境、光影、镜头语言、风格关键词。',
  video: '根据视频生成结构化中文提示词，包括主体与场景、动作、运镜、景别、光影色彩、节奏转场、声音氛围和风格关键词，并按时间顺序描述关键画面。',
}

function createTextData(number, source) {
  const reverseType = ['image', 'video'].includes(source?.type) ? source.type : null
  const textTask = Boolean(source)
  return {
    model: reverseType ? defaultReverseModel.id : 'Qwen3-VL-Flash',
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
    type: 'text', label: '文本', model: 'Qwen3-VL-Flash', hint: '商品资料与生成要求',
    placeholder: '输入商品信息、卖点或生成要求…', setting: '多模态文本 · 中文', icon: FileText,
    generationPanel: true, inputs: ['text', 'image', 'video'], outputs: ['text', 'image', 'video', 'audio'],
    createData: ({ number, source }) => createTextData(number, source),
  },
  image: {
    type: 'image', label: '图片', model: 'Moon Image', hint: '商品图与视觉生成',
    placeholder: '描述你想生成的商品画面，@ 引用素材…', setting: '16:9 · 2K', icon: Image,
    generationPanel: true, inputs: ['text', 'image', 'product', 'product_visual', 'outfit'], outputs: ['text', 'image', 'video', 'audio', 'product', 'outfit'],
    createData: ({ number }) => ({ model: defaultImageModel.id, title: `图片节点 ${number}`, status: 'empty', prompt: '' }),
  },
  video: {
    type: 'video', label: '视频', model: 'Seedance 2.0', hint: '商品展示与广告视频',
    placeholder: '描述商品动作、运镜和节奏…', setting: '16:9 · 720P · 5s', icon: Video,
    generationPanel: true, inputs: ['text', 'image', 'video', 'audio', 'product'], outputs: ['text', 'video'],
    createData: ({ number }) => ({ model: defaultVideoModel.id, title: `视频节点 ${number}`, status: 'empty', prompt: '' }),
  },
  audio: {
    type: 'audio', label: '音频', model: 'seed-audio-1.0-multilingual', hint: '广告旁白与商品讲解',
    placeholder: '描述旁白、音效或声音氛围，@ 引用音频…', setting: 'MP3 · 48 kHz', icon: Music2,
    generationPanel: true, inputs: ['text', 'image', 'audio'], outputs: ['audio', 'video'],
    createData: ({ number }) => ({ model: 'seed-audio-1.0-multilingual', title: `音频节点 ${number}`, status: 'empty', prompt: '' }),
  },
  product: {
    type: 'product', label: '商品创作', model: '', hint: '识别商品并创建整套商品图',
    placeholder: '可选：补充识别要求，例如重点读取容量、材质或包装文字…', setting: '', icon: Package,
    generationPanel: true, inputs: ['image'], outputs: ['product_visual', 'image', 'video'],
    createData: ({ number }) => ({
      title: `商品创作 ${number}`,
      status: 'empty',
      workflowStep: 'recognition',
      model: defaultReverseModel.id,
      textModel: defaultReverseModel.id,
      imageModel: defaultImageModel.id,
      aspectRatio: defaultImageModel.defaultAspectRatio,
      resolution: defaultImageModel.defaultResolution,
      items: createProductVisualItems(),
      prompt: '',
      product: { name: '', brand: '', category: '', price: '', specifications: '', sellingPoints: '', audience: '', scenario: '', additionalInfo: '' },
    }),
  },
  product_visual: {
    type: 'product_visual', label: '商品出图', model: defaultReverseModel.id, hint: '批量规划商品套图与详情图',
    setting: '17 类商品图', icon: Images,
    inputs: ['product'], outputs: ['image'],
    createData: ({ number }) => ({
      title: `商品出图 ${number}`,
      status: 'empty',
      textModel: defaultReverseModel.id,
      imageModel: defaultImageModel.id,
      aspectRatio: defaultImageModel.defaultAspectRatio,
      resolution: defaultImageModel.defaultResolution,
      items: createProductVisualItems(),
    }),
  },
  outfit: {
    type: 'outfit', label: '服饰穿搭', model: defaultReverseModel.id, hint: '规划多场景服饰穿搭图',
    setting: '服饰图 + 模特图', icon: Shirt,
    inputs: ['image'], outputs: ['image'],
    createData: ({ number }) => ({
      title: `服饰穿搭 ${number}`,
      status: 'empty',
      textModel: defaultReverseModel.id,
      imageModel: defaultImageModel.id,
      aspectRatio: defaultImageModel.defaultAspectRatio,
      resolution: defaultImageModel.defaultResolution,
      sceneIds: ['studio'],
      customScene: '',
      generatedNodeIds: [],
    }),
  },
  world: {
    type: 'world', label: '世界观创作', model: defaultReverseModel.id, hint: '生成统一的短剧世界设定',
    setting: '设定输入 + 世界观结果', icon: Globe2,
    inputs: [], outputs: [],
    createData: ({ number }) => ({
      title: `世界观创作 ${number}`,
      status: 'empty',
      workflowStep: 'setting',
      model: defaultReverseModel.id,
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
}

export function getNodeDefinition(type) {
  const definition = nodeDefinitions[type]
  if (!definition) throw new Error(`不支持的节点类型：${type}`)
  return definition
}

export function createNodeData(type, number, source) {
  return getNodeDefinition(type).createData({ number, source })
}

export function getReversePrompt(type) {
  return reversePrompts[type]
}
