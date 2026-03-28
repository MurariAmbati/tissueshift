import { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';
import AnimatedCounter from '../components/AnimatedCounter';

/* ── Sample clinical trials ──────────────────────────────────── */
const TRIALS = [
  {
    id: 'NCT05012345', phase: 'Phase III', status: 'Recruiting',
    title: 'Trastuzumab Deruxtecan vs T-DM1 in HER2+ Metastatic Breast Cancer',
    sponsor: 'Daiichi Sankyo / AstraZeneca', pi: 'Dr. S. Modi',
    matchScore: 96, matchReasons: ['HER2+ confirmed (IHC 3+)', 'Prior taxane therapy', 'ECOG 0-1', 'No brain mets'],
    exclusions: [],
    arms: ['T-DXd 5.4mg/kg q3w', 'T-DM1 3.6mg/kg q3w'],
    primaryEndpoint: 'Progression-Free Survival',
    enrollment: { current: 412, target: 500 },
    locations: ['Memorial Sloan Kettering', 'MD Anderson', 'Dana-Farber'],
    biomarkers: ['ERBB2 amp', 'ESR1+', 'PIK3CA wt'],
    distance: '2.3 mi',
  },
  {
    id: 'NCT05098765', phase: 'Phase II', status: 'Recruiting',
    title: 'Sacituzumab Govitecan + Pembrolizumab in Triple-Negative Breast Cancer',
    sponsor: 'Gilead Sciences', pi: 'Dr. A. Bardia',
    matchScore: 89, matchReasons: ['TNBC subtype confirmed', 'PD-L1 CPS ≥ 10', '1-2 prior lines'],
    exclusions: ['Patient has HER2+ status — may conflict'],
    arms: ['SG 10mg/kg + Pembro 200mg', 'SG monotherapy'],
    primaryEndpoint: 'Objective Response Rate',
    enrollment: { current: 178, target: 300 },
    locations: ['Dana-Farber', 'Johns Hopkins', 'UCLA'],
    biomarkers: ['TROP2 high', 'PD-L1 CPS≥10', 'BRCA1 wt'],
    distance: '5.1 mi',
  },
  {
    id: 'NCT05045678', phase: 'Phase I/II', status: 'Enrolling by Invitation',
    title: 'Capivasertib + Fulvestrant in PIK3CA-mutated HR+/HER2- Advanced BC',
    sponsor: 'AstraZeneca', pi: 'Dr. F. André',
    matchScore: 82, matchReasons: ['PIK3CA mutation detected', 'HR+/HER2- confirmed', 'Post-CDK4/6i'],
    exclusions: ['Patient is HER2+ — arm mismatch'],
    arms: ['Capivasertib 400mg BID + Fulvestrant', 'Placebo + Fulvestrant'],
    primaryEndpoint: 'PFS (investigator assessed)',
    enrollment: { current: 220, target: 350 },
    locations: ['Gustave Roussy', 'Royal Marsden', 'MD Anderson'],
    biomarkers: ['PIK3CA H1047R', 'ESR1+', 'AKT1 wt'],
    distance: '14.7 mi',
  },
  {
    id: 'NCT05067890', phase: 'Phase III', status: 'Active, not recruiting',
    title: 'Olaparib + Durvalumab in BRCA-mutated Early Breast Cancer',
    sponsor: 'AstraZeneca', pi: 'Dr. N. Turner',
    matchScore: 65, matchReasons: ['Female', 'Early stage eligible', 'No prior PARP inhibitor'],
    exclusions: ['BRCA mutation not detected', 'Study no longer recruiting'],
    arms: ['Olaparib 300mg BID + Durvalumab', 'Placebo'],
    primaryEndpoint: 'Invasive Disease-Free Survival',
    enrollment: { current: 1280, target: 1300 },
    locations: ['Royal Marsden', 'Charité Berlin', 'Gustave Roussy'],
    biomarkers: ['BRCA1/2 germline mut', 'HRD+'],
    distance: '3,241 mi',
  },
  {
    id: 'NCT05023456', phase: 'Phase II', status: 'Recruiting',
    title: 'Datopotamab Deruxtecan in HR+/HER2-low Breast Cancer',
    sponsor: 'Daiichi Sankyo', pi: 'Dr. K. Jhaveri',
    matchScore: 74, matchReasons: ['HR+ confirmed', 'HER2-low (IHC 1+)', '≤3 prior therapies'],
    exclusions: ['HER2 3+ status — requires HER2-low'],
    arms: ['Dato-DXd 6mg/kg q3w'],
    primaryEndpoint: 'ORR by BICR',
    enrollment: { current: 95, target: 150 },
    locations: ['Memorial Sloan Kettering', 'Northwestern', 'Cedars-Sinai'],
    biomarkers: ['TROP2 medium', 'HER2 IHC 1+'],
    distance: '8.2 mi',
  },
];

function MatchBadge({ score }) {
  const color = score >= 90 ? 'emerald' : score >= 75 ? 'violet' : score >= 60 ? 'amber' : 'gray';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-${color}-500/15 text-${color}-600 dark:text-${color}-400`}>
      {score}% match
    </span>
  );
}

function PhaseBadge({ phase }) {
  const colors = { 'Phase I': 'sky', 'Phase I/II': 'sky', 'Phase II': 'violet', 'Phase III': 'emerald' };
  const c = colors[phase] || 'gray';
  return <span className={`px-2 py-0.5 rounded text-[10px] font-bold bg-${c}-500/15 text-${c}-600 dark:text-${c}-400`}>{phase}</span>;
}

export default function TrialMatcher() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selected, setSelected] = useState(TRIALS[0]);
  const [minScore, setMinScore] = useState(0);

  const filtered = TRIALS.filter(t => t.matchScore >= minScore).sort((a, b) => b.matchScore - a.matchScore);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
              <div>
                <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                  Clinical Trial Matcher
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">AI-powered trial eligibility engine — matching patient molecular profile to active studies</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">Min match:</span>
                <input
                  type="range" min={0} max={95} step={5} value={minScore}
                  onChange={e => setMinScore(+e.target.value)}
                  className="w-28 accent-emerald-500"
                />
                <span className="text-xs font-bold text-emerald-500 tabular-nums w-8">{minScore}%</span>
              </div>
            </div>

            {/* Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <GlowCard glowColor="emerald" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Matched Trials</div>
                <div className="text-2xl font-extrabold text-gray-800 dark:text-white"><AnimatedCounter end={filtered.length} /></div>
              </GlowCard>
              <GlowCard glowColor="violet" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Top Match</div>
                <div className="text-2xl font-extrabold text-emerald-500"><AnimatedCounter end={filtered[0]?.matchScore || 0} suffix="%" /></div>
              </GlowCard>
              <GlowCard glowColor="sky" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Recruiting Now</div>
                <div className="text-2xl font-extrabold text-gray-800 dark:text-white"><AnimatedCounter end={filtered.filter(t => t.status === 'Recruiting').length} /></div>
              </GlowCard>
              <GlowCard glowColor="amber" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Nearest Site</div>
                <div className="text-lg font-extrabold text-gray-800 dark:text-white">{filtered[0]?.distance || '—'}</div>
              </GlowCard>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Trial list */}
              <div className="xl:col-span-2 space-y-3">
                {filtered.map(trial => (
                  <button
                    key={trial.id}
                    onClick={() => setSelected(trial)}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      selected?.id === trial.id
                        ? 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-400 dark:border-emerald-500 shadow-lg shadow-emerald-500/10'
                        : 'bg-white dark:bg-gray-800/50 border-gray-200 dark:border-gray-700/60 hover:border-emerald-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <PhaseBadge phase={trial.phase} />
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                            trial.status === 'Recruiting' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                              : trial.status === 'Enrolling by Invitation' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                              : 'bg-gray-500/10 text-gray-500'
                          }`}>{trial.status}</span>
                        </div>
                        <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mt-1.5 leading-snug">{trial.title}</h3>
                        <p className="text-[10px] text-gray-400 mt-0.5">{trial.id} · {trial.sponsor}</p>
                      </div>
                      <MatchBadge score={trial.matchScore} />
                    </div>

                    {/* Match reasons */}
                    <div className="flex gap-1 flex-wrap mt-2">
                      {trial.matchReasons.map(r => (
                        <span key={r} className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">✓ {r}</span>
                      ))}
                      {trial.exclusions.map(r => (
                        <span key={r} className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400">✗ {r}</span>
                      ))}
                    </div>

                    {/* Enrollment bar */}
                    <div className="mt-3">
                      <div className="flex justify-between mb-0.5">
                        <span className="text-[10px] text-gray-400">Enrollment</span>
                        <span className="text-[10px] text-gray-400">{trial.enrollment.current}/{trial.enrollment.target}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                        <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${(trial.enrollment.current / trial.enrollment.target) * 100}%` }} />
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* Detail panel */}
              <div className="space-y-4">
                {selected && (
                  <>
                    <GlowCard glowColor="emerald" className="!p-4">
                      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-1">{selected.title}</h3>
                      <p className="text-xs text-gray-400 mb-3">{selected.id} · PI: {selected.pi}</p>

                      <div className="grid grid-cols-2 gap-2 mb-4">
                        <div className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                          <div className="text-[10px] text-gray-400">Match Score</div>
                          <div className={`text-lg font-extrabold ${selected.matchScore >= 90 ? 'text-emerald-500' : selected.matchScore >= 75 ? 'text-violet-500' : 'text-amber-500'}`}>{selected.matchScore}%</div>
                        </div>
                        <div className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                          <div className="text-[10px] text-gray-400">Nearest Site</div>
                          <div className="text-lg font-extrabold text-gray-800 dark:text-white">{selected.distance}</div>
                        </div>
                      </div>

                      <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1.5">Treatment Arms</h4>
                      <div className="space-y-1 mb-3">
                        {selected.arms.map((a, i) => (
                          <div key={a} className="text-xs p-2 bg-violet-500/5 rounded-lg text-gray-700 dark:text-gray-300">
                            <span className="text-violet-500 font-bold mr-1">Arm {i + 1}:</span>{a}
                          </div>
                        ))}
                      </div>

                      <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1.5">Primary Endpoint</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-300 mb-3">{selected.primaryEndpoint}</p>

                      <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1.5">Required Biomarkers</h4>
                      <div className="flex gap-1 flex-wrap mb-3">
                        {selected.biomarkers.map(b => (
                          <span key={b} className="text-[10px] px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-600 dark:text-sky-400 font-mono">{b}</span>
                        ))}
                      </div>

                      <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1.5">Active Sites</h4>
                      <div className="space-y-1">
                        {selected.locations.map(l => (
                          <div key={l} className="text-xs text-gray-600 dark:text-gray-300 flex items-center gap-1">
                            <span className="text-gray-500">•</span> {l}
                          </div>
                        ))}
                      </div>
                    </GlowCard>
                  </>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
