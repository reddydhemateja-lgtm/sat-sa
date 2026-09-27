import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Loader2, PlayCircle } from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import { useAnalyticsSummary, useRunAnalytics } from '../hooks/useFindings';

export default function AnalyticsPage() {
  const { data, isLoading, refetch } = useAnalyticsSummary(1);
  const run = useRunAnalytics();
  const [message, setMessage] = useState<string | null>(null);

  const handleRun = async () => {
    setMessage(null);
    try {
      const result = (await run.mutateAsync(1)) as {
        total_created?: number;
        total_deleted?: number;
      };
      setMessage(
        `Analytics run complete. ${result?.total_created ?? 0} findings created, ` +
          `${result?.total_deleted ?? 0} replaced.`,
      );
      await refetch();
    } catch {
      setMessage('Analytics run failed. Check the backend.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Analytics</h1>
          <p className="page-subheading">
            Explainable analytics modules — execution gaps, negative space, anomalies,
            peer comparison, and the Supervisory Review Indicator.
          </p>
        </div>
        <Button
          variant="primary"
          leftIcon={run.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PlayCircle className="h-3.5 w-3.5" />}
          onClick={handleRun}
          disabled={run.isPending}
        >
          {run.isPending ? 'Running…' : 'Run Analytics'}
        </Button>
      </div>

      {message && (
        <Card className="border-l-4 border-l-accent">
          <p className="text-sm text-slate-700 dark:text-slate-200">{message}</p>
        </Card>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Execution Gap Detection"
              subtitle="Rules EG-001 … EG-007"
              action={
                <Badge tone="neutral">
                  {data?.by_category?.EXECUTION_GAP ?? 0} findings
                </Badge>
              }
            />
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Detects fast critical closures without escalation, missing investigations,
              template documentation, and other patterns that suggest a gap between
              policy and execution.
            </p>
          </Card>

          <Card>
            <CardHeader
              title="Negative Space Detection"
              subtitle="Expected evidence vs observed evidence"
              action={
                <Badge tone="neutral">
                  {data?.by_category?.NEGATIVE_SPACE ?? 0} findings
                </Badge>
              }
            />
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Flags missing telemetry, absent alert categories, and missing investigation
              or escalation evidence for critical records.
            </p>
          </Card>

          <Card>
            <CardHeader
              title="Anomaly Detection"
              subtitle="Robust z-score · IQR · trend deviation"
              action={
                <Badge tone="neutral">
                  {data?.by_category?.ANOMALY ?? 0} findings
                </Badge>
              }
            />
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Statistical, explainable anomaly detection against the entity's own
              historical baseline and peer group.
            </p>
          </Card>

          <Card>
            <CardHeader
              title="Supervisory Review Indicator"
              subtitle="0–100 · priority ranking"
              action={
                <Badge tone="neutral">
                  {data?.findings_total ?? 0} total
                </Badge>
              }
            />
            <div className="space-y-2">
              {(data?.entities ?? []).map((e) => (
                <div
                  key={e.entity_id}
                  className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-sm dark:border-navy-800"
                >
                  <span className="text-slate-700 dark:text-slate-200">{e.code}</span>
                  <span className="font-mono text-slate-900 dark:text-white">
                    {e.indicator.toFixed(1)}
                  </span>
                </div>
              ))}
              {(!data?.entities || data.entities.length === 0) && (
                <EmptyState
                  icon={<Activity className="h-4 w-4" />}
                  title="No indicators yet"
                  description="Run analytics to populate."
                />
              )}
            </div>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader
          title="Review Queue"
          subtitle="Findings awaiting supervisory decision"
          action={
            <Link
              to="/review-queue"
              className="text-xs text-accent hover:underline dark:text-accent-soft"
            >
              Open queue
            </Link>
          }
        />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {data?.pending_reviews ?? 0} findings pending. Priority HIGH:{' '}
          {data?.by_priority?.HIGH ?? 0}, MEDIUM: {data?.by_priority?.MEDIUM ?? 0}, LOW:{' '}
          {data?.by_priority?.LOW ?? 0}.
        </p>
      </Card>
    </div>
  );
}