import { apiClient } from './client'

export async function getCredits() {
  return (await apiClient.get('/credits')).data
}
