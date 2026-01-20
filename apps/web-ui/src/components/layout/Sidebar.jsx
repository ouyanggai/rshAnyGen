import { NavLink, useLocation } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import {
  ChatBubbleLeftRightIcon,
  ClockIcon,
  Cog6ToothIcon,
  BeakerIcon,
  WrenchIcon,
  BookOpenIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

const navItems = [
  { to: '/', icon: ChatBubbleLeftRightIcon, label: '聊天' },
  { to: '/history', icon: ClockIcon, label: '历史' },
  { to: '/settings', icon: Cog6ToothIcon, label: '设置' },
];

const adminNavItems = [
  { to: '/admin/models', icon: BeakerIcon, label: '模型配置' },
  { to: '/admin/skills', icon: WrenchIcon, label: '技能管理' },
  { to: '/admin/knowledge', icon: BookOpenIcon, label: '知识库' },
];

function SidebarItem({ to, icon: Icon, label, collapsed }) {
  const location = useLocation();
  const isActive = location.pathname === to || location.pathname.startsWith(to + '/');

  return (
    <NavLink
      to={to}
      className={`
        flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer
        transition-all duration-200 font-medium
        ${isActive
          ? 'bg-primary text-white shadow-glow-sm'
          : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'
        }
      `}
    >
      <Icon className="w-5 h-5 flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
    </NavLink>
  );
}

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, user } = useApp();
  const isAdmin = user?.isAdmin || false;

  return (
    <aside
      className={`
        flex flex-col h-full bg-white border-r border-border
        transition-all duration-300 ease-in-out
        ${sidebarCollapsed ? 'w-16' : 'w-56'}
      `}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-border">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-primary-600 flex items-center justify-center shadow-glow-sm">
              <span className="text-white font-bold text-sm">AI</span>
            </div>
            <span className="font-heading font-semibold text-lg text-text-primary">rshAnyGen</span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/50"
          aria-label={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          {sidebarCollapsed ? (
            <ChevronRightIcon className="w-5 h-5" />
          ) : (
            <ChevronLeftIcon className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        {/* 主要导航 */}
        <div className="space-y-1">
          {navItems.map((item) => (
            <SidebarItem
              key={item.to}
              to={item.to}
              icon={item.icon}
              label={item.label}
              collapsed={sidebarCollapsed}
            />
          ))}
        </div>

        {/* 管理员导航 */}
        {isAdmin && (
          <div className="space-y-1">
            {!sidebarCollapsed && (
              <div className="px-3 pb-2 text-xs font-semibold text-text-muted uppercase tracking-wider">
                管理
              </div>
            )}
            {adminNavItems.map((item) => (
              <SidebarItem
                key={item.to}
                to={item.to}
                icon={item.icon}
                label={item.label}
                collapsed={sidebarCollapsed}
              />
            ))}
          </div>
        )}
      </nav>

      {/* User Info */}
      <div className="px-3 py-4 border-t border-border">
        <div className={`flex items-center gap-3 ${sidebarCollapsed ? 'justify-center' : ''}`}>
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-semibold text-sm shadow-elevation-2">
            {user?.name?.charAt(0) || 'U'}
          </div>
          {!sidebarCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate text-text-primary">{user?.name || '用户'}</p>
              <p className="text-xs text-text-muted">
                {isAdmin ? '管理员' : '普通用户'}
              </p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
