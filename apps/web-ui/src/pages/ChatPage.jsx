import { useState, useCallback, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatStream } from '../hooks/useChatStream';
import { listSessionMessages, getActiveSession, createSession, getSession, updateSessionTitle, updateSessionKb } from '../api/sessions';
import { getKbs } from '../api/kb';
import {
  UserIcon,
  PaperAirplaneIcon,
  GlobeAltIcon,
  ClipboardIcon,
  CheckIcon,
  PencilSquareIcon,
  XMarkIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import ThinkingIndicator from '../components/chat/ThinkingIndicator';
import KbSelector from '../components/chat/KbSelector';
import logo from '../assets/logo.png';
import { getActiveSessionId, subscribeActiveSession } from '../utils/session';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const QUICK_START = [
  {
    title: '工作汇报',
    description: '整理要点为结构化周报',
    prompt: '帮我写一份工作汇报：包含本周完成事项、风险与下周计划（用要点列出）。',
  },
  {
    title: '材料总结',
    description: '提炼结论与行动项',
    prompt: '请帮我总结下面内容，并输出：关键结论 / 风险点 / 下一步行动。\n\n（在这里粘贴材料）',
  },
  {
    title: '任务拆解',
    description: '制定落地执行清单',
    prompt: '请把“XXX 目标”拆成 10 条可执行的任务清单，并标注优先级与预计耗时。',
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingContent, setThinkingContent] = useState('');
  const [enableSearch, setEnableSearch] = useState(false);
  const [selectedKbs, setSelectedKbs] = useState([]);
  const [copiedId, setCopiedId] = useState(null);
  const [sessionTitle, setSessionTitle] = useState('');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const { send } = useChatStream();
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const isComposing = useRef(false);
  const suppressHistoryLoadRef = useRef(false);
  const [sessionId, setSessionId] = useState(getActiveSessionId());

  // Copy handler
  const handleCopy = async (content, id) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(content);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = content;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        if (successful) {
          setCopiedId(id);
          setTimeout(() => setCopiedId(null), 2000);
        }
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinkingContent]);

  useEffect(() => {
    const unsubscribe = subscribeActiveSession((nextSessionId) => {
      setSessionId(nextSessionId || null);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function ensureSession() {
      if (sessionId) return;
      try {
        const active = await getActiveSession();
        if (active?.session_id) return;
        await createSession('新会话');
      } catch (error) {
        if (!cancelled) console.error('Failed to ensure session:', error);
      }
    }
    ensureSession();
    return () => { cancelled = true; };
  }, [sessionId]);

  useEffect(() => {
    let cancelled = false;
    async function loadSessionMeta() {
      if (!sessionId) {
        setSessionTitle('');
        setTitleDraft('');
        setSelectedKbs([]);
        return;
      }
      try {
        const [session, allKbs] = await Promise.all([getSession(sessionId), getKbs()]);
        if (cancelled) return;
        setSessionTitle(session?.title || '');
        setTitleDraft(session?.title || '');
        const kbMap = new Map((allKbs || []).map(kb => [kb.kb_id, kb]));
        const sessionKbs = (session?.kb_ids || []).map(id => kbMap.get(id)).filter(Boolean);
        setSelectedKbs(sessionKbs);
      } catch (error) {
        if (!cancelled) console.error('Failed to load session meta:', error);
      }
    }
    setIsEditingTitle(false);
    loadSessionMeta();
    return () => { cancelled = true; };
  }, [sessionId]);

  useEffect(() => {
    let cancelled = false;
    async function loadSessionMessages() {
      if (suppressHistoryLoadRef.current) {
        suppressHistoryLoadRef.current = false;
        return;
      }
      if (!sessionId) {
        setMessages([]);
        return;
      }
      try {
        const data = await listSessionMessages(sessionId, 200);
        if (cancelled) return;
        const mapped = (data || []).map((m, idx) => ({
          id: `${m.ts || 0}-${idx}`,
          role: m.role,
          content: m.content,
          timestamp: m.ts ? new Date(m.ts * 1000).toISOString() : new Date().toISOString(),
        }));
        setMessages(mapped);
        setInputValue('');
        setThinkingContent('');
        setIsLoading(false);
        if (textareaRef.current) textareaRef.current.style.height = 'auto';
      } catch (error) {
        if (!cancelled) {
          if (error?.response?.status === 404) {
             suppressHistoryLoadRef.current = true;
             await createSession('新会话');
          }
        }
      }
    }
    loadSessionMessages();
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleTitleSave = async () => {
    if (!sessionId) return;
    const nextTitle = titleDraft.trim();
    if (!nextTitle) return;
    try {
      await updateSessionTitle(sessionId, nextTitle);
      setSessionTitle(nextTitle);
      setIsEditingTitle(false);
    } catch (error) {
      console.error('Failed to update title:', error);
    }
  };

  const refreshSessionTitle = async () => {
    if (!sessionId) return;
    try {
      const session = await getSession(sessionId);
      if (session?.title && session.title !== sessionTitle) {
        setSessionTitle(session.title);
        if (!isEditingTitle) setTitleDraft(session.title);
      }
    } catch (error) {
      console.error('Failed to refresh session title:', error);
    }
  };

  const handleKbChange = async (nextKbs) => {
    setSelectedKbs(nextKbs);
    if (!sessionId) return;
    try {
      await updateSessionKb(sessionId, nextKbs.map(kb => kb.kb_id));
    } catch (error) {
      console.error('Failed to update session knowledge base:', error);
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputValue]);

  const handleSend = useCallback(async () => {
    const message = inputValue.trim();
    if (!message || isLoading) return;

    if (!sessionId) {
      try {
        suppressHistoryLoadRef.current = true;
        await createSession('新会话');
      } catch (error) {
        suppressHistoryLoadRef.current = false;
      }
    }

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    
    setIsLoading(true);
    setThinkingContent('思考中...');

    let accumulatedContent = '';
    let accumulatedThinking = '';
    let aiMsgId = null;
    const hasStartedRef = { current: false };

    try {
      await send(message, {
        enableSearch: enableSearch,
        kbIds: selectedKbs.map(kb => kb.kb_id),
        onThinking: (content) => {
          if (!hasStartedRef.current) {
            accumulatedThinking += content;
            setThinkingContent(accumulatedThinking);
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
          setMessages(prev => prev.map(msg => msg.id === aiMsgId ? { ...msg, content: accumulatedContent } : msg));
        },
        onDone: () => {
          setIsLoading(false);
          setThinkingContent('');
          hasStartedRef.current = false;
          refreshSessionTitle();
        },
        onError: (errorMsg) => {
           // Error handling (omitted for brevity, same logic)
           setIsLoading(false);
           setThinkingContent('');
        },
      });
    } catch (error) {
      setIsLoading(false);
      setThinkingContent('');
    }
  }, [inputValue, isLoading, send, enableSearch, selectedKbs, sessionId]);

  const handleKeyDown = (e) => {
    if (isComposing.current) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-background relative">
      {/* 1. Header (Sticky & Glass) */}
      <header className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 bg-background/80 backdrop-blur-md border-b border-border/40">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          {isEditingTitle ? (
            <div className="flex items-center gap-2 w-full max-w-md">
              <input
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-white/10 border-transparent text-sm focus:ring-2 focus:ring-primary/20 outline-none"
                autoFocus
              />
              <button onClick={handleTitleSave} className="p-1.5 text-green-600 hover:bg-green-50 rounded-md"><CheckIcon className="w-4 h-4"/></button>
              <button onClick={() => { setIsEditingTitle(false); setTitleDraft(sessionTitle); }} className="p-1.5 text-muted-foreground hover:bg-zinc-100 rounded-md"><XMarkIcon className="w-4 h-4"/></button>
            </div>
          ) : (
            <div className="group flex items-center gap-2 cursor-pointer" onClick={() => setIsEditingTitle(true)}>
              <h2 className="text-sm font-semibold text-foreground truncate max-w-[200px] sm:max-w-md">
                {sessionTitle || '新会话'}
              </h2>
              <PencilSquareIcon className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-2">
           <KbSelector selectedKbs={selectedKbs} onChange={handleKbChange} />
        </div>
      </header>

      {/* 2. Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6">
        <div className="max-w-3xl mx-auto py-6 space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[40vh] space-y-8 animate-fade-in">
               <div className="flex flex-col items-center text-center space-y-3">
                 <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white shadow-lg">
                   <SparklesIcon className="w-7 h-7" />
                 </div>
                 <h1 className="text-xl font-semibold text-foreground">
                   你好，我是润小华
                 </h1>
                 <p className="text-sm text-muted-foreground max-w-md">
                   您的企业级 AI 助手。随时为您提供分析、写作和编码帮助。
                 </p>
               </div>

               <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
                 {QUICK_START.map((item) => (
                   <button
                     key={item.title}
                     onClick={() => { setInputValue(item.prompt); textareaRef.current?.focus(); }}
                     className="text-left p-3 rounded-xl border border-border bg-card hover:bg-zinc-50 dark:hover:bg-white/5 transition-all hover:border-primary/20 group"
                   >
                     <div className="font-medium text-sm text-foreground group-hover:text-primary transition-colors">{item.title}</div>
                     <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{item.description}</div>
                   </button>
                 ))}
               </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={cn("flex gap-4 animate-fade-in", msg.role === 'user' ? "justify-end" : "justify-start")}>
                 {/* Avatar (AI Only) */}
                 {msg.role !== 'user' && (
                   <div className="w-8 h-8 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center flex-shrink-0 mt-1">
                     <SparklesIcon className="w-4 h-4 text-primary-600" />
                   </div>
                 )}
                 
                 {/* Bubble */}
                 <div className={cn(
                   "max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                   msg.role === 'user' 
                     ? "bg-transparent px-0 py-0 sm:px-0 text-foreground font-medium" // User: No bg, just text
                     : "bg-transparent px-0 py-0 sm:px-0" // AI: No bg
                 )}>
                   {msg.role === 'user' ? (
                     <p className="whitespace-pre-wrap">{msg.content}</p>
                   ) : (
                     <div className="prose prose-sm dark:prose-invert max-w-none">
                       <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                     </div>
                   )}
                   
                   {/* AI Footer */}
                   {msg.role === 'assistant' && !msg.isError && (
                     <div className="flex items-center gap-2 mt-2">
                       <button onClick={() => handleCopy(msg.content, msg.id)} className="p-1 text-muted-foreground hover:text-foreground transition-colors" title="Copy">
                         {copiedId === msg.id ? <CheckIcon className="w-3.5 h-3.5 text-green-500"/> : <ClipboardIcon className="w-3.5 h-3.5"/>}
                       </button>
                     </div>
                   )}
                 </div>
              </div>
            ))
          )}
          
          {isLoading && thinkingContent && <ThinkingIndicator content={thinkingContent} />}
          <div ref={messagesEndRef} className="h-4" />
        </div>
      </div>

      {/* 3. Composer Area */}
      <div className="p-4 bg-background/50 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto relative">
          <div className={cn(
            "relative flex items-end gap-2 p-2 rounded-2xl border border-border bg-background shadow-sm transition-all duration-200"
          )}>
             <div className="pb-1">
                <button
                   onClick={() => setEnableSearch(!enableSearch)}
                   className={cn(
                     "p-2 rounded-xl text-xs font-medium transition-colors flex items-center justify-center gap-1 h-9 w-9",
                     enableSearch ? "bg-blue-50 text-blue-600 dark:bg-blue-900/20" : "text-muted-foreground hover:bg-zinc-100 dark:hover:bg-white/10"
                   )}
                   title={enableSearch ? "关闭联网搜索" : "开启联网搜索"}
                 >
                   <GlobeAltIcon className="w-5 h-5" />
                 </button>
             </div>

             <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入您的问题..."
                rows={1}
                className="flex-1 w-full max-h-[200px] py-2 bg-transparent border-none outline-none focus:outline-none focus:ring-0 focus:border-none resize-none text-sm text-foreground placeholder:text-muted-foreground leading-6 shadow-none appearance-none"
                disabled={isLoading}
              />
             
             <div className="pb-1">
               <button
                 onClick={handleSend}
                 disabled={!inputValue.trim() || isLoading}
                 className={cn(
                   "p-2 rounded-xl transition-all duration-200 h-9 w-9 flex items-center justify-center",
                   !inputValue.trim() || isLoading
                     ? "bg-zinc-100 text-muted-foreground cursor-not-allowed"
                     : "bg-gradient-to-r from-[#007AFF] to-[#00B388] text-white shadow-sm hover:shadow hover:opacity-90"
                 )}
               >
                 <PaperAirplaneIcon className="w-4 h-4" />
               </button>
             </div>
          </div>
          <div className="text-center mt-2">
            <span className="text-[10px] text-muted-foreground/60">AI 可能会犯错，请核对重要信息。</span>
          </div>
        </div>
      </div>
    </div>
  );
}
