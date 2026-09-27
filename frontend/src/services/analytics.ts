import { api } from './api';
import type {
  AlertListItem,
  AnalyticsSummary,
  AuditLogResponse,
  CaseListItem,
  EntityListItem,
  FindingDetail,
  FindingsListResponse,
  InvestigationListItem,
  ListResponse,
  ReviewDecisionResponse,
  ReviewQueueResponse,
} from '../types';

export interface FindingsFilters {
  period_id?: number;
  entity_id?: number;
  category?: string;
  priority?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

function buildQs(params: object): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `?${s}` : '';
}

export async function fetchFindings(
  filters: FindingsFilters = {},
): Promise<FindingsListResponse> {
  return api.get<FindingsListResponse>(`/findings${buildQs(filters)}`);
}

export async function fetchFinding(id: number): Promise<FindingDetail> {
  return api.get<FindingDetail>(`/findings/${id}`);
}

export async function fetchReviewQueue(
  periodId: number,
  includeDecided = false,
): Promise<ReviewQueueResponse> {
  return api.get<ReviewQueueResponse>(
    `/review-queue${buildQs({
      period_id: periodId,
      include_decided: includeDecided,
    })}`,
  );
}

export async function fetchAnalyticsSummary(
  periodId: number,
): Promise<AnalyticsSummary> {
  return api.get<AnalyticsSummary>(
    `/analytics/summary${buildQs({ period_id: periodId })}`,
  );
}

export async function fetchAuditLog(
  params: {
    action?: string;
    target_type?: string;
    limit?: number;
    offset?: number;
  } = {},
): Promise<AuditLogResponse> {
  return api.get<AuditLogResponse>(`/audit-log${buildQs(params)}`);
}

export async function submitReview(
  findingId: number,
  decision: 'CONFIRMED' | 'REJECTED' | 'FURTHER_REVIEW',
  comment?: string | null,
): Promise<ReviewDecisionResponse> {
  return api.post<ReviewDecisionResponse>(`/findings/${findingId}/review`, {
    decision,
    comment: comment ?? null,
  });
}

export async function runAnalytics(periodId: number): Promise<unknown> {
  return api.post(`/analytics/run${buildQs({ period_id: periodId })}`);
}

// ---------------------------------------------------------------------------
// List endpoints
// ---------------------------------------------------------------------------
export async function fetchEntities(
  periodId?: number,
): Promise<EntityListItem[]> {
  return api.get<EntityListItem[]>(`/entities${buildQs({ period_id: periodId })}`);
}

export async function fetchAlerts(params: {
  entity_id?: number;
  period_id?: number;
  severity?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ListResponse<AlertListItem>> {
  return api.get<ListResponse<AlertListItem>>(`/alerts${buildQs(params)}`);
}

export async function fetchCases(params: {
  entity_id?: number;
  period_id?: number;
  limit?: number;
  offset?: number;
} = {}): Promise<ListResponse<CaseListItem>> {
  return api.get<ListResponse<CaseListItem>>(`/cases${buildQs(params)}`);
}

export async function fetchInvestigations(params: {
  entity_id?: number;
  period_id?: number;
  limit?: number;
  offset?: number;
} = {}): Promise<ListResponse<InvestigationListItem>> {
  return api.get<ListResponse<InvestigationListItem>>(
    `/investigations${buildQs(params)}`,
  );
}import type {
  BatchCommitResponse,
  BatchReport,
} from '../types';

export async function scanBatch(
  files: File[],
  entityId: number,
  periodId: number,
): Promise<BatchReport> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f, f.name));
  form.append('entity_id', String(entityId));
  form.append('period_id', String(periodId));

  const token = localStorage.getItem('sat-sa-token');
  const response = await fetch(
    `${import.meta.env.VITE_API_BASE ?? '/api/v1'}/ingestion/batch/scan`,
    {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: form,
    },
  );

  if (!response.ok) {
    let message = `Batch scan failed (${response.status})`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data?.detail) message = data.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await response.json()) as BatchReport;
}

export async function commitBatch(
  files: File[],
  entityId: number,
  periodId: number,
): Promise<BatchCommitResponse> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f, f.name));
  form.append('entity_id', String(entityId));
  form.append('period_id', String(periodId));

  const token = localStorage.getItem('sat-sa-token');
  const response = await fetch(
    `${import.meta.env.VITE_API_BASE ?? '/api/v1'}/ingestion/batch/commit`,
    {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: form,
    },
  );

  if (!response.ok) {
    let message = `Batch commit failed (${response.status})`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data?.detail) message = data.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await response.json()) as BatchCommitResponse;
}export interface ReportAvailability {
  period_id: number;
  period_label: string;
  entities: number;
  findings: number;
  decisions: number;
  audits: number;
  formats: Array<{ id: string; label: string }>;
}

export async function fetchReportAvailability(
  periodId: number,
): Promise<ReportAvailability> {
  return api.get<ReportAvailability>(`/reports/available?period_id=${periodId}`);
}

export function reportDownloadUrl(
  kind: 'pdf' | 'findings.csv' | 'decisions.csv',
  periodId: number,
): string {
  const base = import.meta.env.VITE_API_BASE ?? '/api/v1';
  return `${base}/reports/${kind}?period_id=${periodId}`;
}

export async function downloadReport(
  kind: 'pdf' | 'findings.csv' | 'decisions.csv',
  periodId: number,
): Promise<{ blob: Blob; filename: string }> {
  const token = localStorage.getItem('sat-sa-token');
  const response = await fetch(reportDownloadUrl(kind, periodId), {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    let message = `Download failed (${response.status})`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data?.detail) message = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  const disposition = response.headers.get('content-disposition') ?? '';
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? `SAT-SA-report.${kind}`;
  const blob = await response.blob();
  return { blob, filename };
}