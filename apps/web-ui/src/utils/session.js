import { storage } from './storage';

const SESSION_KEY = 'active_session_id';
const listeners = new Set();

export function getActiveSessionId() {
  return storage.get(SESSION_KEY);
}

export function setActiveSessionId(sessionId) {
  if (sessionId) {
    storage.set(SESSION_KEY, sessionId);
  } else {
    storage.remove(SESSION_KEY);
  }
  listeners.forEach((listener) => {
    try {
      listener(sessionId || null);
    } catch (error) {
      console.error('Session listener error:', error);
    }
  });
}

export function subscribeActiveSession(listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

