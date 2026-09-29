import { api } from './api';

export interface Connector {
  id: number;
  name: string;
  connector_type: string;
  base_url: string | null;
  mode: string;
  is_demo: boolean;
  status: string;
  payload_types: string[];
  last_run_at: string | null;
  last_run_summary: Record<string, unknown> | null;
  notes: string | null;
}

export interface AvailableType {
  type: string;
  label: string;
  description: string;
}

export interface ConnectorListResponse {
  items: Connector[];
  available_types: AvailableType[];
}

export interface TestResponse {
  connector_id: number;
  name: string;
  is_demo: boolean;
  reachable: boolean;
  mode: string;
  payload_path: string;
  message: string;
}

export interface FetchResponse {
  connector: { id: number; name: string; is_demo: boolean };
  submission_id: number;
  version: number;
  records_received: number;
  records_inserted: number;
  records_skipped: number;
  warnings: number;
  errors: number;
  validation_summary: Record<string, unknown>;
  analytics: Record<string, unknown> | null;
}

export async function listConnectors(): Promise<ConnectorListResponse> {
  return api.get<ConnectorListResponse>('/connectors');
}

export async function testConnector(id: number): Promise<TestResponse> {
  return api.post<TestResponse>(`/connectors/${id}/test`);
}

export async function fetchFromConnector(
  id: number,
  entityId: number,
  periodId: number,
  payloadType: string = 'alerts',
): Promise<FetchResponse> {
  const qs = new URLSearchParams({
    entity_id: String(entityId),
    period_id: String(periodId),
    payload_type: payloadType,
  });
  return api.post<FetchResponse>(`/connectors/${id}/fetch?${qs.toString()}`);
}