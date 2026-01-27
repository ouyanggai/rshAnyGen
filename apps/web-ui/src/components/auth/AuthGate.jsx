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
      <div className="min-h-screen flex flex-col items-center justify-center bg-bg-primary dark:bg-bg-dark">
        <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-4"></div>
        <div className="text-lg font-medium text-text-primary dark:text-text-primary-dark">
          正在前往集团统一认证平台...
        </div>
      </div>
    );
  }

  return children;
}
