import { createNodeData } from './nodeCatalog'
import { createStoryboardTemplates } from './productStoryboard'

export const CURRENT_CANVAS_SCHEMA_VERSION = 6

function legacyMigrations(canvas, version, defaultTextModelId, templates) {
  const storyboardTemplate = templates?.product_storyboard
  if (version < 2) {
    canvas.nodes = canvas.nodes.map((node) => node.type === 'product_storyboard'
      ? {
          ...node,
          data: {
            ...node.data,
            textModel: node.data?.textModel ?? defaultTextModelId,
            templateId: node.data?.templateId ?? 'ugc-seeding',
            ...(node.data?.templates || !storyboardTemplate
              ? {}
              : { templates: createStoryboardTemplates(storyboardTemplate) }),
            ...(node.data?.templateVersion != null || !storyboardTemplate
              ? {}
              : { templateVersion: storyboardTemplate.version }),
          },
        }
      : node)
  }
  if (version < 3) {
    canvas.nodes = canvas.nodes.map((node) => node.type === 'product_storyboard'
      && !Object.hasOwn(node.data || {}, 'templateKey')
      ? { ...node, data: { ...node.data, templateKey: 'product_storyboard' } }
      : node)
  }
}

function migrateEcommerceWorkflows(canvas, models, templates) {
  if (!models || !templates) throw new Error('电商画布迁移需要模型能力和内容模板')
  const nodes = canvas.nodes
  const edges = canvas.edges
  let sequence = Math.max(
    Number(canvas.sequence || 1),
    ...nodes.map((node) => Number(node.id.match(/-(\d+)$/)?.[1] || 0) + 1),
  )

  const nodeById = (id) => nodes.find((node) => node.id === id)
  const createNode = (type, position, data = {}) => {
    const number = sequence++
    const node = {
      id: `${type}-${number}`,
      type,
      position,
      data: { ...createNodeData(type, number, null, models, templates), ...data },
    }
    nodes.push(node)
    return node
  }
  const addEdge = (source, target, targetHandle) => {
    const existing = edges.find((edge) => edge.source === source && edge.target === target)
    if (existing) {
      if (targetHandle) existing.targetHandle = targetHandle
      return existing
    }
    const edge = {
      id: `edge-v4-${source}-${target}${targetHandle ? `-${targetHandle}` : ''}`,
      source,
      target,
      ...(targetHandle ? { targetHandle } : {}),
      type: 'cinematic',
    }
    edges.push(edge)
    return edge
  }
  const markNode = (node, workflowId, workflowType, workflowRole, workflowRoot = false) => {
    if (!node) return
    node.data = {
      ...node.data,
      workflowId,
      workflowType,
      workflowRole,
      ...(workflowRoot ? { workflowRoot: true } : {}),
    }
  }
  const markEdges = (workflowId) => {
    const ids = new Set(nodes.filter((node) => node.data?.workflowId === workflowId).map((node) => node.id))
    edges.forEach((edge) => {
      if (ids.has(edge.source) && ids.has(edge.target)) edge.workflowId = workflowId
    })
  }

  const sceneIds = new Set(nodes.filter((node) => node.data?.inputRole === 'scene').map((node) => node.id))
  edges.filter((edge) => edge.targetHandle === 'scene' && nodeById(edge.target)?.type === 'apparel_storyboard')
    .forEach((edge) => sceneIds.add(edge.source))
  if (sceneIds.size) {
    nodes.splice(0, nodes.length, ...nodes.filter((node) => !sceneIds.has(node.id)))
    edges.splice(0, edges.length, ...edges.filter((edge) => !sceneIds.has(edge.source) && !sceneIds.has(edge.target)))
    canvas.groups = canvas.groups
      .map((group) => ({ ...group, nodeIds: group.nodeIds.filter((id) => !sceneIds.has(id)) }))
      .filter((group) => group.nodeIds.length > 1)
  }

  const activeNodes = canvas.nodes
  const activeEdges = canvas.edges
  const activeNodeById = (id) => activeNodes.find((node) => node.id === id)
  const activeIncoming = (id, type) => activeEdges.filter((edge) => edge.target === id && (!type || activeNodeById(edge.source)?.type === type))
  const activeOutgoing = (id, type) => activeEdges.filter((edge) => edge.source === id && (!type || activeNodeById(edge.target)?.type === type))

  activeNodes.filter((node) => node.type === 'product').forEach((product) => {
    const workflowId = product.data?.workflowId || `workflow-product-${product.id}`
    const visuals = activeOutgoing(product.id, 'product_visual').map((edge) => activeNodeById(edge.target)).filter(Boolean)
    const visualResults = visuals.flatMap((visual) => activeOutgoing(visual.id).map((edge) => activeNodeById(edge.target))).filter(Boolean)
    visuals.forEach((visual) => {
      const settings = ['textModel', 'imageModel', 'aspectRatio', 'resolution', 'items', 'templateVersion']
      settings.forEach((key) => {
        if (visual.data?.[key] !== undefined) product.data[key] = visual.data[key]
      })
      activeOutgoing(visual.id).forEach((edge) => addEdge(product.id, edge.target, edge.targetHandle))
    })
    const visualIds = new Set(visuals.map((node) => node.id))
    if (visualIds.size) {
      nodes.splice(0, nodes.length, ...nodes.filter((node) => !visualIds.has(node.id)))
      edges.splice(0, edges.length, ...edges.filter((edge) => !visualIds.has(edge.source) && !visualIds.has(edge.target)))
      canvas.groups = canvas.groups
        .map((group) => ({ ...group, nodeIds: group.nodeIds.filter((id) => !visualIds.has(id)) }))
        .filter((group) => group.nodeIds.length > 1)
    }
    let references = canvas.edges
      .filter((edge) => edge.target === product.id && canvas.nodes.find((node) => node.id === edge.source)?.type === 'image')
      .map((edge) => canvas.nodes.find((node) => node.id === edge.source))
      .filter(Boolean)
    if (!references.length) {
      const reference = createNode('image', { x: product.position.x - 460, y: product.position.y + 3 }, { title: '商品参考图', assetSource: 'upload' })
      addEdge(reference.id, product.id)
      references = [reference]
    }
    let storyboard = canvas.edges
      .filter((edge) => edge.source === product.id && canvas.nodes.find((node) => node.id === edge.target)?.type === 'product_storyboard')
      .map((edge) => canvas.nodes.find((node) => node.id === edge.target))[0]
    if (!storyboard) {
      storyboard = createNode('product_storyboard', { x: product.position.x + 520, y: product.position.y })
      addEdge(product.id, storyboard.id)
    }
    markNode(product, workflowId, 'product', 'product', true)
    references.forEach((node) => markNode(node, workflowId, 'product', 'product_reference'))
    markNode(storyboard, workflowId, 'product', 'storyboard')
    visualResults.forEach((node) => markNode(node, workflowId, 'product', 'product_visual_result'))
    canvas.edges
      .filter((edge) => edge.source === product.id && ['image', 'video'].includes(nodeById(edge.target)?.type))
      .map((edge) => nodeById(edge.target))
      .forEach((node) => markNode(node, workflowId, 'product', 'product_visual_result'))
    canvas.nodes.filter((node) => node.data?.storyboardSourceId === storyboard.id || node.data?.productSourceId === product.id)
      .forEach((node) => markNode(node, workflowId, 'product', node.type === 'video' ? 'storyboard_video' : 'storyboard_image'))
    markEdges(workflowId)
  })

  canvas.sequence = sequence
}

