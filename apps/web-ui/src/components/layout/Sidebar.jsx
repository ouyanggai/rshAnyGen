import { useCallback, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { useTheme } from '../../hooks/useTheme';
import { createSession } from '../../api/sessions';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  ChatBubbleLeftRightIcon,
  ClockIcon,
  Cog6ToothIcon,
  BeakerIcon,
  WrenchIcon,
  BookOpenIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MoonIcon,
  SunIcon,
  PlusIcon,
  SparklesIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { to: '/', icon: ChatBubbleLeftRightIcon, label: '对话' },
  { to: '/history', icon: ClockIcon, label: '历史记录' },
  { to: '/settings', icon: Cog6ToothIcon, label: '系统设置' },
];

const adminNavItems = [
  { to: '/admin/models', icon: BeakerIcon, label: '模型配置' },
  { to: '/admin/skills', icon: WrenchIcon, label: '技能中心' },
  { to: '/admin/knowledge', icon: BookOpenIcon, label: '知识库' },
  { to: '/admin/tokens', icon: ChartBarIcon, label: 'Token 监控' },
];

function SidebarItem({ to, icon: Icon, label, collapsed }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'relative flex items-center rounded-lg cursor-pointer select-none group transition-all duration-200',
          'px-3 py-2 text-sm font-medium',
          collapsed ? 'justify-center' : '',
          isActive
            ? 'bg-zinc-100 dark:bg-white/10 text-foreground'
            : 'text-muted-foreground hover:bg-zinc-50 dark:hover:bg-white/5 hover:text-foreground'
        )
      }
      title={collapsed ? label : ''}
    >
      <Icon className="w-5 h-5 flex-shrink-0" />
      {!collapsed && (
        <span className="ml-3 truncate transition-all duration-300">
          {label}
        </span>
      )}
    </NavLink>
  );
}

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, user } = useApp();
  const { theme, toggleTheme } = useTheme();
  const isAdmin = user?.isAdmin || false;
  const navigate = useNavigate();
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  const handleNewChat = async () => {
    if (isCreatingSession) return;
    setIsCreatingSession(true);
    try {
      await createSession('新会话');
    } catch (e) {
      console.error('Failed to create session', e);
    } finally {
      setIsCreatingSession(false);
      navigate('/');
    }
  };

  return (
    <aside
      className={cn(
        'flex flex-col h-full z-30',
        'bg-background/80 backdrop-blur-xl border-r border-border',
        'transition-all duration-300 ease-[cubic-bezier(0.25,1,0.5,1)]',
        sidebarCollapsed ? 'w-[72px]' : 'w-[280px]'
      )}
    >
      {/* 1. Header Area */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border/50">
        <div className={cn("flex items-center gap-3 overflow-hidden transition-all duration-300", sidebarCollapsed ? "w-full justify-center" : "w-full")}>
           <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center flex-shrink-0 shadow-sm text-white">
             <SparklesIcon className="w-5 h-5" />
           </div>
           {!sidebarCollapsed && (
             <div className="flex flex-col">
               <span className="font-semibold text-sm leading-none">润小华</span>
               <span className="text-[10px] text-muted-foreground mt-1">Enterprise AI</span>
             </div>
           )}
        </div>
      </div>

      {/* 2. New Chat Action */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          disabled={isCreatingSession}
          className={cn(
            'w-full flex items-center justify-center',
            'rounded-lg transition-all duration-200',
            'bg-gradient-to-r from-[#007AFF] to-[#00B388] text-white shadow-sm', // Keeping the requested gradient
            'hover:shadow-md hover:opacity-95 active:scale-[0.98]',
            sidebarCollapsed ? 'h-10 w-10 p-0' : 'h-10 px-4 gap-2'
          )}
          title="新建对话"
        >
          <PlusIcon className="w-5 h-5" />
          {!sidebarCollapsed && <span className="font-medium text-sm">新建对话</span>}
        </button>
      </div>

      {/* 3. Navigation Areas */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-muted-foreground/20 hover:scrollbar-thumb-muted-foreground/40 p-3 space-y-6">
        
        {/* Main Menu */}
        <div className="space-y-1">
          {!sidebarCollapsed && <div className="px-3 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">工作区</div>}
          {navItems.map((item) => (
            <SidebarItem key={item.to} {...item} collapsed={sidebarCollapsed} />
          ))}
        </div>

        {/* Admin Menu */}
        {isAdmin && (
          <div className="space-y-1">
             {!sidebarCollapsed && <div className="px-3 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">管理后台</div>}
             {adminNavItems.map((item) => (
               <SidebarItem key={item.to} {...item} collapsed={sidebarCollapsed} />
             ))}
          </div>
        )}
      </div>

      {/* 4. Bottom Actions (Footer) */}
      <div className="p-3 border-t border-border/50 bg-background/50 backdrop-blur-sm">
        <div className={cn("flex items-center gap-1", sidebarCollapsed ? "flex-col" : "justify-between")}>
          <button
            onClick={toggleTheme}
            className="p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors"
            title="切换主题"
          >
            {theme === 'light' ? <MoonIcon className="w-5 h-5" /> : <SunIcon className="w-5 h-5" />}
          </button>
          
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors"
            title={sidebarCollapsed ? "展开" : "收起"}
          >
            {sidebarCollapsed ? <ChevronRightIcon className="w-5 h-5" /> : <ChevronLeftIcon className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </aside>
  );
}
