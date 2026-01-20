import { Outlet, NavLink } from 'react-router-dom';
import { BeakerIcon, WrenchIcon, BookOpenIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

const adminNavItems = [
  { to: '/admin/models', icon: BeakerIcon, label: '模型配置' },
  { to: '/admin/skills', icon: WrenchIcon, label: '技能管理' },
  { to: '/admin/knowledge', icon: BookOpenIcon, label: '知识库' },
];

export default function AdminLayout() {
  return (
    <div className="h-full flex">
      {/* 管理员侧边栏 */}
      <aside className="w-56 bg-white border-r border-border p-4">
        {/* 返回按钮 */}
        <NavLink
          to="/"
          className="flex items-center gap-2 px-3 py-2 text-text-muted hover:text-text-primary mb-4 rounded-lg hover:bg-bg-tertiary transition-colors"
        >
          <ArrowLeftIcon className="w-4 h-4" />
          <span className="text-sm">返回</span>
        </NavLink>

        {/* 管理菜单 */}
        <nav className="space-y-1">
          {adminNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200
                ${isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'
                }
              `}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
