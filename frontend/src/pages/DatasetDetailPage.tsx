import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { fetchDataset, fetchDatasetRecords } from '../services/datasets';
import { formatDateTime } from '../utils/format';

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

function prettifyKey(key: string): string {
  return key
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const datasetId = id ?? null;
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const { data: meta, isLoading: loadingMeta } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => fetchDataset(datasetId as string),
    enabled: datasetId !== null,
  });

  const { data: records, isLoading: loadingRecords } = useQuery({
    queryKey: ['dataset', datasetId, 'records', { page }],
    queryFn: () =>
      fetchDatasetRecords(datasetId as string, {
        limit: pageSize,
        offset: page * pageSize,
      }),
    enabled: datasetId !== null,
    staleTime: 30_000,
  });

  if (loadingMeta) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    );
  }

  if (!meta) {
    return (
      <Card>
        <EmptyState
          title="Dataset not found"
          description="It may have been removed."
          action={
            <Link
              to="/data"
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-deep"
            >
              Back to Data
            </Link>
          }
        />
      </Card>
    );
  }

  const total = records?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const sampleRecord = records?.records?.[0] ?? null;
  const columnKeys = sampleRecord ? Object.keys(sampleRecord) : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link
            to="/data"
            className="mt-1 rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-navy-800"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <p className="font-mono text-xs text-slate-500 dark:text-slate-400">
              {meta.synthetic ? 'DATASET (FROM DB)' : `SUBMISSION #${meta.id}`}
            </p>
            <h1 className="page-heading mt-0.5">{meta.file_name}</h1>
            <p className="page-subheading">
              {meta.entity?.code} · {meta.entity?.name} ·{' '}
              {meta.period?.label ?? '—'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="info">{meta.payload_type}</Badge>
          <Badge tone={STATUS_TONE[meta.status] ?? 'neutral'}>
            {meta.status}
          </Badge>
        </div>
      </div>

      <Card>
        <CardHeader title="File information" subtitle="What was received" />
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          <Meta label="Format" value={meta.format.toUpperCase()} />
          <Meta label="Size" value={humanSize(meta.file_size)} />
          <Meta
            label="Records received"
            value={meta.records_received.toLocaleString()}
          />
          <Meta
            label="Records valid"
            value={meta.records_valid.toLocaleString()}
          />
          <Meta
            label="Warnings"
            value={meta.records_warning.toLocaleString()}
          />
          <Meta label="Errors" value={meta.records_error.toLocaleString()} />
          <Meta label="Uploaded by" value={meta.submitted_by ?? '—'} />
          <Meta label="Uploaded at" value={formatDateTime(meta.created_at)} />
          <Meta
            label="File hash"
            value={meta.file_hash ? meta.file_hash.slice(0, 16) + '…' : '—'}
            mono
          />
          <Meta label="Entity code" value={meta.entity?.code ?? '—'} />
          <Meta label="Sector" value={meta.entity?.sector ?? '—'} />
          <Meta label="Period" value={meta.period?.label ?? '—'} />
        </dl>
      </Card>

      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title="Records in this dataset"
            subtitle={`${total.toLocaleString()} record${total === 1 ? '' : 's'} stored`}
          />
        </div>

        {loadingRecords ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : records?.kind === 'summary' ? (
          <div className="px-5 py-6 text-sm text-slate-600 dark:text-slate-300">
            {records.message ?? 'This submission contains multiple record types.'}
          </div>
        ) : !records || total === 0 ? (
          <div className="px-5 py-6">
            <EmptyState
              title="No records in this dataset"
              description="The records may have been filtered out during validation."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  {columnKeys.map((k) => (
                    <th key={k} className="px-4 py-2.5 font-medium">
                      {prettifyKey(k)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.records.map((r, i) => (
                  <tr
                    key={i}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                  >
                    {columnKeys.map((k) => (
                      <td
                        key={k}
                        className="max-w-md truncate px-4 py-2.5 text-xs text-slate-700 dark:text-slate-200"
                      >
                        {r[k] === null || r[k] === undefined
                          ? '—'
                          : String(r[k])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {records?.kind === 'records' && total > 0 && (
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

function Meta({
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
          'mt-0.5 truncate ' +
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