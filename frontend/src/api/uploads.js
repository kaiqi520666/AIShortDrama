import { apiClient } from './client'

export async function uploadMedia(type, file, context, onProgress) {
  const form = new FormData()
  form.append('file', file)
  form.append('workspace_id', context.workspaceId)
  form.append('node_id', context.nodeId)
  if (context.width) form.append('width', context.width)
  if (context.height) form.append('height', context.height)
  if (context.duration) form.append('duration', context.duration)
  return (await apiClient.post(`/uploads/${type}`, form, {
    onUploadProgress: ({ loaded, total }) => onProgress?.(total ? Math.round(loaded * 100 / total) : 0),
  })).data
}
