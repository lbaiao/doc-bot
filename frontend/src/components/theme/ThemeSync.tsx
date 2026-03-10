import { useEffect } from 'react';
import { resolveTheme, useThemeStore } from '@/store/theme-store';

export function ThemeSync() {
  const theme = useThemeStore((state) => state.theme);

  useEffect(() => {
    const root = document.documentElement;

    const applyTheme = () => {
      const effectiveTheme = resolveTheme(theme);
      root.classList.toggle('dark', effectiveTheme === 'dark');
    };

    applyTheme();

    if (theme !== 'system') {
      return;
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => applyTheme();
    mediaQuery.addEventListener('change', onChange);

    return () => {
      mediaQuery.removeEventListener('change', onChange);
    };
  }, [theme]);

  return null;
}
