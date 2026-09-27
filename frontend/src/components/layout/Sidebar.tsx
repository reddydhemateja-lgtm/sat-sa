import { NavLink } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  ClipboardList,
  FileText,
  FolderSearch,
  FolderUp,
  GitCompare,
  LayoutDashboard,
  ListChecks,
  Settings,
  ShieldCheck,
  Users,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  highlight?: boolean;
}

// Ingestion first — it's the entry point for CSE data.
const primaryNav: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/ingestion', label: 'Ingestion', icon: FolderUp, highlight: true },
  { to: '/entities', label: 'Entities', icon: Users },
  { to: '/findings', label: 'Findings', icon: AlertTriangle },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/cases', label: 'Cases', icon: ClipboardList },
  { to: '/investigations', label: 'Investigations', icon: FolderSearch },
];

const analyticsNav: NavItem[] = [
  { to: '/analytics', label: 'Analytics', icon: Activity },
  { to: '/peer', label: 'Peer Comparison', icon: GitCompare },
  { to: '/review-queue', label: 'Review Queue', icon: ListChecks },
];

const adminNav: NavItem[] = [
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/audit-log', label: 'Audit Log', icon: ShieldCheck },
  { to: '/settings', label: 'Settings', icon: Settings },
];

interface SidebarProps {
  collapsed?: boolean;
}

export default function Sidebar({ collapsed = false }: SidebarProps) {
  return (
    <aside
      className={clsx(
        'flex h-full flex-col border-r border-slate-200 bg-white transition-[width] duration-200',
        'dark:border-navy-800 dark:bg-navy-900',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <div
        className={clsx(
          'flex h-14 items-center gap-2 border-b border-slate-200 px-4 dark:border-navy-800',
          collapsed && 'justify-center px-0',
        )}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-navy-800 text-white">
          <ShieldCheck className="h-4 w-4" strokeWidth={2.2} />
        </div>
        {!collapsed && (
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white">
              SAT-SA
            </p>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500 dark:text-slate-400">
              Supervisory Analytics
            </p>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {!collapsed && <p className="section-heading px-2 pb-1.5">Overview</p>}
        <NavGroup items={primaryNav} collapsed={collapsed} />

        <div className="my-3 border-t border-slate-200 dark:border-navy-800" />
        {!collapsed && <p className="section-heading px-2 pb-1.5">Analytics</p>}
        <NavGroup items={analyticsNav} collapsed={collapsed} />

        <div className="my-3 border-t border-slate-200 dark:border-navy-800" />
        {!collapsed && <p className="section-heading px-2 pb-1.5">Supervision</p>}
        <NavGroup items={adminNav} collapsed={collapsed} />
      </nav>

      <div
        className={clsx(
          'border-t border-slate-200 px-4 py-3 dark:border-navy-800',
          collapsed && 'px-2 text-center',
        )}
      >
        {!collapsed ? (
          <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
            <BarChart3 className="h-3.5 w-3.5" />
            <span>Evidence-driven supervision</span>
          </div>
        ) : (
          <BarChart3 className="mx-auto h-4 w-4 text-slate-400" />
        )}
      </div>
    </aside>
  );
}

function NavGroup({ items, collapsed }: { items: NavItem[]; collapsed: boolean }) {
  return (
    <ul className="space-y-0.5">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <li key={item.to}>
            <NavLink
              to={item.to}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) => {
                const base =
                  'group flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors';
                if (item.highlight && !isActive) {
                  return clsx(
                    base,
                    collapsed && 'justify-center px-0',
                    // highlighted, but not active
                    'border border-accent/30 bg-accent/5 text-accent hover:bg-accent/10',
                    'dark:border-accent-soft/30 dark:bg-accent-soft/10 dark:text-accent-soft dark:hover:bg-accent-soft/20',
                  );
                }
                return clsx(
                  base,
                  collapsed && 'justify-center px-0',
                  isActive
                    ? 'bg-navy-50 text-navy-800 dark:bg-navy-800 dark:text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-navy-800 dark:hover:text-white',
                );
              }}
            >
              <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && item.highlight && (
                <span className="ml-auto rounded-full bg-accent/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-accent dark:bg-accent-soft/20 dark:text-accent-soft">
                  Data
                </span>
              )}
            </NavLink>
          </li>
        );
      })}
    </ul>
  );
}