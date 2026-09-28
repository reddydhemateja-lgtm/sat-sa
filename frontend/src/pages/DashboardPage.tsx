import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Database,
  FileUp,
  FolderUp,
  Loader2,
  ShieldCheck,
  TrendingUp,
  Upload,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import CategoryDonutChart from '../components/charts/CategoryDonutChart';
import FindingsTrendChart from '../components/charts/FindingsTrendChart';
import IndicatorGauge from '../components/charts/IndicatorGauge';
import EntityComparisonChart from '../components/charts/EntityComparisonChart';
import { useAnalyticsSummary, useFindings } from '../hooks/useFindings';
import { useCurrentUser } from '../hooks/useAuth';
import { api } from '../services/api';
import { formatDateTime } from '../utils/format';

interface SubmissionRow {
  id: number;
  entity_id: number;
  file_name: string;
  payload_type: string;
  status: string;
  records_received: number;
  records_valid: number;
  records_warning: number;
  records_error: number;
  created_at: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  EXECUTION_GAP: '#dc2626',
  NEGATIVE_SPACE: '#0ea5e9',
  ANOMALY: '#d97706',
  PEER_DEVIATION: '#64748b',
  DATA_QUALITY: '#7c3aed',
};

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  const { data, isLoading } = useAnalyticsSummary(1);
  const { data: findingsPage } = useFindings({ period_id: 1, limit: 500 });

  const { data: submissions } = useQuery({
    queryKey: ['dashboard', 'submissions'],
    queryFn: () => api.get<SubmissionRow[]>('/ingestion/submissions'),
    staleTime: 10_000,
  });

  // ---- KPI tiles ----
  const totalRecords = (data?.alerts_total ?? 0) + (data?.cases_total ?? 0);

  const kpis = [
    {
      label: 'Entities Assessed',
      value: String(data?.entities_assessed ?? 0),
      helper: 'registered CSE entities',
      icon: ShieldCheck,
      tone: 'neutral' as const,
    },
    {
      label: 'Records Ingested',
      value: totalRecords.toLocaleString(),
      helper: `${data?.alerts_total ?? 0} alerts · ${data?.cases_total ?? 0} cases`,
      icon: Database,
      tone: 'neutral' as const,
    },
    {
      label: 'Findings',
      value: String(data?.findings_total ?? 0),
      helper: `${Object.keys(data?.by_category ?? {}).length} categories`,
      icon: AlertTriangle,
      tone: 'critical' as const,
    },
    {
      label: 'Pending Review',
      value: String(data?.pending_reviews ?? 0),
      helper: 'awaiting supervisor decision',
      icon: ClipboardList,
      tone: 'warning' as const,
    },
    {
      label: 'High Priority',
      value: String(data?.high_priority ?? 0),
      helper: 'need immediate attention',
      icon: TrendingUp,
      tone: 'critical' as const,
    },
  ];

  // ---- Donut ----
  const categoryData = Object.entries(data?.by_category ?? {}).map(([k, v]) => ({
    name: k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    value: v as number,
    color: CATEGORY_COLORS[k] ?? '#64748b',
  }));

  // ---- Entity ranking ----
  const entityRanking = [...(data?.entities ?? [])]
    .sort((a, b) => b.indicator - a.indicator)
    .slice(0, 10);

  const topEntity = entityRanking[0];

  // ---- Trend: group findings by creation month ----
  const trendData = (() => {
    const items = findingsPage?.items ?? [];
    if (items.length === 0) return [];
    const buckets: Record<
      string,
      { EXECUTION_GAP: number; NEGATIVE_SPACE: number; ANOMALY: number; PEER_DEVIATION: number }
    > = {};
    for (const f of items) {
      const d = new Date(f.created_at);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      buckets[key] ??= {
        EXECUTION_GAP: 0,
        NEGATIVE_SPACE: 0,
        ANOMALY: 0,
        PEER_DEVIATION: 0,
      };
      const cat = f.category;
      if (cat in buckets[key]) {
        buckets[key][cat as keyof (typeof buckets)[string]] += 1;
      }
    }
    return Object.entries(buckets)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => ({ label: k, ...v }));
  })();

  // ---- Entity comparison bars ----
  const entityComparison = entityRanking.map((e) => ({
    entity_id: e.entity_id,
    code: e.code,
    indicator: e.indicator,
    findings: e.findings,
  }));

  // ---- Recent submissions for Section 2 ----
  const recentSubmissions = (submissions ?? []).slice(0, 4);
  const totalUploadedRows = (submissions ?? []).reduce(
    (s, r) => s + (r.records_valid || 0),
    0,
  );
  const totalUploadedFiles = (submissions ?? []).length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Supervisory Overview</h1>
          <p className="page-subheading">
            Assessment Period:{' '}
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {data?.period_label ?? 'Q3 2026'}
            </span>
            {user && (
              <>
                {' · '}
                Signed in as{' '}
                <span className="font-medium text-slate-700 dark:text-slate-200">
                  {user.full_name}
                </span>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="info">Live data</Badge>
          <Badge tone="neutral">Offline / Air-gapped</Badge>
        </div>
      </div>

      {/* ================================================================ */}
      {/* SECTION 1 — Supervisory Overview                                 */}
      {/* ================================================================ */}
      <section className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-300 to-transparent dark:via-navy-700" />
          <div className="flex items-center gap-2">
            <Database className="h-3.5 w-3.5 text-slate-400" />
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500 dark:text-slate-400">
              Section 1 — Supervisory Overview
            </p>
            <Badge tone="neutral">{data?.period_label ?? 'Q3 2026'}</Badge>
          </div>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-300 to-transparent dark:via-navy-700" />
        </div>

        {/* KPI tiles */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {kpis.map((k) => {
            const Icon = k.icon;
            const toneClass =
              k.tone === 'critical'
                ? 'bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400'
                : k.tone === 'warning'
                  ? 'bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400'
                  : 'bg-slate-100 text-slate-600 dark:bg-navy-800 dark:text-slate-300';
            return (
              <Card key={k.label} className="flex items-start gap-3">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${toneClass}`}
                >
                  <Icon className="h-4 w-4" strokeWidth={2} />
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    {k.label}
                  </p>
                  <p className="mt-0.5 text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
                    {isLoading ? '…' : k.value}
                  </p>
                  <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                    {k.helper}
                  </p>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Donut + Gauge */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader
              title="Findings Composition"
              subtitle="Distribution by analytical category"
              action={<Badge tone="neutral">{data?.findings_total ?? 0} total</Badge>}
            />
            {isLoading ? (
              <div className="flex h-64 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
              </div>
            ) : (
              <CategoryDonutChart data={categoryData} />
            )}
          </Card>

          <Card>
            <CardHeader
              title="Top-Risk Entity"
              subtitle="Highest Supervisory Review Indicator"
            />
            {topEntity ? (
              <div className="flex flex-col items-center gap-3">
                <IndicatorGauge value={topEntity.indicator} />
                <div className="text-center">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">
                    {topEntity.code} · {topEntity.name}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    {topEntity.findings} findings · {topEntity.sector}
                  </p>
                </div>
              </div>
            ) : (
              <EmptyState
                icon={<ShieldCheck className="h-4 w-4" />}
                title="No entity indicators"
                description="Run analytics to compute indicators."
              />
            )}
          </Card>
        </div>

        {/* Trend + Ranking */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader
              title="Findings Over Time"
              subtitle="Findings grouped by month of creation"
            />
            {trendData.length > 0 ? (
              <FindingsTrendChart data={trendData} />
            ) : (
              <EmptyState
                icon={<TrendingUp className="h-4 w-4" />}
                title="No trend data yet"
                description="Ingest submissions and run analytics to populate this view."
              />
            )}
          </Card>

          <Card>
            <CardHeader
              title="Entity Ranking"
              subtitle="Sorted by indicator"
              action={
                <Link
                  to="/entities"
                  className="text-xs text-accent hover:underline dark:text-accent-soft"
                >
                  View all
                </Link>
              }
            />
            {entityRanking.length > 0 ? (
              <ul className="space-y-3">
                {entityRanking.slice(0, 6).map((e) => (
                  <li key={e.entity_id}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {e.code}
                      </span>
                      <span className="font-mono text-slate-500 dark:text-slate-400">
                        {e.indicator.toFixed(0)}
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-navy-800">
                      <div
                        className={
                          e.indicator >= 70
                            ? 'h-full bg-red-500'
                            : e.indicator >= 40
                              ? 'h-full bg-amber-500'
                              : 'h-full bg-emerald-500'
                        }
                        style={{ width: `${Math.min(100, e.indicator)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                icon={<ShieldCheck className="h-4 w-4" />}
                title="No entities ranked"
                description="Analytics has not produced findings yet."
              />
            )}
          </Card>
        </div>

        {/* Entity comparison bars */}
        <Card>
          <CardHeader
            title="Entity Comparison"
            subtitle="Supervisory Review Indicator per entity"
            action={
              <Link
                to="/peer"
                className="text-xs text-accent hover:underline dark:text-accent-soft"
              >
                Peer view
              </Link>
            }
          />
          {entityComparison.length > 0 ? (
            <EntityComparisonChart data={entityComparison} />
          ) : (
            <EmptyState
              icon={<ShieldCheck className="h-4 w-4" />}
              title="No entity comparison"
              description="Run analytics to populate entity indicators."
            />
          )}
        </Card>
      </section>

      {/* ================================================================ */}
      {/* SECTION 2 — Uploaded Data                                        */}
      {/* ================================================================ */}
      <section className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-accent/40 to-transparent" />
          <div className="flex items-center gap-2">
            <FileUp className="h-3.5 w-3.5 text-accent dark:text-accent-soft" />
            <p className="text-[11px] font-medium uppercase tracking-widest text-accent dark:text-accent-soft">
              Section 2 — Uploaded Data
            </p>
            <Badge tone="info">this session</Badge>
          </div>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-accent/40 to-transparent" />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Upload CTA */}
          <Card className="lg:col-span-2 border-accent/30 dark:border-accent-soft/30">
            <CardHeader
              title="Upload CSE submission data"
              subtitle="Drag a folder or individual files. Everything stays on this machine."
            />
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent dark:bg-accent-soft/10 dark:text-accent-soft">
                <FolderUp className="h-6 w-6" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-900 dark:text-white">
                  CSV · JSON · XLSX
                </p>
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  The tool auto-detects payload types, validates every row, and
                  shows a per-file error report before commit.
                </p>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-2">
              <Link to="/ingestion">
                <Button
                  variant="primary"
                  size="lg"
                  leftIcon={<Upload className="h-3.5 w-3.5" />}
                >
                  Go to Ingestion
                </Button>
              </Link>
              <Link to="/ingestion">
                <Button
                  variant="secondary"
                  size="lg"
                  leftIcon={<ArrowRight className="h-3.5 w-3.5" />}
                >
                  View submissions
                </Button>
              </Link>
            </div>
          </Card>

          {/* Recent uploads */}
          <Card padded={false}>
            <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
              <CardHeader
                title="Recent Uploads"
                subtitle={`${totalUploadedFiles} files · ${totalUploadedRows.toLocaleString()} records`}
              />
            </div>
            {recentSubmissions.length === 0 ? (
              <div className="px-5 py-6">
                <EmptyState
                  icon={<FileUp className="h-4 w-4" />}
                  title="No uploads yet"
                  description="Upload a folder to see it appear here."
                />
              </div>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-navy-800">
                {recentSubmissions.map((s) => (
                  <li key={s.id} className="px-5 py-3">
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-mono text-xs text-slate-700 dark:text-slate-200">
                          {s.file_name}
                        </p>
                        <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                          {s.records_valid}/{s.records_received} valid
                          {s.records_error > 0 && (
                            <span className="ml-2 text-red-600 dark:text-red-400">
                              {s.records_error} err
                            </span>
                          )}
                          {s.records_warning > 0 && (
                            <span className="ml-2 text-amber-600 dark:text-amber-400">
                              {s.records_warning} warn
                            </span>
                          )}
                        </p>
                        <p className="mt-0.5 text-[10px] uppercase tracking-wider text-slate-400">
                          {formatDateTime(s.created_at)}
                        </p>
                      </div>
                      <Badge tone="neutral">{s.payload_type}</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <Card className="border-dashed">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-500 dark:bg-navy-800 dark:text-slate-400">
              <TrendingUp className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-700 dark:text-slate-200">
                After uploading and committing, analytics runs automatically and
                findings appear in Section 1 above.
              </p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                The tool supports real CSE exports — the column mapper auto-detects
                unfamiliar column names such as{' '}
                <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-700 dark:bg-navy-800 dark:text-slate-200">
                  alert_id
                </code>
                ,{' '}
                <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-700 dark:bg-navy-800 dark:text-slate-200">
                  priority
                </code>
                ,{' '}
                <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-700 dark:bg-navy-800 dark:text-slate-200">
                  event_time
                </code>
                .
              </p>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}