import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Loader2,
  Plug,
  RefreshCw,
  Server,
} from 'lucide-react';

import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card, { CardHeader } from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import {
  Connector,
  fetchFromConnector,
  FetchResponse,
  listConnectors,
  testConnector,
  TestResponse,
} from '../services/connectors';

export default function ApiConnectionsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [types, setTypes] = useState<{ type: string; label: string; description: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<TestResponse | null>(null);

  const [fetchingId, setFetchingId] = useState<number | null>(null);
  const [fetchResult, setFetchResult] = useState<FetchResponse | null>(null);
  const [entityId, setEntityId] = useState<string>('1');
  const [periodId, setPeriodId] = useState<string>('1');

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listConnectors();
      setConnectors(res.items);
      setTypes(res.available_types);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load connectors');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onTest = async (id: number) => {
    setTestingId(id);
    setTestResult(null);
    try {
      const res = await testConnector(id);
      setTestResult(res);
    } catch (e) {
      setTestResult({
        connector_id: id,
        name: '',
        is_demo: true,
        reachable: false,
        mode: '',
        payload_path: '',
        message: e instanceof Error ? e.message : 'Test failed',
      });
    } finally {
      setTestingId(null);
    }
  };

  const onFetch = async (id: number) => {
    setFetchingId(id);
    setFetchResult(null);
    try {
      const res = await fetchFromConnector(id, Number(entityId), Number(periodId), 'alerts');
      setFetchResult(res);
      // Reload connector list so last_run fields update.
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fetch failed');
    } finally {
      setFetchingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="page-heading">API Connections</h1>
          <p className="page-subheading">
            Periodic-pull ingestion from internal SOC APIs. Ingestion routes
            through the same validation and analytics pipeline as file uploads.
          </p>
        </div>
        <Badge tone="warning">DEMO / INTERNAL ONLY</Badge>
      </div>

      {error && (
        <Card>
          <div className="flex items-start gap-2 text-sm text-status-critical">
            <AlertCircle className="mt-0.5 h-4 w-4" />
            <span>{error}</span>
          </div>
        </Card>
      )}

      {/* Configured sources */}
      <Card padded={false}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title="Configured sources"
            subtitle="Connectors defined in this environment."
          />
          <Button
            variant="secondary"
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            onClick={load}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : connectors.length === 0 ? (
          <div className="px-5 py-6">
            <EmptyState
              title="No connectors configured"
              description="Demo connectors appear here after the first request."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Source</th>
                  <th className="px-4 py-2.5 font-medium">Type</th>
                  <th className="px-4 py-2.5 font-medium">Mode</th>
                  <th className="px-4 py-2.5 font-medium">Datasets</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Last sync</th>
                  <th className="px-4 py-2.5 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {connectors.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-slate-100 last:border-b-0 dark:border-navy-800"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Server className="h-4 w-4 text-slate-500" />
                        <div>
                          <p className="font-medium text-slate-800 dark:text-slate-100">
                            {c.name}
                          </p>
                          {c.notes && (
                            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                              {c.notes}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600 dark:text-slate-300">
                      {c.connector_type}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-300">
                      {c.mode}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {c.payload_types.map((pt) => (
                          <Badge key={pt} tone="info">
                            {pt}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={c.status === 'TESTED' ? 'success' : c.status === 'ERROR' ? 'critical' : 'info'}>
                        {c.status}
                      </Badge>
                      {c.is_demo && (
                        <span className="ml-2 text-[10px] uppercase tracking-wider text-status-warning">
                          demo
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                      {c.last_run_at ? (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {c.last_run_at}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="secondary"
                          onClick={() => onTest(c.id)}
                          loading={testingId === c.id}
                          disabled={testingId !== null || fetchingId !== null}
                        >
                          Test
                        </Button>
                        <Button
                          variant="primary"
                          onClick={() => onFetch(c.id)}
                          loading={fetchingId === c.id}
                          disabled={testingId !== null || fetchingId !== null}
                        >
                          Fetch
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Fetch controls */}
      <Card>
        <CardHeader
          title="Fetch parameters"
          subtitle="Choose which entity and period the demo payload is attributed to."
        />
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="block">
            <span className="section-heading">Entity ID</span>
            <input
              type="number"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              className="input-base mt-1"
            />
          </label>
          <label className="block">
            <span className="section-heading">Period ID</span>
            <input
              type="number"
              value={periodId}
              onChange={(e) => setPeriodId(e.target.value)}
              className="input-base mt-1"
            />
          </label>
          <label className="block">
            <span className="section-heading">Payload type</span>
            <input type="text" value="alerts" disabled className="input-base mt-1 opacity-60" />
          </label>
        </div>
      </Card>

      {/* Test result */}
      {testResult && (
        <Card>
          <CardHeader
            title="Test result"
            subtitle={`Connector #${testResult.connector_id}`}
          />
          <div className="mt-3 flex items-center gap-3">
            {testResult.reachable ? (
              <CheckCircle2 className="h-5 w-5 text-status-ok" />
            ) : (
              <AlertCircle className="h-5 w-5 text-status-critical" />
            )}
            <div>
              <p className="text-sm text-slate-800 dark:text-slate-100">
                {testResult.message}
              </p>
              <p className="mt-0.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                {testResult.payload_path}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Fetch result */}
      {fetchResult && (
        <Card>
          <CardHeader
            title="Fetch result"
            subtitle="Ingestion completed. Analytics ran against the newly imported records."
          />
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <Metric label="Received" value={fetchResult.records_received} />
            <Metric label="Inserted" value={fetchResult.records_inserted} />
            <Metric label="Skipped" value={fetchResult.records_skipped} />
            <Metric label="Warnings" value={fetchResult.warnings} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to={`/data/${fetchResult.submission_id}`}>
              <Button variant="secondary" leftIcon={<Database className="h-3.5 w-3.5" />}>
                View dataset
              </Button>
            </Link>
            <Link to="/findings">
              <Button variant="secondary">View findings</Button>
            </Link>
          </div>
        </Card>
      )}

      {/* Available connector types */}
      <Card>
        <CardHeader
          title="Available connector types"
          subtitle="Architectural support for API ingestion. Only the demo type is active in this prototype."
        />
        <ul className="mt-3 space-y-2">
          {types.map((t) => (
            <li
              key={t.type}
              className="flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2 dark:border-navy-800 dark:bg-navy-950/40"
            >
              <Plug className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
              <div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                  {t.label}
                </p>
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  {t.description}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2 dark:border-navy-800 dark:bg-navy-950/40">
      <p className="font-mono text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold text-slate-800 dark:text-slate-100">
        {value}
      </p>
    </div>
  );
}