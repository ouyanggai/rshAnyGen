import api from './client';
import { setActiveSessionId } from '../utils/session';

export async function listSessions(limit = 50) {
  const response = await api.get('/v1/sessions', { params: { limit } });
  return response.data;
}

export async function createSession(title = '新会话') {
  const response = await api.post('/v1/sessions', { title });
  const session = response.data;
  if (session?.session_id) {
    setActiveSessionId(session.session_id);
  }
  return session;
}

export async function getActiveSession() {
  const response = await api.get('/v1/sessions/active');
  const sessionId = response?.data?.session_id;
  if (sessionId) {
    setActiveSessionId(sessionId);
  }
  return response.data;
}

export async function setActiveSession(sessionId) {
  const response = await api.post('/v1/sessions/active', { session_id: sessionId });
  if (sessionId) {
    setActiveSessionId(sessionId);
  }
  return response.data;
}

export async function listSessionMessages(sessionId, limit = 50) {
  const response = await api.get(`/v1/sessions/${sessionId}/messages`, { params: { limit } });
  return response.data;
}

export async function updateSessionTitle(sessionId, title) {
  const response = await api.patch(`/v1/sessions/${sessionId}`, { title });
  return response.data;
}

export async function updateSessionKb(sessionId, kbIds) {
  const response = await api.patch(`/v1/sessions/${sessionId}/kb`, { kb_ids: kbIds });
  return response.data;
}

export async function getSession(sessionId) {
  const response = await api.get(`/v1/sessions/${sessionId}`);
  return response.data;
}
