import { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';
import AnimatedCounter from '../components/AnimatedCounter';

/* ── Pipeline stages ────────────────────────────────────────────── */
const STAGES = [
  {
    id: 'intake', name: 'Patient Intake', icon: 'PI',
    description: 'Biopsy acquisition, clinical data collection, consent management',
    status: 'active', throughput: 42, avgTime: '2.1h', errorRate: 0.3,
    substeps: ['Consent Form', 'Demographics', 'Clinical History', 'Insurance Verify'],
  },
  {
    id: 'digitize', name: 'Slide Digitization', icon: 'SD',
    description: 'H&E staining, whole-slide scanning at 40x, quality control',
    status: 'active', throughput: 38, avgTime: '45min', errorRate: 1.2,
    substeps: ['Staining Protocol', 'Scanner Queue', '40x Scanning', 'QC Metrics'],
  },
  {
    id: 'preprocess', name: 'AI Preprocessing', icon: 'PP',
    description: 'Tissue detection, tile extraction, normalization, augmentation',
    status: 'active', throughput: 36, avgTime: '8min', errorRate: 0.1,
    substeps: ['Tissue Mask', 'Tile Extraction', 'Stain Normalize', 'Augmentation'],
  },
  {
    id: 'encode', name: 'Feature Encoding', icon: 'FE',
    description: 'Multi-resolution attention encoder, latent space projection',
    status: 'active', throughput: 35, avgTime: '3min', errorRate: 0.0,
    substeps: ['Patch Encode', 'Attention Pool', 'Latent Project', 'Feature Cache'],
  },
  {
    id: 'worldmodel', name: 'World Model', icon: 'WM',
    description: 'Subtype prediction, risk scoring, uncertainty quantification',
    status: 'active', throughput: 35, avgTime: '12s', errorRate: 0.0,
    substeps: ['Subtype Head', 'Survival Head', 'Uncertainty', 'Conformal Set'],
  },
  {
    id: 'twin', name: 'Digital Twin', icon: 'DT',
    description: 'Neural ODE simulation, treatment response, trajectory forecast',
    status: 'active', throughput: 28, avgTime: '45s', errorRate: 0.5,
    substeps: ['ODE Init', 'Drug Params', 'Forward Sim', 'CI Compute'],
  },
  {
    id: 'causal', name: 'Causal Inference', icon: 'CI',
    description: 'Counterfactual analysis, treatment effect estimation, confounding control',
    status: 'idle', throughput: 12, avgTime: '2min', errorRate: 0.8,
    substeps: ['DAG Build', 'IV Estimation', 'Counterfactual', 'Sensitivity'],
  },
  {
    id: 'report', name: 'Report Generation', icon: 'RG',
    description: 'Clinical narrative, recommendations, guideline alignment, PDF export',
    status: 'active', throughput: 30, avgTime: '18s', errorRate: 0.0,
    substeps: ['Template Select', 'AI Narrative', 'Guideline Check', 'PDF Render'],
  },
  {
    id: 'review', name: 'Clinical Review', icon: 'CR',
    description: 'Pathologist sign-off, multi-disciplinary tumor board, EHR integration',
    status: 'active', throughput: 22, avgTime: '4.5h', errorRate: 0.0,
    substeps: ['Queue Assign', 'Path Review', 'Tumor Board', 'EHR Push'],
  },
];

const statusColor = { active: 'emerald', idle: 'amber', error: 'rose', offline: 'gray' };

export default function ClinicalWorkflow() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expanded, setExpanded] = useState(null);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Clinical Workflow Orchestrator
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">End-to-end biopsy-to-treatment pipeline — every stage of clinical AI processing</p>
            </div>

            {/* Summary ribbon */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[
                { label: 'Pipeline Throughput', value: 42, suffix: '/day', glow: 'violet' },
                { label: 'Active Stages', value: STAGES.filter(s => s.status === 'active').length, suffix: `/${STAGES.length}`, glow: 'emerald' },
                { label: 'Avg End-to-End', value: 7.2, suffix: 'h', decimals: 1, glow: 'sky' },
                { label: 'Error Rate', value: 0.32, suffix: '%', decimals: 2, glow: 'rose' },
              ].map((m) => (
                <GlowCard key={m.label} glowColor={m.glow} className="!p-4 text-center">
                  <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">{m.label}</div>
                  <div className="text-2xl font-extrabold text-gray-900 dark:text-white">
                    <AnimatedCounter value={m.value} decimals={m.decimals || 0} suffix={m.suffix} duration={1500} />
                  </div>
                </GlowCard>
              ))}
            </div>

            {/* Pipeline stages */}
            <div className="relative">
              {/* Central vertical connector */}
              <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-violet-400/30 dark:bg-violet-500/30 hidden lg:block" />

              <div className="space-y-4">
                {STAGES.map((stage, idx) => (
                  <div key={stage.id} className="relative lg:pl-20">
                    {/* Stage number badge on the line */}
                    <div className="hidden lg:flex absolute left-5 top-6 w-7 h-7 rounded-full bg-violet-500 items-center justify-center text-white text-xs font-bold shadow-sm z-10">
                      {idx + 1}
                    </div>

                    <GlowCard
                      glowColor={stage.status === 'active' ? 'violet' : 'amber'}
                      className="cursor-pointer !p-5"
                      hover
                    >
                      <div onClick={() => setExpanded(expanded === stage.id ? null : stage.id)}>
                        <div className="flex items-center gap-4 mb-2">
                          <span className="text-sm font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-500/10 w-8 h-8 rounded-lg flex items-center justify-center">{stage.icon}</span>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <h3 className="text-base font-bold text-gray-800 dark:text-gray-100">{stage.name}</h3>
                              <PulseRing color={statusColor[stage.status]} size="sm" />
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{stage.description}</p>
                          </div>
                          <div className="hidden sm:flex gap-6 text-center">
                            <div>
                              <div className="text-lg font-bold text-gray-800 dark:text-gray-100">{stage.throughput}</div>
                              <div className="text-[10px] text-gray-400">per day</div>
                            </div>
                            <div>
                              <div className="text-lg font-bold text-gray-800 dark:text-gray-100">{stage.avgTime}</div>
                              <div className="text-[10px] text-gray-400">avg time</div>
                            </div>
                            <div>
                              <div className={`text-lg font-bold ${stage.errorRate > 0.5 ? 'text-amber-500' : stage.errorRate > 0 ? 'text-emerald-500' : 'text-gray-300 dark:text-gray-600'}`}>{stage.errorRate}%</div>
                              <div className="text-[10px] text-gray-400">error rate</div>
                            </div>
                          </div>
                          <svg className={`w-5 h-5 text-gray-400 transition-transform ${expanded === stage.id ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                        </div>
                      </div>

                      {/* Expanded substeps */}
                      {expanded === stage.id && (
                        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700/60">
                          <div className="flex items-center gap-2 mb-3">
                            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">Sub-processes:</span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {stage.substeps.map((ss, si) => (
                              <div key={ss} className="flex items-center gap-2">
                                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-50 dark:bg-violet-500/10 text-xs font-medium text-gray-700 dark:text-gray-200">
                                  <span className="w-5 h-5 rounded-md bg-violet-500/20 flex items-center justify-center text-[10px] font-bold text-violet-600 dark:text-violet-300">{si + 1}</span>
                                  {ss}
                                </div>
                                {si < stage.substeps.length - 1 && (
                                  <svg className="w-4 h-4 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </GlowCard>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
