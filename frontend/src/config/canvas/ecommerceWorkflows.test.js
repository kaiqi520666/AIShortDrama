import { describe, expect, it } from 'vitest'
import { BASIC_NODE_TYPES, getNodeMenuGroups } from './ecommerceWorkflows'

describe('ecommerce workflow menus', () => {
  it('shows four basic nodes and two workflows in the global menu', () => {
    const groups = getNodeMenuGroups('ecommerce')

    expect(groups.map((group) => group.label)).toEqual(['基础节点', '电商流程'])
    expect(groups[0].options.map((option) => option.type)).toEqual(BASIC_NODE_TYPES)
    expect(groups[1].options).toEqual([
      expect.objectContaining({ kind: 'workflow', type: 'product', label: '商品创作' }),
      expect.objectContaining({ kind: 'workflow', type: 'apparel', label: '服饰穿搭' }),
    ])
  })

  it('keeps contextual creation limited to compatible basic nodes', () => {
    const groups = getNodeMenuGroups('ecommerce', { contextual: true, sourceType: 'image' })

    expect(groups).toHaveLength(1)
    expect(groups[0].options.map((option) => option.type)).toEqual(BASIC_NODE_TYPES)
    expect(getNodeMenuGroups('ecommerce', {
      contextual: true,
      sourceType: 'image',
      sourceWorkflowId: 'workflow-1',
    })).toEqual([])
  })
})
