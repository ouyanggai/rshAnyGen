import { Outlet, NavLink } from 'react-router-dom';
import { BeakerIcon, WrenchIcon, BookOpenIcon, ArrowLeftIcon, ChartBarIcon } from '@heroicons/react/24/outline';

const adminNavItems = [
  { to: '/admin/models', icon: BeakerIcon, label: '模型配置' },
  { to: '/admin/skills', icon: WrenchIcon, label: '技能管理' },
  { to: '/admin/knowledge', icon: BookOpenIcon, label: '知识库' },
  { to: '/admin/tokens', icon: ChartBarIcon, label: 'Token监控' },
];

export default function AdminLayout() {
  return (
    <div className="h-full flex flex-col">
      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
