import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClockIcon, TrashIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { storage } from '../utils/storage';

// 模拟对话历史数据结构
// ChatHistory: { id, title, messages, createdAt, updatedAt }

export default function HistoryPage() {
  const navigate = useNavigate();
  const [histories, setHistories] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  // 加载历史记录
  useEffect(() => {
    loadHistories();
  }, []);

  const loadHistories = () => {
    setLoading(true);
    // 从 localStorage 加载（后续可以改为从API获取）
    const saved = storage.get('chat_histories', []);
    setHistories(saved);
    setLoading(false);
  };

  // 删除对话
  const handleDelete = (id) => {
    if (confirm('确定要删除这个对话吗？')) {
      const updated = histories.filter(h => h.id !== id);
      setHistories(updated);
      storage.set('chat_histories', updated);
    }
  };

  // 打开对话
  const handleOpen = (id) => {
    // TODO: 实现恢复对话功能
    navigate('/');
  };

  // 过滤后的历史记录
  const filteredHistories = histories.filter(h =>
    h.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 按日期分组
  const groupedHistories = filteredHistories.reduce((groups, history) => {
    const date = new Date(history.updatedAt).toDateString();
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(history);
    return groups;
  }, {});

  return (
    <div className="h-full p-6 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        {/* 标题和搜索 */}
        <div className="mb-6">
          <h2 className="text-2xl font-heading font-semibold mb-4">对话历史</h2>
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              type="text"
              placeholder="搜索对话..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
            />
          </div>
        </div>

        {/* 加载状态 */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filteredHistories.length === 0 ? (
          <div className="text-center py-12">
            <ClockIcon className="w-16 h-16 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted">
              {searchQuery ? '没有找到匹配的对话' : '还没有对话历史'}
            </p>
          </div>
        ) : (
          // 按日期分组显示
          Object.entries(groupedHistories).map(([date, items]) => (
            <div key={date} className="mb-6">
              <h3 className="text-sm font-medium text-text-muted mb-3 px-1">
                {new Date(date).toLocaleDateString('zh-CN', {
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </h3>
              <div className="space-y-2">
                {items.map((history) => (
                  <div
                    key={history.id}
                    onClick={() => handleOpen(history.id)}
                    className="group flex items-center gap-4 p-4 bg-white rounded-lg border border-border hover:shadow-soft hover:border-primary/30 cursor-pointer transition-all duration-200"
                  >
                    {/* 图标 */}
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <ClockIcon className="w-5 h-5 text-primary" />
                    </div>

                    {/* 内容 */}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-text-primary truncate">
                        {history.title}
                      </h4>
                      <p className="text-sm text-text-muted">
                        {history.messages} 条消息 · {new Date(history.updatedAt).toLocaleTimeString('zh-CN', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>

                    {/* 删除按钮 */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(history.id);
                      }}
                      className="p-2 text-text-muted hover:text-red-500 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                    >
                      <TrashIcon className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
