import { useState } from 'react';
import { Bell, Loader2 } from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useAlerts } from '../hooks/useFindings';
import { formatDateTime } from '../utils/format';

const SEVERITIES = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];

const severityTone = (s: string) => {
  switch (s) {
    case 'CRITICAL':
      return 'critical' as const;
    case 'HIGH':
      return 'high' as const;
    case 'MEDIUM':
      return 'warning' as const;
    case 'LOW':
      return 'info' as const;
    default:
      return 'neutral' as const;
  }
};

export default function AlertsPage() {
  const [severity, setSeverity] = useState('');
  const [entityId, setEntityId] = useState<number | undefined>();
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const { data, isLoading, isError } = useAlerts({
    period_id: 1,
    severity: severity || undefined,
    entity_id: entityId,
    limit: pageSize,
    offset: page * pageSize,
  });

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Alerts</h1>
          <p className="page-subheading">
            Alert metadata submitted by CSEs for the active assessment period.
          </p>
        </div>
        <Badge tone="neutral">{total} alerts</Badge>
      </div>

      <Card className="flex flex-wrap items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Severity
        </span>
        <select
          value={severity}
          onChange={(e) => {
            setSeverity(e.target.value);
            setPage(0);
          }}
          className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
        >
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s === '' ? 'All' : s}
            </option>
          ))}
        </select>

        <span className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Entity
        </span>
        <select
          value={entityId ?? ''}
          onChange={(e) => {
            const v = e.target.value;
            setEntityId(v === '' ? undefined : Number(v));
            setPage(0);
          }}
          className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
        >
          <option value="">All</option>
          <option value="1">BANK-A</option>
          <option value="2">POWER-B</option>
          <option value="3">TELEC-C</option>
        </select>
      </Card>

      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader title="Alert Register" subtitle="Newest first" />
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        )}

        {isError && (
          <div className="px-5 py-6 text-sm text-red-600 dark:text-red-400">
            Failed to load alerts. Check the backend.
          </div>
        )}

        {!isLoading && !isError && total === 0 && (
          <div className="px-5 py-6">
            <EmptyState
              icon={<Bell className="h-4 w-4" />}
              title="No alerts match the filters"
              description="Try clearing filters or ingest alert data first."
            />
          </div>
        )}

        {!isLoading && !isError && total > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">External ID</th>
                  <th className="px-4 py-2.5 font-medium">Entity</th>
                  <th className="px-4 py-2.5 font-medium">Title</th>
                  <th className="px-4 py-2.5 font-medium">Category</th>
                  <th className="px-4 py-2.5 font-medium">Severity</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Detected</th>
                </tr>
              </thead>
              <tbody>
                {data!.items.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                      {a.external_id}
                    </td>
                    <td className="px-4 py-2.5 text-slate-800 dark:text-slate-200">
                      {a.entity_code ?? '—'}
                    </td>
                    <td className="max-w-md truncate px-4 py-2.5 text-slate-800 dark:text-slate-200">
                      {a.title}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                      {a.category}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge tone={severityTone(a.severity)}>{a.severity}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                      {a.status}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400">
                      {formatDateTime(a.detected_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!isLoading && !isError && total > 0 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3 text-xs text-slate-500 dark:border-navy-800 dark:text-slate-400">
            <span>
              Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md px-2 py-1 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-navy-800"
              >
                Previous
              </button>
              <span>
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page + 1 >= totalPages}
                className="rounded-md px-2 py-1 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-navy-800"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}