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

export async function getAdminBillingPolicy() {
  return (await apiClient.get('/admin/billing-policy')).data
}

export async function updateAdminBillingPolicy(payload) {
  return (await apiClient.put('/admin/billing-policy', payload)).data
}

export async function getAdminModels() {
  return (await apiClient.get('/admin/models')).data
}

export async function updateAdminModel(mediaType, modelId, payload) {
  return (await apiClient.put(`/admin/models/${mediaType}/${modelId}`, payload)).data
}

export async function getAdminContentTemplate(key) {
  return (await apiClient.get(`/admin/content-templates/${key}`)).data
}

export async function getAdminContentTemplates() {
  return (await apiClient.get('/admin/content-templates')).data
}

export async function updateAdminContentTemplate(key, payload) {
  return (await apiClient.put(`/admin/content-templates/${key}`, payload)).data
}

export async function getAdminReferenceAssets(params) {
  return (await apiClient.get('/admin/reference-assets', { params })).data
}

export async function createAdminReferenceAsset(formData) {
  return (await apiClient.post('/admin/reference-assets', formData)).data
}

export async function updateAdminReferenceAsset(resourceType, assetId, payload) {
  return (await apiClient.put(`/admin/reference-assets/${resourceType}/${assetId}`, payload)).data
}

export async function registerAdminSystemCharacter(assetId, formData) {
  return (await apiClient.post(`/admin/reference-assets/character/${assetId}/register`, formData)).data
}

export async function getAdminDashboard(days = 7) {
  return (await apiClient.get('/admin/dashboard', { params: { days } })).data
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
