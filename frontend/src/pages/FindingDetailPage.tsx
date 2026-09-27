import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  MessageSquarePlus,
  RotateCcw,
  XCircle,
} from 'lucide-react';

import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card, { CardHeader } from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import { useFinding, useSubmitReview } from '../hooks/useFindings';
import {
  categoryTone,
  formatDateTime,
  humanizeCategory,
  priorityTone,
} from '../utils/format';

type DecisionType = 'CONFIRMED' | 'REJECTED' | 'FURTHER_REVIEW';

export default function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const findingId = id ? Number(id) : null;
  const { data, isLoading, isError } = useFinding(findingId);
  const submit = useSubmitReview();

  const [comment, setComment] = useState('');
  const [pendingDecision, setPendingDecision] = useState<DecisionType | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <EmptyState
          title="Finding not found"
          description="It may have been removed by a re-run of analytics."
          action={
            <Link to="/findings">
              <Button variant="secondary" leftIcon={<ArrowLeft className="h-3.5 w-3.5" />}>
                Back to Findings
              </Button>
            </Link>
          }
        />
      </Card>
    );
  }

  const f = data.finding;

  const handleDecide = async (decision: DecisionType) => {
    setPendingDecision(decision);
    try {
      await submit.mutateAsync({
        findingId: f.id,
        decision,
        comment: comment.trim() || null,
      });
      setComment('');
    } finally {
      setPendingDecision(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Link
            to="/findings"
            className="mt-1 rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-navy-800"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <p className="font-mono text-xs text-slate-500 dark:text-slate-400">
              Finding {f.code}
            </p>
            <h1 className="page-heading mt-0.5">{f.title}</h1>
            <p className="page-subheading">{f.analytical_basis}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={categoryTone(f.category)}>{humanizeCategory(f.category)}</Badge>
          <Badge tone={priorityTone(f.priority)}>{f.priority}</Badge>
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
        </div>
      </div>

      {/* WHAT / WHY / EVIDENCE grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="What was detected" subtitle="Narrative" />
          <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">
            {f.narrative}
          </p>

          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="section-heading">Expected behaviour</p>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
                {f.expected_behavior ?? '—'}
              </p>
            </div>
            <div>
              <p className="section-heading">Observed pattern</p>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
                {f.observed_pattern ?? '—'}
              </p>
            </div>
          </div>

          <div className="mt-5">
            <p className="section-heading">Analytical basis</p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
              {f.analytical_basis}
            </p>
          </div>

          {f.metrics && Object.keys(f.metrics).length > 0 && (
            <div className="mt-5">
              <p className="section-heading">Metrics</p>
              <dl className="mt-2 grid grid-cols-2 gap-3 text-xs">
                {Object.entries(f.metrics).map(([k, v]) => (
                  <div
                    key={k}
                    className="rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2 dark:border-navy-800 dark:bg-navy-950/40"
                  >
                    <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      {k}
                    </dt>
                    <dd className="mt-0.5 font-mono text-slate-800 dark:text-slate-100">
                      {String(v)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Entity" subtitle="CSE context" />
          {data.entity ? (
            <dl className="space-y-2 text-sm">
              <Row label="Code" value={data.entity.code} mono />
              <Row label="Name" value={data.entity.name} />
              <Row label="Sector" value={data.entity.sector} />
              <Row label="Criticality" value={data.entity.criticality} />
              <Row label="Peer group" value={data.entity.peer_group ?? '—'} />
            </dl>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">—</p>
          )}

          <div className="mt-5 space-y-2 text-sm">
            <Row label="Rule" value={f.rule_id} mono />
            <Row label="Confidence" value={`${(f.confidence * 100).toFixed(0)}%`} />
            <Row
              label="Review indicator"
              value={f.review_indicator.toFixed(1)}
            />
            <Row label="Detected" value={formatDateTime(f.created_at)} />
          </div>
        </Card>
      </div>

      {/* Evidence */}
      <Card padded={false}>
        <div className="border-b border-slate-200 px-5 py-4 dark:border-navy-800">
          <CardHeader
            title="Supporting evidence"
            subtitle={`${data.evidence.length} record${data.evidence.length === 1 ? '' : 's'} link this finding to the underlying data`}
          />
        </div>
        {data.evidence.length === 0 ? (
          <div className="px-5 py-6">
            <EmptyState
              title="No evidence rows attached"
              description="This finding was produced from aggregate metrics."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/60 text-[11px] uppercase tracking-wider text-slate-500 dark:border-navy-800 dark:bg-navy-950/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Record type</th>
                  <th className="px-4 py-2.5 font-medium">Record id</th>
                  <th className="px-4 py-2.5 font-medium">Snippet</th>
                  <th className="px-4 py-2.5 text-right font-medium">Weight</th>
                </tr>
              </thead>
              <tbody>
                {data.evidence.map((ev) => (
                  <tr
                    key={ev.id}
                    className="border-b border-slate-100 last:border-b-0 dark:border-navy-800"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-300">
                      {ev.record_type}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-300">
                      #{ev.record_id}
                    </td>
                    <td className="px-4 py-2.5 text-slate-700 dark:text-slate-200">
                      {ev.snippet ?? '—'}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-500 dark:text-slate-400">
                      {ev.weight.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Supervisor decision */}
      <Card>
        <CardHeader
          title="Supervisor decision"
          subtitle="Confirm, reject, or request further review. Every decision is recorded in the audit log."
        />

        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a comment (optional) — rationale, context, or request details."
          rows={3}
          className="input-base mb-4 resize-y"
        />

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            leftIcon={<CheckCircle2 className="h-3.5 w-3.5" />}
            onClick={() => handleDecide('CONFIRMED')}
            loading={pendingDecision === 'CONFIRMED'}
            disabled={submit.isPending}
          >
            Confirm Finding
          </Button>
          <Button
            variant="danger"
            leftIcon={<XCircle className="h-3.5 w-3.5" />}
            onClick={() => handleDecide('REJECTED')}
            loading={pendingDecision === 'REJECTED'}
            disabled={submit.isPending}
          >
            Reject
          </Button>
          <Button
            variant="secondary"
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            onClick={() => handleDecide('FURTHER_REVIEW')}
            loading={pendingDecision === 'FURTHER_REVIEW'}
            disabled={submit.isPending}
          >
            Request Further Review
          </Button>
        </div>

        {data.review_decisions.length > 0 && (
          <div className="mt-6 border-t border-slate-200 pt-4 dark:border-navy-800">
            <p className="section-heading mb-3">Decision history</p>
            <ul className="space-y-2">
              {data.review_decisions.map((d) => (
                <li
                  key={d.id}
                  className="flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2 text-sm dark:border-navy-800 dark:bg-navy-950/40"
                >
                  <MessageSquarePlus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        tone={
                          d.decision === 'CONFIRMED'
                            ? 'critical'
                            : d.decision === 'REJECTED'
                              ? 'success'
                              : 'warning'
                        }
                      >
                        {d.decision}
                      </Badge>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {formatDateTime(d.decided_at)}
                      </span>
                      {d.previous_decision && (
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          (was {d.previous_decision})
                        </span>
                      )}
                    </div>
                    {d.comment && (
                      <p className="mt-1 text-slate-700 dark:text-slate-200">
                        {d.comment}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </dt>
      <dd
        className={
          mono
            ? 'font-mono text-xs text-slate-800 dark:text-slate-100'
            : 'text-sm text-slate-800 dark:text-slate-100'
        }
      >
        {value}
      </dd>
    </div>
  );
}