function removeLegacyApparelStoryboard(canvas) {
  const storyboardIds = new Set(
    canvas.nodes.filter((node) => node.type === 'apparel_storyboard').map((node) => node.id),
  )
  if (!storyboardIds.size) return
  const obsoleteIds = new Set(storyboardIds)
  canvas.nodes.forEach((node) => {
    if (node.data?.inputRole === 'scene') obsoleteIds.add(node.id)
  })
  canvas.nodes.forEach((node) => {
    if (storyboardIds.has(node.data?.storyboardSourceId)) obsoleteIds.add(node.id)
  })
  canvas.nodes = canvas.nodes.filter((node) => !obsoleteIds.has(node.id))
  canvas.edges = canvas.edges.filter((edge) => !obsoleteIds.has(edge.source) && !obsoleteIds.has(edge.target))
  canvas.groups = canvas.groups
    .map((group) => ({ ...group, nodeIds: group.nodeIds.filter((id) => !obsoleteIds.has(id)) }))
    .filter((group) => group.nodeIds.length > 1)
}

export function migrateCanvas(source = {}, options = {}, legacyTemplates) {
  const canvas = JSON.parse(JSON.stringify(source || {}))
  canvas.nodes ||= []
  canvas.edges ||= []
  canvas.groups ||= []
  const version = Number(canvas.schema_version || 1)
  if (version > CURRENT_CANVAS_SCHEMA_VERSION) {
    throw new Error(`画布版本 ${version} 高于当前支持版本 ${CURRENT_CANVAS_SCHEMA_VERSION}`)
  }
  const normalized = typeof options === 'string'
    ? { models: null, templates: legacyTemplates, defaultTextModelId: options }
    : { ...options, defaultTextModelId: options.models?.text?.id }
  legacyMigrations(canvas, version, normalized.defaultTextModelId, normalized.templates)
  if (version < 4 && normalized.workspaceType === 'ecommerce') {
    migrateEcommerceWorkflows(canvas, normalized.models, normalized.templates)
  }
  if (version < 6 && normalized.workspaceType === 'ecommerce') {
    removeLegacyApparelStoryboard(canvas)
  }
  canvas.schema_version = CURRENT_CANVAS_SCHEMA_VERSION
  return canvas
}
