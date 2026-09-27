import { Loader2, Users } from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useEntities } from '../hooks/useFindings';

export default function EntitiesPage() {
  const { data, isLoading, isError } = useEntities(1);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Entities</h1>
          <p className="page-subheading">
            Critical Sector Entities onboarded for supervisory assessment, with
            submission activity and current findings.
          </p>
        </div>
        <Badge tone="neutral">{data?.length ?? 0} entities</Badge>
      </div>

      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title="Registered Entities"
            subtitle="Sector · Peer group · Activity · Indicator"
          />
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        )}

        {isError && (
          <div className="px-5 py-6 text-sm text-red-600 dark:text-red-400">
            Failed to load entities. Check the backend.
          </div>
        )}

        {!isLoading && !isError && (data?.length ?? 0) === 0 && (
          <div className="px-5 py-6">
            <EmptyState
              icon={<Users className="h-4 w-4" />}
              title="No entities onboarded"
              description="Register CSEs through the ingestion flow to begin."
            />
          </div>
        )}

        {!isLoading && !isError && (data?.length ?? 0) > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Code</th>
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Sector</th>
                  <th className="px-4 py-2.5 font-medium">Peer group</th>
                  <th className="px-4 py-2.5 font-medium">Criticality</th>
                  <th className="px-4 py-2.5 text-right font-medium">Alerts</th>
                  <th className="px-4 py-2.5 text-right font-medium">Cases</th>
                  <th className="px-4 py-2.5 text-right font-medium">Findings</th>
                  <th className="px-4 py-2.5 text-right font-medium">Indicator</th>
                </tr>
              </thead>
              <tbody>
                {data!.map((e) => (
                  <tr
                    key={e.id}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-700 dark:text-slate-200">
                      {e.code}
                    </td>
                    <td className="px-4 py-2.5 text-slate-800 dark:text-slate-200">
                      {e.name}
                    </td>
                    <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">
                      {e.sector}
                    </td>
                    <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">
                      {e.peer_group ?? '—'}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge
                        tone={
                          e.criticality === 'CRITICAL'
                            ? 'critical'
                            : e.criticality === 'HIGH'
                              ? 'high'
                              : 'neutral'
                        }
                      >
                        {e.criticality}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-600 dark:text-slate-300">
                      {e.alerts}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-600 dark:text-slate-300">
                      {e.cases}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-600 dark:text-slate-300">
                      {e.findings}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs font-semibold text-slate-800 dark:text-slate-100">
                      {e.indicator.toFixed(1)}
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