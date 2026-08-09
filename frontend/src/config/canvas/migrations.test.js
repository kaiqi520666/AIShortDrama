import { describe, expect, it } from 'vitest'
import { CURRENT_CANVAS_SCHEMA_VERSION, migrateCanvas } from './migrations'
import { contentTemplatesFixture } from '../../test/contentTemplates'

const models = {
  text: { id: 'gpt-5.6-sol' },
  image: { id: 'gpt-image-2', defaultAspectRatio: '1:1', defaultResolution: '1K' },
  video: { id: 'seedance-2-mini', defaultDuration: 10, defaultAspectRatio: '16:9', defaultResolution: '720p' },
  audio: { model: { id: 'seed-audio' } },
}
const ecommerceOptions = { workspaceType: 'ecommerce', models, templates: contentTemplatesFixture }

describe('canvas migrations', () => {
  it('fills missing storyboard fields without overwriting saved values', () => {
    const migrated = migrateCanvas({
      schema_version: 1,
      nodes: [
        { id: 'a', type: 'product_storyboard', data: {} },
        { id: 'b', type: 'product_storyboard', data: { textModel: 'custom', templateKey: 'saved-key', templateId: 'saved', templates: [{ id: 'saved' }] } },
      ],
    }, 'gpt-5.6-sol', contentTemplatesFixture)

    expect(migrated.schema_version).toBe(CURRENT_CANVAS_SCHEMA_VERSION)
    expect(migrated.nodes[0].data).toEqual(expect.objectContaining({ textModel: expect.any(String), templateKey: 'product_storyboard', templateId: 'ugc-seeding', templates: expect.any(Array) }))
    expect(migrated.nodes[1].data).toEqual(expect.objectContaining({ textModel: 'custom', templateKey: 'saved-key', templateId: 'saved', templates: [{ id: 'saved' }], templateVersion: 1 }))
    expect(migrateCanvas(migrated, 'gpt-5.6-sol', contentTemplatesFixture)).toEqual(migrated)
  })

  it('rejects canvases created by a newer client', () => {
    expect(() => migrateCanvas({ schema_version: CURRENT_CANVAS_SCHEMA_VERSION + 1 })).toThrow('高于当前支持版本')
  })

  it('migrates product workflows, merges legacy visual settings, and preserves results', () => {
    const source = {
      schema_version: 3,
      sequence: 5,
      nodes: [
        { id: 'image-1', type: 'image', position: { x: -460, y: 3 }, data: { title: '自定义商品图', asset: 'product.png' } },
        { id: 'product-2', type: 'product', position: { x: 0, y: 0 }, data: { title: '自定义商品', product: { name: '已保存商品' } } },
        { id: 'product_visual-3', type: 'product_visual', position: { x: 500, y: 0 }, data: { resolution: '2K', items: [{ id: 'saved' }] } },
        { id: 'image-4', type: 'image', position: { x: 900, y: 0 }, data: { title: '已生成主图', asset: 'result.png' } },
      ],
      edges: [
        { id: 'e1', source: 'image-1', target: 'product-2' },
        { id: 'e2', source: 'product-2', target: 'product_visual-3' },
        { id: 'e3', source: 'product_visual-3', target: 'image-4' },
      ],
      groups: [],
    }

    const migrated = migrateCanvas(source, ecommerceOptions)
    const product = migrated.nodes.find((node) => node.id === 'product-2')
    const storyboard = migrated.nodes.find((node) => node.type === 'product_storyboard')

    expect(migrated.schema_version).toBe(4)
    expect(migrated.nodes.some((node) => node.type === 'product_visual')).toBe(false)
    expect(product.position).toEqual({ x: 0, y: 0 })
    expect(product.data).toEqual(expect.objectContaining({ resolution: '2K', items: [{ id: 'saved' }], workflowRoot: true }))
    expect(migrated.nodes.find((node) => node.id === 'image-4').data).toEqual(expect.objectContaining({ title: '已生成主图', asset: 'result.png', workflowId: product.data.workflowId }))
    expect(migrated.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'product-2', target: storyboard.id, workflowId: product.data.workflowId }),
      expect.objectContaining({ source: 'product-2', target: 'image-4', workflowId: product.data.workflowId }),
    ]))
    expect(migrateCanvas(migrated, ecommerceOptions)).toEqual(migrated)
  })

  it('removes apparel scene nodes and marks existing results without moving nodes', () => {
    const source = {
      schema_version: 3,
      sequence: 9,
      nodes: [
        { id: 'image-1', type: 'image', position: { x: 0, y: 0 }, data: { title: '服饰参考图' } },
        { id: 'apparel-2', type: 'apparel', position: { x: 460, y: 0 }, data: { title: '服饰识别' } },
        { id: 'outfit-3', type: 'outfit', position: { x: 960, y: 0 }, data: { title: '模特试穿 3' } },
        { id: 'image-4', type: 'image', position: { x: 460, y: 360 }, data: { title: '模特参考图' } },
        { id: 'image-5', type: 'image', position: { x: 960, y: 360 }, data: { title: '场景节点', inputRole: 'scene', asset: 'scene.png' } },
        { id: 'apparel_storyboard-6', type: 'apparel_storyboard', position: { x: 1480, y: 0 }, data: { title: '服饰分镜' } },
        { id: 'image-7', type: 'image', position: { x: 2040, y: 0 }, data: { storyboardSourceId: 'apparel_storyboard-6', asset: 'board.png' } },
        { id: 'video-8', type: 'video', position: { x: 2490, y: 0 }, data: { storyboardSourceId: 'apparel_storyboard-6', storyboardImageId: 'image-7', asset: 'video.mp4' } },
      ],
      edges: [
        { id: 'e1', source: 'image-1', target: 'apparel-2' },
        { id: 'e2', source: 'apparel-2', target: 'outfit-3', targetHandle: 'apparel' },
        { id: 'e3', source: 'image-4', target: 'outfit-3', targetHandle: 'model' },
        { id: 'e4', source: 'outfit-3', target: 'apparel_storyboard-6', targetHandle: 'outfit' },
        { id: 'e5', source: 'image-5', target: 'apparel_storyboard-6', targetHandle: 'scene' },
        { id: 'e6', source: 'apparel_storyboard-6', target: 'image-7' },
        { id: 'e7', source: 'image-7', target: 'video-8' },
      ],
      groups: [{ id: 'group-1', nodeIds: ['image-5', 'image-7'] }],
    }

    const migrated = migrateCanvas(source, ecommerceOptions)
    const outfit = migrated.nodes.find((node) => node.id === 'outfit-3')

    expect(migrated.nodes.some((node) => node.id === 'image-5')).toBe(false)
    expect(migrated.edges.some((edge) => edge.targetHandle === 'scene')).toBe(false)
    expect(migrated.groups).toEqual([])
    expect(outfit.position).toEqual({ x: 960, y: 0 })
    expect(outfit.data).toEqual(expect.objectContaining({ title: '服饰穿搭 3', workflowRoot: true }))
    expect(migrated.nodes.find((node) => node.id === 'video-8').data.workflowId).toBe(outfit.data.workflowId)
    expect(migrated.edges.every((edge) => edge.workflowId === outfit.data.workflowId)).toBe(true)
    expect(migrateCanvas(migrated, ecommerceOptions)).toEqual(migrated)
  })

  it('conservatively fills a storyboard-only apparel workflow', () => {
    const migrated = migrateCanvas({
      schema_version: 3,
      sequence: 2,
      nodes: [{ id: 'apparel_storyboard-1', type: 'apparel_storyboard', position: { x: 1500, y: 200 }, data: { title: '保留的服饰分镜', customRequirement: '海边场景' } }],
      edges: [],
      groups: [],
    }, ecommerceOptions)

    expect(migrated.nodes.map((node) => node.type).sort()).toEqual(['apparel', 'apparel_storyboard', 'image', 'image', 'outfit'].sort())
    expect(migrated.nodes.find((node) => node.id === 'apparel_storyboard-1')).toEqual(expect.objectContaining({
      position: { x: 1500, y: 200 },
      data: expect.objectContaining({ title: '保留的服饰分镜', customRequirement: '海边场景', workflowRole: 'storyboard' }),
    }))
  })
})
