import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import ParticleField from '../components/ParticleField';
import GlowCard from '../components/GlowCard';
import AnimatedCounter from '../components/AnimatedCounter';
import PulseRing from '../components/PulseRing';
import Sparkline from '../components/Sparkline';

/* ── fake real-time data generator ─────────────────────────────── */
const sparkData = () => Array.from({ length: 20 }, () => Math.random() * 40 + 60);

export default function CommandCenter() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [time, setTime] = useState(new Date());
  const [alertFeed, setAlertFeed] = useState([
    { id: 1, level: 'critical', msg: 'High-risk basal-like detected — P-2846', ts: '2 min ago' },
    { id: 2, level: 'warning', msg: 'Federated round #42 — Charité site offline', ts: '8 min ago' },
    { id: 3, level: 'info', msg: 'Model v2.1 calibration verified (ECE 0.018)', ts: '14 min ago' },
    { id: 4, level: 'info', msg: 'Batch analysis complete — 24 slides processed', ts: '21 min ago' },
    { id: 5, level: 'warning', msg: 'Ki-67 outlier detected in cohort C-0419', ts: '35 min ago' },
  ]);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const kpis = [
    { label: 'Active Patients', value: 2847, prefix: '', suffix: '', decimals: 0, glow: 'violet', trend: sparkData(), color: '#8b5cf6' },
    { label: 'Slides Today', value: 142, prefix: '', suffix: '', decimals: 0, glow: 'sky', trend: sparkData(), color: '#0ea5e9' },
    { label: 'Model Accuracy', value: 94.2, prefix: '', suffix: '%', decimals: 1, glow: 'emerald', trend: sparkData(), color: '#10b981' },
    { label: 'Digital Twins', value: 1893, prefix: '', suffix: '', decimals: 0, glow: 'teal', trend: sparkData(), color: '#14b8a6' },
    { label: 'Federated Sites', value: 5, prefix: '', suffix: ' active', decimals: 0, glow: 'indigo', trend: sparkData(), color: '#6366f1' },
    { label: 'Reports Generated', value: 8412, prefix: '', suffix: '', decimals: 0, glow: 'amber', trend: sparkData(), color: '#f59e0b' },
  ];

  const systems = [
    { name: 'World Model v2.1', status: 'online', latency: '12ms', load: 34 },
    { name: 'Neural ODE Engine', status: 'online', latency: '28ms', load: 67 },
    { name: 'Knowledge Graph DB', status: 'online', latency: '5ms', load: 22 },
    { name: 'Federated Hub', status: 'degraded', latency: '142ms', load: 89 },
    { name: 'Uncertainty Quantifier', status: 'online', latency: '8ms', load: 41 },
    { name: 'Report Generator', status: 'online', latency: '35ms', load: 28 },
    { name: 'Spatial Omics Pipeline', status: 'online', latency: '19ms', load: 53 },
    { name: 'Causal Inference Engine', status: 'online', latency: '45ms', load: 45 },
  ];

  const pipeline = [
    { step: 'Biopsy Intake', done: 2847, active: 3, color: 'violet' },
    { step: 'Slide Digitization', done: 18392, active: 12, color: 'sky' },
    { step: 'AI Inference', done: 18104, active: 8, color: 'indigo' },
    { step: 'Uncertainty Check', done: 17980, active: 2, color: 'teal' },
    { step: 'Report Generation', done: 8412, active: 5, color: 'emerald' },
    { step: 'Clinical Review', done: 7891, active: 14, color: 'amber' },
  ];

  const levelColor = { critical: 'rose', warning: 'amber', info: 'sky' };

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-gray-50 dark:bg-gray-950">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        {/* Particle backdrop */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <ParticleField color="139,92,246" count={45} />
        </div>

        <main className="grow relative z-10">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">

            {/* Header bar */}
            <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
              <div>
                <h1 className="text-3xl md:text-4xl font-bold text-gray-800 dark:text-gray-100">
                  Command Center
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  TissueShift Clinical AI — Real-time Ecosystem Overview
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-mono font-bold text-gray-800 dark:text-gray-100 tabular-nums">
                  {time.toLocaleTimeString()}
                </div>
                <div className="text-xs text-gray-400">{time.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
              </div>
            </div>

            {/* ── KPI Strip ───────────────────────────────────────── */}
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
              {kpis.map((k) => (
                <GlowCard key={k.label} glowColor={k.glow} className="flex flex-col gap-2 !p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{k.label}</span>
                  </div>
                  <div className="text-2xl font-extrabold text-gray-900 dark:text-white">
                    <AnimatedCounter value={k.value} decimals={k.decimals} prefix={k.prefix} suffix={k.suffix} duration={1800} />
                  </div>
                  <Sparkline data={k.trend} color={k.color} width={120} height={24} />
                </GlowCard>
              ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">

              {/* ── Clinical Pipeline ─────────────────────────────── */}
              <GlowCard glowColor="violet" className="xl:col-span-2 !p-5">
                <h2 className="text-base font-bold text-gray-800 dark:text-gray-100 mb-4">Clinical Processing Pipeline</h2>
                <div className="relative flex items-center justify-between gap-2">
                  {pipeline.map((p, i) => (
                    <div key={p.step} className="flex-1 relative text-center">
                      {/* connector line */}
                      {i > 0 && (
                        <div className="absolute top-5 -left-1/2 w-full h-0.5">
                          <div className="h-full bg-violet-300/40 dark:bg-violet-500/30 rounded-full" />
                          {/* animated dot */}
                          <div className="absolute top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-violet-400 animate-pulse" style={{ left: `${50 + Math.sin(Date.now() / 600 + i) * 30}%` }} />
                        </div>
                      )}
                      <div className="relative z-10 mx-auto w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-500/20 flex items-center justify-center text-sm font-bold text-violet-600 dark:text-violet-300 mb-2">
                        {i + 1}
                      </div>
                      <div className="text-xs font-semibold text-gray-700 dark:text-gray-300">{p.step}</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">
                        <span className="font-bold text-gray-600 dark:text-gray-200">{p.done.toLocaleString()}</span> done
                      </div>
                      {p.active > 0 && (
                        <div className="mt-1">
                          <PulseRing color="emerald" size="sm" label={`${p.active} active`} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </GlowCard>

              {/* ── Live Alert Feed ────────────────────────────────── */}
              <GlowCard glowColor="rose" className="!p-5">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-bold text-gray-800 dark:text-gray-100">Live Alerts</h2>
                  <PulseRing color="rose" size="sm" label="Live" />
                </div>
                <div className="space-y-3 max-h-56 overflow-y-auto pr-1 no-scrollbar">
                  {alertFeed.map((a) => (
                    <div key={a.id} className="flex gap-3 items-start">
                      <span className={`mt-1 flex-shrink-0 h-2 w-2 rounded-full ${a.level === 'critical' ? 'bg-rose-500' : a.level === 'warning' ? 'bg-amber-500' : 'bg-sky-500'}`} />
                      <div className="min-w-0">
                        <p className="text-sm text-gray-700 dark:text-gray-200 leading-snug">{a.msg}</p>
                        <p className="text-[10px] text-gray-400 mt-0.5">{a.ts}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </GlowCard>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">

              {/* ── System Status Grid ─────────────────────────── */}
              <GlowCard glowColor="indigo" className="!p-5">
                <h2 className="text-base font-bold text-gray-800 dark:text-gray-100 mb-4">System Health</h2>
                <div className="space-y-3">
                  {systems.map((s) => (
                    <div key={s.name} className="flex items-center gap-3">
                      <PulseRing color={s.status === 'online' ? 'emerald' : s.status === 'degraded' ? 'amber' : 'rose'} size="sm" />
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-200 flex-1">{s.name}</span>
                      <span className="text-xs text-gray-400 w-14 text-right">{s.latency}</span>
                      {/* load bar */}
                      <div className="w-20 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-1000 ${s.load > 80 ? 'bg-rose-500' : s.load > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                          style={{ width: `${s.load}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-400 w-8 text-right">{s.load}%</span>
                    </div>
                  ))}
                </div>
              </GlowCard>

              {/* ── Quick Navigation Matrix ─────────────────────── */}
              <GlowCard glowColor="teal" className="!p-5">
                <h2 className="text-base font-bold text-gray-800 dark:text-gray-100 mb-4">Ecosystem Access</h2>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { to: '/tumor-microenvironment', label: 'Tumor\nMicroEnv' },
                    { to: '/genomic-constellation', label: 'Genomic\nConstellation' },
                    { to: '/spatial-transcriptomics', label: 'Spatial\nTranscriptomics' },
                    { to: '/multi-omics', label: 'Multi-Omics\nHub' },
                    { to: '/clinical-workflow', label: 'Workflow\nOrchestrator' },
                    { to: '/trial-matcher', label: 'Trial\nMatcher' },
                    { to: '/drug-mechanisms', label: 'Drug\nMechanisms' },
                    { to: '/tumor-board', label: 'Tumor\nBoard' },
                    { to: '/pathology-lab', label: 'CV Pathology\nLab' },
                    { to: '/guideline-navigator', label: 'NCCN\nGuidelines' },
                    { to: '/population-health', label: 'Population\nHealth' },
                    { to: '/digital-twin', label: 'Digital\nTwin' },
                  ].map((nav) => (
                    <Link
                      key={nav.to}
                      to={nav.to}
                      className="group rounded-xl bg-gray-50 dark:bg-gray-800 p-3 text-center hover:scale-105 transition-transform duration-200 border border-gray-200 dark:border-gray-700 hover:border-violet-300 dark:hover:border-violet-600"
                    >
                      <div className="text-[10px] font-semibold text-gray-600 dark:text-gray-300 whitespace-pre-line leading-tight">{nav.label}</div>
                    </Link>
                  ))}
                </div>
              </GlowCard>
            </div>

            {/* ── Bottom Ribbon — Key Insights ──────────────────── */}
            <GlowCard glowColor="neutral" className="!p-4">
              <div className="flex flex-wrap items-center gap-6 text-xs">
                <div><span className="text-gray-400">Cohort:</span> <span className="font-bold text-gray-700 dark:text-gray-200">BRCA Multi-Institutional (n=2,847)</span></div>
                <div><span className="text-gray-400">Model:</span> <span className="font-bold text-gray-700 dark:text-gray-200">TissueShift World Model v2.1</span></div>
                <div><span className="text-gray-400">Privacy:</span> <span className="font-bold text-gray-700 dark:text-gray-200">ε=1.2 DP Guarantee</span></div>
                <div><span className="text-gray-400">Calibration:</span> <span className="font-bold text-emerald-600">ECE 0.018 ✓</span></div>
                <div><span className="text-gray-400">AUROC:</span> <span className="font-bold text-emerald-600">0.943</span></div>
                <div className="ml-auto"><PulseRing color="emerald" size="sm" label="All systems nominal" /></div>
              </div>
            </GlowCard>
          </div>
        </main>
      </div>
    </div>
  );
}
