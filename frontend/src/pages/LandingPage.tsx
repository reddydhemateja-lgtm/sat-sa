import { useNavigate } from 'react-router-dom';
import { ArrowRight, Activity, AlertTriangle, GitCompare, ShieldCheck, TrendingUp } from 'lucide-react';

const FEATURES = [
  {
    icon: AlertTriangle,
    title: 'Execution Gaps',
    description: 'Critical alerts closed unusually fast, missing escalation evidence, template investigations.',
  },
  {
    icon: Activity,
    title: 'Negative Space',
    description: 'Expected evidence that is missing from submissions — blind spots, absent categories, missing follow-up.',
  },
  {
    icon: TrendingUp,
    title: 'Anomalies',
    description: 'Statistically unusual activity vs the entity\'s own historical baseline.',
  },
  {
    icon: GitCompare,
    title: 'Peer Deviation',
    description: 'Normalised indicators compared within configured peer groups.',
  },
];

export default function IntroPage() {
  const navigate = useNavigate();

  const enter = () => {
    // Remember that the intro was seen — only show it once per browser session
    try {
      sessionStorage.setItem('sat-sa-intro-seen', '1');
    } catch {
      // ignore
    }
    navigate('/dashboard', { replace: true });
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-navy-950">
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-3xl">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-md bg-navy-800 text-white">
              <ShieldCheck className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white">
                SAT-SA
              </p>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500 dark:text-slate-400">
                Supervisory Analytics Tool for SOC Assessment
              </p>
            </div>
          </div>

          {/* Headline */}
          <div className="mt-12">
            <h1 className="text-3xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-4xl dark:text-white">
              Identify operational patterns that may require supervisory attention.
            </h1>
            <p className="mt-5 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">
              SAT-SA analyses periodic SOC operational evidence from Critical Sector
              Entities — detecting execution gaps, missing evidence, anomalies, and
              peer deviations. Every finding is traceable to the underlying alert,
              case, or investigation record.
            </p>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">
              The tool supports human supervisors. Final supervisory decisions remain
              with the supervisor.
            </p>
          </div>

          {/* Metric strip */}
          <div className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-slate-200 bg-slate-200 sm:grid-cols-4 dark:border-navy-800 dark:bg-navy-800">
            {[
              { value: '16', label: 'Analytics rules' },
              { value: '9', label: 'CSE entities' },
              { value: '4', label: 'Detection modules' },
              { value: '100%', label: 'Offline' },
            ].map((s) => (
              <div
                key={s.label}
                className="bg-white px-4 py-3 dark:bg-navy-900"
              >
                <p className="text-lg font-semibold tracking-tight text-slate-900 dark:text-white">
                  {s.value}
                </p>
                <p className="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  {s.label}
                </p>
              </div>
            ))}
          </div>

          {/* Feature grid */}
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="rounded-md border border-slate-200 bg-white p-4 dark:border-navy-800 dark:bg-navy-900"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-600 dark:bg-navy-800 dark:text-slate-300">
                      <Icon className="h-4 w-4" strokeWidth={2} />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">
                        {f.title}
                      </p>
                      <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                        {f.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* CTA */}
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={enter}
              className="inline-flex items-center gap-2 rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-deep"
            >
              Enter Supervisory Workspace
              <ArrowRight className="h-4 w-4" />
            </button>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              No credentials required — this is a demonstration environment.
            </p>
          </div>

          {/* Footer */}
          <div className="mt-12 border-t border-slate-200 pt-5 dark:border-navy-800">
            <p className="text-[11px] uppercase tracking-widest text-slate-400 dark:text-slate-500">
              NTRO / NCIIPC · Smart India Hackathon 2026 · SIH26157
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}