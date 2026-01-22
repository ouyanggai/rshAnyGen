/**
 * 聊天 API - 支持 SSE 流式传输
 */

import { getAccessToken } from '../auth/authStore';
import { storage } from '../utils/storage';

const SESSION_KEY = 'active_session_id';

// 流式聊天
export async function streamChat(message, options = {}) {
  const {
    enableSearch = false,
    kbIds = [],
    onThinking = () => {},
    onChunk = () => {},
    onDone = () => {},
    onError = () => {},
  } = options;

  try {
    const token = getAccessToken();
    const sessionId = storage.get(SESSION_KEY);

    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(sessionId ? { 'X-Session-ID': sessionId } : {}),
      },
      body: JSON.stringify({ 
        message, 
        enable_search: enableSearch, 
        kb_ids: kbIds,
        stream: true 
      }),
    });

    const nextSessionId = response.headers.get('X-Session-ID');
    if (nextSessionId) storage.set(SESSION_KEY, nextSessionId);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onDone();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();

          if (data === '[DONE]') {
            onDone();
            return;
          }

          try {
            const parsed = JSON.parse(data);

            switch (parsed.type) {
              case 'thinking':
                onThinking(parsed.content);
                break;
              case 'chunk':
                onChunk(parsed.content);
                break;
              case 'done':
                onDone();
                return;
              case 'error':
                onError(parsed.message);
                return;
              default:
                console.log('Unknown message type:', parsed);
            }
          } catch (e) {
            console.error('Parse error:', e, data);
          }
        }
      }
    }
  } catch (error) {
    console.error('Stream chat error:', error);
    onError(error.message || '网络连接失败');
  }
}

// 发送消息（非流式，用于兼容）
export async function sendMessage(message, options = {}) {
  const {
    enableSearch = false,
    kbIds = [],
  } = options;

  const token = getAccessToken();
  const sessionId = storage.get(SESSION_KEY);

  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(sessionId ? { 'X-Session-ID': sessionId } : {}),
    },
    body: JSON.stringify({ 
      message, 
      enable_search: enableSearch, 
      kb_ids: kbIds,
      stream: false 
    }),
  });

  const nextSessionId = response.headers.get('X-Session-ID');
  if (nextSessionId) storage.set(SESSION_KEY, nextSessionId);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}
