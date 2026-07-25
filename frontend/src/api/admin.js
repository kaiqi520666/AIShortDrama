import { apiClient } from './client'

export async function getAdminUsers(params) {
  return (await apiClient.get('/admin/users', { params })).data
}

export async function adjustUserCredits(userId, payload) {
  return (await apiClient.post(`/admin/users/${userId}/credits`, payload)).data
}

export async function updateUserRole(userId, payload) {
  return (await apiClient.post(`/admin/users/${userId}/role`, payload)).data
}

export async function updateUserStatus(userId, payload) {
  return (await apiClient.post(`/admin/users/${userId}/status`, payload)).data
}

export async function resetUserPassword(userId, payload) {
  return (await apiClient.post(`/admin/users/${userId}/password`, payload)).data
}

export async function getAdminPricing() {
  return (await apiClient.get('/admin/pricing')).data
}

export async function updateAdminPricing(ruleId, payload) {
  return (await apiClient.put(`/admin/pricing/${ruleId}`, payload)).data
}

export async function getAdminTasks(params) {
  return (await apiClient.get('/admin/tasks', { params })).data
}

export async function getAdminAudits(params) {
  return (await apiClient.get('/admin/audits', { params })).data
}

export async function getAdminRechargeTiers() {
  return (await apiClient.get('/admin/recharge/tiers')).data
}

export async function createAdminRechargeTier(payload) {
  return (await apiClient.post('/admin/recharge/tiers', payload)).data
}

export async function updateAdminRechargeTier(tierId, payload) {
  return (await apiClient.put(`/admin/recharge/tiers/${tierId}`, payload)).data
}

export async function getAdminRechargeOrders(params) {
  return (await apiClient.get('/admin/recharge/orders', { params })).data
}
