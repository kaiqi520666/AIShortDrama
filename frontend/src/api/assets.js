import { apiClient } from './client'

export async function listAssets(workspaceId, type = '') {
  return (await apiClient.get('/assets', { params: { workspace_id: workspaceId, ...(type ? { type } : {}) } })).data
}

export async function renameAsset(id, name) {
  return (await apiClient.patch(`/assets/${id}`, { name })).data
}

export async function deleteAsset(id) {
  return (await apiClient.delete(`/assets/${id}`)).data
}
