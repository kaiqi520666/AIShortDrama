import modelCapabilitiesFixture from '../../../contracts/generation-capabilities.v1.json'
import { useModelCapabilitiesStore } from '../stores/modelCapabilities'

export { modelCapabilitiesFixture }

export function seedModelCapabilities() {
  const store = useModelCapabilitiesStore()
  store.capabilities = structuredClone(modelCapabilitiesFixture)
  return store
}
