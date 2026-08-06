import { describe, expect, it } from 'vitest'
import { CURRENT_CANVAS_SCHEMA_VERSION, migrateCanvas } from './migrations'

describe('canvas migrations', () => {
  it('fills missing storyboard fields without overwriting saved values', () => {
    const migrated = migrateCanvas({
      schema_version: 1,
      nodes: [
        { id: 'a', type: 'product_storyboard', data: {} },
        { id: 'b', type: 'product_storyboard', data: { textModel: 'custom', templateId: 'saved', templates: [{ id: 'saved' }] } },
      ],
    }, 'gpt-5.6-sol')

    expect(migrated.schema_version).toBe(CURRENT_CANVAS_SCHEMA_VERSION)
    expect(migrated.nodes[0].data).toEqual(expect.objectContaining({ textModel: expect.any(String), templateId: 'ugc-seeding', templates: expect.any(Array) }))
    expect(migrated.nodes[1].data).toEqual({ textModel: 'custom', templateId: 'saved', templates: [{ id: 'saved' }] })
    expect(migrateCanvas(migrated, 'gpt-5.6-sol')).toEqual(migrated)
  })

  it('rejects canvases created by a newer client', () => {
    expect(() => migrateCanvas({ schema_version: CURRENT_CANVAS_SCHEMA_VERSION + 1 })).toThrow('高于当前支持版本')
  })
})
