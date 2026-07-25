import { apiClient } from './client'

export async function getAccount() {
  return (await apiClient.get('/account')).data
}

export async function getCreditLedger(params) {
  return (await apiClient.get('/account/credits', { params })).data
}

export async function getGenerationHistory(params) {
  return (await apiClient.get('/account/generations', { params })).data
}

export async function getGenerationDetail(taskId) {
  return (await apiClient.get(`/account/generations/${taskId}`)).data
}
