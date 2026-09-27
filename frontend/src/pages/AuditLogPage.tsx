import { useState } from 'react';
import { Loader2, ShieldCheck } from 'lucide-react';

import Badge from '../components/ui/Badge';
import Card, { CardHeader } from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import { useAuditLog } from '../hooks/useFindings';
import { formatDateTime } from '../utils/format';

const ACTIONS = [
  '',
  'REVIEW_DECISION',
  'INGEST_COMMIT',
  'ANALYTICS_RUN',
  'LOGIN',
  'USER_CREATE',
];

export default function AuditLogPage() {
  const [action, setAction] = useState('');
  const { data, isLoading, isError } = useAuditLog({
    action: action || undefined,
    limit: 200,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Audit Log</h1>
          <p className="page-subheading">
            Append-only history of every action performed on findings, submissions,
            configuration, and review decisions.
          </p>
        </div>
        <Badge tone="neutral">{data?.total ?? 0} events</Badge>
      </div>

      <Card className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Filter by action
        </span>
        <select
          value={action}
          onChange={(e) => setAction(e.target.value)}
          className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
        >
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a === '' ? 'All actions' : a}
            </option>
          ))}
        </select>
      </Card>

      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader title="Audit Events" subtitle="Newest first" />
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        )}

        {isError && (
          <div className="px-5 py-6 text-sm text-red-600 dark:text-red-400">
            Failed to load the audit log. Check the backend.
          </div>
        )}

        {!isLoading && !isError && (data?.total ?? 0) === 0 && (
          <div className="px-5 py-6">
            <EmptyState
              icon={<ShieldCheck className="h-4 w-4" />}
              title="No audit events"
              description="Actions will appear here as they are performed."
            />
          </div>
        )}

        {!isLoading && !isError && (data?.total ?? 0) > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">When</th>
                  <th className="px-4 py-2.5 font-medium">User</th>
                  <th className="px-4 py-2.5 font-medium">Action</th>
                  <th className="px-4 py-2.5 font-medium">Target</th>
                  <th className="px-4 py-2.5 font-medium">Change</th>
                </tr>
              </thead>
              <tbody>
                {data!.items.map((e) => (
                  <tr
                    key={e.id}
                    className="border-b border-slate-100 last:border-b-0 align-top dark:border-navy-800"
                  >
                    <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                      {formatDateTime(e.created_at)}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-300">
                      {e.username ?? '—'}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge
                        tone={
                          e.action === 'REVIEW_DECISION'
                            ? 'critical'
                            : e.action === 'INGEST_COMMIT'
                              ? 'info'
                              : 'neutral'
                        }
                      >
                        {e.action}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                      {e.target_type ? (
                        <>
                          <span className="font-mono">{e.target_type}</span>
                          {e.target_id !== null && (
                            <span className="text-slate-400"> #{e.target_id}</span>
                          )}
                        </>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="max-w-lg px-4 py-2.5">
                      <details className="group">
                        <summary className="cursor-pointer text-xs text-accent hover:underline dark:text-accent-soft">
                          Show
                        </summary>
                        <pre className="mt-1 max-h-64 overflow-auto rounded-md border border-slate-200 bg-slate-50 p-2 text-[10px] leading-tight text-slate-700 dark:border-navy-800 dark:bg-navy-950 dark:text-slate-200">
{JSON.stringify({ previous: e.previous_value, next: e.new_value }, null, 2)}
                        </pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}