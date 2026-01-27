import { createContext, useContext, useEffect, useState } from 'react';
import api from '../api/client';
import { setAccessToken } from './authStore';

const CasdoorContext = createContext(null);

export function useCasdoor() {
  const context = useContext(CasdoorContext);
  if (!context) {
    throw new Error('useCasdoor must be used within CasdoorProvider');
  }
  return context;
}

export default function CasdoorProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    async function init() {
      try {
        // Fetch auth config from backend
        const { data } = await api.get('/v1/auth/config');
        setConfig(data);
      } catch (e) {
        console.error("Failed to load auth config", e);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const login = () => {
    if (config?.login_url) {
      window.location.href = config.login_url;
    } else {
        console.error("Login URL not available");
    }
  };

  const logout = () => {
      setAccessToken(null);
      setIsAuthenticated(false);
      // Optional: Redirect to Casdoor logout
      // if (config?.logout_url) window.location.href = config.logout_url;
      window.location.href = "/"; 
  };

  return (
    <CasdoorContext.Provider value={{ config, login, logout, isAuthenticated, setIsAuthenticated, loading }}>
      {children}
    </CasdoorContext.Provider>
  );
}
