import api from './client';

export async function listUsers({ search = '', first = 0, max = 50 } = {}) {
  const response = await api.get('/v1/admin/users', { params: { search, first, max } });
  return response.data;
}

export async function getUser(userId) {
  const response = await api.get(`/v1/admin/users/${userId}`);
  return response.data;
}

export async function createUser(payload) {
  const response = await api.post('/v1/admin/users', payload);
  return response.data;
}

export async function updateUser(userId, payload) {
  const response = await api.patch(`/v1/admin/users/${userId}`, payload);
  return response.data;
}

export async function resetUserPassword(userId, payload) {
  const response = await api.post(`/v1/admin/users/${userId}/reset-password`, payload);
  return response.data;
}

export async function listRoles() {
  const response = await api.get('/v1/admin/roles');
  return response.data;
}

export async function updateUserRoles(userId, payload) {
  const response = await api.post(`/v1/admin/users/${userId}/roles`, payload);
  return response.data;
}

