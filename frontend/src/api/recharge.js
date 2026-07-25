import { apiClient } from './client'

export async function getRechargeConfig() {
  return (await apiClient.get('/recharge/config')).data
}

export async function createRechargeOrder(amountCents) {
  return (await apiClient.post('/recharge/orders', { amount_cents: amountCents })).data
}

export async function getRechargeOrder(orderId) {
  return (await apiClient.get(`/recharge/orders/${orderId}`)).data
}
