import { defineAsyncComponent, defineComponent, h, markRaw } from 'vue'
import { nodeDefinitions } from './nodeDefinitions'

const componentLoaders = import.meta.glob([
  '../../components/canvas/*Node.vue',
  '../../components/canvas/*Panel.vue',
  '!../../components/canvas/ShortcutPanel.vue',
])
const loaders = Object.fromEntries(Object.entries(componentLoaders).map(([path, loader]) => [
  path.split('/').pop().replace('.vue', ''),
  loader,
]))

const loadingPlaceholder = markRaw(defineComponent({
  name: 'CanvasAsyncLoading',
  setup() {
    return () => h('div', { class: 'canvas-async-placeholder', role: 'status' }, '节点加载中…')
  },
}))

const errorPlaceholder = markRaw(defineComponent({
  name: 'CanvasAsyncError',
  setup() {
    return () => h('div', { class: 'canvas-async-placeholder canvas-async-placeholder--error', role: 'alert' }, '节点加载失败，请重试')
  },
}))

function resolveComponent(name, type) {
  const loader = loaders[name]
  if (!loader) throw new Error(`节点 ${type} 的组件 ${name} 未注册`)
  return markRaw(defineAsyncComponent({
    loader,
    loadingComponent: loadingPlaceholder,
    errorComponent: errorPlaceholder,
    delay: 100,
    timeout: 30000,
  }))
}

export const nodeRegistry = Object.fromEntries(Object.entries(nodeDefinitions).map(([type, definition]) => [type, {
  ...definition,
  component: resolveComponent(definition.componentName, type),
  panelComponent: definition.panelName ? resolveComponent(definition.panelName, type) : null,
}]))

export function getNodeRegistry(type) {
  const entry = nodeRegistry[type]
  if (!entry) throw new Error(`不支持的节点类型：${type}`)
  return entry
}
