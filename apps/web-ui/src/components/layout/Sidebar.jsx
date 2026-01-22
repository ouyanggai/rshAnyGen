import { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { useTheme } from '../../hooks/useTheme';
import {
  ChatBubbleLeftRightIcon,
  ClockIcon,
  Cog6ToothIcon,
  BeakerIcon,
  WrenchIcon,
  BookOpenIcon,
  UsersIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MoonIcon,
  SunIcon,
  PlusIcon,
  SparklesIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';

const navItems = [
  { to: '/', icon: ChatBubbleLeftRightIcon, label: '聊天' },
  { to: '/history', icon: ClockIcon, label: '历史' },
  { to: '/settings', icon: Cog6ToothIcon, label: '设置' },
  { to: '/diagnostics', icon: InformationCircleIcon, label: '诊断' },
];

const adminNavItems = [
  { to: '/admin/models', icon: BeakerIcon, label: '模型配置' },
  { to: '/admin/users', icon: UsersIcon, label: '用户管理' },
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
        flex items-center px-3 py-3 rounded-xl cursor-pointer
        transition-all duration-200 font-medium select-none group
        ${collapsed ? 'justify-center' : ''}
        ${isActive
          ? 'bg-gradient-to-r from-primary/20 to-secondary/10 text-primary dark:text-primary-400'
          : 'text-text-secondary dark:text-text-secondary-dark hover:bg-bg-tertiary dark:hover:bg-white/5 hover:text-text-primary dark:hover:text-text-primary-dark'
        }
      `}
      title={collapsed ? label : ''}
    >
      <Icon className={`w-5 h-5 flex-shrink-0 transition-colors ${isActive ? 'text-primary dark:text-primary-400' : 'text-text-muted group-hover:text-text-primary dark:text-text-muted dark:group-hover:text-text-primary-dark'}`} />
      <span className={`whitespace-nowrap overflow-hidden transition-all duration-300 ease-in-out ${collapsed ? 'w-0 opacity-0' : 'w-auto opacity-100 ml-3'}`}>
        {label}
      </span>
    </NavLink>
  );
}

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, user } = useApp();
  const { theme, toggleTheme } = useTheme();
  const isAdmin = user?.isAdmin || false;
  const navigate = useNavigate();

  return (
    <aside
      className={`
        flex flex-col h-full 
        bg-white dark:bg-bg-card-dark 
        border-r border-border dark:border-border-dark
        transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)]
        shadow-elevation-2 z-20
        overflow-hidden whitespace-nowrap
        ${sidebarCollapsed ? 'w-20' : 'w-64'}
      `}
    >
      {/* Logo Area */}
      <div className={`flex items-center px-5 py-6 mb-2 h-[88px] transition-all duration-300 ${sidebarCollapsed ? 'justify-center' : 'justify-start'}`}>
        <div 
          className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-glow-sm flex-shrink-0 cursor-pointer z-10"
          onClick={sidebarCollapsed ? toggleSidebar : undefined}
        >
           {sidebarCollapsed ? <span className="text-white font-bold text-xs">RSH</span> : <SparklesIcon className="w-6 h-6 text-white" />}
        </div>
        
        <div className={`flex flex-col overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'w-0 opacity-0' : 'w-32 opacity-100 ml-3'}`}>
          <span className="font-heading font-bold text-lg text-text-primary dark:text-text-primary-dark tracking-tight leading-tight">润小华</span>
          <span className="text-[10px] font-bold tracking-widest text-primary uppercase">Version 2.0</span>
        </div>
      </div>

      {/* New Chat Button */}
      <div className={`px-4 mb-6 transition-all duration-300 ${sidebarCollapsed ? 'px-2' : ''}`}>
        <button
          onClick={() => navigate('/')}
          className={`
            w-full flex items-center justify-center
            bg-gradient-to-r from-primary to-secondary 
            hover:shadow-glow-md active:scale-[0.98]
            text-white rounded-xl transition-all duration-200
            ${sidebarCollapsed ? 'p-3 aspect-square' : 'py-3.5 px-4'}
          `}
          title="新建对话"
        >
          <PlusIcon className="w-5 h-5 flex-shrink-0" />
          <span className={`font-semibold overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100 ml-2'}`}>新建对话</span>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-8 overflow-y-auto scrollbar-none overflow-x-hidden">
        {/* Main Nav */}
        <div className="space-y-1.5">
          <div className={`px-3 text-xs font-semibold text-text-muted dark:text-text-muted/60 uppercase tracking-wider mb-2 overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'h-0 opacity-0 mb-0' : 'h-auto opacity-100'}`}>Menu</div>
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

        {/* Admin Nav */}
        {isAdmin && (
          <div className="space-y-1.5">
            <div className={`px-3 text-xs font-semibold text-text-muted dark:text-text-muted/60 uppercase tracking-wider mb-2 overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'h-0 opacity-0 mb-0' : 'h-auto opacity-100'}`}>Admin</div>
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

      {/* Bottom Actions */}
      <div className="p-4 border-t border-border dark:border-border-dark bg-bg-primary/30 dark:bg-black/10 backdrop-blur-sm">
        <div className={`flex flex-col gap-2 ${sidebarCollapsed ? 'items-center' : ''}`}>
          
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={`
              flex items-center p-2.5 rounded-xl
              text-text-secondary dark:text-text-secondary-dark
              hover:bg-white dark:hover:bg-white/10 hover:text-primary dark:hover:text-primary-400
              hover:shadow-sm transition-all duration-200
              ${sidebarCollapsed ? 'justify-center w-full aspect-square' : ''}
            `}
            title={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}
          >
            {theme === 'light' ? (
              <MoonIcon className="w-5 h-5 flex-shrink-0" />
            ) : (
              <SunIcon className="w-5 h-5 flex-shrink-0" />
            )}
            <span className={`font-medium overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100 ml-3'}`}>
              {theme === 'light' ? '深色模式' : '浅色模式'}
            </span>
          </button>

          {/* Collapse Toggle */}
          <button
            onClick={toggleSidebar}
            className={`
              flex items-center p-2.5 rounded-xl
              text-text-secondary dark:text-text-secondary-dark
              hover:bg-white dark:hover:bg-white/10 hover:text-primary dark:hover:text-primary-400
              hover:shadow-sm transition-all duration-200
              ${sidebarCollapsed ? 'justify-center w-full aspect-square' : ''}
            `}
          >
            {sidebarCollapsed ? (
              <ChevronRightIcon className="w-5 h-5 flex-shrink-0" />
            ) : (
              <ChevronLeftIcon className="w-5 h-5 flex-shrink-0" />
            )}
            <span className={`font-medium overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100 ml-3'}`}>收起侧边栏</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
