import { useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FilePlus2,
  FolderUp,
  Loader2,
  Upload,
} from 'lucide-react';

import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card, { CardHeader } from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import CategoryDonutChart from '../components/charts/CategoryDonutChart';
import SuccessRateGauge from '../components/charts/SuccessRateGauge';
import { useCommitBatch, useScanBatch } from '../hooks/useFindings';
import type { BatchFileReport, BatchReport } from '../types';

const ENTITIES = [
  { id: 1, code: 'BANK-A' },
  { id: 2, code: 'POWER-B' },
  { id: 3, code: 'TELEC-C' },
  { id: 4, code: 'BANK-X' },
  { id: 5, code: 'BANK-Y' },
  { id: 6, code: 'GRID-M' },
  { id: 7, code: 'GRID-N' },
  { id: 8, code: 'TELEC-P' },
  { id: 9, code: 'TELEC-Q' },
];

function fileStatusBadge(f: BatchFileReport) {
  if (f.error) return { tone: 'critical' as const, label: 'Failed' };
  if (f.records_error > 0) return { tone: 'critical' as const, label: 'Errors' };
  if (f.records_warning > 0) return { tone: 'warning' as const, label: 'Warnings' };
  return { tone: 'success' as const, label: 'Clean' };
}

export default function IngestionPage() {
  const folderInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [entityId, setEntityId] = useState(1);
  const [periodId] = useState(1);
  const [pickedFiles, setPickedFiles] = useState<File[]>([]);
  const [report, setReport] = useState<BatchReport | null>(null);
  const [commitResult, setCommitResult] = useState<string | null>(null);
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  const scan = useScanBatch();
  const commit = useCommitBatch();

  const mergeFiles = (incoming: File[]) => {
    setPickedFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const merged = [...prev];
      for (const f of incoming) {
        if (!existing.has(f.name)) {
          merged.push(f);
          existing.add(f.name);
        }
      }
      return merged;
    });
    setReport(null);
    setCommitResult(null);
  };

  const handleFolderPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    mergeFiles(Array.from(e.target.files ?? []));
  };

  const handleFilePick = (e: React.ChangeEvent<HTMLInputElement>) => {
    mergeFiles(Array.from(e.target.files ?? []));
  };

  const clearFiles = () => {
    setPickedFiles([]);
    setReport(null);
    setCommitResult(null);
  };

  const handleScan = async () => {
    if (pickedFiles.length === 0) return;
    setCommitResult(null);
    try {
      const result = await scan.mutateAsync({
        files: pickedFiles,
        entityId,
        periodId,
      });
      setReport(result);
    } catch (err) {
      setCommitResult(`Scan failed: ${(err as Error).message}`);
    }
  };

  const handleCommit = async () => {
    if (pickedFiles.length === 0) return;
    setCommitResult(null);
    try {
      const result = await commit.mutateAsync({
        files: pickedFiles,
        entityId,
        periodId,
      });
      setCommitResult(
        `Committed ${result.records_inserted} of ${result.records_received} rows. ` +
          `By payload: ${
            Object.entries(result.by_payload)
              .map(([k, v]) => `${k}=${v}`)
              .join(', ') || 'none'
          }`,
      );
    } catch (err) {
      setCommitResult(`Commit failed: ${(err as Error).message}`);
    }
  };

  // ---- Chart data derived from the scan report ----
  const statusData = (() => {
    if (!report) return [];
    let clean = 0;
    let errors = 0;
    let failed = 0;
    for (const f of report.files) {
      if (f.error) failed += 1;
      else if (f.records_error > 0) errors += 1;
      else clean += 1;
    }
    return [
      { name: 'Clean', value: clean, color: '#16a34a' },
      { name: 'Errors', value: errors, color: '#dc2626' },
      { name: 'Failed', value: failed, color: '#64748b' },
    ].filter((d) => d.value > 0);
  })();

  const payloadData = (() => {
    if (!report) return [];
    const totals: Record<string, number> = {};
    for (const f of report.files) {
      if (!f.payload_type) continue;
      totals[f.payload_type] = (totals[f.payload_type] ?? 0) + f.records_received;
    }
    return Object.entries(totals)
      .sort(([, a], [, b]) => b - a)
      .map(([k, v]) => ({ name: k, value: v }));
  })();

  const successRate =
    report && report.total_received > 0
      ? (report.total_valid / report.total_received) * 100
      : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Ingestion</h1>
          <p className="page-subheading">
            Upload a folder or a set of CSE submission files. Each file is
            auto-classified, validated, and reported before commit. No data is
            written until you click Commit.
          </p>
        </div>
        <Badge tone="info">Offline · Air-gapped</Badge>
      </div>

      <Card>
        <CardHeader
          title="1 · Select submission files"
          subtitle="Use either the folder picker or the file picker. All files must belong to one CSE and one assessment period."
        />

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="label-base">Entity</label>
            <select
              value={entityId}
              onChange={(e) => setEntityId(Number(e.target.value))}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
            >
              {ENTITIES.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.code}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label-base">Assessment period</label>
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 dark:border-navy-700 dark:bg-navy-950 dark:text-slate-200">
              Q3-2026
            </div>
          </div>
        </div>

        <input
          ref={folderInputRef}
          type="file"
          multiple
          // @ts-expect-error webkitdirectory is not part of TS lib.dom typings
          webkitdirectory=""
          onChange={handleFolderPick}
          className="hidden"
        />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".csv,.json,.xlsx,.xls"
          onChange={handleFilePick}
          className="hidden"
        />

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            leftIcon={<FolderUp className="h-3.5 w-3.5" />}
            onClick={() => folderInputRef.current?.click()}
          >
            Choose folder
          </Button>
          <Button
            variant="secondary"
            leftIcon={<FilePlus2 className="h-3.5 w-3.5" />}
            onClick={() => fileInputRef.current?.click()}
          >
            Choose files
          </Button>
          {pickedFiles.length > 0 && (
            <>
              <Badge tone="neutral">
                {pickedFiles.length} file{pickedFiles.length === 1 ? '' : 's'} selected
              </Badge>
              <Button variant="ghost" size="sm" onClick={clearFiles}>
                Clear
              </Button>
            </>
          )}
        </div>

        {pickedFiles.length > 0 && (
          <ul className="mt-4 max-h-48 space-y-1 overflow-y-auto rounded-md border border-slate-200 bg-slate-50/60 p-2 text-xs dark:border-navy-800 dark:bg-navy-950/40">
            {pickedFiles.map((f) => (
              <li
                key={f.name}
                className="flex items-center justify-between gap-3 px-1.5 py-0.5 font-mono text-slate-600 dark:text-slate-300"
              >
                <span className="truncate">{f.name}</span>
                <span className="shrink-0 text-slate-400">
                  {(f.size / 1024).toFixed(1)} KB
                </span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            leftIcon={
              scan.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Upload className="h-3.5 w-3.5" />
              )
            }
            onClick={handleScan}
            disabled={pickedFiles.length === 0 || scan.isPending}
          >
            {scan.isPending ? 'Scanning…' : 'Scan files'}
          </Button>

          {report && report.total_valid > 0 && (
            <Button
              variant="primary"
              leftIcon={
                commit.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                )
              }
              onClick={handleCommit}
              disabled={commit.isPending}
            >
              {commit.isPending
                ? 'Committing…'
                : `Commit ${report.total_valid} valid rows`}
            </Button>
          )}
        </div>
      </Card>

      {commitResult && (
        <Card className="border-l-4 border-l-accent">
          <p className="text-sm text-slate-700 dark:text-slate-200">{commitResult}</p>
        </Card>
      )}

      {report && (
        <>
          {/* Summary tiles */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Files scanned" value={report.file_count} />
            <Stat label="Records received" value={report.total_received} />
            <Stat label="Valid" value={report.total_valid} tone="success" />
            <Stat
              label="Errors"
              value={report.total_error}
              tone={report.total_error > 0 ? 'critical' : 'neutral'}
            />
          </div>

          {/* Charts — new */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                        <Card>
              <CardHeader
                title="Files by Status"
                subtitle="Clean vs errors vs failed"
              />
              <CategoryDonutChart
                data={statusData}
                centerLabel="files"
                centerValue={report.file_count}
              />
            </Card>

            <Card>
              <CardHeader
                title="Records by Payload Type"
                subtitle="Row counts per detected type"
              />
              <PayloadTypeBars data={payloadData} />
            </Card>

            <Card>
              <CardHeader
                title="Success Rate"
                subtitle="Valid / received"
              />
              <div className="flex flex-col items-center justify-center py-2">
                <SuccessRateGauge
                  value={successRate}
                  label={`${report.total_valid.toLocaleString()} of ${report.total_received.toLocaleString()}`}
                  sublabel="rows accepted"
                />
              </div>
            </Card>
          </div>

          {/* Validation report table */}
          <Card padded={false}>
            <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
              <CardHeader
                title="2 · Validation report"
                subtitle="Per-file breakdown. Expand a file to see individual issues."
              />
            </div>

            {report.files.length === 0 ? (
              <div className="px-5 py-6">
                <EmptyState
                  title="No files were scanned"
                  description="Pick at least one CSV, JSON, or XLSX file."
                />
              </div>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-navy-800">
                {report.files.map((f) => {
                  const badge = fileStatusBadge(f);
                  const isOpen = expandedFile === f.file_name;
                  return (
                    <li key={f.file_name}>
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedFile(isOpen ? null : f.file_name)
                        }
                        className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-slate-50/60 dark:hover:bg-navy-800/40"
                      >
                        {isOpen ? (
                          <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
                        )}
                        <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-700 dark:text-slate-200">
                          {f.file_name}
                        </span>
                        <span className="shrink-0 text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
                          {f.payload_type ?? '—'}
                        </span>
                        <span className="shrink-0 font-mono text-xs text-slate-600 dark:text-slate-300">
                          {f.records_valid}/{f.records_received}
                        </span>
                        {f.records_warning > 0 && (
                          <span className="shrink-0 font-mono text-xs text-amber-600 dark:text-amber-400">
                            {f.records_warning} warn
                          </span>
                        )}
                        {f.records_error > 0 && (
                          <span className="shrink-0 font-mono text-xs text-red-600 dark:text-red-400">
                            {f.records_error} err
                          </span>
                        )}
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                      </button>

                      {isOpen && (
                        <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-4 dark:border-navy-800 dark:bg-navy-950/40">
                          {f.error && (
                            <p className="mb-2 text-xs text-red-600 dark:text-red-400">
                              {f.error}
                            </p>
                          )}

                          {f.issues.length === 0 && !f.error && (
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              No issues detected in this file.
                            </p>
                          )}

                          {f.issues.length > 0 && (
                            <table className="w-full text-left text-xs">
                              <thead className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                <tr>
                                  <th className="py-1.5 pr-3 font-medium">Row</th>
                                  <th className="py-1.5 pr-3 font-medium">Severity</th>
                                  <th className="py-1.5 pr-3 font-medium">Field</th>
                                  <th className="py-1.5 font-medium">Message</th>
                                </tr>
                              </thead>
                              <tbody>
                                {f.issues.map((issue, i) => (
                                  <tr
                                    key={i}
                                    className="border-t border-slate-200 dark:border-navy-800"
                                  >
                                    <td className="py-1.5 pr-3 font-mono text-slate-600 dark:text-slate-300">
                                      {issue.row ?? '—'}
                                    </td>
                                    <td className="py-1.5 pr-3">
                                      <Badge
                                        tone={
                                          issue.severity === 'ERROR'
                                            ? 'critical'
                                            : issue.severity === 'WARNING'
                                              ? 'warning'
                                              : 'info'
                                        }
                                      >
                                        {issue.severity}
                                      </Badge>
                                    </td>
                                    <td className="py-1.5 pr-3 font-mono text-slate-600 dark:text-slate-300">
                                      {issue.field ?? '—'}
                                    </td>
                                    <td className="py-1.5 text-slate-700 dark:text-slate-200">
                                      {issue.message}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        </>
      )}

      {!report && pickedFiles.length === 0 && (
        <Card>
          <EmptyState
            icon={<AlertCircle className="h-4 w-4" />}
            title="No files selected"
            description="Click 'Choose folder' to pick the CSE's submission folder, or 'Choose files' to pick individual files."
          />
        </Card>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: number;
  tone?: 'neutral' | 'success' | 'critical';
}) {
  const color =
    tone === 'success'
      ? 'text-emerald-600 dark:text-emerald-400'
      : tone === 'critical'
        ? 'text-red-600 dark:text-red-400'
        : 'text-slate-900 dark:text-white';
  return (
    <Card>
      <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-semibold tracking-tight ${color}`}>
        {value.toLocaleString()}
      </p>
    </Card>
  );
}

function PayloadTypeBars({ data }: { data: Array<{ name: string; value: number }> }) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-400">
        No payload data
      </div>
    );
  }
  const max = Math.max(...data.map((d) => d.value));
  return (
    <ul className="space-y-3 py-2">
      {data.map((d) => (
        <li key={d.name}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-mono text-slate-700 dark:text-slate-200">
              {d.name}
            </span>
            <span className="font-mono text-slate-500 dark:text-slate-400">
              {d.value.toLocaleString()}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-navy-800">
            <div
              className="h-full bg-accent"
              style={{ width: `${(d.value / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}