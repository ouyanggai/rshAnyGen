import { useEffect, useMemo, useState } from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import api from '../api/client';
import { createKeycloakClient } from './keycloak';
import { setAccessToken } from './authStore';

export default function KeycloakProvider({ children }) {
  const [kcConfig, setKcConfig] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [initStuck, setInitStuck] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      try {
        const response = await api.get('/v1/auth/config');
        if (cancelled) return;
        setKcConfig(response.data);
      } catch (e) {
        if (cancelled) return;
        setLoadError(e);
      }
    }

    loadConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  const keycloak = useMemo(() => {
    if (!kcConfig) return null;
    return createKeycloakClient(kcConfig);
  }, [kcConfig]);

  const initOptions = useMemo(() => {
    const secure = window.isSecureContext;
    const onLoad = secure ? 'check-sso' : 'login-required';
    return {
      onLoad,
      pkceMethod: 'S256',
      checkLoginIframe: false,
      redirectUri: `${window.location.origin}/`,
      ...(secure ? { silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html` } : {}),
    };
  }, []);

  useEffect(() => {
    if (!keycloak) return;
    setInitStuck(false);
    const timer = window.setTimeout(() => setInitStuck(true), 6000);
    return () => window.clearTimeout(timer);
  }, [keycloak]);

  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-primary dark:text-text-primary-dark bg-bg-primary dark:bg-bg-dark">
        <div className="max-w-md w-full p-6 rounded-2xl border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark">
          <div className="text-lg font-semibold mb-2">认证配置加载失败</div>
          <div className="text-sm text-text-secondary dark:text-text-secondary-dark break-all">
            {String(loadError?.message || loadError)}
          </div>
        </div>
      </div>
    );
  }

  if (!keycloak) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-secondary dark:text-text-secondary-dark bg-bg-primary dark:bg-bg-dark">
        正在初始化认证...
      </div>
    );
  }

  const Loading = () => (
    <div className="min-h-screen flex items-center justify-center text-text-secondary dark:text-text-secondary-dark bg-bg-primary dark:bg-bg-dark p-6">
      <div className="max-w-md w-full p-6 rounded-2xl border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark">
        <div className="text-lg font-semibold mb-2 text-text-primary dark:text-text-primary-dark">正在初始化...</div>
        <div className="text-sm text-text-secondary dark:text-text-secondary-dark">
          {initStuck
            ? '初始化耗时较长：请检查 Keycloak 是否可达、以及是否需要 HTTPS（不同 IP/域名下浏览器可能拒收 Secure Cookie）。'
            : '请稍候'}
        </div>
        {initStuck && (
          <div className="mt-4 text-sm">
            <a
              href="/diagnostics"
              className="text-primary hover:underline"
            >
              打开诊断页面
            </a>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={initOptions}
      LoadingComponent={Loading}
      onTokens={(tokens) => {
        setAccessToken(tokens?.token || null);
      }}
    >
      {children}
    </ReactKeycloakProvider>
  );
}
