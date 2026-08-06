import { defineStore } from 'pinia'
import { getGenerationCapabilities } from '../api/generations'
import { normalizeAudioCapability } from '../config/audioModels'
import { normalizeImageModels } from '../config/imageModels'
import { normalizeTextModels } from '../config/reverseModels'
import { normalizeVideoModels } from '../config/videoModels'
import { validateModelCapabilities } from '../config/modelCapabilitiesValidation'
import { getApiErrorMessage } from '../utils/apiError'

let loadPromise = null

export const useModelCapabilitiesStore = defineStore('modelCapabilities', {
  state: () => ({
    capabilities: null,
    loading: false,
    error: '',
  }),
  getters: {
    textModels: (state) => normalizeTextModels(state.capabilities?.text),
    imageModels: (state) => normalizeImageModels(state.capabilities?.image),
    videoModels: (state) => normalizeVideoModels(state.capabilities?.video),
    audioCapability: (state) => normalizeAudioCapability(state.capabilities?.audio),
    defaultTextModel() {
      return this.textModels.find(({ id }) => id === this.capabilities?.text.default_model)
    },
    defaultImageModel() {
      return this.imageModels.find(({ id }) => id === this.capabilities?.image.default_model)
    },
    defaultVideoModel() {
      return this.videoModels.find(({ id }) => id === this.capabilities?.video.default_model)
    },
  },
  actions: {
    async load(force = false) {
      if (this.capabilities && !force) return this.capabilities
      if (loadPromise && !force) return loadPromise
      this.loading = true
      this.error = ''
      loadPromise = getGenerationCapabilities()
        .then((response) => {
          if (response?.code !== 0) throw new Error(response?.message || '模型能力加载失败')
          const validationError = validateModelCapabilities(response.data)
          if (validationError) throw new Error(validationError)
          this.capabilities = response.data
          return response.data
        })
        .catch((error) => {
          this.error = getApiErrorMessage(error, '模型能力加载失败')
          throw error
        })
        .finally(() => {
          this.loading = false
          loadPromise = null
        })
      return loadPromise
    },
    clear() {
      this.capabilities = null
      this.error = ''
      loadPromise = null
    },
  },
})
