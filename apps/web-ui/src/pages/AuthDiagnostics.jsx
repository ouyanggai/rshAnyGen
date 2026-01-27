import { useEffect, useMemo, useState } from 'react';
import { useApp } from '../context/AppContext';
import api from '../api/client';

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <div className="text-sm text-text-muted dark:text-text-secondary-dark whitespace-nowrap">{label}</div>
      <div className="text-sm text-text-primary dark:text-text-primary-dark break-all text-right">{String(value ?? '')}</div>
    </div>
  );
}

export default function AuthDiagnostics() {
  const { user, accessToken, logout } = useApp();
  const [configStatus, setConfigStatus] = useState(null);
  const [userinfoStatus, setUserinfoStatus] = useState(null);
  const [lastError, setLastError] = useState(null);

  const origin = useMemo(() => window.location.origin, []);
  const secure = useMemo(() => window.isSecureContext, []);
  const roles = useMemo(() => {
    const nextRoles = user?.roles || [];
    return Array.isArray(nextRoles) ? nextRoles : [];
  }, [user?.roles]);

  useEffect(() => {
    async function run() {
      setLastError(null);
      try {
        const c = await api.get('/v1/auth/config');
        setConfigStatus({ ok: true, data: c.data });
      } catch (e) {
        setConfigStatus({ ok: false, error: e?.response?.data?.detail || e.message });
      }

      try {
        const u = await api.get('/v1/auth/userinfo');
        setUserinfoStatus({ ok: true, data: u.data });
      } catch (e) {
        setUserinfoStatus({ ok: false, error: e?.response?.data?.detail || e.message });
      }
    }
    run().catch((e) => setLastError(e?.message || String(e)));
  }, []);

  const redirectHint = `${origin}/*`;

  return (
    <div className="h-full p-6 overflow-y-auto bg-bg-primary dark:bg-bg-dark transition-colors duration-300">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-heading font-semibold mb-6 text-text-primary dark:text-text-primary-dark">
          认证与权限诊断
        </h2>

        <div className="bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark rounded-2xl p-6 shadow-elevation-1 mb-6">
          <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-4">环境</div>
          <div className="divide-y divide-border dark:divide-border-dark">
            <Row label="Origin" value={origin} />
            <Row label="安全上下文 (HTTPS/localhost)" value={secure ? '是' : '否'} />
            <Row label="建议 Redirect URI" value={redirectHint} />
          </div>
          <div className="mt-4 text-sm text-text-muted dark:text-text-secondary-dark">
            如果你用局域网 IP 访问（如 192.168.x.x），请在 Casdoor 的应用回调地址里配置上面的 Redirect URI。
          </div>
        </div>

        <div className="bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark rounded-2xl p-6 shadow-elevation-1 mb-6">
          <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-4">认证状态 (Casdoor)</div>
          <div className="divide-y divide-border dark:divide-border-dark">
            <Row label="authenticated" value={accessToken ? 'true' : 'false'} />
            <Row label="用户名" value={user?.name || '未登录'} />
            <Row label="是否管理员 (admin 角色)" value={user?.isAdmin ? '是' : '否'} />
            <Row label="roles" value={roles.join(', ') || '(空)'} />
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={logout}
              className="px-4 py-2 rounded-xl bg-primary text-white font-semibold hover:opacity-90 transition-opacity"
            >
              退出登录
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark rounded-2xl p-6 shadow-elevation-1 mb-6">
          <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-4">后端连通性</div>
          <div className="divide-y divide-border dark:divide-border-dark">
            <Row label="/api/v1/auth/config" value={configStatus ? (configStatus.ok ? 'OK' : `失败：${configStatus.error}`) : '检查中...'} />
            <Row label="/api/v1/auth/userinfo" value={userinfoStatus ? (userinfoStatus.ok ? 'OK' : `失败：${userinfoStatus.error}`) : '检查中...'} />
          </div>
          {lastError && (
            <div className="mt-4 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200/50 dark:border-red-900/30">
              {lastError}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark rounded-2xl p-6 shadow-elevation-1">
          <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-4">进入用户管理需要什么</div>
          <div className="text-sm text-text-secondary dark:text-text-secondary-dark leading-6">
            1) 给你的 MaxKey 用户分配 admin 角色。 2) 确保后端 JWT 中携带 roles 信息。
          </div>
        </div>
      </div>
    </div>
  );
}
