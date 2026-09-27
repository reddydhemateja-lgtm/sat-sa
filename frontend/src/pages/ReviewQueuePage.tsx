import { Link } from 'react-router-dom';
import { ListChecks, Loader2 } from 'lucide-react';

import Badge from '../components/ui/Badge';
import Card, { CardHeader } from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import { useReviewQueue } from '../hooks/useFindings';
import { categoryTone, humanizeCategory, priorityTone } from '../utils/format';

export default function ReviewQueuePage() {
  const { data, isLoading, isError } = useReviewQueue(1, false);

  const buckets = data?.buckets ?? { HIGH: 0, MEDIUM: 0, LOW: 0, INFORMATIONAL: 0 };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Review Queue</h1>
          <p className="page-subheading">
            Prioritized items awaiting supervisory review. Priority is for review — not
            a final security verdict.
          </p>
        </div>
        <Badge tone="neutral">{data?.total ?? 0} items</Badge>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <p className="section-heading">High Priority</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
            {buckets.HIGH ?? 0}
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Items requiring immediate supervisory attention.
          </p>
        </Card>
        <Card>
          <p className="section-heading">Medium Priority</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
            {buckets.MEDIUM ?? 0}
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Items that warrant review in the current cycle.
          </p>
        </Card>
        <Card>
          <p className="section-heading">Low Priority</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
            {buckets.LOW ?? 0}
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Informational items for awareness.
          </p>
        </Card>
      </div>

      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title="Queue"
            subtitle="Ordered by review priority, then by contribution to the Supervisory Review Indicator"
          />
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        )}

        {isError && (
          <div className="px-5 py-6 text-sm text-red-600 dark:text-red-400">
            Failed to load the queue. Check the backend.
          </div>
        )}

        {!isLoading && !isError && (data?.total ?? 0) === 0 && (
          <div className="px-5 py-6">
            <EmptyState
              icon={<ListChecks className="h-4 w-4" />}
              title="No items awaiting review"
              description="Run analytics or clear existing decisions to see items here."
            />
          </div>
        )}

        {!isLoading && !isError && (data?.total ?? 0) > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Code</th>
                  <th className="px-4 py-2.5 font-medium">Entity</th>
                  <th className="px-4 py-2.5 font-medium">Category</th>
                  <th className="px-4 py-2.5 font-medium">Title</th>
                  <th className="px-4 py-2.5 font-medium">Priority</th>
                  <th className="px-4 py-2.5 text-right font-medium">Indicator</th>
                </tr>
              </thead>
              <tbody>
                {data!.items.map((f) => (
                  <tr
                    key={f.id}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60 dark:border-navy-800 dark:hover:bg-navy-800/40"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs">
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
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-600 dark:text-slate-300">
                      {f.review_indicator.toFixed(1)}
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