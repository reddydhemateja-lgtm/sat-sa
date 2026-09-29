import { ArrowDown, Database, FileJson, HardDrive, Send, ShieldCheck } from 'lucide-react';

import Card, { CardHeader } from '../components/ui/Card';

interface Stage {
  title: string;
  icon: typeof Database;
  input: string;
  process: string;
  output: string;
  why: string;
}

const stages: Stage[] = [
  {
    title: 'CSE Entity',
    icon: ShieldCheck,
    input: 'Critical Sector Entity with an obligation to submit periodic SOC evidence.',
    process: 'Prepares the periodic submission — alerts, cases, investigations, escalations, dispositions, asset inventory.',
    output: 'One or more submission files / exports.',
    why: 'The whole supervisory picture is built from what each CSE actually sends, not from anything SAT-SA collects itself.',
  },
  {
    title: 'Submission channel',
    icon: Send,
    input: 'Files or connectors offered by the CSE.',
    process: 'CSV / JSON / XLSX upload, database export (.sqlite/.db/.parquet), or periodic API pull.',
    output: 'Raw bytes handed to the ingestion pipeline.',
    why: 'Multiple channels keep the tool usable regardless of how each CSE operates its SOC tooling.',
  },
  {
    title: 'Ingestion',
    icon: FileJson,
    input: 'Raw bytes + declared payload type + target entity + period.',
    process: 'detect_format → read_file → column mapping → canonical DataFrame.',
    output: 'Uniform records ready for validation.',
    why: 'Normalising here means every downstream analytic sees the same shape regardless of source.',
  },
  {
    title: 'Validation',
    icon: ShieldCheck,
    input: 'Canonical DataFrame.',
    process: 'Required-field checks, enum checks, datetime parsing, duplicate detection, cross-entity code checks.',
    output: 'Clean rows + a ValidationSummary (received / valid / warnings / errors / issues).',
    why: 'Findings must never be driven by malformed data. Errors are rejected; warnings are surfaced to the supervisor.',
  },
  {
    title: 'Local database',
    icon: HardDrive,
    input: 'Clean rows + a DataSubmission row recording file, version, uploader, status.',
    process: 'Transactional insert into operational tables. Re-uploading the same file bumps the version, it does not overwrite.',
    output: 'Persisted operational evidence, versioned and traceable.',
    why: 'Findings must always be traceable to a specific submitted record. Versioning preserves history for supervisory comparison.',
  },
  {
    title: 'Analytics',
    icon: Database,
    input: 'Operational tables for the current assessment period.',
    process: 'Execution-gap rules, negative-space rules, anomaly detection, peer comparison, prioritisation.',
    output: 'FindingDraft objects, later persisted as Findings with Evidence links.',
    why: 'This is where raw operational records become reviewable supervisory indicators — nothing leaves this stage without evidence.',
  },
];

export default function DataFlowPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-heading">Data Flow</h1>
        <p className="page-subheading">
          How submitted CSE evidence reaches the local database, and how it is
          kept versioned, validated, and traceable.
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