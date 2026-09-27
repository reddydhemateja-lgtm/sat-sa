import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  fetchAnalyticsSummary,
  fetchAuditLog,
  fetchFinding,
  fetchFindings,
  fetchReviewQueue,
  runAnalytics,
  submitReview,
  type FindingsFilters,
} from '../services/analytics';

export const findingsKeys = {
  list: (filters: FindingsFilters) => ['findings', 'list', filters] as const,
  detail: (id: number) => ['findings', 'detail', id] as const,
  reviewQueue: (periodId: number, includeDecided: boolean) =>
    ['review-queue', periodId, includeDecided] as const,
  auditLog: (params: Record<string, unknown>) => ['audit-log', params] as const,
  analyticsSummary: (periodId: number) => ['analytics', 'summary', periodId] as const,
};

export function useFindings(filters: FindingsFilters) {
  return useQuery({
    queryKey: findingsKeys.list(filters),
    queryFn: () => fetchFindings(filters),
    staleTime: 10_000,
  });
}

export function useFinding(id: number | null) {
  return useQuery({
    queryKey: findingsKeys.detail(id ?? 0),
    queryFn: () => fetchFinding(id as number),
    enabled: id !== null && id > 0,
  });
}

export function useReviewQueue(periodId: number, includeDecided = false) {
  return useQuery({
    queryKey: findingsKeys.reviewQueue(periodId, includeDecided),
    queryFn: () => fetchReviewQueue(periodId, includeDecided),
    staleTime: 10_000,
  });
}

export function useAnalyticsSummary(periodId: number) {
  return useQuery({
    queryKey: findingsKeys.analyticsSummary(periodId),
    queryFn: () => fetchAnalyticsSummary(periodId),
    staleTime: 30_000,
  });
}

export function useAuditLog(params: {
  action?: string;
  target_type?: string;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: findingsKeys.auditLog(params),
    queryFn: () => fetchAuditLog(params),
    staleTime: 10_000,
  });
}

export function useSubmitReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      findingId: number;
      decision: 'CONFIRMED' | 'REJECTED' | 'FURTHER_REVIEW';
      comment?: string | null;
    }) => submitReview(input.findingId, input.decision, input.comment),
    onSuccess: () => {
      // invalidate everything that a decision affects
      qc.invalidateQueries({ queryKey: ['findings'] });
      qc.invalidateQueries({ queryKey: ['review-queue'] });
      qc.invalidateQueries({ queryKey: ['audit-log'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

export function useRunAnalytics() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (periodId: number) => runAnalytics(periodId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['findings'] });
      qc.invalidateQueries({ queryKey: ['review-queue'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}import {
  fetchAlerts,
  fetchCases,
  fetchEntities,
  fetchInvestigations,
} from '../services/analytics';

export function useEntities(periodId?: number) {
  return useQuery({
    queryKey: ['entities', periodId ?? 'all'],
    queryFn: () => fetchEntities(periodId),
    staleTime: 15_000,
  });
}

export function useAlerts(params: {
  entity_id?: number;
  period_id?: number;
  severity?: string;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: ['alerts', params],
    queryFn: () => fetchAlerts(params),
    staleTime: 10_000,
  });
}

export function useCases(params: {
  entity_id?: number;
  period_id?: number;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: ['cases', params],
    queryFn: () => fetchCases(params),
    staleTime: 10_000,
  });
}

export function useInvestigations(params: {
  entity_id?: number;
  period_id?: number;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: ['investigations', params],
    queryFn: () => fetchInvestigations(params),
    staleTime: 10_000,
  });
}import { commitBatch, scanBatch } from '../services/analytics';
import type { BatchCommitResponse, BatchReport } from '../types';

export function useScanBatch() {
  return useMutation<
    BatchReport,
    Error,
    { files: File[]; entityId: number; periodId: number }
  >({
    mutationFn: ({ files, entityId, periodId }) =>
      scanBatch(files, entityId, periodId),
  });
}

export function useCommitBatch() {
  const qc = useQueryClient();
  return useMutation<
    BatchCommitResponse,
    Error,
    { files: File[]; entityId: number; periodId: number }
  >({
    mutationFn: ({ files, entityId, periodId }) =>
      commitBatch(files, entityId, periodId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
      qc.invalidateQueries({ queryKey: ['cases'] });
      qc.invalidateQueries({ queryKey: ['investigations'] });
      qc.invalidateQueries({ queryKey: ['findings'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}