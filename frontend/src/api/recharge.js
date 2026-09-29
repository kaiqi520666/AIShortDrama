import { apiClient } from './client'

export async function getRechargeConfig() {
  return (await apiClient.get('/recharge/config')).data
}

export async function createRechargeOrder(payload) {
  return (await apiClient.post('/recharge/orders', payload)).data
}

export async function getRechargeOrder(orderId) {
  return (await apiClient.get(`/recharge/orders/${orderId}`)).data
}

export async function queryRechargeOrder(orderId) {
  return (await apiClient.post(`/recharge/orders/${orderId}/query`)).data
}
