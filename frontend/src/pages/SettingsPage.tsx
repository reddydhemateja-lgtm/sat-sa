import { Settings as SettingsIcon } from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useCurrentUser } from '../hooks/useAuth';

export default function SettingsPage() {
  const { data: user } = useCurrentUser();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Settings</h1>
          <p className="page-subheading">
            Analytics thresholds, peer groups, user management, and system configuration.
          </p>
        </div>
        <Badge tone="info">ADMIN only</Badge>
      </div>

      <Card>
        <CardHeader
          title="Current User"
          subtitle="Signed-in account and role"
        />
        {user ? (
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Full name
              </dt>
              <dd className="mt-0.5 text-sm text-slate-900 dark:text-white">
                {user.full_name}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Username
              </dt>
              <dd className="mt-0.5 text-sm text-slate-900 dark:text-white">
                {user.username}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Email
              </dt>
              <dd className="mt-0.5 text-sm text-slate-900 dark:text-white">
                {user.email}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Role
              </dt>
              <dd className="mt-0.5 text-sm text-slate-900 dark:text-white">
                {user.role}
              </dd>
            </div>
          </dl>
        ) : (
          <EmptyState
            icon={<SettingsIcon className="h-4 w-4" />}
            title="No active session"
            description="Sign in to see account details."
          />
        )}
      </Card>

      <Card>
        <CardHeader
          title="Analytics Configuration"
          subtitle="Execution-gap thresholds · Anomaly sensitivity · Peer tolerance"
          action={<Badge tone="neutral">Phase 4</Badge>}
        />
        <EmptyState
          icon={<SettingsIcon className="h-4 w-4" />}
          title="Configuration will arrive in Phase 4"
          description="All threshold changes will be recorded in the audit log."
        />
      </Card>
    </div>
  );
}