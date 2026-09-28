import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Eye,
  GitCompare,
  ListChecks,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';

function LandingHeader() {
  return (
    <header className="border-b border-navy-800/80 bg-navy-950/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-10">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy-800 ring-1 ring-navy-700">
            <ShieldCheck className="h-4 w-4 text-white" strokeWidth={2.2} />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-tight text-white">SAT-SA</p>
            <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-400">
              Supervisory Analytics Tool for SOC Assessment
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          <a href="#about" className="text-[13px] font-medium text-slate-300 transition hover:text-white">About</a>
          <a href="#platform" className="text-[13px] font-medium text-slate-300 transition hover:text-white">Platform</a>
          <a href="#motto" className="text-[13px] font-medium text-slate-300 transition hover:text-white">Motto</a>
        </nav>

        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 rounded-md border border-navy-700 bg-navy-900 px-3.5 py-1.5 text-[13px] font-medium text-slate-100 transition hover:border-navy-600 hover:bg-navy-800"
        >
          Enter Platform
        </Link>
      </div>
    </header>
  );
}

function LandingVisual() {
  const findings = [
    { code: 'SAT-2026-0042', entity: 'POWER-B', category: 'Execution Gap', priority: 'High' },
    { code: 'SAT-2026-0061', entity: 'GRID-N', category: 'Negative Space', priority: 'High' },
    { code: 'SAT-2026-0078', entity: 'BANK-Y', category: 'Execution Gap', priority: 'Medium' },
    { code: 'SAT-2026-0104', entity: 'TELEC-C', category: 'Negative Space', priority: 'Medium' },
    { code: 'SAT-2026-0119', entity: 'BANK-A', category: 'Peer Deviation', priority: 'Low' },
  ];
  const indicatorBars = [
    { code: 'POWER-B', value: 87, tone: 'critical' as const },
    { code: 'GRID-N', value: 78, tone: 'critical' as const },
    { code: 'BANK-Y', value: 62, tone: 'warning' as const },
    { code: 'TELEC-C', value: 51, tone: 'warning' as const },
    { code: 'BANK-A', value: 34, tone: 'success' as const },
  ];
  const toneColor = (t: 'critical' | 'warning' | 'success') =>
    t === 'critical' ? '#dc2626' : t === 'warning' ? '#d97706' : '#16a34a';

  return (
    <div className="relative">
      <div aria-hidden className="pointer-events-none absolute -inset-8 rounded-[24px] bg-accent/5 blur-3xl" />
      <div className="relative rounded-xl border border-navy-800 bg-navy-900/70 p-2 shadow-2xl ring-1 ring-white/5">
        <div className="flex items-center gap-2 rounded-t-lg border-b border-navy-800 bg-navy-950/60 px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-slate-600" />
          <span className="h-2 w-2 rounded-full bg-slate-700" />
          <span className="h-2 w-2 rounded-full bg-slate-700" />
          <div className="ml-3 flex-1 rounded-md bg-navy-900/80 px-2 py-1">
            <p className="font-mono text-[10px] text-slate-500">sat-sa · supervisory overview · Q3-2026</p>
          </div>
        </div>
        <div className="rounded-b-lg bg-navy-950 p-4">
          <div className="mb-4 grid grid-cols-4 gap-2">
            {[
              { label: 'Entities', value: '9' },
              { label: 'Records', value: '2,830' },
              { label: 'Findings', value: '464' },
              { label: 'Pending', value: '441' },
            ].map((k) => (
              <div key={k.label} className="rounded-md border border-navy-800 bg-navy-900/60 px-3 py-2">
                <p className="text-[9px] font-medium uppercase tracking-wider text-slate-500">{k.label}</p>
                <p className="mt-0.5 text-base font-semibold tracking-tight text-white">{k.value}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-5 gap-2">
            <div className="col-span-3 rounded-md border border-navy-800 bg-navy-900/60">
              <div className="flex items-center justify-between border-b border-navy-800 px-3 py-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Findings requiring review</p>
                <span className="rounded-full bg-red-950/60 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider text-red-400 ring-1 ring-red-900/60">High priority</span>
              </div>
              <ul className="divide-y divide-navy-800/70">
                {findings.map((f) => (
                  <li key={f.code} className="flex items-center gap-2 px-3 py-2 text-[10px]">
                    <span className="font-mono text-slate-500">{f.code}</span>
                    <span className="text-slate-300">{f.entity}</span>
                    <span className="ml-auto truncate text-slate-400">{f.category}</span>
                    <span className={f.priority === 'High' ? 'text-red-400' : f.priority === 'Medium' ? 'text-amber-400' : 'text-emerald-400'}>{f.priority}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="col-span-2 rounded-md border border-navy-800 bg-navy-900/60">
              <div className="border-b border-navy-800 px-3 py-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Entity indicators</p>
              </div>
              <ul className="space-y-2 px-3 py-2.5">
                {indicatorBars.map((e) => (
                  <li key={e.code}>
                    <div className="mb-1 flex items-center justify-between text-[10px]">
                      <span className="font-mono text-slate-300">{e.code}</span>
                      <span className="font-mono text-slate-500">{e.value}</span>
                    </div>
                    <div className="h-1 overflow-hidden rounded-full bg-navy-800">
                      <div className="h-full rounded-full" style={{ width: `${e.value}%`, backgroundColor: toneColor(e.tone) }} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between rounded-md border border-navy-800 bg-navy-900/40 px-3 py-2">
            <p className="text-[10px] text-slate-400">Supervisor review · decisions recorded in audit trail</p>
            <div className="flex gap-1.5">
              <span className="rounded bg-emerald-950/60 px-1.5 py-0.5 text-[9px] font-medium text-emerald-400 ring-1 ring-emerald-900/60">Confirm</span>
              <span className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[9px] font-medium text-slate-300 ring-1 ring-slate-700/60">Review</span>
            </div>
          </div>
        </div>
      </div>
      <div aria-hidden className="mx-auto mt-3 h-2 w-32 rounded-b-lg bg-navy-800/60" />
    </div>
  );
}

function HeroSection() {
  return (
    <section id="about" className="relative overflow-hidden bg-navy-950">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'linear-gradient(#94a3b8 1px, transparent 1px), linear-gradient(90deg, #94a3b8 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />
      <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-14 px-6 py-20 lg:grid-cols-2 lg:gap-16 lg:px-10 lg:py-28">
        <div className="flex flex-col justify-center">
          <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-navy-800 bg-navy-900/60 px-3 py-1">
            <ShieldCheck className="h-3.5 w-3.5 text-accent-soft" strokeWidth={2.2} />
            <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-300">NTRO · NCIIPC</span>
          </div>
          <h1 className="text-4xl font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-[56px]">
            Smarter Oversight for a
            <br />
            <span className="text-accent-soft">Safer Digital India.</span>
          </h1>
          <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-slate-300">
            SAT-SA analyzes periodic SOC and case data from Critical Sector Entities to identify potential execution gaps, missing evidence, anomalies and peer deviations — helping supervisors focus where it matters most.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-white transition hover:bg-accent-deep"
            >
              Enter Platform
              <ArrowRight className="h-4 w-4" />
            </Link>
            <span className="text-xs text-slate-500">Runs locally · Offline · Air-gapped</span>
          </div>
          <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-navy-800/80 pt-5">
            {['Explainable analytics', 'Evidence traceability', 'Human-in-the-loop'].map((t) => (
              <div key={t} className="flex items-center gap-2">
                <span className="h-1 w-1 rounded-full bg-accent-soft" />
                <span className="text-[11px] uppercase tracking-wider text-slate-500">{t}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="relative flex items-center justify-center">
          <LandingVisual />
        </div>
      </div>
    </section>
  );
}

const CAPABILITIES = [
  { icon: AlertTriangle, title: 'Detects Execution Gaps', description: 'Identifies patterns that may require supervisory review.' },
  { icon: Eye, title: 'Finds Missing Evidence', description: 'Highlights expected evidence that is not observed.' },
  { icon: TrendingUp, title: 'Identifies Anomalies', description: 'Detects unusual operational patterns.' },
  { icon: GitCompare, title: 'Enables Peer Comparison', description: 'Compares operational indicators across selected entities.' },
  { icon: ListChecks, title: 'Prioritizes Review', description: 'Helps supervisors focus attention where it matters most.' },
];

function CapabilitySection() {
  return (
    <section id="platform" className="border-t border-navy-800/80 bg-navy-950 py-20 lg:py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-10">
        <div className="mb-14 max-w-2xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-accent-soft">Core capabilities</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">What SAT-SA does for supervisors.</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            Five analytical lenses applied to every CSE submission — each producing findings that are fully traceable to their source records.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-navy-800 bg-navy-800 sm:grid-cols-2 lg:grid-cols-5">
          {CAPABILITIES.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.title} className="bg-navy-950 p-6 transition hover:bg-navy-900/60">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy-900 ring-1 ring-navy-800">
                  <Icon className="h-4 w-4 text-accent-soft" strokeWidth={2} />
                </div>
                <p className="mt-4 text-sm font-semibold text-white">{c.title}</p>
                <p className="mt-2 text-[12px] leading-relaxed text-slate-400">{c.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function MottoSection() {
  return (
    <section id="motto" className="relative overflow-hidden border-t border-navy-800/80 bg-navy-950 py-24 lg:py-32">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-1/2 mx-auto h-64 max-w-3xl -translate-y-1/2 rounded-full bg-accent/5 blur-3xl" />
      <div className="relative mx-auto max-w-4xl px-6 text-center lg:px-10">
        <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-slate-500">Our motto</p>
        <h2 className="mt-6 text-4xl font-semibold leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
          Better Insights.
          <br />
          <span className="text-accent-soft">Safer Decisions.</span>
        </h2>
        <p className="mx-auto mt-7 max-w-xl text-[15px] leading-relaxed text-slate-400">
          From operational evidence to deeper supervisory insight.
        </p>
        <div className="mx-auto mt-14 max-w-2xl rounded-md border border-navy-800 bg-navy-900/40 px-6 py-6">
          <p className="text-[15px] font-medium leading-relaxed text-slate-200">
            Analytics identifies the signals.
            <br />
            <span className="text-white">Supervisors make the decisions.</span>
          </p>
          <p className="mt-3 text-[11px] uppercase tracking-wider text-slate-500">
            SAT-SA supports human supervisory judgment — it does not replace it.
          </p>
        </div>
      </div>
    </section>
  );
}

function LandingFooter() {
  return (
    <footer className="border-t border-navy-800/80 bg-navy-950">
      <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-6 py-10 md:flex-row md:items-center lg:px-10">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy-900 ring-1 ring-navy-800">
            <ShieldCheck className="h-4 w-4 text-slate-300" strokeWidth={2.2} />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-white">SAT-SA</p>
            <p className="text-[11px] uppercase tracking-wider text-slate-500">
              Supervisory Analytics Tool for SOC Assessment
            </p>
          </div>
        </div>
        <div className="flex flex-col gap-1 text-right">
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">NTRO · NCIIPC</p>
          <p className="text-[11px] uppercase tracking-wider text-slate-600">
            Smart India Hackathon 2026 · SIH26157
          </p>
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 antialiased">
      <LandingHeader />
      <HeroSection />
      <CapabilitySection />
      <MottoSection />
      <LandingFooter />
    </div>
  );
}