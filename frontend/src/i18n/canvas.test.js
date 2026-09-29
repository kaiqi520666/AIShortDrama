import { afterEach, describe, expect, it, vi } from 'vitest'
import { computed, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { canvasLabel, canvasOptions, canvasTemplateText } from './canvas'
import { i18n } from './index'
import zhCN from './locales/zh-CN.json'
import id from './locales/id.json'
import { useCanvasStore } from '../stores/canvas'
import { buildWorldPrompt } from '../config/canvas/drama'
import { buildCharacterProfilePrompt, buildCharacterVisualPrompt } from '../config/canvas/character'
import { nodeCatalog, createNodeData } from '../config/canvas/nodeCatalog'
import { getConnectionError } from '../config/canvas/connectionRules'
import { buildVideoRequest, normalizeVideoModels } from '../config/videoModels'
import { modelCapabilitiesFixture } from '../test/modelCapabilities'

afterEach(() => {
  i18n.global.locale.value = 'id'
  vi.restoreAllMocks()
})

describe('canvas interface localization', () => {
  it('translates only matching built-in template defaults and preserves custom names', () => {
    i18n.global.locale.value = 'id'
    expect(canvasTemplateText('white-bg', '白底图')).toBe('Latar putih')
    expect(canvasTemplateText('white-bg', '我的商品图')).toBe('我的商品图')
    expect(canvasTemplateText('white-bg', '核心卖点')).toBe('核心卖点')
    expect(canvasTemplateText('custom', '白底图')).toBe('白底图')
    expect(canvasTemplateText('ugc-seeding', '自定义说明', 'description')).toBe('自定义说明')
  })
  it('updates fixed option labels without changing values or unknown labels', () => {
    const options = [{ value: '电影写实', label: '电影写实' }, { value: 'custom', label: '我的自定义风格' }]
    const original = JSON.stringify(options)
    const display = computed(() => canvasOptions(options))
    i18n.global.locale.value = 'zh-CN'
    expect(display.value[0].label).toBe('电影写实')
    i18n.global.locale.value = 'id'
    expect(display.value[0]).toEqual({ value: '电影写实', label: 'Realisme sinematik' })
    expect(display.value[1]).toEqual(options[1])
    expect(JSON.stringify(options)).toBe(original)
  })

  it.each(['zh-CN', 'id'])('compiles every canvas message in %s', (locale) => {
    i18n.global.locale.value = locale
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const messages = (locale === 'id' ? id : zhCN).canvas
    for (const [key, value] of Object.entries(messages)) {
      if (key === 'labels') {
        for (const label of Object.keys(value)) expect(canvasLabel(label)).not.toContain('canvas.')
      } else {
        const params = Object.fromEntries([...value.matchAll(/\{(\w+)\}/g)].map(([, name]) => [name, 3]))
        expect(i18n.global.t(`canvas.${key}`, params)).not.toBe(`canvas.${key}`)
      }
    }
    expect(error).not.toHaveBeenCalled()
    expect(warning).not.toHaveBeenCalled()
  })

  it('covers all fixed node menu labels and placeholders', () => {
    for (const node of Object.values(nodeCatalog)) {
      for (const field of ['label', 'hint', 'placeholder', 'setting']) {
        if (/[\u3400-\u9fff]/.test(node[field] || '')) {
          expect(id.canvas.labels, `${node.type}.${field}`).toHaveProperty(node[field])
        }
      }
    }
  })

  it('switches validation feedback without changing connection decisions', () => {
    i18n.global.locale.value = 'zh-CN'
    expect(getConnectionError('world', 'character', ['world'], 'drama')).toContain('只能连接 1 个')
    i18n.global.locale.value = 'id'
    expect(getConnectionError('world', 'character', ['world'], 'drama')).toContain('1 dunia cerita')
    expect(getConnectionError('world', 'character', [], 'drama')).toBe('')
  })

  it('preserves stored canvas content and prompt builders across locale switches', async () => {
    setActivePinia(createPinia())
    const store = useCanvasStore()
    const data = {
      title: '我的角色节点',
      prompt: '原有提示词：图片1，保留中文',
      content: '既有剧本、对白、旁白和字幕',
      videoPrompt: '既有视频脚本',
      promptParts: [{ type: 'text', value: '原始提示词' }, { type: 'image', nodeId: 'ref', id: 'mention' }],
      setting: { genre: '都市', era: '当代', visualStyle: '电影写实', gender: '女' },
      product: { name: '我的商品', packagingType: '带包装' },
      profile: { name: '小雨', appearance: '黑色长发' },
    }
    store.$patch({
      nodes: [
        { id: 'node', type: 'text', position: { x: 0, y: 0 }, data },
        { id: 'ref', type: 'image', position: { x: 400, y: 0 }, data: { title: '我的参考图', asset: 'https://example.test/image.png' } },
      ],
      edges: [{ id: 'edge', source: 'ref', target: 'node' }],
      groups: [{ id: 'group', title: '我的分组', nodeIds: ['node', 'ref'] }],
    })
    const models = normalizeVideoModels(modelCapabilitiesFixture.video)
    const videoData = { prompt: data.videoPrompt, model: models[0].id }
    const snapshot = () => JSON.stringify({
      canvas: store.canvasPayload(),
      world: buildWorldPrompt(data),
      character: buildCharacterProfilePrompt('既有世界观', data, true),
      visual: buildCharacterVisualPrompt('既有世界观', '既有档案', data, true),
      video: buildVideoRequest(videoData, [], models, models[0]),
      defaults: createNodeData('world', 1, null, { text: { id: 'text' }, image: {}, video: {}, audio: {} }),
    })
    i18n.global.locale.value = 'zh-CN'
    const before = snapshot()
    i18n.global.locale.value = 'id'
    await nextTick()
    expect(snapshot()).toBe(before)
    i18n.global.locale.value = 'zh-CN'
    await nextTick()
    expect(snapshot()).toBe(before)
  })
})
