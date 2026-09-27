import { Link } from 'react-router-dom';
import { GitCompare, Loader2 } from 'lucide-react';

import Badge from '../components/ui/Badge';
import Card, { CardHeader } from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import { useEntities, useFindings } from '../hooks/useFindings';

export default function PeerComparisonPage() {
  const { data: entities, isLoading: loadingEnt } = useEntities(1);
  const { data: peerFindings, isLoading: loadingFindings } = useFindings({
    period_id: 1,
    category: 'PEER_DEVIATION',
    limit: 50,
  });

  const loading = loadingEnt || loadingFindings;

  // group entities by peer_group
  const grouped: Record<string, typeof entities> = {};
  for (const e of entities ?? []) {
    if (!e.peer_group) continue;
    (grouped[e.peer_group] ??= []).push(e);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Peer Comparison</h1>
          <p className="page-subheading">
            Normalized indicators compared within configured peer groups.
            Deviation is presented as a review signal — not a judgment of
            security quality.
          </p>
        </div>
        <Badge tone="neutral">{Object.keys(grouped).length} groups</Badge>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        </div>
      ) : (
        <>
          {/* Peer group tables */}
          {Object.entries(grouped).map(([group, members]) => {
            if (!members) return null;
            const maxIndicator = Math.max(1, ...members.map((m) => m.indicator));
            return (
              <Card key={group} padded={false}>
                <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
                  <CardHeader
                    title={group}
                    subtitle={`${members.length} entities in this peer group`}
                    action={
                      <Badge tone={members.length >= 3 ? 'info' : 'neutral'}>
                        {members.length >= 3 ? 'Comparable' : 'Needs ≥ 3'}
                      </Badge>
                    }
                  />
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                      <tr>
                        <th className="px-4 py-2.5 font-medium">Entity</th>
                        <th className="px-4 py-2.5 font-medium">Sector</th>
                        <th className="px-4 py-2.5 text-right font-medium">Alerts</th>
                        <th className="px-4 py-2.5 text-right font-medium">Cases</th>
                        <th className="px-4 py-2.5 text-right font-medium">Findings</th>
                        <th className="px-4 py-2.5 text-right font-medium">Indicator</th>
                        <th className="px-4 py-2.5 font-medium">Relative</th>
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((e) => {
                        const pct = (e.indicator / maxIndicator) * 100;
                        return (
                          <tr
                            key={e.id}
                            className="border-b border-slate-100 last:border-b-0 dark:border-navy-800"
                          >
                            <td className="px-4 py-2.5">
                              <span className="font-mono text-xs text-slate-700 dark:text-slate-200">
                                {e.code}
                              </span>
                              <span className="ml-2 text-slate-500 dark:text-slate-400">
                                {e.name}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                              {e.sector}
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
                            <td className="px-4 py-2.5">
                              <div className="h-1.5 w-32 overflow-hidden rounded-full bg-slate-100 dark:bg-navy-800">
                                <div
                                  className="h-full bg-accent"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            );
          })}

          {/* Peer deviation findings */}
          <Card padded={false}>
            <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
              <CardHeader
                title="Peer Deviation Findings"
                subtitle="Findings raised by the peer comparison rule (PEER-001)"
                action={
                  <Badge tone="neutral">
                    {peerFindings?.total ?? 0} findings
                  </Badge>
                }
              />
            </div>
            {!peerFindings || peerFindings.total === 0 ? (
              <div className="px-5 py-6">
                <EmptyState
                  icon={<GitCompare className="h-4 w-4" />}
                  title="No peer deviations raised"
                  description="Either the peer groups are similar enough not to raise deviations, or analytics has not been run since seeding."
                />
              </div>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-navy-800">
                {peerFindings.items.map((f) => (
                  <li key={f.id}>
                    <Link
                      to={`/findings/${f.id}`}
                      className="flex items-start gap-3 px-5 py-3 hover:bg-slate-50/60 dark:hover:bg-navy-800/40"
                    >
                      <span className="mt-0.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                        {f.code}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm text-slate-800 dark:text-slate-200">
                          {f.title}
                        </span>
                        <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                          {f.entity_code} · {f.rule_id}
                        </span>
                      </span>
                      <Badge tone="warning">{f.priority}</Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}