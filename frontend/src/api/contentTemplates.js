import { apiClient } from './client'

export async function getProductContentTemplates() {
  return (await apiClient.get('/content-templates/product')).data
}
