import { describe, expect, it } from 'vitest'
import { canConnect, getConnectionError } from './connectionRules'
import { createNodeData, getNodeDescriptor, nodeCatalog } from './nodeCatalog'
import { getNodeTypes, getWorkspaceType, isNodeTypeAvailable } from './nodePacks'

describe('canvas node packs', () => {
  it('derives node metadata and workspace packs from one catalog', () => {
    expect(Object.values(nodeCatalog).every((node) => node.componentName && node.panelName)).toBe(true)
    expect(getNodeDescriptor('product').businessCreator).toBe('product')
  })

  it('creates default data without importing UI components', () => {
    const models = {
      text: { id: 'text-model' },
      image: { id: 'image-model', defaultAspectRatio: '1:1', defaultResolution: '1K' },
      video: { id: 'video-model', defaultDuration: 5, defaultAspectRatio: '16:9', defaultResolution: '720P' },
      audio: { model: { id: 'audio-model' } },
    }
    expect(createNodeData('image', 2, null, models)).toMatchObject({ title: '图片节点 2', model: 'image-model' })
    expect(() => getNodeDescriptor('missing')).toThrow('不支持的节点类型')
    expect(() => isNodeTypeAvailable('general', 'missing')).toThrow('未在 nodeCatalog 注册')
  })

  it('provides the expected nodes for every workspace', () => {
    const expectedPacks = {
      general: ['text', 'image', 'video', 'audio'],
      drama: ['world', 'character', 'text', 'image', 'video', 'audio'],
      ecommerce: ['product', 'product_visual', 'product_storyboard', 'apparel', 'outfit', 'text', 'image', 'video', 'audio'],
    }

    Object.entries(expectedPacks).forEach(([workspace, nodeTypes]) => {
      expect(getWorkspaceType(workspace).id).toBe(workspace)
      expect(getNodeTypes(workspace)).toEqual(nodeTypes)
      expect(nodeTypes).toEqual(Object.values(nodeCatalog)
        .filter((node) => node.workspaces.includes(workspace))
        .sort((left, right) => left.order[workspace] - right.order[workspace])
        .map((node) => node.type))
    })
  })

  it('keeps drama connection rules', () => {
    expect(canConnect('world', 'character', 'drama')).toBe(true)
    expect(canConnect('image', 'character', 'drama')).toBe(true)
    expect(canConnect('character', 'image', 'drama')).toBe(true)
    expect(getConnectionError('world', 'character', ['world'], 'drama')).toContain('只能连接 1 个')
    expect(getConnectionError('image', 'character', ['image'], 'drama')).toContain('只能连接 1 张')
  })

  it('keeps ecommerce connection rules', () => {
    expect(canConnect('product', 'product_visual', 'ecommerce')).toBe(true)
    expect(canConnect('product', 'product_storyboard', 'ecommerce')).toBe(true)
    expect(canConnect('product_visual', 'image', 'ecommerce')).toBe(true)
    expect(canConnect('product_storyboard', 'image', 'ecommerce')).toBe(true)
    expect(canConnect('image', 'product_visual', 'ecommerce')).toBe(false)
    expect(getConnectionError('image', 'product', Array(6).fill('image'), 'ecommerce')).toContain('6 张参考图片')
    expect(getConnectionError('product', 'product_visual', ['product'], 'ecommerce')).toContain('只能连接 1 个')
    expect(getConnectionError('product', 'product_storyboard', ['product'], 'ecommerce')).toContain('只能连接 1 个')
    expect(canConnect('image', 'apparel', 'ecommerce')).toBe(true)
    expect(canConnect('apparel', 'outfit', 'ecommerce')).toBe(true)
    expect(canConnect('outfit', 'image', 'ecommerce')).toBe(true)
    expect(canConnect('outfit', 'video', 'ecommerce')).toBe(true)
    expect(getConnectionError('apparel', 'outfit', ['apparel'], 'ecommerce')).toContain('只能连接 1 个')
  })

  it('keeps existing media connection rules', () => {
    expect(canConnect('image', 'video', 'ecommerce')).toBe(true)
    expect(canConnect('video', 'image', 'drama')).toBe(false)
    expect(getConnectionError('audio', 'audio', ['image'], 'general')).toBe('参考图片和参考音频不能混用')
    expect(canConnect('audio', 'video')).toBe(true)
    expect(canConnect('audio', 'audio')).toBe(true)
    expect(canConnect('audio', 'text')).toBe(false)
    expect(canConnect('audio', 'image')).toBe(false)
    expect(canConnect('text', 'audio')).toBe(true)
    expect(canConnect('image', 'audio')).toBe(true)
    expect(canConnect('video', 'audio')).toBe(false)
    expect(getConnectionError('image', 'audio', ['image'])).toContain('最多连接 1 张')
    expect(getConnectionError('audio', 'audio', ['audio', 'audio', 'audio'])).toContain('最多连接 3 条')
  })
})
