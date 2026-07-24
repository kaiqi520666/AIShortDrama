import { apiClient } from './client'

export async function register(payload) {
  return (await apiClient.post('/auth/register', payload)).data
}

export async function login(payload) {
  return (await apiClient.post('/auth/login', payload)).data
}

export async function logout() {
  return (await apiClient.post('/auth/logout')).data
}

export async function getCurrentUser() {
  return (await apiClient.get('/auth/me')).data
}

export async function changePassword(payload) {
  return (await apiClient.post('/auth/change-password', payload)).data
}
