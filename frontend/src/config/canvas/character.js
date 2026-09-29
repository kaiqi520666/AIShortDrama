import { i18n } from '../../i18n/index'

const { t } = i18n.global
const profileFields = ['name', 'identity', 'background', 'appearance', 'personality', 'costume', 'signature', 'constraints']

export const characterOptions = {
  roleType: ['主角', '反派', '重要配角', '导师', '群像角色'],
  gender: ['女', '男', '非限定'],
  ageStage: ['少年', '青年', '中年', '老年'],
  visualStyle: ['电影写实', '现代都市', '东方美学', '古典国风', '赛博朋克', '动画质感'],
}

export const characterVisualTypes = [
  { id: 'full-body', label: '正面全身', description: '正面站姿，全身完整入镜，清楚展示体型和服装结构' },
  { id: 'portrait', label: '半身肖像', description: '正面半身肖像，清楚展示面部、发型和标志性特征' },
  { id: 'turnaround', label: '角色三视图', description: '同一画面展示正面、侧面和背面，比例与服装保持一致' },
]

export const emptyCharacterProfile = () => Object.fromEntries(profileFields.map((key) => [key, '']))

export function characterProfileContext(profile = {}) {
  const labels = {
    name: '角色姓名', identity: '身份职业', background: '人物背景', appearance: '外貌特征',
    personality: '性格与动机', costume: '服装造型', signature: '标志性特征', constraints: '一致性约束',
  }
  return profileFields.filter((key) => profile[key]?.trim()).map((key) => `${labels[key]}：${profile[key].trim()}`).join('\n')
}

export function buildCharacterProfilePrompt(worldContext, data, hasReference = false) {
  const setting = data.setting || {}
  return `你是专业的短剧角色设定师。根据世界观、创作条件和用户想法补全角色档案。${hasReference ? '参考图片是角色外形依据，必须保留可见的脸型、五官、发型、体型和辨识特征。' : ''}
世界观：
${worldContext}
创作条件：角色定位=${setting.roleType || ''}；性别=${setting.gender || ''}；年龄阶段=${setting.ageStage || ''}；视觉风格=${setting.visualStyle || ''}
用户想法：${data.prompt?.trim() || ''}

严格输出一个 JSON 对象，不解释，不使用 Markdown。格式固定为：{"name":"角色姓名","identity":"身份职业与剧情定位","background":"与世界观相符的人物背景","appearance":"脸型、五官、发型、体型与年龄感","personality":"性格、欲望、弱点与行为习惯","costume":"固定服装、配色、材质与配饰","signature":"不可替换的标志性特征","constraints":"后续画面必须保持一致的身份、面部、体型、发型、服装与特征"}。每个字段必须是中文字符串且不得为空，每个字段不超过 260 个中文字符，不虚构具体品牌。`
}

export function parseCharacterProfile(content) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('{')
  const end = source.lastIndexOf('}')
  if (start < 0 || end <= start) throw new Error(t('canvas.invalidCharacterResult'))
  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error(t('canvas.invalidCharacterFormat'))
  }
  const profile = Object.fromEntries(profileFields.map((key) => [key, typeof parsed[key] === 'string' ? parsed[key].trim() : '']))
  if (profileFields.some((key) => !profile[key])) throw new Error(t('canvas.incompleteCharacterResult'))
  return profile
}

export function mergeCharacterProfile(current = {}, generated = {}) {
  return Object.fromEntries(profileFields.map((key) => [key, current[key]?.trim() || generated[key] || '']))
}

export function characterReady(profile = {}) {
  return ['name', 'appearance', 'personality', 'costume'].every((key) => profile[key]?.trim())
}

export function buildCharacterVisualPrompt(worldContext, profileContext, data, hasReference = false) {
  const types = characterVisualTypes.map((item) => `${item.id}=${item.label}：${item.description}`).join('\n')
  return `请为同一个短剧角色生成以下 3 条中文图片生成提示词：
${types}
世界观：
${worldContext}
角色档案：
${profileContext}
统一画面规格：${data.aspectRatio || '3:4'}，${data.resolution || '1K'}。${hasReference ? '参考图片是该角色的外形依据。' : ''}

严格输出 JSON 数组，格式为 [{"type":"类型ID","prompt":"提示词"}]。每个类型必须且只能出现一次，顺序与请求一致。每条提示词不超过 260 个中文字符，必须保持同一角色的身份、面部、体型、发型、服装、配色和标志性特征，只允许按类型调整构图和视角；单色中性背景，清晰自然光，不添加文字、水印或其他人物，不解释，不使用 Markdown。`
}

export function parseCharacterVisualPlan(content) {
  const source = content.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('[')
  const end = source.lastIndexOf(']')
  if (start < 0 || end <= start) throw new Error(t('canvas.invalidCharacterPlan'))
  let parsed
  try {
    parsed = JSON.parse(source.slice(start, end + 1))
  } catch {
    throw new Error(t('canvas.invalidCharacterPlanFormat'))
  }
  const prompts = new Map((Array.isArray(parsed) ? parsed : []).map((item) => [item?.type, typeof item?.prompt === 'string' ? item.prompt.trim() : '']))
  const plans = characterVisualTypes.map((item) => ({ ...item, prompt: prompts.get(item.id) || '' }))
  const missing = plans.filter((item) => !item.prompt).map((item) => item.label)
  if (missing.length) throw new Error(t('canvas.missingCharacterPlan', { p0: missing.join('、') }))
  return plans
}
