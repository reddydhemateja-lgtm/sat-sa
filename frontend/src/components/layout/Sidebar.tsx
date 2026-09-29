import { NavLink } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  ClipboardList,
  Database,
  FileText,
  FolderSearch,
  FolderUp,
  GitCompare,
  LayoutDashboard,
  ListChecks,
  Plug,
  Route,
  Settings,
  ShieldCheck,
  Users,
  Workflow,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  prominent?: boolean;
}

const primaryNav: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/entities', label: 'Entities', icon: Users },
  { to: '/findings', label: 'Findings', icon: AlertTriangle },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/cases', label: 'Cases', icon: ClipboardList },
  { to: '/investigations', label: 'Investigations', icon: FolderSearch },
];

const dataNav: NavItem[] = [
  { to: '/data', label: 'Datasets', icon: Database, prominent: true },
  { to: '/ingestion', label: 'Upload Files', icon: FolderUp },
  { to: '/data/connectors', label: 'API Connections', icon: Plug },
  { to: '/data-flow', label: 'Data Flow', icon: Workflow },
];

const analyticsNav: NavItem[] = [
  { to: '/analytics', label: 'Analytics', icon: Activity },
  { to: '/analytics-flow', label: 'Analytics Flow', icon: Route },
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
        collapsed ? 'w-16' : 'w-64',
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
        {!collapsed && <p className="section-heading px-2 pb-1.5">Data</p>}
        <NavGroup items={dataNav} collapsed={collapsed} />

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
    <ul className="space-y-1">
      {items.map((item) => {
        const Icon = item.icon;
        const isProminent = Boolean(item.prominent);
        return (
          <li key={item.to}>
            <NavLink
              to={item.to}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                clsx(
                  'group flex items-center rounded-md transition-colors',
                  collapsed && 'justify-center',
                  isProminent
                    ? clsx(
                        'gap-3 px-3 py-3.5 text-[16px] font-semibold',
                        collapsed && 'px-0 py-3',
                        isActive
                          ? 'bg-navy-100 text-navy-900 dark:bg-navy-800 dark:text-white'
                          : 'text-slate-800 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-100 dark:hover:bg-navy-800 dark:hover:text-white',
                      )
                    : clsx(
                        'gap-2.5 px-2.5 py-2 text-[13.5px] font-medium',
                        collapsed && 'px-0',
                        isActive
                          ? 'bg-navy-50 text-navy-800 dark:bg-navy-800 dark:text-white'
                          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-navy-800 dark:hover:text-white',
                      ),
                )
              }
            >
              <Icon
                className={isProminent ? 'h-5 w-5 shrink-0' : 'h-4 w-4 shrink-0'}
                strokeWidth={isProminent ? 2.4 : 2}
              />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          </li>
        );
      })}
    </ul>
  );
}