// ---------- Auth / Users ----------
export type Role = 'SUPERVISOR' | 'ANALYST' | 'ADMIN';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ---------- Findings ----------
export type FindingCategory =
  | 'EXECUTION_GAP'
  | 'NEGATIVE_SPACE'
  | 'ANOMALY'
  | 'PEER_DEVIATION'
  | 'DATA_QUALITY';

export type Priority = 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';

export interface Finding {
  id: number;
  code: string;
  entity_id: number;
  entity_code: string | null;
  period_id: number;
  category: FindingCategory;
  rule_id: string;
  title: string;
  narrative: string;
  expected_behavior: string | null;
  observed_pattern: string | null;
  analytical_basis: string;
  priority: Priority;
  confidence: number;
  review_indicator: number;
  metrics: Record<string, unknown> | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Evidence {
  id: number;
  record_type: string;
  record_id: number;
  snippet: string | null;
  weight: number;
}

export interface FindingEntitySummary {
  id: number;
  code: string;
  name: string;
  sector: string;
  criticality: string;
  peer_group: string | null;
}

export interface ReviewDecision {
  id: number;
  finding_id: number;
  reviewer_id: number;
  decision: 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'FURTHER_REVIEW';
  comment: string | null;
  previous_decision: string | null;
  decided_at: string;
  created_at: string;
}

export interface FindingDetail {
  finding: Finding;
  entity: FindingEntitySummary | null;
  evidence: Evidence[];
  review_decisions: ReviewDecision[];
}

export interface FindingsListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Finding[];
}

export interface ReviewQueueItem {
  id: number;
  code: string;
  entity_id: number;
  entity_code: string | null;
  period_id: number;
  category: FindingCategory;
  rule_id: string;
  title: string;
  priority: Priority;
  confidence: number;
  review_indicator: number;
  status: string;
  created_at: string;
}

export interface ReviewQueueResponse {
  period_id: number;
  total: number;
  buckets: Record<Priority, number>;
  items: ReviewQueueItem[];
}

export interface ReviewDecisionRequest {
  decision: 'CONFIRMED' | 'REJECTED' | 'FURTHER_REVIEW';
  comment?: string | null;
}

export interface ReviewDecisionResponse {
  finding_id: number;
  finding_code: string;
  new_status: string;
  decision: ReviewDecision;
}

// ---------- Analytics summary ----------
export interface EntityIndicator {
  entity_id: number;
  code: string;
  name: string;
  sector: string;
  peer_group: string | null;
  findings: number;
  indicator: number;
}

export interface AnalyticsSummary {
  period_id: number;
  period_label: string;
  entities_assessed: number;
  findings_total: number;
  pending_reviews: number;
  high_priority: number;
  alerts_total: number;
  cases_total: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  entities: EntityIndicator[];
}

// ---------- Audit log ----------
export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  previous_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogResponse {
  total: number;
  limit: number;
  offset: number;
  items: AuditLogEntry[];
}

// ---------- API errors ----------
export interface ApiError {
  detail: string;
  status?: number;
}// ---------- List endpoints ----------
export interface EntityListItem {
  id: number;
  code: string;
  name: string;
  sector: string;
  sub_sector: string | null;
  region: string | null;
  criticality: string;
  peer_group: string | null;
  is_active: boolean;
  alerts: number;
  cases: number;
  findings: number;
  indicator: number;
}

export interface AlertListItem {
  id: number;
  entity_id: number;
  entity_code: string | null;
  external_id: string;
  title: string;
  severity: string;
  category: string;
  source_system: string | null;
  detected_at: string | null;
  acknowledged_at: string | null;
  closed_at: string | null;
  status: string;
}

export interface CaseListItem {
  id: number;
  entity_id: number;
  entity_code: string | null;
  external_id: string;
  title: string;
  severity: string;
  status: string;
  opened_at: string | null;
  closed_at: string | null;
  assigned_to: string | null;
}

export interface InvestigationListItem {
  id: number;
  entity_id: number;
  entity_code: string | null;
  case_id: number;
  investigator: string | null;
  started_at: string | null;
  ended_at: string | null;
  summary: string | null;
  artifacts_count: number;
  content_hash: string | null;
}

export interface ListResponse<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}// ---------- Batch ingestion ----------
export interface BatchFileIssue {
  row: number | null;
  severity: 'ERROR' | 'WARNING' | 'INFO';
  field: string | null;
  message: string;
}

export interface BatchFileReport {
  file_name: string;
  payload_type: string | null;
  detected_payload_type: string | null;
  format: string | null;
  records_received: number;
  records_valid: number;
  records_warning: number;
  records_error: number;
  inferred_by: string;
  error: string | null;
  suggested_mapping: Record<string, string | null> | null;
  issues: BatchFileIssue[];
  preview: Array<Record<string, unknown>>;
}

export interface BatchReport {
  entity_code: string;
  period_label: string;
  file_count: number;
  total_received: number;
  total_valid: number;
  total_warning: number;
  total_error: number;
  files: BatchFileReport[];
}

export interface BatchCommitResponse {
  submission_id: number;
  status: string;
  records_received: number;
  records_inserted: number;
  warnings: number;
  errors: number;
  by_payload: Record<string, number>;
}