import { defineStore } from 'pinia'
import { createWorkspace, deleteWorkspace, duplicateWorkspace, getWorkspace, listWorkspaces, renameWorkspace } from '../api/workspaces'
import { getWorkspaceType } from '../config/canvas/nodePacks'

let workspaceRequestSequence = 0

export const useWorkspaceStore = defineStore('workspaces', {
  state: () => ({
    items: [],
    current: null,
    loading: false,
    error: '',
  }),
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const result = await listWorkspaces()
        if (result.code !== 0) throw new Error(result.message)
        this.items = result.data
      } catch (error) {
        this.error = error.response?.data?.message || error.message || '工作台加载失败'
      } finally {
        this.loading = false
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
      const definition = getWorkspaceType(workspaceType)
      const result = await createWorkspace(definition.defaultName, workspaceType)
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
