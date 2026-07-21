import { apiClient } from './client'

export async function createImageGeneration(payload) {
  return (await apiClient.post('/generations/images', payload)).data
}

export async function getGenerationTask(taskId) {
  return (await apiClient.get(`/generations/${taskId}`)).data
}
