import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useKeycloak } from '@react-keycloak/web';
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
  const { keycloak, initialized } = useKeycloak();
  // 用户信息
  const [user, setUser] = useState(null);

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

  useEffect(() => {
    if (!initialized) return;
    if (!keycloak?.authenticated) {
      setUser(null);
      storage.remove('user');
      return;
    }

    const token = keycloak.tokenParsed || {};
    const roles = token?.realm_access?.roles || [];
    const nextUser = {
      id: token.sub,
      name: token.name || token.preferred_username || token.email || '用户',
      email: token.email || null,
      roles,
      isAdmin: roles.includes('admin'),
      avatar: null,
    };
    setUser(nextUser);
    storage.set('user', nextUser);
  }, [initialized, keycloak?.authenticated, keycloak?.token]);

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
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}
