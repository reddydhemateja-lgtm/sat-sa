import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Bell,
  ClipboardList,
  FolderSearch,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import {
  useAlerts,
  useCases,
  useEntities,
  useInvestigations,
} from '../hooks/useFindings';
import { formatDateTime } from '../utils/format';

type Tab = 'overview' | 'alerts' | 'cases' | 'investigations';

export default function EntityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const entityId = id ? Number(id) : null;
  const [tab, setTab] = useState<Tab>('overview');

  const { data: entities, isLoading: loadingEnt } = useEntities(1);
  const entity = entities?.find((e) => e.id === entityId);

  const { data: alerts, isLoading: loadingAlerts } = useAlerts({
    entity_id: entityId ?? undefined,
    limit: 200,
  });
  const { data: cases, isLoading: loadingCases } = useCases({
    entity_id: entityId ?? undefined,
    limit: 200,
  });
  const { data: investigations, isLoading: loadingInvs } = useInvestigations({
    entity_id: entityId ?? undefined,
    limit: 200,
  });

  if (loadingEnt) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Loading entity…
        </p>
      </div>
    );
  }

  if (!entity) {
    return (
      <Card>
        <EmptyState
          title="Entity not found"
          description="It may have been removed or the ID is invalid."
          action={
            <Link
              to="/entities"
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-deep"
            >
              Back to Entities
            </Link>
          }
        />
      </Card>
    );
  }

  const TABS: { id: Tab; label: string; count: number }[] = [
    { id: 'overview', label: 'Overview', count: 0 },
    { id: 'alerts', label: 'Alerts', count: alerts?.total ?? 0 },
    { id: 'cases', label: 'Cases', count: cases?.total ?? 0 },
    {
      id: 'investigations',
      label: 'Investigations',
      count: investigations?.total ?? 0,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link
            to="/entities"
            className="mt-1 rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-navy-800"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <p className="font-mono text-xs text-slate-500 dark:text-slate-400">
              {entity.code}
            </p>
            <h1 className="page-heading mt-0.5">{entity.name}</h1>
            <p className="page-subheading">
              {entity.sector}
              {entity.sub_sector ? ` · ${entity.sub_sector}` : ''}
              {entity.peer_group ? ` · ${entity.peer_group}` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            tone={
              entity.criticality === 'CRITICAL'
                ? 'critical'
                : entity.criticality === 'HIGH'
                  ? 'high'
                  : 'neutral'
            }
          >
            {entity.criticality}
          </Badge>
          <Badge tone="info">Indicator {entity.indicator.toFixed(0)}</Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <Kpi label="Alerts" value={entity.alerts} icon={Bell} />
        <Kpi label="Cases" value={entity.cases} icon={ClipboardList} />
        <Kpi
          label="Investigations"
          value={investigations?.total ?? 0}
          icon={FolderSearch}
        />
        <Kpi label="Findings" value={entity.findings} icon={ShieldCheck} />
        <Kpi
          label="Indicator"
          value={Math.round(entity.indicator)}
          icon={ShieldCheck}
          tone={
            entity.indicator >= 70
              ? 'critical'
              : entity.indicator >= 40
                ? 'warning'
                : 'success'
          }
        />
      </div>

      <div className="border-b border-slate-200 dark:border-navy-800">
        <nav className="flex flex-wrap gap-6">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={
                'relative -mb-px border-b-2 px-1 py-3 text-sm font-medium transition-colors ' +
                (tab === t.id
                  ? 'border-accent text-slate-900 dark:text-white'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200')
              }
            >
              {t.label}
              {t.count > 0 && (
                <span className="ml-2 font-mono text-xs text-slate-400">
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'overview' && (
        <Card>
          <CardHeader
            title="Overview"
            subtitle="Submission summary for this CSE"
          />
          <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <Detail label="Code" value={entity.code} mono />
            <Detail label="Name" value={entity.name} />
            <Detail label="Sector" value={entity.sector} />
            <Detail label="Sub-sector" value={entity.sub_sector ?? '—'} />
            <Detail label="Region" value={entity.region ?? '—'} />
            <Detail label="Criticality" value={entity.criticality} />
            <Detail label="Peer group" value={entity.peer_group ?? '—'} />
            <Detail
              label="Status"
              value={entity.is_active ? 'Active' : 'Inactive'}
            />
            <Detail label="Findings" value={String(entity.findings)} mono />
          </dl>
        </Card>
      )}

      {tab === 'alerts' && (
        <Card padded={false}>
          <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
            <CardHeader
              title="Alerts submitted by this entity"
              subtitle="Every alert record linked to this CSE"
            />
          </div>
          {loadingAlerts ? (
            <div className="px-5 py-6 text-sm text-slate-500">Loading…</div>
          ) : !alerts || alerts.items.length === 0 ? (
            <div className="px-5 py-6">
              <EmptyState
                icon={<Bell className="h-4 w-4" />}
                title="No alerts"
                description="This entity has not submitted alert data for the period."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">External ID</th>
                    <th className="px-4 py-2.5 font-medium">Title</th>
                    <th className="px-4 py-2.5 font-medium">Severity</th>
                    <th className="px-4 py-2.5 font-medium">Category</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                    <th className="px-4 py-2.5 font-medium">Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.items.map((a) => (
                    <tr
                      key={a.id}
                      className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                    >
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                        {a.external_id}
                      </td>
                      <td className="max-w-md truncate px-4 py-2.5 text-slate-800 dark:text-slate-200">
                        {a.title}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge
                          tone={
                            a.severity === 'CRITICAL'
                              ? 'critical'
                              : a.severity === 'HIGH'
                                ? 'high'
                                : a.severity === 'MEDIUM'
                                  ? 'warning'
                                  : 'neutral'
                          }
                        >
                          {a.severity}
                        </Badge>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                        {a.category}
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
        </Card>
      )}

      {tab === 'cases' && (
        <Card padded={false}>
          <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
            <CardHeader
              title="Cases opened by this entity"
              subtitle="Every case-management record linked to this CSE"
            />
          </div>
          {loadingCases ? (
            <div className="px-5 py-6 text-sm text-slate-500">Loading…</div>
          ) : !cases || cases.items.length === 0 ? (
            <div className="px-5 py-6">
              <EmptyState
                icon={<ClipboardList className="h-4 w-4" />}
                title="No cases"
                description="This entity has not submitted case records."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">External ID</th>
                    <th className="px-4 py-2.5 font-medium">Title</th>
                    <th className="px-4 py-2.5 font-medium">Severity</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                    <th className="px-4 py-2.5 font-medium">Assigned</th>
                    <th className="px-4 py-2.5 font-medium">Opened</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.items.map((c) => (
                    <tr
                      key={c.id}
                      className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                    >
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                        {c.external_id}
                      </td>
                      <td className="max-w-md truncate px-4 py-2.5 text-slate-800 dark:text-slate-200">
                        {c.title}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge
                          tone={
                            c.severity === 'CRITICAL'
                              ? 'critical'
                              : c.severity === 'HIGH'
                                ? 'high'
                                : c.severity === 'MEDIUM'
                                  ? 'warning'
                                  : 'neutral'
                          }
                        >
                          {c.severity}
                        </Badge>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                        {c.status}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                        {c.assigned_to ?? '—'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400">
                        {formatDateTime(c.opened_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'investigations' && (
        <Card padded={false}>
          <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
            <CardHeader
              title="Investigations conducted by this entity"
              subtitle="Every investigation record linked to this CSE"
            />
          </div>
          {loadingInvs ? (
            <div className="px-5 py-6 text-sm text-slate-500">Loading…</div>
          ) : !investigations || investigations.items.length === 0 ? (
            <div className="px-5 py-6">
              <EmptyState
                icon={<FolderSearch className="h-4 w-4" />}
                title="No investigations"
                description="This entity has not submitted investigation records."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Investigator</th>
                    <th className="px-4 py-2.5 font-medium">Case</th>
                    <th className="px-4 py-2.5 font-medium">Summary</th>
                    <th className="px-4 py-2.5 font-medium">Artifacts</th>
                    <th className="px-4 py-2.5 font-medium">Started</th>
                    <th className="px-4 py-2.5 font-medium">Content hash</th>
                  </tr>
                </thead>
                <tbody>
                  {investigations.items.map((i) => (
                    <tr
                      key={i.id}
                      className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                    >
                      <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                        {i.investigator ?? '—'}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                        #{i.case_id}
                      </td>
                      <td className="max-w-lg truncate px-4 py-2.5 text-slate-700 dark:text-slate-200">
                        {i.summary ?? '—'}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-300">
                        {i.artifacts_count}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400">
                        {formatDateTime(i.started_at)}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-[10px] text-slate-400 dark:text-slate-500">
                        {i.content_hash
                          ? i.content_hash.slice(0, 10) + '…'
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  icon: Icon,
  tone = 'neutral',
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  tone?: 'neutral' | 'critical' | 'warning' | 'success';
}) {
  const toneClass =
    tone === 'critical'
      ? 'text-red-600 dark:text-red-400'
      : tone === 'warning'
        ? 'text-amber-600 dark:text-amber-400'
        : tone === 'success'
          ? 'text-emerald-600 dark:text-emerald-400'
          : 'text-slate-900 dark:text-white';
  return (
    <Card className="flex items-start gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-600 dark:bg-navy-800 dark:text-slate-300">
        <Icon className="h-4 w-4" strokeWidth={2} />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {label}
        </p>
        <p
          className={`mt-0.5 text-xl font-semibold tracking-tight ${toneClass}`}
        >
          {value.toLocaleString()}
        </p>
      </div>
    </Card>
  );
}

function Detail({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </dt>
      <dd
        className={
          'mt-0.5 ' +
          (mono
            ? 'font-mono text-xs text-slate-800 dark:text-slate-100'
            : 'text-sm text-slate-800 dark:text-slate-100')
        }
      >
        {value}
      </dd>
    </div>
  );
}