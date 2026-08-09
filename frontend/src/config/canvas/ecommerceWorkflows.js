import { canConnect } from './connectionRules'
import { getNodeTypes } from './nodePacks'

export const BASIC_NODE_TYPES = ['text', 'image', 'video', 'audio']

export const ECOMMERCE_WORKFLOWS = [
  { id: 'product', label: '商品创作', nodeType: 'product' },
  { id: 'apparel', label: '服饰穿搭', nodeType: 'outfit' },
]

export function createWorkflowId(type) {
  return `${type}-${crypto.randomUUID()}`
}

export function assignWorkflowNode(node, workflowId, workflowType, workflowRole, workflowRoot = false) {
  if (!node) return
  node.data = {
    ...node.data,
    workflowId,
    workflowType,
    workflowRole,
    ...(workflowRoot ? { workflowRoot: true } : {}),
  }
}

export function assignWorkflowEdges(edges, workflowId, nodeIds) {
  const ids = new Set(nodeIds)
  edges.forEach((edge) => {
    if (ids.has(edge.source) && ids.has(edge.target)) edge.workflowId = workflowId
  })
}

export function getNodeMenuGroups(workspaceType, { contextual = false, sourceType = '', sourceWorkflowId = '' } = {}) {
  if (workspaceType !== 'ecommerce') {
    const options = getNodeTypes(workspaceType)
      .filter((type) => !contextual || canConnect(sourceType, type, workspaceType))
      .map((type) => ({ kind: 'node', type }))
    return options.length ? [{ id: 'nodes', label: '', options }] : []
  }

  if (contextual && sourceWorkflowId) return []
  const basicOptions = BASIC_NODE_TYPES
    .filter((type) => !contextual || canConnect(sourceType, type, workspaceType))
    .map((type) => ({ kind: 'node', type }))
  const groups = basicOptions.length ? [{ id: 'basic', label: contextual ? '' : '基础节点', options: basicOptions }] : []
  if (!contextual) groups.push({
    id: 'workflows',
    label: '电商流程',
    options: ECOMMERCE_WORKFLOWS.map((workflow) => ({ kind: 'workflow', type: workflow.id, nodeType: workflow.nodeType, label: workflow.label })),
  })
  return groups
}
