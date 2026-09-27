import { useState } from 'react';
import {
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card, { CardHeader } from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import {
  downloadReport,
  fetchReportAvailability,
} from '../services/analytics';

type ReportKind = 'pdf' | 'findings.csv' | 'decisions.csv';

const REPORTS: Array<{
  id: ReportKind;
  title: string;
  description: string;
  icon: LucideIcon;
  formats: string;
}> = [
  {
    id: 'pdf',
    title: 'Supervisory Report',
    description:
      'Comprehensive PDF: executive summary, entities, findings by category, top findings, supervisor decisions, and audit trail.',
    icon: ShieldCheck,
    formats: 'PDF',
  },
  {
    id: 'findings.csv',
    title: 'Findings Register',
    description:
      'Every finding for the period with entity, rule, priority, indicator, and full narrative.',
    icon: FileText,
    formats: 'CSV',
  },
  {
    id: 'decisions.csv',
    title: 'Supervisor Decisions',
    description:
      'Every review decision with reviewer, timestamp, comment, and previous decision for full traceability.',
    icon: FileSpreadsheet,
    formats: 'CSV',
  },
];

export default function ReportsPage() {
  const periodId = 1;
  const { data: availability } = useQuery({
    queryKey: ['reports', 'available', periodId],
    queryFn: () => fetchReportAvailability(periodId),
  });

  const [busy, setBusy] = useState<ReportKind | null>(null);
  const [lastDone, setLastDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async (kind: ReportKind) => {
    setError(null);
    setLastDone(null);
    setBusy(kind);
    try {
      const { blob, filename } = await downloadReport(kind, periodId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setLastDone(`Downloaded ${filename}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Reports</h1>
          <p className="page-subheading">
            Generate supervisory reports for the active assessment period.
            Downloads are recorded in the audit log.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="info">{availability?.period_label ?? 'Q3-2026'}</Badge>
          {availability && (
            <Badge tone="neutral">
              {availability.findings} findings · {availability.decisions} decisions
            </Badge>
          )}
        </div>
      </div>

      {lastDone && (
        <Card className="flex items-center gap-2 border-l-4 border-l-emerald-500">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          <p className="text-sm text-slate-700 dark:text-slate-200">{lastDone}</p>
        </Card>
      )}

      {error && (
        <Card className="border-l-4 border-l-red-500">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </Card>
      )}

      {!availability ? (
        <Card>
          <EmptyState
            icon={<Loader2 className="h-4 w-4 animate-spin" />}
            title="Loading available reports"
            description="Checking what data is available for the current period."
          />
        </Card>
      ) : availability.findings === 0 && availability.decisions === 0 ? (
        <Card>
          <EmptyState
            icon={<FileText className="h-4 w-4" />}
            title="No data to report"
            description="Run analytics on the current assessment period to populate reports."
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          {REPORTS.map((r) => {
            const Icon = r.icon;
            return (
              <Card key={r.id} className="flex flex-col">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-600 dark:bg-navy-800 dark:text-slate-300">
                    <Icon className="h-4 w-4" strokeWidth={2} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                        {r.title}
                      </h3>
                      <Badge tone="neutral">{r.formats}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {r.description}
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider text-slate-400">
                    period {availability.period_label}
                  </span>
                  <Button
                    variant="primary"
                    size="sm"
                    leftIcon={
                      busy === r.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Download className="h-3.5 w-3.5" />
                      )
                    }
                    onClick={() => handleDownload(r.id)}
                    disabled={busy !== null}
                  >
                    {busy === r.id ? 'Generating…' : 'Download'}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <Card>
        <CardHeader
          title="Report contents"
          subtitle="What each report contains"
        />
        <div className="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
          <div>
            <p className="font-medium text-slate-900 dark:text-white">
              Supervisory Report (PDF)
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-600 dark:text-slate-400">
              <li>• Executive summary with totals</li>
              <li>• Findings by category</li>
              <li>• Entities assessed with indicators</li>
              <li>• Top 50 findings by review indicator</li>
              <li>• Recent supervisor decisions</li>
              <li>• Audit trail excerpt</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-slate-900 dark:text-white">
              Findings Register (CSV)
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-600 dark:text-slate-400">
              <li>• One row per finding</li>
              <li>• Code, entity, rule, priority</li>
              <li>• Confidence & review indicator</li>
              <li>• Full narrative & analytical basis</li>
              <li>• Opens in Excel / Sheets</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-slate-900 dark:text-white">
              Decisions (CSV)
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-600 dark:text-slate-400">
              <li>• One row per supervisor decision</li>
              <li>• Reviewer, timestamp, decision</li>
              <li>• Comment and previous decision</li>
              <li>• Full audit traceability</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}