import { useState, useCallback, useRef } from 'react';
import { streamChat } from '../api/chat';

export function useChatStream() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const send = useCallback(async (message, callbacks = {}) => {
    setIsLoading(true);
    setError(null);

    try {
      await streamChat(message, {
        ...callbacks,
        onError: (errorMsg) => {
          setError(errorMsg);
          callbacks.onError?.(errorMsg);
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
