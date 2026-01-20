import { useState, useCallback, useRef, useEffect } from 'react';
import { useChatStream } from '../hooks/useChatStream';
import { useSkills } from '../hooks/useSkills';
import {
  PlusIcon,
  SparklesIcon,
  UserIcon,
  PaperAirplaneIcon,
} from '@heroicons/react/24/outline';

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { send } = useChatStream();
  const { enabledSkills } = useSkills();
  const messagesEndRef = useRef(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 处理发送消息
  const handleSend = useCallback(async () => {
    const message = inputValue.trim();
    if (!message || isLoading) return;

    // 添加用户消息
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    // 创建 AI 消息占位符
    const aiMsgId = Date.now() + 1;
    const aiMsg = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, aiMsg]);

    let accumulatedContent = '';

    try {
      await send(message, {
        onChunk: (content) => {
          accumulatedContent += content;
          setMessages(prev => prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, content: accumulatedContent }
              : msg
          ));
        },
        onDone: () => {
          setIsLoading(false);
        },
        onError: (errorMsg) => {
          setMessages(prev => prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, content: `抱歉，发生了错误：${errorMsg}`, isError: true }
              : msg
          ));
          setIsLoading(false);
        },
      });
    } catch (error) {
      setMessages(prev => prev.map(msg =>
        msg.id === aiMsgId
          ? { ...msg, content: `网络错误：${error.message}`, isError: true }
          : msg
      ));
      setIsLoading(false);
    }
  }, [inputValue, isLoading, send]);

  // 处理回车发送
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col bg-bg-primary">
      {/* 顶部状态栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-white">
        <div className="flex items-center gap-2">
          <SparklesIcon className="w-5 h-5 text-primary" />
          <span className="font-semibold text-text-primary">rshAnyGen 智能助手</span>
        </div>
        {enabledSkills.length > 0 && (
          <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full">
            {enabledSkills.length} 个技能已启用
          </span>
        )}
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-text-muted">
            <SparklesIcon className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg mb-2">欢迎使用 rshAnyGen</p>
            <p className="text-sm">输入您的问题开始对话</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} gap-3`}>
                {/* 头像 */}
                <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-primary-400 to-primary-600 text-white'
                    : 'bg-gradient-to-br from-secondary-light to-secondary text-white'
                }`}>
                  {msg.role === 'user' ? (
                    <UserIcon className="w-4 h-4" />
                  ) : (
                    <SparklesIcon className="w-4 h-4" />
                  )}
                </div>

                {/* 消息气泡 */}
                <div
                  className={`px-4 py-3 rounded-2xl ${
                    msg.role === 'user'
                      ? 'bg-primary text-white rounded-br-sm'
                      : msg.isError
                      ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800'
                      : 'bg-white text-text-primary border border-border rounded-bl-sm shadow-elevation-1'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                    {msg.content}
                  </p>
                  {msg.role === 'assistant' && !msg.isError && (
                    <p className="text-xs text-text-muted mt-2">
                      {new Date(msg.timestamp).toLocaleTimeString('zh-CN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {/* 加载中动画 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-secondary-light to-secondary text-white flex items-center justify-center">
                <SparklesIcon className="w-4 h-4" />
              </div>
              <div className="px-4 py-3 bg-white rounded-2xl rounded-bl-sm border border-border shadow-elevation-1">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className="p-4 border-t border-border bg-white">
        <div className="flex items-end gap-3 max-w-4xl mx-auto">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题... (Shift+Enter 换行)"
            rows={1}
            className="flex-1 px-4 py-3 bg-bg-tertiary border border-border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
            style={{ minHeight: '48px', maxHeight: '120px' }}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="p-3 bg-gradient-to-r from-primary to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white rounded-xl shadow-glow-sm hover:shadow-glow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none active:scale-[0.98]"
            aria-label="发送消息"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
