import { useApp } from '../../context/AppContext';

export default function AdminGate({ children }) {
  const { user } = useApp();

  if (!user?.isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary dark:bg-bg-dark transition-colors duration-300 p-6">
        <div className="max-w-md w-full rounded-2xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-elevation-2 p-6">
          <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-2">
            无权限访问
          </div>
          <div className="text-sm text-text-secondary dark:text-text-secondary-dark">
            需要管理员权限
          </div>
        </div>
      </div>
    );
  }

  return children;
}

