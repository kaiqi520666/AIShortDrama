import { apiClient } from './client'

export async function uploadMedia(type, file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  return (await apiClient.post(`/uploads/${type}`, form, {
    onUploadProgress: ({ loaded, total }) => onProgress?.(total ? Math.round(loaded * 100 / total) : 0),
  })).data
}
