import { ArrowDown, Activity, AlertTriangle, GitCompare, Layers, ListChecks, ScanSearch, ShieldCheck, TrendingDown } from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';

interface Stage {
  title: string;
  icon: typeof Activity;
  input: string;
  process: string;
  output: string;
  why: string;
}

const stages: Stage[] = [
  {
    title: 'Local database',
    icon: Layers,
    input: 'Operational tables for one entity and one assessment period.',
    process: 'Loaded once per entity+period; shared across every analytic family.',
    output: 'In-memory dataset (alerts, cases, investigations, escalations, assets).',
    why: 'Every subsequent stage reads the same snapshot — no hidden re-fetching, no silent data drift.',
  },
  {
    title: 'Execution-gap detection',
    icon: ScanSearch,
    input: 'Alerts, cases, investigations, escalations, dispositions.',
    process: 'Rules EG-01… compare what happened against the expected workflow.',
    output: 'Findings describing specific execution gaps with observed vs expected.',
    why: 'Closure without investigation, unusual speed, missing escalation — the concrete “did the process run?” questions.',
  },
  {
    title: 'Negative-space detection',
    icon: TrendingDown,
    input: 'Asset inventory, historical baselines, peer baselines.',
    process: 'Rules NS-001… identify expected evidence that is absent, then classify it as submission-quality, evidence-gap, or supervisory.',
    output: 'Negative-space findings with an explicit classification.',
    why: 'Absence is not failure. The classification forces the tool to distinguish “the CSE did not send enough” from “a specific chain is broken”.',
  },
  {
    title: 'Anomaly detection',
    icon: AlertTriangle,
    input: 'Per-entity metric series.',
    process: 'Rule-based and statistical checks against thresholds, self-baselines, and cross-entity distributions.',
    output: 'Anomaly findings with the observed value, reference value, and deviation.',
    why: 'Identifies entities and cases that sit outside normal operating ranges without requiring black-box models.',
  },
  {
    title: 'Peer comparison',
    icon: GitCompare,
    input: 'Peer groups defined by sector and size band.',
    process: 'Median / p25 / p75 / robust z-score per metric, per peer group.',
    output: 'PeerComparison rows plus peer-deviation findings.',
    why: 'A figure only becomes meaningful when compared with entities in the same sector operating under similar constraints.',
  },
  {
    title: 'Supervisory indicators',
    icon: Activity,
    input: 'All findings for the entity+period.',
    process: 'Weighted combination per indicator (execution, negative space, investigation, escalation, completeness).',
    output: 'Entity-level and control-level indicator values with an explicit calculation.',
    why: 'Supervisors need a coarse-grained view alongside the detailed findings — but never an unexplained score.',
  },
  {
    title: 'Priority review',
    icon: ListChecks,
    input: 'Findings + indicators + peer context.',
    process: 'Ranking by severity, confidence, and supervisory-review weight.',
    output: 'A prioritised queue of records for human review.',
    why: 'Not everything can be reviewed. The tool’s job is to make sure the highest-signal items surface first.',
  },
  {
    title: 'Evidence & supervisor decision',
    icon: ShieldCheck,
    input: 'Findings + their evidence rows.',
    process: 'Supervisor confirms, rejects, or requests further review. Every decision is audited.',
    output: 'Decisions recorded, reports generated, audit log updated.',
    why: 'Analytics identifies the signals. Supervisors make the decisions. The final call is always human.',
  },
];

export default function AnalyticsFlowPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-heading">Analytics Flow</h1>
        <p className="page-subheading">
          How stored CSE evidence is turned into explainable, evidence-linked
          supervisory findings — and where the human decision happens.
        </p>
      </div>

      <div className="space-y-3">
        {stages.map((s, i) => (
          <div key={s.title} className="space-y-3">
            <Card>
              <div className="flex items-start gap-3">
                <div className="rounded-md bg-navy-800 p-2 text-white">
                  <s.icon className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <CardHeader title={s.title} subtitle={`Stage ${i + 1} of ${stages.length}`} />
                  <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <Field label="Input" value={s.input} />
                    <Field label="Process" value={s.process} />
                    <Field label="Output" value={s.output} />
                  </dl>
                  <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
                    <span className="font-medium text-slate-800 dark:text-slate-100">
                      Why it matters:{' '}
                    </span>
                    {s.why}
                  </p>
                </div>
              </div>
            </Card>
            {i < stages.length - 1 && (
              <div className="flex justify-center">
                <ArrowDown className="h-4 w-4 text-slate-400" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2 dark:border-navy-800 dark:bg-navy-950/40">
      <p className="font-mono text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-slate-700 dark:text-slate-200">
        {value}
      </p>
    </div>
  );
}