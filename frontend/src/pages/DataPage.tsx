import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Database, FileSpreadsheet, Loader2, Trash2, Sparkles } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import {
  deleteDataset,
  fetchDatasets,
  seedSyntheticData,
} from '../services/datasets';
import { useDataModeStore } from '../store/dataMode';
import { formatDateTime } from '../utils/format';

const PAYLOAD_LABELS: Record<string, string> = {
  alerts: 'SOC Alerts',
  cases: 'Case Management',
  investigations: 'Investigations',
  escalations: 'Escalations',
  dispositions: 'Alert Dispositions',
  assets: 'Asset Inventory',
  entities: 'Entity Master',
  batch: 'Batch Submission',
};

const STATUS_TONE: Record<
  string,
  'neutral' | 'info' | 'success' | 'warning' | 'critical'
> = {
  PENDING: 'neutral',
  PROCESSING: 'info',
  COMMITTED: 'success',
  FAILED: 'critical',
};

function humanSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DataPage() {
  const [page, setPage] = useState(0);
  const pageSize = 25;
  const qc = useQueryClient();
  const mode = useDataModeStore((s) => s.mode);
  const [message, setMessage] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['datasets', { page, mode }],
    queryFn: () =>
      fetchDatasets({ limit: pageSize, offset: page * pageSize, mode }),
    staleTime: 10_000,
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteDataset(id),
    onSuccess: () => {
      setMessage('Dataset removed.');
      qc.invalidateQueries({ queryKey: ['datasets'] });
      qc.invalidateQueries({ queryKey: ['entities'] });
      qc.invalidateQueries({ queryKey: ['findings'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (e) => setMessage(`Delete failed: ${(e as Error).message}`),
  });

  const seedMut = useMutation({
    mutationFn: () => seedSyntheticData(),
    onSuccess: (r) => {
      setMessage(
        `Seeded ${r.inserted.toLocaleString()} rows across ${
          Object.keys(r.by_entity).length
        } entities.`,
      );
      qc.invalidateQueries({ queryKey: ['datasets'] });
      qc.invalidateQueries({ queryKey: ['entities'] });
      qc.invalidateQueries({ queryKey: ['findings'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (e) => setMessage(`Seed failed: ${(e as Error).message}`),
  });

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Data</h1>
          <p className="page-subheading">
            Every dataset submitted by Critical Sector Entities. Files with a
            blue link open the underlying records.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="neutral">{total} datasets</Badge>
          <Badge tone={mode === 'complete' ? 'info' : 'warning'}>
            {mode === 'complete' ? 'Complete' : 'Modified'}
          </Badge>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={
              seedMut.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )
            }
            onClick={() => seedMut.mutate()}
            disabled={seedMut.isPending}
          >
            {seedMut.isPending ? 'Seeding…' : 'Seed synthetic data'}
          </Button>
          <Link
            to="/ingestion"
            className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-deep"
          >
            Upload new
          </Link>
        </div>
      </div>

      {message && (
        <Card className="border-l-4 border-l-accent">
          <p className="text-sm text-slate-700 dark:text-slate-200">{message}</p>
        </Card>
      )}

      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title="Submitted datasets"
            subtitle="Newest first — click a filename to view its records"
          />
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        )}

        {isError && (
          <div className="px-5 py-6 text-sm text-red-600 dark:text-red-400">
            Failed to load datasets.
          </div>
        )}

        {!isLoading && !isError && total === 0 && (
          <div className="px-5 py-6">
            <EmptyState
              icon={<Database className="h-4 w-4" />}
              title="No data available"
              description="Click 'Seed synthetic data' to load the bundled sample CSVs, or upload your own folder from Ingestion."
            />
          </div>
        )}

        {!isLoading && !isError && total > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">File</th>
                  <th className="px-4 py-2.5 font-medium">Entity</th>
                  <th className="px-4 py-2.5 font-medium">Type</th>
                  <th className="px-4 py-2.5 font-medium">Period</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Records
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">Valid</th>
                  <th className="px-4 py-2.5 text-right font-medium">Errors</th>
                  <th className="px-4 py-2.5 font-medium">Size</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Uploaded</th>
                  <th className="px-4 py-2.5 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {data!.items.map((d) => {
                  const key = String(d.id);
                  const isSynthetic = Boolean(d.synthetic);
                  const numericId = typeof d.id === 'number' ? d.id : null;
                  return (
                    <tr
                      key={key}
                      className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                    >
                      <td className="max-w-xs px-4 py-2.5">
                        {isSynthetic || numericId === null ? (
                          <span className="flex items-center gap-2 font-mono text-xs text-slate-500 dark:text-slate-400">
                            <FileSpreadsheet className="h-3.5 w-3.5 shrink-0" />
                            <span className="truncate">{d.file_name}</span>
                          </span>
                        ) : (
                          <Link
                            to={`/data/${numericId}`}
                            className="flex items-center gap-2 font-mono text-xs text-accent hover:underline dark:text-accent-soft"
                          >
                            <FileSpreadsheet className="h-3.5 w-3.5 shrink-0" />
                            <span className="truncate">{d.file_name}</span>
                          </Link>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-slate-700 dark:text-slate-200">
                        {d.entity_code ?? '—'}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                        {PAYLOAD_LABELS[d.payload_type] ?? d.payload_type}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400">
                        {d.period_label ?? '—'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-600 dark:text-slate-300">
                        {d.records_received.toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400">
                        {d.records_valid.toLocaleString()}
                      </td>
                      <td
                        className={
                          'px-4 py-2.5 text-right font-mono text-xs ' +
                          (d.records_error > 0
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-slate-400')
                        }
                      >
                        {d.records_error.toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                        {humanSize(d.file_size)}
                      </td>
                      <td className="px-4 py-2.5">
                        {isSynthetic ? (
                          <Badge tone="info">In database</Badge>
                        ) : (
                          <Badge tone={STATUS_TONE[d.status] ?? 'neutral'}>
                            {d.status}
                          </Badge>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400">
                        {formatDateTime(d.created_at)}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {numericId !== null && !isSynthetic && (
                          <button
                            type="button"
                            onClick={() => {
                              if (
                                window.confirm(
                                  `Delete "${d.file_name}" and its records? This cannot be undone.`,
                                )
                              ) {
                                deleteMut.mutate(numericId);
                              }
                            }}
                            disabled={deleteMut.isPending}
                            className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-950/40 dark:hover:text-red-400"
                            title="Delete dataset"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!isLoading && !isError && total > 0 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3 text-xs text-slate-500 dark:border-navy-800 dark:text-slate-400">
            <span>
              Showing {page * pageSize + 1}–
              {Math.min((page + 1) * pageSize, total)} of {total}
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