import { apiClient } from './client'

export async function getAccount() {
  return (await apiClient.get('/account')).data
}
