import { useState, useCallback, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatStream } from '../hooks/useChatStream';
import { useSkills } from '../hooks/useSkills';
import {
  UserIcon,
  PaperAirplaneIcon,
  GlobeAltIcon,
  ClipboardIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import ThinkingIndicator from '../components/chat/ThinkingIndicator';
import KbSelector from '../components/chat/KbSelector';
import logo from '../assets/logo.png';

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingContent, setThinkingContent] = useState(''); // 新增：实时思考内容
  const [enableSearch, setEnableSearch] = useState(false);
  const [selectedKbs, setSelectedKbs] = useState([]); // 新增：选中的知识库
  const [copiedId, setCopiedId] = useState(null); // 新增：复制状态
  const { send } = useChatStream();
  const { enabledSkills } = useSkills();
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const isComposing = useRef(false);

  // 复制功能
  const handleCopy = async (content, id) => {
    try {
      // 优先尝试使用标准 Clipboard API
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(content);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      } else {
        // 降级方案：使用 textarea + execCommand
        const textArea = document.createElement("textarea");
        textArea.value = content;
        
        // 确保 textarea 不可见但可选中
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "0";
        document.body.appendChild(textArea);
        
        textArea.focus();
        textArea.select();
        
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        
        if (successful) {
          setCopiedId(id);
          setTimeout(() => setCopiedId(null), 2000);
        } else {
          console.error('Fallback: Copying text command was unsuccessful');
        }
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinkingContent]); // 监听 thinkingContent 变化

  // 自动调整输入框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputValue]);

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
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    
    setIsLoading(true);
    setThinkingContent('思考中...');

    let accumulatedContent = '';
    let aiMsgId = null;

    const hasStartedRef = { current: false };

    try {
      await send(message, {
        enableSearch: enableSearch,
        kbIds: selectedKbs.map(kb => kb.kb_id), // 传递选中的知识库ID
        onThinking: (content) => {
          if (!hasStartedRef.current) {
            setThinkingContent(content);
          }
        },
        onChunk: (content) => {
          accumulatedContent += content;
          
          if (!aiMsgId) {
             hasStartedRef.current = true;
             setThinkingContent(''); 
             
             aiMsgId = Date.now() + 1;
             const aiMsg = {
               id: aiMsgId,
               role: 'assistant',
               content: '',
               timestamp: new Date().toISOString(),
             };
             setMessages(prev => [...prev, aiMsg]);
          }

          setMessages(prev => prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, content: accumulatedContent }
              : msg
          ));
        },
        onDone: () => {
          setIsLoading(false);
          setThinkingContent('');
          hasStartedRef.current = false;
        },
        onError: (errorMsg) => {
          if (!aiMsgId) {
             hasStartedRef.current = true;
             setThinkingContent('');
             
             aiMsgId = Date.now() + 1;
             const errorMsgObj = {
               id: aiMsgId,
               role: 'assistant',
               content: `抱歉，发生了错误：${errorMsg}`,
               timestamp: new Date().toISOString(),
               isError: true
             };
             setMessages(prev => [...prev, errorMsgObj]);
          } else {
             setMessages(prev => prev.map(msg =>
               msg.id === aiMsgId
                 ? { ...msg, content: `抱歉，发生了错误：${errorMsg}`, isError: true }
                 : msg
             ));
          }
          setIsLoading(false);
          setThinkingContent('');
        },
      });
    } catch (error) {
       if (!aiMsgId) {
          hasStartedRef.current = true;
          setThinkingContent('');
          
          aiMsgId = Date.now() + 1;
          const errorMsgObj = {
            id: aiMsgId,
            role: 'assistant',
            content: `网络错误：${error.message}`,
            timestamp: new Date().toISOString(),
            isError: true
          };
          setMessages(prev => [...prev, errorMsgObj]);
       } else {
          setMessages(prev => prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, content: `网络错误：${error.message}`, isError: true }
              : msg
          ));
       }
      setIsLoading(false);
      setThinkingContent('');
    }
  }, [inputValue, isLoading, send, enableSearch, selectedKbs]);

  // 处理回车发送
  const handleKeyDown = (e) => {
    if (isComposing.current) return;

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col bg-bg-primary dark:bg-bg-dark transition-colors duration-200">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-text-muted dark:text-text-secondary-dark py-20">
              <div className="w-20 h-20 mb-6 rounded-full overflow-hidden shadow-glow-lg opacity-80">
                <img src={logo} alt="rshAnyGen" className="w-full h-full object-cover" />
              </div>
              <p className="text-xl font-heading font-medium mb-2 text-text-primary dark:text-text-primary-dark">rshAnyGen 智能助手</p>
              <p className="text-sm">输入您的问题开始对话</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
              >
                <div className={`flex max-w-[95%] md:max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} gap-3`}>
                  {/* 头像 */}
                  <div className={`w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm overflow-hidden ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-primary-400 to-primary-600 text-white'
                      : 'bg-transparent'
                  }`}>
                    {msg.role === 'user' ? (
                      <UserIcon className="w-5 h-5" />
                    ) : (
                      <img src={logo} alt="AI" className="w-full h-full object-cover" />
                    )}
                  </div>

                  {/* 消息气泡 */}
                  {/* 只有当消息内容不为空时才渲染气泡 */}
                  {msg.content && (
                    <div
                      className={`px-5 py-3.5 rounded-2xl shadow-sm ${
                        msg.role === 'user'
                          ? 'bg-gradient-to-r from-primary to-primary-600 text-white rounded-br-sm'
                          : msg.isError
                          ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800'
                          : 'bg-white dark:bg-bg-card-dark text-text-primary dark:text-text-primary-dark border border-border dark:border-border-dark rounded-bl-sm'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">
                          {msg.content}
                        </p>
                      ) : (
                        <div className="prose dark:prose-invert max-w-none text-[15px] leading-relaxed break-words">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      )}
                      
                      {msg.role === 'assistant' && !msg.isError && (
                        <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50 dark:border-border-dark/50">
                           <span className="text-xs text-text-muted dark:text-text-secondary-dark/70">
                            rshAnyGen AI
                           </span>
                           <div className="flex items-center gap-2">
                             <button
                               onClick={() => handleCopy(msg.content, msg.id)}
                               className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors text-text-muted"
                               title="复制内容"
                             >
                               {copiedId === msg.id ? (
                                 <CheckIcon className="w-3.5 h-3.5 text-green-500" />
                               ) : (
                                 <ClipboardIcon className="w-3.5 h-3.5" />
                               )}
                             </button>
                             <span className="text-xs text-text-muted dark:text-text-secondary-dark/70">
                               {new Date(msg.timestamp).toLocaleTimeString('zh-CN', {
                                 hour: '2-digit',
                                 minute: '2-digit',
                               })}
                             </span>
                           </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {/* 思考状态指示器 (仅在有思考内容且尚未开始生成文本时显示) */}
          {isLoading && thinkingContent && (
            <ThinkingIndicator content={thinkingContent} />
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 输入区域 */}
      <div className="p-4 md:p-6 bg-transparent">
        <div className="max-w-3xl mx-auto">
          
          {/* 知识库选择器 */}
          <KbSelector selectedKbs={selectedKbs} onChange={setSelectedKbs} />

          <div className="relative flex items-end gap-2 p-2 bg-white dark:bg-bg-card-dark rounded-[24px] shadow-elevation-2 border border-border dark:border-border-dark transition-colors duration-200">
            {/* 联网搜索按钮 (悬浮样式) */}
            <button
              onClick={() => setEnableSearch(!enableSearch)}
              className={`p-2.5 rounded-full transition-all duration-200 ${
                enableSearch
                  ? 'bg-primary/10 text-primary hover:bg-primary/20'
                  : 'text-text-muted hover:text-text-secondary hover:bg-bg-tertiary dark:hover:bg-bg-input-dark'
              }`}
              title={enableSearch ? "已开启联网搜索" : "点击开启联网搜索"}
            >
              <GlobeAltIcon className="w-5 h-5" />
            </button>

            {/* 输入框 */}
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => isComposing.current = true}
              onCompositionEnd={() => isComposing.current = false}
              placeholder="输入您的问题... (Shift+Enter 换行)"
              rows={1}
              className="flex-1 max-h-[200px] py-2.5 bg-transparent border-none focus:ring-0 resize-none text-text-primary dark:text-text-primary-dark placeholder-text-muted text-[15px] leading-relaxed"
              disabled={isLoading}
            />

            {/* 发送按钮 */}
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              className={`p-2.5 rounded-full transition-all duration-200 flex-shrink-0 mb-0.5 ${
                !inputValue.trim() || isLoading
                  ? 'bg-bg-tertiary dark:bg-bg-input-dark text-text-muted cursor-not-allowed'
                  : 'bg-gradient-to-r from-primary to-primary-600 text-white shadow-glow-sm hover:shadow-glow-md hover:scale-105 active:scale-95'
              }`}
              aria-label="发送消息"
            >
              <PaperAirplaneIcon className="w-5 h-5" />
            </button>
          </div>
          
          {/* 底部提示 */}
          <div className="text-center mt-3">
             <span className="text-xs text-text-muted/60 dark:text-text-muted/40">
               内容由 AI 生成，请仔细甄别
             </span>
          </div>
        </div>
      </div>
    </div>
  );
}
