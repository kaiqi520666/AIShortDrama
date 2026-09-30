import { i18n } from '../i18n/index'
import { defineStore } from 'pinia'
import { getProductContentTemplates } from '../api/contentTemplates'
import { validateProductContentTemplates } from '../config/canvas/contentTemplates'
import { getApiErrorMessage } from '../utils/apiError'
import { createRequestState, failRequest, finishRequest, startRequest } from '../utils/requestState'

const { t } = i18n.global

let loadPromise = null

export const useContentTemplatesStore = defineStore('contentTemplates', {
  state: () => ({
    templates: null,
    loading: false,
    error: '',
    requestState: createRequestState(),
  }),
  actions: {
    async load(force = false) {
      if (this.templates && !force) return this.templates
      if (loadPromise && !force) return loadPromise
      const requestId = startRequest(this.requestState)
      this.loading = true
      this.error = ''
      loadPromise = getProductContentTemplates()
        .then((response) => {
          if (response?.code !== 0) throw new Error(response?.message || t('canvas.productTemplatesFailed'))
          const error = validateProductContentTemplates(response.data)
          if (error) throw new Error(error)
          this.templates = response.data
          finishRequest(this.requestState, requestId)
          return response.data
        })
        .catch((error) => {
          this.error = getApiErrorMessage(error, t('canvas.productTemplatesFailed'))
          failRequest(this.requestState, requestId, this.error)
          throw error
        })
        .finally(() => {
          this.loading = false
          this.error = this.requestState.error
          loadPromise = null
        })
      return loadPromise
    },
    clear() {
      this.templates = null
      this.error = ''
      this.requestState.status = 'idle'
      this.requestState.error = ''
      loadPromise = null
    },
  },
})
