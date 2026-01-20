import { useApp } from '../context/AppContext';

export function useTheme() {
  const { theme, setTheme, toggleTheme } = useApp();

  return {
    theme,
    setTheme,
    toggleTheme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
  };
}
