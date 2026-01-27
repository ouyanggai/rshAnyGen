import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import api from '../api/client';
import { setAccessToken as setAccessTokenStore } from '../auth/authStore';
import { storage } from '../utils/storage';

const AppContext = createContext();

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};

export function AppProvider({ children }) {
  // 用户信息
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(() => storage.get('accessToken'));
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);

  // 主题设置
  const [theme, setTheme] = useState(() => {
    return storage.get('theme') || 'light';
  });

  // 侧边栏折叠状态
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return storage.get('sidebarCollapsed') || false;
  });

  // 加载状态
  const [isLoading, setIsLoading] = useState(false);

  // 初始化时清理无效的 localStorage 数据
  useEffect(() => {
    const cleanupOldStorage = () => {
      try {
        // 清理旧的无前缀键（迁移前的数据）
        const oldKeys = ['theme', 'sidebarCollapsed', 'user', 'chat_histories'];
        oldKeys.forEach(key => {
          const item = localStorage.getItem(key);
          if (item) {
            try {
              JSON.parse(item); // 验证是否有效
              // 如果有效且有新前缀版本，删除旧的
              const newKey = `rshanygen_${key}`;
              const newItem = localStorage.getItem(newKey);
              if (!newItem) {
                localStorage.setItem(newKey, item);
              }
              localStorage.removeItem(key);
            } catch {
              // 无效数据，直接删除
              localStorage.removeItem(key);
            }
          }
        });
      } catch (error) {
        console.error('Storage cleanup error:', error);
      }
    };

    cleanupOldStorage();
  }, []);

  // 应用主题到 DOM
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    storage.set('theme', theme);
  }, [theme]);

  // 保存侧边栏状态
  useEffect(() => {
    storage.set('sidebarCollapsed', sidebarCollapsed);
  }, [sidebarCollapsed]);

  const parsedToken = useMemo(() => {
    if (!accessToken) return null;
    try {
      const payload = accessToken.split('.')[1];
      if (!payload) return null;
      const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
      const decoded = atob(normalized);
      return JSON.parse(decoded);
    } catch {
      return null;
    }
  }, [accessToken]);

  useEffect(() => {
    setAccessTokenStore(accessToken || null);
    if (!accessToken) {
      storage.remove('accessToken');
      return;
    }
    storage.set('accessToken', accessToken);
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) {
      setUser(null);
      storage.remove('user');
      return;
    }
    const payload = parsedToken || {};
    const exp = payload.exp;
    if (exp && Date.now() / 1000 >= exp) {
      setAccessToken(null);
      setUser(null);
      storage.remove('user');
      return;
    }
    const roles = payload.roles || payload.authorities || payload?.realm_access?.roles || [];
    const nextUser = {
      id: payload.sub,
      name: payload.name || payload.preferred_username || payload.email || '用户',
      email: payload.email || null,
      roles,
      isAdmin: roles.includes('admin'),
      avatar: null,
    };
    setUser(nextUser);
    storage.set('user', nextUser);
  }, [accessToken, parsedToken]);

  // 切换主题
  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  }, []);

  // 切换侧边栏
  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  // 更新用户信息
  const updateUser = useCallback((updates) => {
    setUser(prev => {
      const newUser = { ...prev, ...updates };
      storage.set('user', newUser);
      return newUser;
    });
  }, []);

  const login = useCallback(async (username, password) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const response = await api.post('/v1/auth/login', { username, password });
      const token = response?.data?.access_token || null;
      if (!token) {
        throw new Error('登录失败');
      }
      setAccessToken(token);
      return { ok: true };
    } catch (error) {
      const message = error?.response?.data?.detail || error?.message || '登录失败';
      setAuthError(message);
      return { ok: false, error: message };
    } finally {
      setAuthLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/v1/auth/logout');
    } catch {
    }
    setAccessToken(null);
    setUser(null);
    storage.remove('user');
    storage.remove('accessToken'); // Ensure token is removed
    window.location.href = '/'; // Force reload to trigger AuthGate
  }, []);

  const value = {
    user,
    setUser,
    theme,
    setTheme,
    toggleTheme,
    sidebarCollapsed,
    setSidebarCollapsed,
    toggleSidebar,
    isLoading,
    setIsLoading,
    updateUser,
    accessToken,
    setAccessToken,
    login,
    logout,
    authError,
    authLoading,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}
