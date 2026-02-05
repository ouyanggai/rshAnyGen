import { useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { useCasdoor } from '../../auth/CasdoorProvider';

export default function AuthGate({ children }) {
  const { user } = useApp();
  const { login, loading } = useCasdoor();

  useEffect(() => {
    if (!loading && !user) {
      login();
    }
  }, [loading, user, login]);

  if (loading || !user) {
    return (
      <div className="min-h-screen app-shell flex flex-col items-center justify-center">
        <div className="relative z-10 flex flex-col items-center justify-center">
          <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-4" />
          <div className="text-lg font-medium text-text-primary dark:text-text-primary-dark">
            正在前往集团统一认证平台...
          </div>
          <div className="mt-2 text-sm text-text-muted dark:text-text-secondary-dark">
            新能源 · 蓝绿品牌体系
          </div>
        </div>
      </div>
    );
  }

  return children;
}
