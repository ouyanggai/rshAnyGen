import { useState, useCallback, useRef } from 'react';
import { streamChat } from '../api/chat';

export function useChatStream() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const send = useCallback(async (message, options = {}) => {
    setIsLoading(true);
    setError(null);

    try {
      await streamChat(message, {
        enableSearch: options.enableSearch || false,
        onThinking: options.onThinking,
        onChunk: options.onChunk,
        onDone: options.onDone,
        onError: (errorMsg) => {
          setError(errorMsg);
          options.onError?.(errorMsg);
        },
      });
    } catch (err) {
      const errorMsg = err.message || '发送消息失败';
      setError(errorMsg);
      callbacks.onError?.(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    send,
    isLoading,
    error,
  };
}
