import { apiClient } from './client'

export async function listWorkspaces() {
  return (await apiClient.get('/workspaces')).data
}

export async function createWorkspace(name, workspaceType) {
  return (await apiClient.post('/workspaces', { name, workspace_type: workspaceType })).data
}

export async function getWorkspace(id) {
  return (await apiClient.get(`/workspaces/${id}`)).data
}

export async function renameWorkspace(id, name) {
  return (await apiClient.patch(`/workspaces/${id}`, { name })).data
}

export async function duplicateWorkspace(id) {
  return (await apiClient.post(`/workspaces/${id}/duplicate`)).data
}

export async function deleteWorkspace(id) {
  return (await apiClient.delete(`/workspaces/${id}`)).data
}

export async function saveWorkspaceCanvas(id, canvas) {
  return (await apiClient.put(`/workspaces/${id}/canvas`, canvas)).data
}
