import { defineStore } from 'pinia'
import { createWorkspace, deleteWorkspace, duplicateWorkspace, getWorkspace, listWorkspaces, renameWorkspace } from '../api/workspaces'

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
    async open(id) {
      const result = await getWorkspace(id)
      if (result.code !== 0) throw new Error(result.message)
      this.current = result.data
    },
    close() {
      this.current = null
    },
    async create(name = '未命名工作台') {
      const result = await createWorkspace(name)
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
