import { useState } from 'react';
import { Bell, ChevronDown, LogOut, Menu, Moon, Search, Sun, UserCircle2 } from 'lucide-react';

import Button from '../ui/Button';
import { useLogout } from '../../hooks/useAuth';
import { useSessionStore } from '../../store/session';
import { useThemeStore } from '../../store/theme';

interface TopbarProps {
  onToggleSidebar: () => void;
}

export default function Topbar({ onToggleSidebar }: TopbarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const user = useSessionStore((s) => s.user);
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const logout = useLogout();

  return (
    <header className="flex h-14 items-center gap-3 border-b border-slate-200 bg-white px-4 dark:border-navy-800 dark:bg-navy-900">
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-label="Toggle sidebar"
        className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-navy-800 dark:hover:text-white"
      >
        <Menu className="h-4 w-4" />
      </button>

      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <input
          type="search"
          placeholder="Search entities, findings, alert IDs…"
          className="input-base h-9 pl-8"
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          className="hidden items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 md:inline-flex dark:border-navy-700 dark:bg-navy-900 dark:text-slate-300 dark:hover:bg-navy-800"
        >
          <span className="text-slate-400">Assessment Period</span>
          <span className="text-slate-900 dark:text-white">Q3 2026</span>
          <ChevronDown className="h-3.5 w-3.5" />
        </button>

        <button
          type="button"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-navy-800 dark:hover:text-white"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>

        <button
          type="button"
          aria-label="Notifications"
          className="relative rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-navy-800 dark:hover:text-white"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-status-critical" />
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-white py-1 pl-1 pr-2 text-left hover:bg-slate-50 dark:border-navy-700 dark:bg-navy-900 dark:hover:bg-navy-800"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-navy-800 text-white">
              <UserCircle2 className="h-4 w-4" />
            </span>
            <span className="hidden leading-tight md:block">
              <span className="block text-xs font-semibold text-slate-900 dark:text-white">
                {user?.full_name ?? 'Signed in'}
              </span>
              <span className="block text-[10px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {user?.role ?? '—'}
              </span>
            </span>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          {menuOpen && (
            <div
              className="absolute right-0 top-11 z-20 w-56 rounded-md border border-slate-200 bg-white p-1.5 shadow-panel dark:border-navy-800 dark:bg-navy-900"
              onMouseLeave={() => setMenuOpen(false)}
            >
              <div className="border-b border-slate-100 px-2.5 py-2 dark:border-navy-800">
                <p className="truncate text-sm font-medium text-slate-900 dark:text-white">
                  {user?.full_name}
                </p>
                <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                  {user?.email}
                </p>
              </div>
              <div className="pt-1.5">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start"
                  leftIcon={<LogOut className="h-3.5 w-3.5" />}
                  onClick={() => {
                    setMenuOpen(false);
                    logout();
                  }}
                >
                  Sign out
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}