import { defineStore } from 'pinia'
import { getProductContentTemplates } from '../api/contentTemplates'
import { validateProductContentTemplates } from '../config/canvas/contentTemplates'
import { getApiErrorMessage } from '../utils/apiError'

let loadPromise = null

export const useContentTemplatesStore = defineStore('contentTemplates', {
  state: () => ({
    templates: null,
    loading: false,
    error: '',
  }),
  actions: {
    async load(force = false) {
      if (this.templates && !force) return this.templates
      if (loadPromise && !force) return loadPromise
      this.loading = true
      this.error = ''
      loadPromise = getProductContentTemplates()
        .then((response) => {
          if (response?.code !== 0) throw new Error(response?.message || '商品模板加载失败')
          const error = validateProductContentTemplates(response.data)
          if (error) throw new Error(error)
          this.templates = response.data
          return response.data
        })
        .catch((error) => {
          this.error = getApiErrorMessage(error, '商品模板加载失败')
          throw error
        })
        .finally(() => {
          this.loading = false
          loadPromise = null
        })
      return loadPromise
    },
    clear() {
      this.templates = null
      this.error = ''
      loadPromise = null
    },
  },
})
