import { apiClient } from './client'

const endpoints = { model: '/outfit-models', character: '/characters' }

export async function listReferenceItems(resourceType) {
  return (await apiClient.get(endpoints[resourceType])).data
}

export async function uploadReferenceItem(resourceType, file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  return (await apiClient.post(endpoints[resourceType], form, {
    onUploadProgress: ({ loaded, total }) => onProgress?.(total ? Math.round(loaded * 100 / total) : 0),
  })).data
}
