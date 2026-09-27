import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Filter, Loader2 } from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import { useFindings } from '../hooks/useFindings';
import { categoryTone, humanizeCategory, priorityTone } from '../utils/format';

const CATEGORIES = [
  '',
  'EXECUTION_GAP',
  'NEGATIVE_SPACE',
  'ANOMALY',
  'PEER_DEVIATION',
  'DATA_QUALITY',
];

const PRIORITIES = ['', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL'];

const STATUSES = ['', 'OPEN', 'CONFIRMED', 'REJECTED', 'FURTHER_REVIEW'];

export default function FindingsPage() {
  const [category, setCategory] = useState('');
  const [priority, setPriority] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const { data, isLoading, isError } = useFindings({
    period_id: 1,
    category: category || undefined,
    priority: priority || undefined,
    status: status || undefined,
    limit: pageSize,
    offset: page * pageSize,
  });

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Findings</h1>
          <p className="page-subheading">
            Indicators identified by the supervisory analytics engine. Every finding
            links to its supporting evidence.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="neutral">{total} findings</Badge>
        </div>
      </div>

      <Card className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Filter
          </span>
        </div>

        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(0);
          }}
          className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c === '' ? 'All categories' : humanizeCategory(c)}
            </option>
          ))}
        </select>

        <select
          value={priority}
          onChange={(e) => {
            setPriority(e.target.value);
            setPage(0);
          }}
          className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
        >
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p === '' ? 'All priorities' : p}
            </option>
          ))}
        </select>

        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(0);
          }}
          className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === '' ? 'All statuses' : s}
            </option>
          ))}
        </select>
      </Card>

      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title="Findings Register"
            subtitle="Click any row to open its evidence and supervisory decision panel"
          />
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        )}

        {isError && (
          <div className="px-5 py-6 text-sm text-red-600 dark:text-red-400">
            Failed to load findings. Check that the backend is running.
          </div>
        )}

        {!isLoading && !isError && total === 0 && (
          <div className="px-5 py-6">
            <EmptyState
              icon={<AlertTriangle className="h-4 w-4" />}
              title="No findings match the filters"
              description="Try clearing filters or run analytics on the assessment period."
            />
          </div>
        )}

        {!isLoading && !isError && total > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Code</th>
                  <th className="px-4 py-2.5 font-medium">Entity</th>
                  <th className="px-4 py-2.5 font-medium">Category</th>
                  <th className="px-4 py-2.5 font-medium">Rule</th>
                  <th className="px-4 py-2.5 font-medium">Title</th>
                  <th className="px-4 py-2.5 font-medium">Priority</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 text-right font-medium">Indicator</th>
                </tr>
              </thead>
              <tbody>
                {data!.items.map((f) => (
                  <tr
                    key={f.id}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                      <Link
                        to={`/findings/${f.id}`}
                        className="text-accent hover:underline dark:text-accent-soft"
                      >
                        {f.code}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-slate-800 dark:text-slate-200">
                      {f.entity_code ?? '—'}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge tone={categoryTone(f.category)}>
                        {humanizeCategory(f.category)}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                      {f.rule_id}
                    </td>
                    <td className="max-w-md truncate px-4 py-2.5 text-slate-800 dark:text-slate-200">
                      <Link
                        to={`/findings/${f.id}`}
                        className="hover:text-accent dark:hover:text-accent-soft"
                      >
                        {f.title}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge tone={priorityTone(f.priority)}>{f.priority}</Badge>
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge
                        tone={
                          f.status === 'OPEN'
                            ? 'info'
                            : f.status === 'CONFIRMED'
                              ? 'critical'
                              : f.status === 'REJECTED'
                                ? 'success'
                                : 'warning'
                        }
                      >
                        {f.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-600 dark:text-slate-300">
                      {f.review_indicator.toFixed(1)}
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
              Showing {page * pageSize + 1}–
              {Math.min((page + 1) * pageSize, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </Button>
              <span>
                Page {page + 1} of {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}