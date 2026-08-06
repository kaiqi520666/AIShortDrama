import { nodeDefinitions } from './nodeDefinitions'

const componentModules = import.meta.glob('../../components/canvas/*.vue', { eager: true })
const components = Object.fromEntries(Object.entries(componentModules).map(([path, module]) => [
  path.split('/').pop().replace('.vue', ''),
  module.default,
]))

function resolveComponent(name, type) {
  const component = components[name]
  if (!component) throw new Error(`节点 ${type} 的组件 ${name} 未注册`)
  return component
}

export const nodeRegistry = Object.fromEntries(Object.entries(nodeDefinitions).map(([type, definition]) => [type, {
  ...definition,
  component: resolveComponent(definition.componentName, type),
  panelComponent: definition.panelName ? resolveComponent(definition.panelName, type) : null,
}]))
