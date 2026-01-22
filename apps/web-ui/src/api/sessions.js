import api from './client';

export async function listSessions(limit = 50) {
  const response = await api.get('/v1/sessions', { params: { limit } });
  return response.data;
}

export async function createSession(title = '新会话') {
  const response = await api.post('/v1/sessions', { title });
  return response.data;
}

export async function getActiveSession() {
  const response = await api.get('/v1/sessions/active');
  return response.data;
}

export async function setActiveSession(sessionId) {
  const response = await api.post('/v1/sessions/active', { session_id: sessionId });
  return response.data;
}

export async function listSessionMessages(sessionId, limit = 50) {
  const response = await api.get(`/v1/sessions/${sessionId}/messages`, { params: { limit } });
  return response.data;
}

