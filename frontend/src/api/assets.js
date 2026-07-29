import { apiClient } from './client'

export async function listAssets(type = '') {
  return (await apiClient.get('/assets', { params: type ? { type } : {} })).data
}

export async function renameAsset(id, name) {
  return (await apiClient.patch(`/assets/${id}`, { name })).data
}

export async function registerAssetPrivateAvatar(id, groupId = null) {
  return (await apiClient.post(`/assets/${id}/private-avatar`, { group_id: groupId })).data
}

export async function deleteAsset(id) {
  return (await apiClient.delete(`/assets/${id}`)).data
}
