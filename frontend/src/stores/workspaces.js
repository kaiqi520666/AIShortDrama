import { defineStore } from 'pinia'
import { createWorkspace, deleteWorkspace, duplicateWorkspace, getWorkspace, listWorkspaces, renameWorkspace } from '../api/workspaces'
import { getWorkspaceType } from '../config/canvas/nodePacks'
import { getApiErrorMessage } from '../utils/apiError'
import { createRequestState, failRequest, finishRequest, startRequest } from '../utils/requestState'

let workspaceRequestSequence = 0

export const useWorkspaceStore = defineStore('workspaces', {
  state: () => ({
    items: [],
    current: null,
    loading: false,
    error: '',
    requestState: createRequestState(),
  }),
  actions: {
    async load() {
      const requestId = startRequest(this.requestState)
      this.loading = true
      this.error = ''
      try {
        const result = await listWorkspaces()
        if (result.code !== 0) throw new Error(result.message)
        this.items = result.data
        finishRequest(this.requestState, requestId)
      } catch (error) {
        this.error = getApiErrorMessage(error, '工作台加载失败')
        failRequest(this.requestState, requestId, this.error)
      } finally {
        this.loading = false
        this.error = this.requestState.error
      }
    },
    async fetch(id, config = {}) {
      const requestSequence = ++workspaceRequestSequence
      const result = await getWorkspace(id, config)
      if (result.code !== 0) throw new Error(result.message)
      return requestSequence === workspaceRequestSequence ? result.data : null
    },
    async open(id, config = {}) {
      const workspace = await this.fetch(id, config)
      if (workspace) this.current = workspace
      return workspace
    },
    setCurrent(workspace) {
      this.current = workspace
    },
    close() {
      workspaceRequestSequence += 1
      this.current = null
    },
    async create(workspaceType) {
      getWorkspaceType(workspaceType)
      const name = String(this.items.length + 1).padStart(2, '0')
      const result = await createWorkspace(name, workspaceType)
      if (result.code !== 0) throw new Error(result.message)
      this.items.unshift(result.data)
      return result.data
    },
    async rename(id, name) {
      const result = await renameWorkspace(id, name)
      if (result.code !== 0) throw new Error(result.message)
      const item = this.items.find((workspace) => workspace.id === id)
      if (item) Object.assign(item, result.data)
      if (this.current?.id === id) Object.assign(this.current, result.data)
    },
    async duplicate(id) {
      const result = await duplicateWorkspace(id)
      if (result.code !== 0) throw new Error(result.message)
      this.items.unshift(result.data)
    },
    async remove(id) {
      const result = await deleteWorkspace(id)
      if (result.code !== 0) throw new Error(result.message)
      this.items = this.items.filter((workspace) => workspace.id !== id)
    },
  },
})
