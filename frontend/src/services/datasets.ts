import { api } from './api';

export interface DatasetListItem {
  id: number | string;
  entity_id: number;
  entity_code: string | null;
  entity_name: string | null;
  period_id: number | null;
  period_label: string | null;
  file_name: string;
  format: string;
  payload_type: string;
  file_size: number;
  file_hash: string;
  status: string;
  submitted_by: string | null;
  records_received: number;
  records_valid: number;
  records_warning: number;
  records_error: number;
  created_at: string;
  synthetic?: boolean;
  included?: boolean;
  deleted?: boolean;
}

export interface DatasetListResponse {
  total: number;
  limit: number;
  offset: number;
  mode?: string;
  items: DatasetListItem[];
}

export interface DatasetDetail {
  id: string;
  entity: {
    id: number;
    code: string;
    name: string;
    sector: string;
    criticality: string;
  } | null;
  period: { id: number; label: string } | null;
  file_name: string;
  format: string;
  payload_type: string;
  file_size: number;
  file_hash: string;
  status: string;
  submitted_by: string | null;
  records_received: number;
  records_valid: number;
  records_warning: number;
  records_error: number;
  validation_report: Record<string, unknown> | null;
  created_at: string;
  synthetic?: boolean;
}

export interface DatasetRecordsResponse {
  payload_type: string;
  kind: 'records' | 'summary';
  total: number;
  limit: number;
  offset: number;
  records: Record<string, unknown>[];
  message?: string;
}

export async function fetchDatasets(params: {
  entity_id?: number;
  period_id?: number;
  mode?: 'complete' | 'modified';
  limit?: number;
  offset?: number;
} = {}): Promise<DatasetListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  });
  const suffix = qs.toString() ? `?${qs}` : '';
  return api.get<DatasetListResponse>(`/datasets${suffix}`);
}

export async function fetchDataset(id: number | string): Promise<DatasetDetail> {
  return api.get<DatasetDetail>(`/datasets/${id}`);
}

export async function fetchDatasetRecords(
  id: number | string,
  params: { limit?: number; offset?: number } = {},
): Promise<DatasetRecordsResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  });
  const suffix = qs.toString() ? `?${qs}` : '';
  return api.get<DatasetRecordsResponse>(`/datasets/${id}/records${suffix}`);
}

export async function deleteDataset(
  id: number,
): Promise<{ status: string; submission_id: number }> {
  return api.delete(`/admin/datasets/${id}`);
}

export async function seedSyntheticData(): Promise<{
  status: string;
  inserted: number;
  by_entity: Record<string, number>;
  analytics: unknown;
}> {
  return api.post('/admin/seed-synthetic');
}

export async function updateDatasetPreference(
  submissionId: number,
  payload: { included?: boolean; deleted?: boolean },
): Promise<{ submission_id: number; included: boolean; deleted: boolean }> {
  return api.post(`/admin/datasets/${submissionId}/preference`, payload);
}