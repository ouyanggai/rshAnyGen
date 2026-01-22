import { useState, useEffect } from 'react';
import { ClockIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { listSessionMessages, listSessions, setActiveSession } from '../api/sessions';

export default function HistoryPage() {
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

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
        setSelectedSessionId(data[0].session_id);
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
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
        await setActiveSession(selectedSessionId);
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
  const filteredSessions = sessions.filter(s =>
    String(s.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full bg-bg-primary dark:bg-bg-dark transition-colors duration-300 overflow-hidden">
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
                className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark rounded-xl text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder-text-muted dark:placeholder-text-muted/50"
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
                  return (
                    <div
                      key={s.session_id}
                      onClick={() => setSelectedSessionId(s.session_id)}
                      className={`p-3 rounded-xl cursor-pointer transition-all border ${
                        active
                          ? 'bg-primary/10 border-primary/30 text-primary dark:bg-primary/20'
                          : 'bg-transparent border-transparent hover:bg-bg-tertiary dark:hover:bg-white/5 text-text-secondary dark:text-text-secondary-dark'
                      }`}
                    >
                      <div className="font-medium truncate">{s.title}</div>
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
              <div className="space-y-3">
                {messages.map((m, idx) => (
                  <div
                    key={`${m.ts || 0}-${idx}`}
                    className={`p-4 rounded-2xl border ${
                      m.role === 'user'
                        ? 'bg-white dark:bg-bg-card-dark border-border dark:border-border-dark'
                        : 'bg-primary/5 dark:bg-primary/10 border-primary/20'
                    }`}
                  >
                    <div className="text-xs text-text-muted dark:text-text-secondary-dark mb-2">
                      {m.role === 'user' ? '用户' : '助手'} · {new Date((m.ts || 0) * 1000).toLocaleString('zh-CN')}
                    </div>
                    <div className="whitespace-pre-wrap text-text-primary dark:text-text-primary-dark">
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
  );
}
