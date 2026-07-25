import { FileText, Image, Music2, Video } from 'lucide-vue-next'
import { defaultImageModel } from '../imageModels'
import { defaultReverseModel } from '../reverseModels'
import { defaultVideoModel } from '../videoModels'

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
    generationPanel: true, inputs: ['text', 'image'], outputs: ['text', 'image', 'video', 'audio'],
    createData: ({ number }) => ({ model: defaultImageModel.id, title: `图片节点 ${number}`, status: 'empty', prompt: '' }),
  },
  video: {
    type: 'video', label: '视频', model: 'Seedance 2.0', hint: '商品展示与广告视频',
    placeholder: '描述商品动作、运镜和节奏…', setting: '16:9 · 720P · 5s', icon: Video,
    generationPanel: true, inputs: ['text', 'image', 'video', 'audio'], outputs: ['text', 'video'],
    createData: ({ number }) => ({ model: defaultVideoModel.id, title: `视频节点 ${number}`, status: 'empty', prompt: '' }),
  },
  audio: {
    type: 'audio', label: '音频', model: 'seed-audio-1.0-multilingual', hint: '广告旁白与商品讲解',
    placeholder: '描述旁白、音效或声音氛围，@ 引用音频…', setting: 'MP3 · 48 kHz', icon: Music2,
    generationPanel: true, inputs: ['text', 'image', 'audio'], outputs: ['audio', 'video'],
    createData: ({ number }) => ({ model: 'seed-audio-1.0-multilingual', title: `音频节点 ${number}`, status: 'empty', prompt: '' }),
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
