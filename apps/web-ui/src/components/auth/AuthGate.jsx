import { useEffect } from 'react';
import { useKeycloak } from '@react-keycloak/web';

export default function AuthGate({ children }) {
  const { keycloak, initialized } = useKeycloak();

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-secondary dark:text-text-secondary-dark bg-bg-primary dark:bg-bg-dark">
        正在初始化...
      </div>
    );
  }

  if (!keycloak?.authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary dark:bg-bg-dark transition-colors duration-300 p-6">
        <div className="max-w-md w-full rounded-2xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-elevation-2 p-6">
          <div className="text-2xl font-heading font-bold text-text-primary dark:text-text-primary-dark mb-2">
            rshAnyGen
          </div>
          <div className="text-sm text-text-secondary dark:text-text-secondary-dark mb-6">
            请先登录后使用
          </div>
          <button
            onClick={() => keycloak.login()}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-semibold shadow-glow-sm hover:shadow-glow-md transition-all"
          >
            登录
          </button>
        </div>
      </div>
    );
  }

  return children;
}

