import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClockIcon, MagnifyingGlassIcon, PencilSquareIcon, CheckIcon, XMarkIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';
import { listSessionMessages, listSessions, setActiveSession, updateSessionTitle } from '../api/sessions';
import { getActiveSessionId, subscribeActiveSession } from '../utils/session';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState(getActiveSessionId());
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  useEffect(() => {
    const unsubscribe = subscribeActiveSession((nextSessionId) => {
      setActiveSessionId(nextSessionId || null);
    });
    return unsubscribe;
  }, []);

  // 加载历史记录
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listSessions(100);
      setSessions(data);
      if (data.length > 0 && !selectedSessionId) {
        const available = data.filter(s => s.session_id !== activeSessionId);
        setSelectedSessionId(available.length > 0 ? available[0].session_id : null);
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditStart = (session) => {
    setEditingId(session.session_id);
    setEditTitle(session.title || '');
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const handleEditSave = async (sessionId) => {
    const nextTitle = editTitle.trim();
    if (!nextTitle) return;
    try {
      await updateSessionTitle(sessionId, nextTitle);
      await loadSessions();
      setEditingId(null);
      setEditTitle('');
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    }
  };

  const handleContinue = async () => {
    if (!selectedSessionId) return;
    try {
      await setActiveSession(selectedSessionId);
      navigate('/');
    } catch (e) {
      console.error('Failed to continue session', e);
    }
  };

  useEffect(() => {
    async function loadMsgs() {
      if (!selectedSessionId) {
        setMessages([]);
        return;
      }
      setMessagesLoading(true);
      setError(null);
      try {
        await setActiveSession(selectedSessionId); // Optional: Just to ensure we can read it, but here we just list msgs
        // Wait, listSessionMessages doesn't require it to be active.
        const data = await listSessionMessages(selectedSessionId, 200);
        setMessages(data);
      } catch (e) {
        setError(e?.response?.data?.detail || e.message);
      } finally {
        setMessagesLoading(false);
      }
    }
    loadMsgs();
  }, [selectedSessionId]);

  // 过滤后的历史记录
  const filteredSessions = sessions
    .filter(s => s.session_id !== activeSessionId)
    .filter(s => String(s.title || '').toLowerCase().includes(searchQuery.toLowerCase()));

  const selectedSession = sessions.find(s => s.session_id === selectedSessionId);

  return (
    <div className="h-full bg-transparent transition-colors duration-300 overflow-hidden">
      <div className="h-full flex">
        <div className="w-80 border-r border-border dark:border-border-dark bg-white dark:bg-bg-card-dark flex flex-col">
          <div className="p-4 border-b border-border dark:border-border-dark">
            <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-3">
              对话历史
            </div>
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted dark:text-text-secondary-dark" />
              <input
                type="text"
                placeholder="搜索会话..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="text-center py-12">
                <ClockIcon className="w-16 h-16 text-text-muted dark:text-text-muted/30 mx-auto mb-4" />
                <p className="text-text-muted dark:text-text-secondary-dark">
                  {searchQuery ? '没有找到匹配的会话' : '还没有会话历史'}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredSessions.map((s) => {
                  const active = s.session_id === selectedSessionId;
                  const isEditing = editingId === s.session_id;
                  return (
                    <div
                      key={s.session_id}
                      onClick={() => setSelectedSessionId(s.session_id)}
                      className={`p-3 rounded-xl cursor-pointer transition-all border ${
                        active
                          ? 'bg-bg-tertiary border-border text-text-primary dark:bg-white/5 dark:border-border-dark dark:text-text-primary-dark'
                          : 'bg-transparent border-transparent hover:bg-bg-tertiary/70 dark:hover:bg-white/5 text-text-secondary dark:text-text-secondary-dark'
                      }`}
                    >
                      {isEditing ? (
                        <div className="flex items-center gap-2">
                          <input
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="flex-1 px-2 py-1 rounded-lg border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark text-text-primary dark:text-text-primary-dark"
                            onClick={(e) => e.stopPropagation()}
                          />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditSave(s.session_id);
                            }}
                            className="p-1 rounded-lg hover:bg-bg-tertiary dark:hover:bg-white/5 text-green-600"
                          >
                            <CheckIcon className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditCancel();
                            }}
                            className="p-1 rounded-lg hover:bg-bg-tertiary dark:hover:bg-white/5 text-text-muted"
                          >
                            <XMarkIcon className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between gap-2">
                          <div className="font-medium truncate">{s.title}</div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditStart(s);
                            }}
                            className="p-1 rounded-lg hover:bg-bg-tertiary dark:hover:bg-white/5 text-text-muted"
                          >
                            <PencilSquareIcon className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                      <div className="text-xs opacity-70 mt-1">
                        {new Date((s.updated_at || 0) * 1000).toLocaleString('zh-CN')}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col h-full bg-background/50">
           {/* Header */}
           {selectedSessionId && (
              <div className="h-16 border-b border-border flex items-center justify-between px-6 bg-background/80 backdrop-blur shrink-0">
                 <h2 className="font-semibold truncate max-w-lg text-lg">
                   {selectedSession?.title || '无标题会话'}
                 </h2>
                 <button 
                   onClick={handleContinue} 
                   className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-xl shadow-sm hover:opacity-90 transition-all font-medium text-sm"
                 >
                   <ChatBubbleLeftRightIcon className="w-4 h-4" />
                   继续对话
                 </button>
              </div>
           )}

          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-4xl mx-auto">
              {error && (
                <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200/50 dark:border-red-900/30">
                  {error}
                </div>
              )}

              {!selectedSessionId ? (
                <div className="text-center py-12 text-text-muted dark:text-text-secondary-dark">
                  请选择一个会话
                </div>
              ) : messagesLoading ? (
                <div className="text-center py-12">
                  <div className="inline-block w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : messages.length === 0 ? (
                <div className="text-center py-12 text-text-muted dark:text-text-secondary-dark">
                  该会话暂无消息
                </div>
              ) : (
                <div className="space-y-6">
                  {messages.map((m, idx) => (
                    <div
                      key={`${m.ts || 0}-${idx}`}
                      className={`p-4 rounded-2xl border ${
                        m.role === 'user'
                          ? 'bg-transparent border-transparent text-right'
                          : 'bg-white dark:bg-bg-card-dark border-border dark:border-border-dark shadow-sm'
                      }`}
                    >
                      <div className={`text-xs text-text-muted dark:text-text-secondary-dark mb-2 ${m.role === 'user' ? 'text-right' : ''}`}>
                        {m.role === 'user' ? '用户' : '助手'} · {new Date((m.ts || 0) * 1000).toLocaleString('zh-CN')}
                      </div>
                      <div className={`whitespace-pre-wrap text-text-primary dark:text-text-primary-dark ${m.role === 'user' ? 'font-medium' : ''}`}>
                        {m.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}