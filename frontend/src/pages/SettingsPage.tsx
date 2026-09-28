import { Loader2, Sparkles, Trash2 } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import { useCurrentUser } from '../hooks/useAuth';
import { useDataModeStore } from '../store/dataMode';
import {
  fetchDatasets,
  seedSyntheticData,
  updateDatasetPreference,
  type DatasetListItem,
} from '../services/datasets';

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

export default function SettingsPage() {
  const { data: user } = useCurrentUser();
  const mode = useDataModeStore((s) => s.mode);
  const setMode = useDataModeStore((s) => s.setMode);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['datasets', 'settings', mode],
    queryFn: () => fetchDatasets({ mode, limit: 500 }),
    staleTime: 10_000,
  });

  const prefMut = useMutation({
    mutationFn: (input: { id: number; included?: boolean; deleted?: boolean }) =>
      updateDatasetPreference(input.id, {
        included: input.included,
        deleted: input.deleted,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets'] });
    },
  });

   const seedMut = useMutation({
    mutationFn: () => seedSyntheticData(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets'] });
      qc.invalidateQueries({ queryKey: ['entities'] });
      qc.invalidateQueries({ queryKey: ['findings'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });

  const items: DatasetListItem[] = data?.items ?? [];

  const grouped: Record<string, DatasetListItem[]> = {};
  for (const d of items) {
    const key = d.entity_code ?? 'Unknown';
    (grouped[key] ??= []).push(d);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-heading">Settings</h1>
          <p className="page-subheading">
            Data source mode, analytics configuration, and account details.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="info">ADMIN only</Badge>
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
            {seedMut.isPending ? 'Seeding…' : 'Seed data'}
          </Button>
        </div>
      </div>

      {/* Data Source */}
      <Card>
        <CardHeader
          title="Data Source"
          subtitle="Choose which datasets are used throughout the application."
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <ModeCard
            active={mode === 'complete'}
            title="Complete Data"
            description="Every dataset received — including test uploads. Check the ones you want available in Modified view."
            onClick={() => setMode('complete')}
          />
          <ModeCard
            active={mode === 'modified'}
            title="Modified Data"
            description="Only the datasets you selected. Use the trash icon to remove entries from this view without losing them from Complete Data."
            onClick={() => setMode('modified')}
          />
        </div>
      </Card>

      {/* Datasets under current mode */}
      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title={mode === 'complete' ? 'All datasets' : 'Selected datasets'}
            subtitle={
              mode === 'complete'
                ? 'Check a dataset to mark it as included in Modified view.'
                : 'These are the datasets currently active in the application. Trash removes them from this view.'
            }
            action={<Badge tone="neutral">{items.length} datasets</Badge>}
          />
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : items.length === 0 ? (
          <div className="px-5 py-6">
            <EmptyState
              title={
                mode === 'complete' ? 'No datasets yet' : 'No datasets selected'
              }
              description={
                mode === 'complete'
                  ? 'Click "Seed demo data" or upload files from Ingestion.'
                  : 'Switch to Complete Data to select datasets.'
              }
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-navy-800">
            {Object.entries(grouped).map(([entityCode, rows]) => (
              <div key={entityCode} className="px-5 py-4">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">
                      {entityCode}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {rows[0].entity_name ?? '—'}
                    </p>
                  </div>
                  <Badge tone="neutral">{rows.length} files</Badge>
                </div>
                <ul className="space-y-2">
                  {rows.map((r) => {
                    const numericId =
                      typeof r.id === 'number' ? r.id : null;
                    return (
                      <li
                        key={String(r.id)}
                        className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50/40 px-3 py-2 dark:border-navy-800 dark:bg-navy-950/40"
                      >
                        {mode === 'complete' && numericId !== null && (
                          <input
                            type="checkbox"
                            checked={r.included ?? true}
                            onChange={(e) =>
                              prefMut.mutate({
                                id: numericId,
                                included: e.target.checked,
                              })
                            }
                            className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent/40 dark:border-navy-700 dark:bg-navy-900"
                          />
                        )}

                        <div className="min-w-0 flex-1">
                          <p className="truncate font-mono text-xs text-slate-800 dark:text-slate-100">
                            {r.file_name}
                          </p>
                          <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                            {PAYLOAD_LABELS[r.payload_type] ?? r.payload_type} ·{' '}
                            {r.records_received.toLocaleString()} records
                            {r.period_label ? ` · ${r.period_label}` : ''}
                          </p>
                        </div>

                        {mode === 'modified' && numericId !== null && (
                          <button
                            type="button"
                            onClick={() =>
                              prefMut.mutate({
                                id: numericId,
                                deleted: true,
                              })
                            }
                            disabled={prefMut.isPending}
                            className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-950/40 dark:hover:text-red-400"
                            title="Remove from Modified view"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}

                        {mode === 'complete' && (
                          <Badge tone={r.included === false ? 'neutral' : 'info'}>
                            {r.included === false ? 'Not included' : 'Included'}
                          </Badge>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Current user */}
      <Card>
        <CardHeader title="Account" subtitle="Signed-in user" />
        {user ? (
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Detail label="Name" value={user.full_name} />
            <Detail label="Username" value={user.username} />
            <Detail label="Email" value={user.email} />
            <Detail label="Role" value={user.role} />
          </dl>
        ) : (
          <EmptyState
            icon={<Sparkles className="h-4 w-4" />}
            title="No active session"
          />
        )}
      </Card>
    </div>
  );
}

function ModeCard({
  active,
  title,
  description,
  onClick,
}: {
  active: boolean;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        'rounded-md border p-4 text-left transition ' +
        (active
          ? 'border-accent bg-accent/5 dark:border-accent-soft dark:bg-accent-soft/10'
          : 'border-slate-200 bg-white hover:bg-slate-50 dark:border-navy-800 dark:bg-navy-900 dark:hover:bg-navy-800/50')
      }
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-900 dark:text-white">
          {title}
        </p>
        {active && <Badge tone="info">Active</Badge>}
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        {description}
      </p>
    </button>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm text-slate-800 dark:text-slate-100">
        {value}
      </dd>
    </div>
  );
}