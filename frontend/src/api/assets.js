import { apiClient } from './client'

export async function listAssets(type = '') {
  return (await apiClient.get('/assets', { params: type ? { type } : {} })).data
}
