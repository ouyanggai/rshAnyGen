import { useNavigate, useLocation } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { PlusIcon, MoonIcon, SunIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../../hooks/useTheme';

export default function Header({ title, showNewChat = true }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const handleNewChat = () => {
    navigate('/');
  };

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-border">
      <div>
        <h1 className="text-xl font-heading font-semibold text-text-primary">
          {title || 'rshAnyGen 智能助手'}
        </h1>
        {location.pathname !== '/' && (
          <p className="text-sm text-text-secondary mt-0.5">
            {location.pathname === '/history' && '查看历史对话记录'}
            {location.pathname === '/settings' && '管理您的个人设置'}
            {location.pathname.startsWith('/admin') && '系统管理'}
          </p>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* 主题切换 */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-bg-tertiary text-text-secondary hover:text-text-primary transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/50"
          title={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}
          aria-label={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}
        >
          {theme === 'light' ? (
            <MoonIcon className="w-5 h-5" />
          ) : (
            <SunIcon className="w-5 h-5" />
          )}
        </button>

        {/* 新建对话按钮 */}
        {showNewChat && (
          <button
            onClick={handleNewChat}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-primary to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white rounded-lg shadow-glow-sm hover:shadow-glow-md transition-all duration-200 cursor-pointer font-medium focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 active:scale-[0.98]"
          >
            <PlusIcon className="w-4 h-4" />
            <span>新建对话</span>
          </button>
        )}
      </div>
    </header>
  );
}
